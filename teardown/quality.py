"""Data quality checks on captured ads.

Written after WS2 read the first 79 real ads and found that a large share of
them are not what the matrix assumes they are. Run this BEFORE trusting any
analysis:

    python3 -m teardown quality

The four problems it catches, all found in the real capture:

1. NON-ENGLISH ADS. The Transparency Center's region filter is about where an
   ad was *served*, not what language it is in. Arc'teryx served French, German
   and Spanish copy into the US; On served Spanish. Classifying those against an
   English taxonomy produces confident nonsense.

2. STORE-LOCATION ADS. Google local ads put the STORE NAME in the headline
   ("Nike Brickell", "Under Armour Factory House"). That is not a claim, and
   treating it as one pollutes the headline field for a third of the set.

3. NEAR-DUPLICATE COPY ACROSS STORES. Nike ran ONE message -- "Use promo code
   DAYONE to get an extra 25% off on select styles." -- across six different
   store locations. Deduping on headline+body keeps all six, because the store
   names differ, so Nike looks like six ads when it has one message.

4. CROSS-BRAND BLEED. An advertiser account can run ads for sibling brands.
   Just Fabulous, Inc. (Fabletics) served a Savage X Fenty ad, which would land
   in the Fabletics row of the matrix.

Nothing here deletes data. Every issue is reported, and `flag()` annotates the
Ad so the dashboard and the extractor can decide what to do.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Dict, List, Tuple

from .schema import Ad
from .taxonomy import BRANDS

# --------------------------------------------------------------------------
# 1. Language
# --------------------------------------------------------------------------
# No langdetect dependency. Function words + diacritics are plenty to separate
# English ad copy from French/German/Spanish ad copy at this length.

_LANG_CUES = {
    "fr": r"\b(pour|avec|sur|nos|votre|qui|des|les|une|tout|fiable|terrain)\b",
    "de": r"\b(und|mit|die|der|das|für|über|dich|deine|leichte|hinaus)\b",
    "es": r"\b(para|con|que|nuestras|sea|cual|una|los|las|más|diseño|comodidad)\b",
    "it": r"\b(per|con|che|della|nostri|tutti)\b",
}
_DIACRITIC = re.compile(r"[àâäçéèêëîïôöùûüÿñáíóúÀÂÄÇÉÈÊËÎÏÔÖÙÛÜÑÁÍÓÚ]")


def detect_language(text: str) -> str:
    """Return 'en' or a best-guess non-English code."""
    t = (text or "").lower()
    scores = {code: len(re.findall(pat, t)) for code, pat in _LANG_CUES.items()}
    best = max(scores, key=lambda k: scores[k]) if scores else "en"
    if scores.get(best, 0) >= 2:
        return best
    # A couple of diacritics with even one cue word is enough.
    if _DIACRITIC.search(text or "") and scores.get(best, 0) >= 1:
        return best
    return "en"


# --------------------------------------------------------------------------
# 2. Store-location ads
# --------------------------------------------------------------------------

# Retail-format words that only ever appear in a physical location's name.
_STORE_CUES = re.compile(
    r"\b(factory house|factory store|clearance store|outlet|flagship store)\b",
    re.IGNORECASE,
)

# "Official Site" / "Official Store" are search-ad headline conventions, NOT
# store locations. Without this exclusion the check flags real ad copy like
# "Gymshark Official Store - Gym Clothes Store" and becomes useless noise.
_AD_HEADLINE_CUES = re.compile(r"official (site|store)|\|", re.IGNORECASE)


def is_brand_only_headline(ad: Ad) -> bool:
    """Headline is just the advertiser name.

    Expected for SerpApi rows -- its `title` field is the advertiser display
    name, not the search headline. Not a defect, but it means the headline
    carries no claim and the body is doing all the work.
    """
    h = re.sub(r"[^a-z0-9 ]", "", (ad.headline or "").lower()).strip()
    b = re.sub(r"[^a-z0-9 ]", "", ad.brand.lower()).strip()
    return bool(h) and (h == b or h in b or b in h) and len(h.split()) <= 3


def is_store_headline(ad: Ad) -> bool:
    """True when the headline is a physical retail location, not ad copy."""
    h = (ad.headline or "").strip()
    if not h or is_brand_only_headline(ad):
        return False
    if _AD_HEADLINE_CUES.search(h):
        return False  # real ad headline that happens to contain "Store"
    if not h.lower().startswith(ad.brand.lower().split()[0].lower()):
        return False
    if _STORE_CUES.search(h):
        return True
    # "Nike Brickell", "Arc'teryx Oslo", "Patagonia Fulton Market" --
    # brand + place name, no sentence punctuation, no verb-y claim.
    rest = h[len(ad.brand.split()[0]):].strip(" -–—")
    return bool(rest) and len(rest.split()) <= 4 and not re.search(r"[.!?|,]", rest)


# --------------------------------------------------------------------------
# 3 & 4. Duplicates and cross-brand bleed
# --------------------------------------------------------------------------


def body_key(ad: Ad) -> str:
    """Dedupe key that ignores the store-name headline."""
    return re.sub(r"\s+", " ", (ad.body or ad.headline or "").strip().lower())


_KNOWN_SIBLINGS = {
    "Fabletics": ["savage x fenty", "savage x", "justfab", "shoedazzle", "fabkids"],
}


def cross_brand_hits(ad: Ad) -> List[str]:
    """Sibling brands mentioned in copy attributed to this brand."""
    text = ad.full_text.lower()
    return [s for s in _KNOWN_SIBLINGS.get(ad.brand, []) if s in text]


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------


def audit(ads: List[Ad]) -> Dict[str, object]:
    non_english: List[Tuple[Ad, str]] = []
    store_ads: List[Ad] = []
    brand_only: List[Ad] = []
    cross_brand: List[Tuple[Ad, List[str]]] = []

    by_body: Dict[str, List[Ad]] = defaultdict(list)
    for ad in ads:
        lang = detect_language(ad.full_text)
        if lang != "en":
            non_english.append((ad, lang))
        if is_store_headline(ad):
            store_ads.append(ad)
        if is_brand_only_headline(ad):
            brand_only.append(ad)
        hits = cross_brand_hits(ad)
        if hits:
            cross_brand.append((ad, hits))
        by_body[body_key(ad)].append(ad)

    dupes = {k: v for k, v in by_body.items() if len(v) > 1}

    # How many DISTINCT messages does each brand actually have?
    distinct_by_brand: Dict[str, int] = {}
    total_by_brand: Counter = Counter()
    seen: Dict[str, set] = defaultdict(set)
    for ad in ads:
        total_by_brand[ad.brand] += 1
        seen[ad.brand].add(body_key(ad))
    for b in total_by_brand:
        distinct_by_brand[b] = len(seen[b])

    return {
        "n_ads": len(ads),
        "non_english": non_english,
        "store_ads": store_ads,
        "brand_only": brand_only,
        "cross_brand": cross_brand,
        "duplicate_groups": dupes,
        "total_by_brand": dict(total_by_brand),
        "distinct_by_brand": distinct_by_brand,
    }


def flag(ads: List[Ad]) -> List[Ad]:
    """Annotate ads in place with quality notes. Nothing is dropped here."""
    for ad in ads:
        notes = []
        lang = detect_language(ad.full_text)
        if lang != "en":
            notes.append("lang=%s" % lang)
        if is_store_headline(ad):
            notes.append("store_headline")
        hits = cross_brand_hits(ad)
        if hits:
            notes.append("cross_brand=%s" % ",".join(hits))
        if notes:
            ad.notes = (ad.notes + " | " if ad.notes else "") + " ".join(notes)
    return ads


def usable(ads: List[Ad]) -> List[Ad]:
    """The subset safe to analyse: English, not a sibling brand, deduped by body.

    Store-location ads are KEPT -- their body copy is still real messaging, and
    dropping them would delete a third of the set. Only the headline is junk.
    """
    out: List[Ad] = []
    seen: Dict[str, set] = defaultdict(set)
    for ad in ads:
        if detect_language(ad.full_text) != "en":
            continue
        if cross_brand_hits(ad):
            continue
        key = body_key(ad)
        if key in seen[ad.brand]:
            continue
        seen[ad.brand].add(key)
        out.append(ad)
    return out
