"""The messaging taxonomy for fitness apparel.

This is the strategic heart of the product and it is deliberately plain Python
so a non-engineer can own it. Editing the wording here changes what the whole
system looks for -- no other file needs to change.

Rule of thumb: territories should be MECE enough that a human marketer would
put a given ad in exactly one of them. If two categories keep fighting over the
same ads, merge them.
"""

from __future__ import annotations

from typing import Dict, List

# --------------------------------------------------------------------------
# Claim territories -- the columns of the messaging matrix
# --------------------------------------------------------------------------

CLAIM_TERRITORIES: Dict[str, str] = {
    "performance": "Makes you faster/stronger/better at the activity itself.",
    "comfort_feel": "How it feels on the body: softness, weightlessness, buttery, second-skin.",
    "style_versatility": "How it looks; wearable beyond the workout; goes gym-to-street.",
    "fit_inclusivity": "Fit quality, size range, body diversity, 'fits every body'.",
    "technical_innovation": "Proprietary fabric/engineering as the hero: named tech, patents.",
    "durability_quality": "Built to last, repairable, lifetime guarantee, cost-per-wear.",
    "sustainability_ethics": "Recycled/organic materials, carbon, labor practices, B Corp.",
    "community_identity": "Who you become / who you belong to. Tribe, movement, run club.",
    "heritage_craft": "Founded in, made by, obsessive craft, authenticity, origin story.",
    "price_value": "Discounts, sales, free shipping, bundles, 'from $X', affordability.",
    "convenience_service": "Free returns, fast shipping, easy exchange, try-before-you-buy.",
    "newness_seasonal": "Just dropped, new arrivals, seasonal collection, limited edition.",
}

# --------------------------------------------------------------------------
# Audiences -- the rows of the audience matrix
# --------------------------------------------------------------------------

AUDIENCES: Dict[str, str] = {
    "runners": "Road/trail running, marathon training, race prep.",
    "yoga_studio": "Yoga, pilates, barre, studio fitness.",
    "strength_gym": "Lifting, CrossFit, bodybuilding, gym training.",
    "outdoor_alpine": "Hiking, climbing, skiing, mountain and technical outdoor.",
    "athleisure_lifestyle": "Everyday wear, travel, work-from-home, brunch-to-gym.",
    "team_field_sport": "Football, basketball, soccer, training for team sports.",
    "women_explicit": "Copy explicitly addressed to women.",
    "men_explicit": "Copy explicitly addressed to men.",
    "plus_extended_size": "Explicitly addresses extended or inclusive sizing.",
    "gen_z_young": "Youth-coded language, trend-driven, campus, TikTok-native.",
    "value_seekers": "Deal-motivated, sale-driven, budget-conscious.",
    "gift_givers": "Gifting occasions, holiday, 'gifts for'.",
}

# --------------------------------------------------------------------------
# Proof points -- what a brand offers as evidence for its claim
# --------------------------------------------------------------------------

PROOF_TYPES: Dict[str, str] = {
    "technical_spec": "Named fabric/tech, weights, measurements, construction detail.",
    "athlete_pro": "Pro athletes, teams, Olympians, coaches as validation.",
    "awards_press": "Editorial awards, 'best of' lists, magazine mentions.",
    "customer_reviews": "Star ratings, review counts, quoted customers.",
    "social_proof_scale": "Bestseller, 'X million sold', 'most popular', waitlists.",
    "certification": "B Corp, bluesign, Fair Trade, OEKO-TEX, recycled content claims.",
    "guarantee_warranty": "Lifetime warranty, quality promise, repair programs.",
    "free_returns_shipping": "Free shipping/returns/exchanges as risk reversal.",
    "comparison": "Explicit or implied comparison to a competitor or category.",
    "founder_origin": "Founder story, place of origin, years in business.",
    "scarcity_urgency": "Limited stock, ends soon, back in stock, drop timing.",
    "none": "Asserts a claim with no evidence offered.",
}

# --------------------------------------------------------------------------
# Secondary dimensions
# --------------------------------------------------------------------------

TONES: Dict[str, str] = {
    "performance_serious": "Earnest, athletic, achievement-focused.",
    "aspirational_lifestyle": "Elevated, calm, identity-forward.",
    "playful_irreverent": "Jokes, wink, casual voice.",
    "technical_authoritative": "Spec-forward, engineer's voice.",
    "values_driven": "Mission, planet, ethics-forward.",
    "urgent_promotional": "Sale-driven, exclamation-heavy, deadline pressure.",
    "warm_inclusive": "Welcoming, body-positive, 'everyone' framing.",
}

FUNNEL_STAGES: List[str] = ["awareness", "consideration", "conversion"]

