"""Live Google Ads Transparency Center pull via SerpApi.

WHY THIS AND NOT A SCRAPER
--------------------------
Google's Ads Transparency Center has no official public API, and its web app is
backed by a private RPC endpoint. Hitting that endpoint directly violates
Google's Terms of Service and breaks without warning. SerpApi is a commercial
service licensed to do this and exposes a documented, stable API.

TWO CALLS PER AD -- THIS IS NOT OPTIONAL
----------------------------------------
The listing endpoint (`google_ads_transparency_center`) does NOT return ad copy.
Text ads come back as a rendered PNG in an `image` field -- the same iframe wall
you hit trying to read the site by hand. Only the details endpoint
(`google_ads_transparency_center_ad_details`) returns real strings:
`headline`, `snippet`, `call_to_action`, sitelinks.

So the flow is:

    1. list creatives for an advertiser  -> ad_creative_id[]     (1 search)
    2. details for each creative          -> headline + snippet   (1 search each)

SEARCH BUDGET (free tier = 250 searches/month)
----------------------------------------------
    12 brands x 1 listing call        =  12
    12 brands x 10 ads x 1 detail call = 120
                                        ---
                                        132 of 250

That fits, but a second full run does not. **Every raw response is cached to
data/serpapi_cache/ and the cache is committed**, so re-running the pipeline
costs zero searches. Use --no-cache only when you genuinely want fresh data.

    export SERPAPI_KEY=...
    python3 -m teardown ingest --source serpapi --save
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from ..schema import Ad
from ..taxonomy import BRANDS, canonical_brand

BASE = "https://serpapi.com/search.json"

# SerpApi wants numeric region codes here, not ISO country codes -- passing
# "US" returns HTTP 400 "Unsupported `US` region parameter."
# Full list: https://serpapi.com/google-ads-transparency-center-regions
REGION_CODES = {
    "US": "2840",
    "CA": "2124",
    "GB": "2826",
    "UK": "2826",
    "AU": "2036",
    "DE": "2276",
}


def region_code(region: str) -> str:
    """Accept either 'US' or a raw numeric code."""
    r = (region or "US").strip()
    if r.isdigit():
        return r
    code = REGION_CODES.get(r.upper())
    if not code:
        raise SystemExit(
            "Unknown region %r. Use a code from "
            "https://serpapi.com/google-ads-transparency-center-regions "
            "(US = 2840), or add it to REGION_CODES." % region
        )
    return code

CACHE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "serpapi_cache",
)

# Counts real API calls in this process so we can report budget use.
_searches_used = 0


def _cache_key(params: Dict[str, str]) -> str:
    safe = {k: v for k, v in params.items() if k != "api_key"}
    raw = json.dumps(safe, sort_keys=True)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _get(params: Dict[str, str], use_cache: bool = True) -> Dict[str, Any]:
    """One SerpApi call, cached on disk by request shape."""
    global _searches_used

    key = _cache_key(params)
    path = os.path.join(CACHE_DIR, "%s.json" % key)

    if use_cache and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    url = BASE + "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        raise SystemExit("SerpApi HTTP %s: %s" % (e.code, detail))

    _searches_used += 1
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    return payload


def searches_used() -> int:
    return _searches_used


# --------------------------------------------------------------------------


def fetch(
    brands: Optional[List[str]] = None,
    region: str = "US",
    limit_per_brand: int = 10,
    use_cache: bool = True,
    verbose: bool = True,
    **_: object
) -> List[Ad]:
    key = os.environ.get("SERPAPI_KEY")
    if not key:
        raise SystemExit(
            "SERPAPI_KEY is not set.\n"
            "  Get a free key at https://serpapi.com/users/sign_up, then:\n"
            "    export SERPAPI_KEY=...\n"
            "  Or run with --source manual / --source fixtures instead."
        )

    targets = brands or list(BRANDS.keys())
    rcode = region_code(region)
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    out: List[Ad] = []

    for brand in targets:
        advertiser_id = str(BRANDS.get(brand, {}).get("advertiser_id") or "")

        # Step 1 -- list this advertiser's text creatives.
        params = {
            "engine": "google_ads_transparency_center",
            "region": rcode,
            "creative_format": "text",
            "api_key": key,
        }
        if advertiser_id:
            params["advertiser_id"] = advertiser_id
        else:
            # Falling back to text search is unreliable: it happily returns
            # "Alo Yoga Mexico" for "Alo Yoga". Prefer a pinned advertiser_id
            # in taxonomy.py -- see docs/DATA_CAPTURE.md.
            params["text"] = brand
            if verbose:
                print("  ! %-14s no advertiser_id pinned; using text search (may pick the wrong entity)" % brand)

        listing = _get(params, use_cache=use_cache)
        creatives = listing.get("ad_creatives", []) or []
        if not creatives and verbose:
            print("  %-14s no text creatives returned" % brand)

        kept = 0
        for row in creatives[:limit_per_brand]:
            cid = str(row.get("ad_creative_id") or "")
            aid = str(row.get("advertiser_id") or advertiser_id or "")
            if not cid or not aid:
                continue

            # Step 2 -- the only place the actual ad copy lives.
            detail = _get(
                {
                    "engine": "google_ads_transparency_center_ad_details",
                    "advertiser_id": aid,
                    "creative_id": cid,
                    "region": rcode,
                    "api_key": key,
                },
                use_cache=use_cache,
            )

            ad = _to_ad(row, detail, brand, aid, cid, now)
            if ad is not None:
                out.append(ad)
                kept += 1

        if verbose:
            print("  %-14s %d ads" % (brand, kept))

    if verbose:
        print("  (%d SerpApi searches used this run)" % _searches_used)
    return out


def _to_ad(
    listing_row: Dict[str, Any],
    detail: Dict[str, Any],
    brand: str,
    advertiser_id: str,
    creative_id: str,
    captured_at: str,
) -> Optional[Ad]:
    """Merge listing metadata + detail copy into one Ad.

    The details endpoint returns `ad_creatives` as a list of VARIANTS of the
    same ad. Most variants are image-only ({"image": ...}); the useful ones
    carry `title` + `snippet`. Roughly half of all creatives yield no text at
    all -- those are dropped rather than guessed at.

    Note `title` is the advertiser display name ("lululemon"), not the search
    headline you see on the Transparency Center page. The actual claim lives in
    `snippet`, which is what the extraction cares about.
    """
    variants = detail.get("ad_creatives") or []
    if isinstance(variants, dict):
        variants = [variants]

    title = ""
    snippets: List[str] = []
    visible_link = ""
    for v in variants:
        if not isinstance(v, dict):
            continue
        s = (v.get("snippet") or "").strip()
        if s and s not in snippets:
            snippets.append(s)
        if not title:
            title = (v.get("title") or "").strip()
        if not visible_link:
            visible_link = (v.get("visible_link") or "").strip()
        # Sitelinks are real ad copy too and often carry the proof points.
        for k in ("sitelink_texts", "sitelink_descriptions"):
            extra = v.get(k)
            if isinstance(extra, list):
                for x in extra:
                    x = str(x).strip()
                    if x and x not in snippets:
                        snippets.append(x)

    headline = title
    body = " ".join(snippets).strip()

    if not body:
        return None  # image-only creative: tells us nothing about messaging

    info = detail.get("search_information") or {}
    advertiser = (
        listing_row.get("advertiser") or info.get("ad_funded_by") or brand
    )

    return Ad(
        brand=canonical_brand(advertiser) if advertiser else brand,
        platform="google_search",
        headline=headline,
        body=body,
        ad_id=creative_id,
        advertiser_id=advertiser_id,
        cta=None,
        landing_url=visible_link or listing_row.get("target_domain"),
        creative_type="text",
        media_url=listing_row.get("image"),
        first_seen=_ts(listing_row.get("first_shown")),
        last_seen=_ts(listing_row.get("last_shown")),
        still_running=True,
        regions=["US"],
        provenance="api",
        captured_at=captured_at,
        source_url="https://adstransparency.google.com/advertiser/%s/creative/%s?region=US"
        % (advertiser_id, creative_id),
        notes="serpapi:ad_details",
    )


def _ts(v: Any) -> Optional[str]:
    """first_shown / last_shown come back as Unix timestamps, not dates."""
    if v in (None, ""):
        return None
    try:
        return dt.datetime.utcfromtimestamp(int(v)).strftime("%Y-%m-%d")
    except (ValueError, TypeError, OSError):
        return str(v)


def _first(d: Dict[str, Any], keys: List[str]) -> str:
    for k in keys:
        v = d.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
        if isinstance(v, list) and v:
            return " ".join(str(x) for x in v if x).strip()
    return ""
