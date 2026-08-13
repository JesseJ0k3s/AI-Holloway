"""Turn raw ad copy into structured messaging data.

Two engines, same output shape:

    claude  - real extraction via the Claude API. What we demo.
    mock    - keyword rules, no network. Runs when there is no API key, and
              guarantees the pipeline always produces a dashboard.

Results are cached to data/extracted/ keyed by ad fingerprint, so re-running
the pipeline is free and the classroom demo is reproducible. Commit the cache.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

from . import llm, taxonomy
from .schema import Ad, Extraction

CACHE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "extracted"
)

BATCH_SIZE = 8  # ads per Claude call -- fewer round trips, still fits context


def _catalog(d: Dict[str, str]) -> str:
    return "\n".join("  %s: %s" % (k, v) for k, v in d.items())


# NOTE: this template is filled with str.replace, NOT %-formatting. Ad copy is
# full of percent signs ("25% off", "100% Recycled") and %-formatting turns every
# one of them into a crash at import time. Edit the text freely; no escaping.
_SYSTEM_TEMPLATE = """You are a competitive intelligence analyst who reads advertising copy for a living.

You will be given search ads that fitness apparel brands are currently running. \
For each ad, identify what the brand is CLAIMING, WHO it is talking to, and what \
PROOF it offers. Be a strict reader: judge only what the copy actually says, not \
what you know about the brand from elsewhere. A lululemon ad that only says \
"Free Shipping On Orders $75+" is a price_value ad, not a performance ad.

Claim territories (choose exactly one primary):
{TERRITORIES}

Audiences (choose 0-3; only if the copy actually signals them):
{AUDIENCES}

Proof types (choose 0-3; "none" if the ad asserts without evidence):
{PROOFS}

Tones (choose exactly one):
{TONES}

Rules:
- claim_verbatim and proof_verbatim must be EXACT substrings of the ad copy. Never paraphrase.
- If the copy signals no specific audience, return an empty audiences list. Do not guess.
- confidence is 0.0-1.0. Short or generic ads should score low.
- rationale is one short sentence a marketer could read on a slide.

What the real data actually looks like (read these before you start):

