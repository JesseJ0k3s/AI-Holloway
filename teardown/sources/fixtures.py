"""Read ads from committed JSON files in data/ads/.

This is the source the live demo should run on. Everything the team captures
gets committed here, so the classroom demo needs no network, no API key, and no
luck. `data/ads/<slug>.json` is a JSON list of Ad dicts.
"""

from __future__ import annotations

import json
import os
from typing import List, Optional

from ..schema import Ad

DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "ads",
)


def fetch(brands: Optional[List[str]] = None, data_dir: str = DATA_DIR, **_: object) -> List[Ad]:
    ads: List[Ad] = []
    if not os.path.isdir(data_dir):
        return ads

    for fname in sorted(os.listdir(data_dir)):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(data_dir, fname)
        with open(path, "r", encoding="utf-8") as fh:
            try:
                payload = json.load(fh)
            except json.JSONDecodeError as e:
                raise SystemExit("%s is not valid JSON: %s" % (path, e))

        # Accept either a bare list or {"ads": [...]}.
        rows = payload.get("ads", []) if isinstance(payload, dict) else payload
        for row in rows:
            ad = Ad.from_dict(row)
            if brands and ad.brand not in brands:
                continue
            ads.append(ad)

    return dedupe(ads)


def dedupe(ads: List[Ad]) -> List[Ad]:
    """Collapse identical copy captured more than once."""
    seen = {}
    for ad in ads:
        seen.setdefault(ad.fingerprint(), ad)
    return list(seen.values())


def write(ads: List[Ad], slug: str, data_dir: str = DATA_DIR) -> str:
    """Persist ads to data/ads/<slug>.json so they become part of the demo."""
    os.makedirs(data_dir, exist_ok=True)
    path = os.path.join(data_dir, "%s.json" % slug)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump([a.to_dict() for a in ads], fh, indent=2, ensure_ascii=False)
    return path
