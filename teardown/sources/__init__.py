"""Ad ingestion adapters.

Every adapter is a function `fetch(brands, **opts) -> List[Ad]`. Add a new one
by writing a module here and registering it in SOURCES below. Nothing
downstream needs to know where an ad came from -- that is the entire point of
the Ad schema.

Available today:
    fixtures  - read committed JSON from data/ads/. Always works, no network.
    serpapi   - live Google Ads Transparency Center via SerpApi (needs key).
    manual    - import a CSV of ads captured by hand from the browser.
"""

from __future__ import annotations

from typing import Callable, Dict, List

from ..schema import Ad
from . import fixtures, manual, serpapi

SOURCES: Dict[str, Callable[..., List[Ad]]] = {
    "fixtures": fixtures.fetch,
    "serpapi": serpapi.fetch,
    "manual": manual.fetch,
}


def get(name: str) -> Callable[..., List[Ad]]:
    if name not in SOURCES:
        raise SystemExit(
            "Unknown source %r. Available: %s" % (name, ", ".join(sorted(SOURCES)))
        )
    return SOURCES[name]