- MANY HEADLINES ARE NOT CLAIMS. Google local ads put the store name in the
  headline ("Nike Brickell", "Under Armour Factory House", "On Store LA Abbot
  Kinney"), and some rows carry only the advertiser name ("lululemon", "ALO").
  A store or brand name is NOT a claim. When the headline is a location or a
  bare brand name, judge the ad entirely on its body copy, and never quote the
  store name as claim_verbatim.

- PROMO-ONLY ADS ARE price_value, nothing else. "Use promo code DAYONE to get
  an extra 25% off on select styles" is price_value with has_offer=true. Do not
  award it performance or style just because it came from an athletic brand.
  Judge the words, not the logo.

- FREE SHIPPING / FREE RETURNS IS A PROOF POINT, NOT A CLAIM TERRITORY, unless
  it is the whole ad. "Free Shipping On Orders Over $150" inside a running ad is
  free_returns_shipping proof supporting a performance claim.

- SOME ADS ARE NOT IN ENGLISH. They were served in the US but written in
  Spanish, German or French. Classify them normally from their actual meaning;
  set confidence <= 0.4 and say so in the rationale.

- BE WILLING TO USE fit_inclusivity AND sustainability_ethics. Explicit sizing
  language ("Plus Size", "tall activewear", "XXS to 4X") is fit_inclusivity.
  Recycled/repair/trade-in language ("Trade In Your Gear For Credit", "100%
  Recycled Outer Fabrics") is sustainability_ethics or durability_quality. These
  territories are under-detected; do not default everything to comfort_feel.

Return ONLY a JSON array, one object per ad, in the same order given:
[{"ad_id":"...","primary_claim_territory":"...","secondary_claim_territories":[],
  "claim_verbatim":"...","audiences":[],"proof_points":[],"proof_verbatim":[],
  "funnel_stage":"awareness|consideration|conversion","tone":"...",
  "has_offer":false,"offer_verbatim":"","confidence":0.0,"rationale":"..."}]"""

SYSTEM = (
    _SYSTEM_TEMPLATE
    .replace("{TERRITORIES}", _catalog(taxonomy.CLAIM_TERRITORIES))
    .replace("{AUDIENCES}", _catalog(taxonomy.AUDIENCES))
    .replace("{PROOFS}", _catalog(taxonomy.PROOF_TYPES))
    .replace("{TONES}", _catalog(taxonomy.TONES))
)


# --------------------------------------------------------------------------
# Cache
# --------------------------------------------------------------------------


def _cache_path(ad_id: str) -> str:
    return os.path.join(CACHE_DIR, "%s.json" % ad_id)


def _load_cached(ad_id: str) -> Optional[Extraction]:
    path = _cache_path(ad_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return Extraction.from_dict(json.load(fh))
    except (json.JSONDecodeError, TypeError):
        return None


def _save_cached(ex: Extraction) -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(_cache_path(ex.ad_id), "w", encoding="utf-8") as fh:
        json.dump(ex.to_dict(), fh, indent=2, ensure_ascii=False)


# --------------------------------------------------------------------------
# Public entry point
# --------------------------------------------------------------------------


def extract_all(
    ads: List[Ad],
    engine: str = "auto",
    use_cache: bool = True,
    verbose: bool = True,
) -> List[Extraction]:
    if engine == "auto":
        engine = "claude" if llm.have_key() else "mock"
        if verbose and engine == "mock":
            print("  no ANTHROPIC_API_KEY found -> using mock engine")

    results: List[Extraction] = []
    todo: List[Ad] = []

    for ad in ads:
        cached = _load_cached(ad.ad_id) if use_cache else None
        if cached is not None:
            results.append(cached)
        else:
            todo.append(ad)

    if verbose:
        print("  %d cached, %d to extract (engine=%s)" % (len(results), len(todo), engine))

    for i in range(0, len(todo), BATCH_SIZE):
        batch = todo[i : i + BATCH_SIZE]
        if engine == "claude":
            try:
                batch_out = _extract_claude(batch)
            except llm.LLMUnavailable as e:
                if verbose:
                    print("  ! Claude unavailable (%s) -> mock for this batch" % e)
                batch_out = [_extract_mock(a) for a in batch]
        else:
            batch_out = [_extract_mock(a) for a in batch]

        for ex in batch_out:
            _save_cached(ex)
            results.append(ex)

        if verbose:
            print("  extracted %d/%d" % (min(i + BATCH_SIZE, len(todo)), len(todo)))

    return results


# --------------------------------------------------------------------------
# Claude engine
# --------------------------------------------------------------------------


def _extract_claude(batch: List[Ad]) -> List[Extraction]:
    lines = []
    for ad in batch:
        lines.append(
            "---\nad_id: %s\nbrand: %s\nheadline: %s\nbody: %s"
            % (ad.ad_id, ad.brand, ad.headline, ad.body or "(none)")
        )
    prompt = "Analyze these %d ads.\n\n%s" % (len(batch), "\n".join(lines))

    raw = llm.complete_json(prompt, system=SYSTEM, max_tokens=4000)
    if isinstance(raw, dict):
        raw = raw.get("ads") or raw.get("results") or [raw]

    by_id = {str(r.get("ad_id")): r for r in raw if isinstance(r, dict)}
    out: List[Extraction] = []

    for idx, ad in enumerate(batch):
        # Prefer id match; fall back to positional if the model dropped ids.
        r = by_id.get(ad.ad_id) or (raw[idx] if idx < len(raw) and isinstance(raw[idx], dict) else {})
        out.append(_coerce(r, ad, engine="claude"))
    return out


def _coerce(r: Dict[str, Any], ad: Ad, engine: str) -> Extraction:
    """Force whatever the model returned into a valid Extraction."""
    territory = r.get("primary_claim_territory", "unclassified")
    if territory not in taxonomy.CLAIM_TERRITORIES:
        territory = "unclassified"

    stage = r.get("funnel_stage", "consideration")
    if stage not in taxonomy.FUNNEL_STAGES:
        stage = "consideration"

    tone = r.get("tone", "unclassified")
    if tone not in taxonomy.TONES:
        tone = "unclassified"

    def as_list(v: Any) -> List[str]:
        if isinstance(v, list):
            return [str(x) for x in v if x]
        return [str(v)] if v else []

    try:
        conf = float(r.get("confidence", 0.0))
    except (TypeError, ValueError):
        conf = 0.0

    return Extraction(
        ad_id=ad.ad_id,
        brand=ad.brand,
        primary_claim_territory=territory,
        secondary_claim_territories=taxonomy.validate(
            "territory", as_list(r.get("secondary_claim_territories"))
        ),
        claim_verbatim=str(r.get("claim_verbatim", "") or "")[:300],
        audiences=taxonomy.validate("audience", as_list(r.get("audiences"))),
        proof_points=taxonomy.validate("proof", as_list(r.get("proof_points"))),
        proof_verbatim=as_list(r.get("proof_verbatim"))[:3],
        funnel_stage=stage,
        tone=tone,
        has_offer=bool(r.get("has_offer", False)),
        offer_verbatim=str(r.get("offer_verbatim", "") or "")[:200],
        confidence=max(0.0, min(1.0, conf)),
        engine=engine,
        rationale=str(r.get("rationale", "") or "")[:300],
    )


# --------------------------------------------------------------------------
# Mock engine -- keyword rules, no network
# --------------------------------------------------------------------------

# Order is priority: the first cue that matches wins the primary territory.
# A sale ad is a sale ad even if it also says "engineered", so promo sits at
# the top; the broad, easily-triggered cues (performance, style) sit at the
# bottom so they only win when nothing more specific fired.
_TERRITORY_CUES = [
    ("price_value", r"\b(sale|\d+%\s*off|save|deal|from \$|discount|clearance|outlet)\b"),
    ("sustainability_ethics", r"\b(recycl|organic|sustainab|planet|carbon|fair trade|b corp|responsib)\w*"),
    ("durability_quality", r"\b(lifetime|guarantee|built to last|durab|repair|warrant)\w*"),
    ("heritage_craft", r"(\bsince \d{4}|\b(heritage|craft|handmade|founded|made in usa)\w*)"),
    ("fit_inclusivity", r"\b(inclusive|every body|extended size|petite|curve|xxs|4x|wide)\w*"),
    ("newness_seasonal", r"\b(new arrival|just dropped|new in|shop new|latest|limited quantit)\w*"),
    ("community_identity", r"\b(community|run club|join the|movement|together)\w*"),
    ("convenience_service", r"\b(free returns|easy exchange|fast shipping|try at home|cancel anytime)\b"),
    ("comfort_feel", r"\b(comfort|softest|soft|buttery|weightless|second skin|cozy|breathab)\w*"),
    ("technical_innovation", r"\b(engineered|technology|patent|innovat|four-way stretch|sweat-wicking)\w*"),
    ("performance", r"\b(performance|train|training|run|running|racer|marathon|faster|stronger|endurance|athlete)\w*"),
    ("style_versatility", r"\b(style|versatile|everyday|gym to street|wear anywhere|live in)\w*"),
]

_PROOF_CUES = [
    ("free_returns_shipping", r"\b(free (shipping|returns|exchanges))\b"),
    ("customer_reviews", r"\b(\d[\d,\.]*\s*(reviews|ratings)|\d(\.\d)?\s*stars?)\b"),
    ("social_proof_scale", r"\b(bestsell|#1|most popular|million sold|top rated)\w*"),
    ("guarantee_warranty", r"\b(guarantee|warrant|ironclad)\w*"),
    ("certification", r"\b(b corp|bluesign|fair trade|oeko-tex|certified)\b"),
    ("scarcity_urgency", r"\b(limited|ends|while supplies|back in stock|last chance)\w*"),
    ("technical_spec", r"\b(\d+\s*(g|oz|mm|denier)|four-way stretch|nylon|merino)\b"),
    ("athlete_pro", r"\b(athlete|olympi|pro |team |coach)\w*"),
    ("awards_press", r"\b(award|best of|as seen in|voted)\w*"),
]

_AUDIENCE_CUES = [
    ("runners", r"\b(run|running|runner|marathon|5k|10k|race|trail run)\w*"),
    ("yoga_studio", r"\b(yoga|pilates|barre|studio|mat|flow)\w*"),
    ("strength_gym", r"\b(gym|lift|lifting|strength|training|workout)\w*"),
    ("outdoor_alpine", r"\b(hike|hiking|climb|alpine|mountain|ski|trail|outdoor)\w*"),
    ("athleisure_lifestyle", r"\b(everyday|lounge|travel|commute|off-duty|athleisure)\w*"),
    ("women_explicit", r"\b(women|women's|her|she)\b"),
    ("men_explicit", r"\b(men|men's|him|his)\b"),
    ("gift_givers", r"\b(gift|gifts|gifting|holiday)\w*"),
    ("value_seekers", r"\b(sale|deal|save|discount|outlet)\w*"),
]


def _match(text: str, cues: List[tuple]) -> List[str]:
    hits = []
    for label, pattern in cues:
        if re.search(pattern, text, re.IGNORECASE):
            hits.append(label.rstrip("_"))
    return hits


def _extract_mock(ad: Ad) -> Extraction:
    text = ad.full_text
    territories = _match(text, _TERRITORY_CUES)
    proofs = _match(text, _PROOF_CUES)
    audiences = _match(text, _AUDIENCE_CUES)

    primary = territories[0] if territories else "unclassified"
    has_offer = bool(re.search(r"\b(\d+%\s*off|sale|save|free shipping|from \$)\b", text, re.I))

    return Extraction(
        ad_id=ad.ad_id,
        brand=ad.brand,
        primary_claim_territory=primary,
        secondary_claim_territories=territories[1:3],
        claim_verbatim=ad.headline[:300],
        audiences=audiences[:3],
        proof_points=proofs[:3] or ["none"],
        proof_verbatim=[],
        funnel_stage="conversion" if has_offer else "consideration",
        tone="urgent_promotional" if has_offer else "unclassified",
        has_offer=has_offer,
        offer_verbatim="",
        confidence=0.35 if primary != "unclassified" else 0.1,
        engine="mock",
        rationale="Keyword-rule fallback. Re-run with ANTHROPIC_API_KEY for a real read.",
    )
