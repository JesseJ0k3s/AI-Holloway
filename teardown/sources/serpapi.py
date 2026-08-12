"""Live Google Ads Transparency Center pull via SerpApi.

WHY THIS AND NOT A SCRAPER
--------------------------
Google's Ads Transparency Center has no official public API, and its web app is
backed by a private RPC endpoint. Hitting that endpoint directly violates
Google's Terms of Service and breaks without warning. SerpApi is a commercial
service that is licensed to do this and exposes a documented, stable API. Free
tier is ~100 searches/month, which covers 12 brands with room to re-run.

    export SERPAPI_KEY=...
    python3 -m teardown ingest --source serpapi --save

Two-step flow, mirroring how the Transparency Center itself works:
  1. Look up the brand's advertiser_id  (engine=google_ads_transparency_center)
  2. Pull that advertiser's live creatives

If you have no key, use --source fixtures or --source manual instead. This
module never fabricates ads; if the API returns nothing, you get nothing.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from ..schema import Ad
from ..taxonomy import BRANDS, canonical_brand

BASE = "https://serpapi.com/search.json"


def _get(params: Dict[str, str]) -> Dict[str, Any]:
    url = BASE + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch(
    brands: Optional[List[str]] = None,
    region: str = "US",
    limit_per_brand: int = 25,
    verbose: bool = True,
    **_: object
) -> List[Ad]:
    key = os.environ.get("SERPAPI_KEY")
    if not key:
        raise SystemExit(
            "SERPAPI_KEY is not set.\n"
            "  Get a free key at https://serpapi.com, then:  export SERPAPI_KEY=...\n"
            "  Or run with --source fixtures / --source manual instead."
        )

    targets = brands or list(BRANDS.keys())
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    out: List[Ad] = []

    for brand in targets:
        try:
            payload = _get(
                {
                    "engine": "google_ads_transparency_center",
                    "text": brand,
                    "region": region,
                    "api_key": key,
                }
            )
        except Exception as e:
            if verbose:
                print("  ! %-14s lookup failed: %s" % (brand, e))
            continue

        results = payload.get("ad_creatives", []) or []
        kept = 0
        for row in results[:limit_per_brand]:
            ad = _to_ad(row, brand, now)
            if ad is not None:
                out.append(ad)
                kept += 1
        if verbose:
            print("  %-14s %d ads" % (brand, kept))

    return out


def _to_ad(row: Dict[str, Any], requested_brand: str, captured_at: str) -> Optional[Ad]:
    """Map a SerpApi creative onto our Ad schema.

    Field names differ by ad format, so we probe a few likely keys rather than
    assuming one shape. Anything with no readable text is dropped -- an image
    ad with no copy tells us nothing about messaging.
    """
    fmt = (row.get("format") or row.get("type") or "text").lower()

    headline = _first(row, ["headline", "title", "ad_title"])
    body = _first(row, ["description", "body", "ad_text", "snippet"])

    if not headline and not body:
        return None

    advertiser = row.get("advertiser") or row.get("advertiser_name") or requested_brand

    creative_type = "text"
    if "video" in fmt:
        creative_type = "video"
    elif "image" in fmt:
        creative_type = "image"

    return Ad(
        brand=canonical_brand(advertiser) if advertiser else requested_brand,
        platform="google_search" if creative_type == "text" else "google_" + creative_type,
        headline=headline or "",
        body=body or "",
        ad_id=str(row.get("creative_id") or row.get("ad_id") or ""),
        advertiser_id=str(row.get("advertiser_id") or ""),
        landing_url=row.get("target_domain") or row.get("link"),
        creative_type=creative_type,
        media_url=row.get("image") or row.get("thumbnail") or row.get("video_link"),
        first_seen=row.get("first_shown") or row.get("first_seen"),
        last_seen=row.get("last_shown") or row.get("last_seen"),
        still_running=True,
        regions=[str(row.get("region", "US"))],
        provenance="api",
        captured_at=captured_at,
        source_url=row.get("details_link") or row.get("link"),
        notes="serpapi:google_ads_transparency_center",
    )


def _first(row: Dict[str, Any], keys: List[str]) -> str:
    for k in keys:
        v = row.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
        if isinstance(v, list) and v:
            return " ".join(str(x) for x in v if x).strip()
    return ""
