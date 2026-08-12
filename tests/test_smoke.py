"""Fast sanity check. No pytest needed:  python3 tests/test_smoke.py

Run this before you push. It catches the failures that would actually break the
demo, not stylistic nits.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from teardown import extract, matrix as matrix_mod, taxonomy  # noqa: E402
from teardown.schema import Ad  # noqa: E402
from teardown.sources import fixtures  # noqa: E402

failures = []


def check(label: str, cond: bool, detail: str = "") -> None:
    if cond:
        print("  ok   %s" % label)
    else:
        print("  FAIL %s %s" % (label, detail))
        failures.append(label)


print("\nSchema")
a = Ad(brand="Nike", platform="google_search", headline="Test Headline", body="Body copy.")
check("ad_id is auto-generated", bool(a.ad_id))
check("fingerprint is stable", a.fingerprint() == Ad(
    brand="Nike", platform="google_search", headline="Test Headline", body="Body copy.").fingerprint())
check("round-trips through dict", Ad.from_dict(a.to_dict()).headline == a.headline)
check("provenance defaults to placeholder", a.provenance == "placeholder")

print("\nTaxonomy")
check("brand aliases resolve", taxonomy.canonical_brand("lululemon athletica") == "lululemon")
check("unknown labels are dropped", taxonomy.validate("territory", ["performance", "made_up"]) == ["performance"])
check("12 brands defined", len(taxonomy.BRANDS) == 12, "(got %d)" % len(taxonomy.BRANDS))

print("\nAds on disk")
ads = fixtures.fetch()
check("some ads exist", len(ads) > 0, "-> run: python3 -m teardown ingest --source manual --save")
check("every ad has a brand", all(x.brand for x in ads))
check("no duplicate ad_ids", len({x.ad_id for x in ads}) == len(ads))

placeholders = [x for x in ads if x.provenance == "placeholder"]
if placeholders:
    print("  WARN %d placeholder ads still present -- fine now, NOT ok for the demo" % len(placeholders))

print("\nPipeline (mock engine)")
ex = extract.extract_all(ads, engine="mock", use_cache=False, verbose=False)
check("one extraction per ad", len(ex) == len(ads))
check("territories are all valid", all(
    e.primary_claim_territory in taxonomy.CLAIM_TERRITORIES or e.primary_claim_territory == "unclassified"
    for e in ex))

m = matrix_mod.build(ads, ex)
check("matrix has cells", len(m.cells) > 0)
check("whitespace covers every territory", len(m.whitespace) == len(taxonomy.CLAIM_TERRITORIES))
check("opportunity scores are 0-100", all(0 <= w["opportunity_score"] <= 100 for w in m.whitespace))
check("matrix serializes to JSON", len(m.to_json()) > 100)

print("\nDashboard template")
tpl = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard", "index.html")
with open(tpl, encoding="utf-8") as fh:
    html = fh.read()
check("data marker present", "/*__TEARDOWN_DATA__*/null" in html)
check("no external resources", "http://" not in html and "https://" not in html.replace("adstransparency", ""))

print("\n%s" % ("FAILED: " + ", ".join(failures) if failures else "All checks passed."))
sys.exit(1 if failures else 0)
