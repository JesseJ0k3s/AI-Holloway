"""Import ads captured by hand from the Ads Transparency Center.

This is the workstream that needs zero API access and zero coding, so it can
start at hour one while everything else is still being built. Two people with
browsers can log 100+ real ads in an afternoon.

Fill in data/capture.csv with these columns (see docs/DATA_CAPTURE.md):

    brand,headline,body,landing_url,first_seen,last_seen,region,source_url,captured_by

Then:

    python3 -m teardown ingest --source manual --save

Everything imported here is marked provenance="captured", which the dashboard
displays -- these are real ads a human actually saw running.
"""

from __future__ import annotations

import csv
import datetime as dt
import os
from typing import List, Optional

from ..schema import Ad
from ..taxonomy import canonical_brand

DEFAULT_CSV = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "capture.csv",
)

REQUIRED = ["brand", "headline"]


def fetch(
    brands: Optional[List[str]] = None,
    csv_path: str = DEFAULT_CSV,
    verbose: bool = True,
    **_: object
) -> List[Ad]:
    if not os.path.exists(csv_path):
        raise SystemExit(
            "No capture file at %s\n"
            "  Copy data/capture.example.csv to data/capture.csv and start logging ads.\n"
            "  See docs/DATA_CAPTURE.md for the 10-minute walkthrough." % csv_path
        )

    now = dt.datetime.now(dt.timezone.utc).isoformat()
    ads: List[Ad] = []
    skipped = 0

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(
                "%s is missing required column(s): %s" % (csv_path, ", ".join(missing))
            )

        for i, row in enumerate(reader, start=2):
            brand_raw = (row.get("brand") or "").strip()
            headline = (row.get("headline") or "").strip()
            if not brand_raw or not headline:
                skipped += 1
                continue

            brand = canonical_brand(brand_raw)
            if brands and brand not in brands:
                continue

            region = (row.get("region") or "US").strip()
            ads.append(
                Ad(
                    brand=brand,
                    platform=(row.get("platform") or "google_search").strip(),
                    headline=headline,
                    body=(row.get("body") or "").strip(),
                    landing_url=(row.get("landing_url") or "").strip() or None,
                    creative_type="text",
                    first_seen=(row.get("first_seen") or "").strip() or None,
                    last_seen=(row.get("last_seen") or "").strip() or None,
                    still_running=True,
                    regions=[region] if region else [],
                    provenance="captured",
                    captured_at=now,
                    source_url=(row.get("source_url") or "").strip() or None,
                    notes=("captured_by=" + (row.get("captured_by") or "").strip()).rstrip("="),
                )
            )

    if verbose:
        print("  imported %d ads from %s (%d rows skipped)" % (len(ads), os.path.basename(csv_path), skipped))
    return ads