# --------------------------------------------------------------------------
# The competitive set
# --------------------------------------------------------------------------
# `aliases` match advertiser names as they appear in the Transparency Center,
# which are often legal entity names.
#
# `advertiser_id` is the Google advertiser ID (the AR... in the Transparency
# Center URL). PIN THESE. Searching by brand name picks the wrong legal entity
# distressingly often -- searching "Alo Yoga" returns "Alo Yoga Mexico" first,
# and "Nike" returns an account flagged "multiple advertiser accounts have a
# similar name". A wrong entity silently produces a matrix for the wrong market.
#
# To fill one in: open adstransparency.google.com, search the brand, click the
# result whose "Based in" and ad count look right, and copy the AR id out of the
# address bar. See docs/DATA_CAPTURE.md.

BRANDS: Dict[str, Dict[str, object]] = {
    "lululemon": {
        "aliases": ["lululemon athletica", "lululemon usa"],
        "archetype": "premium studio incumbent",
        "advertiser_id": "AR01614014350098432001",  # lululemon athletica canada inc. (CA)
    },
    "Nike": {
        "aliases": ["nike", "nike inc", "nike usa"],
        "archetype": "global performance giant",
        "advertiser_id": "AR16735076323512287233",  # Nike, Inc. (US) -- flagged multi-account; this one runs all 40 loaded ads
    },
    "Alo Yoga": {
        "aliases": ["alo", "alo yoga", "color image apparel"],
        "archetype": "aesthetic/celebrity yoga",
        # NOT "Alo Yoga Mexico", which is what searching "Alo Yoga" returns.
        "advertiser_id": "AR10871259591425916929",  # COLOR IMAGE APPAREL, INC. (US), ~3K ads
    },
    "Vuori": {
        "aliases": ["vuori", "vuori clothing"],
        "archetype": "comfort-first challenger",
        "advertiser_id": "AR04810021938799837185",  # Vuori, Inc. (US), ~2K ads
    },
    "On": {
        "aliases": ["on running", "on ag", "on holding"],
        "archetype": "technical run insurgent",
        "advertiser_id": "AR01566006373894848513",  # On AG (CH), ~3.8K ads
    },
    "Under Armour": {
        "aliases": ["under armour", "ua"],
        "archetype": "performance value",
        "advertiser_id": "AR16916677161513910273",  # Under Armour, Inc. (US) -- 3 accounts; this runs 37 of 40
    },
    "Gymshark": {
        "aliases": ["gymshark", "gym shark"],
        "archetype": "gym-native community brand",
        "advertiser_id": "AR01822115136316375041",  # Gymshark USA Inc (US), ~5K ads -- not Gymshark Ltd (UK, ~16)
    },
    "Arc'teryx": {
        "aliases": ["arcteryx", "arc'teryx", "amer sports"],
        "archetype": "alpine technical premium",
        "advertiser_id": "AR17137590075693989889",  # ARC'TERYX Equipment, Amer Sports Canada Inc. (CA)
    },
    "Patagonia": {
        "aliases": ["patagonia", "patagonia inc"],
        "archetype": "values-led outdoor",
        "advertiser_id": "AR13494478831020408833",  # PATAGONIA, INC. (US)
    },
    "Tracksmith": {
        "aliases": ["tracksmith"],
        "archetype": "running heritage niche",
        "advertiser_id": "AR02037031623316209665",  # Tracksmith Corporation (US), ~600 ads
    },
    "New Balance": {
        "aliases": ["new balance", "new balance athletics"],
        "archetype": "heritage crossover",
        # Two US entities exist; "New Balance Athletics, Inc." has only ~55 ads.
        "advertiser_id": "AR04323445746671026177",  # New Balance Athletic Shoe, Inc. (US), ~2K ads
    },
    "Fabletics": {
        "aliases": ["fabletics", "techstyle", "just fabulous"],
        "archetype": "membership value",
        # Searching "Fabletics" only finds FABLETICS LTD (UK, ~5 ads). The US
        # advertiser is the JustFab/TechStyle operating entity.
        "advertiser_id": "AR03556834903704207361",  # Just Fabulous, Inc. (US), ~3K ads
    },
}


def canonical_brand(name: str) -> str:
    """Map a messy advertiser name onto our canonical brand label."""
    n = (name or "").strip().lower()
    for brand, meta in BRANDS.items():
        if n == brand.lower():
            return brand
        for alias in meta["aliases"]:  # type: ignore[index]
            if alias in n or n in alias:
                return brand
    return name.strip() or "unknown"


def validate(kind: str, values: List[str]) -> List[str]:
    """Drop any label the model invented that is not in our taxonomy.

    Keeps the matrix from growing junk columns when the LLM gets creative.
    """
    allowed = {
        "territory": CLAIM_TERRITORIES,
        "audience": AUDIENCES,
        "proof": PROOF_TYPES,
        "tone": TONES,
    }[kind]
    return [v for v in values if v in allowed]
