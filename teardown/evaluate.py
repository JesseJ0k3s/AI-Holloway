"""Score the extractor against human labels.

This produces WS2's headline number: "Claude agreed with a human marketer on
X of 20 ads." It is the most credible thing in the presentation, because it is
the only claim about the AI that is actually measured.

Workflow:

    python3 -m teardown gold --init      # writes a blank answer key to score
    # ...a human fills in data/gold.csv by hand, WITHOUT looking at the output
    python3 -m teardown gold             # score the current extractions

The order matters. Label first, then run the extractor, then compare. Labelling
after you have seen the model's answer is not an evaluation, it is agreement
with yourself.
"""

from __future__ import annotations

import csv
import json
import os
from typing import Dict, List, Optional, Tuple

from . import taxonomy
from .schema import Ad, Extraction

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLD_CSV = os.path.join(ROOT, "data", "gold.csv")

COLS = ["ad_id", "brand", "headline", "body", "true_territory", "true_audiences", "notes"]


def init_gold(ads: List[Ad], n: int = 20, path: str = GOLD_CSV) -> str:
    """Write a blank answer key: a spread of ads for a human to label.

    Sampled round-robin across brands so one loud brand doesn't dominate.
    """
    by_brand: Dict[str, List[Ad]] = {}
    for a in ads:
        by_brand.setdefault(a.brand, []).append(a)

    picked: List[Ad] = []
    i = 0
    while len(picked) < min(n, len(ads)):
        added = False
        for b in sorted(by_brand):
            if i < len(by_brand[b]):
                picked.append(by_brand[b][i])
                added = True
                if len(picked) >= n:
                    break
        if not added:
            break
        i += 1

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        for a in picked:
            w.writerow(
                {
                    "ad_id": a.ad_id,
                    "brand": a.brand,
                    "headline": a.headline,
                    "body": a.body,
                    "true_territory": "",  # <- human fills this in
                    "true_audiences": "",  # <- optional, comma-separated
                    "notes": "",
                }
            )
    return path


def load_gold(path: str = GOLD_CSV) -> List[Dict[str, str]]:
    if not os.path.exists(path):
        raise SystemExit(
            "No answer key at %s\n"
            "  Create one with:  python3 -m teardown gold --init\n"
            "  Then fill in the true_territory column by hand." % path
        )
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return [r for r in csv.DictReader(fh)]


def score(
    gold: List[Dict[str, str]], extractions: List[Extraction]
) -> Dict[str, object]:
    by_id = {e.ad_id: e for e in extractions}

    labelled = [g for g in gold if (g.get("true_territory") or "").strip()]
    hits: List[Tuple[str, str, str]] = []
    misses: List[Tuple[str, str, str, str]] = []
    missing_extraction = 0

    for g in labelled:
        truth = g["true_territory"].strip()
        ex = by_id.get(g["ad_id"])
        if ex is None:
            missing_extraction += 1
            continue
        got = ex.primary_claim_territory
        if got == truth:
            hits.append((g["brand"], g["headline"][:40], truth))
        else:
            misses.append((g["brand"], g["headline"][:40] or g["body"][:40], truth, got))

    n = len(hits) + len(misses)
    agreement = (len(hits) / n) if n else 0.0

    # Which territories does the model systematically get wrong?
    confusion: Dict[str, Dict[str, int]] = {}
    for _, _, truth, got in misses:
        confusion.setdefault(truth, {}).setdefault(got, 0)
        confusion[truth][got] += 1

    unlabelled = len(gold) - len(labelled)
    engines = {}
    for e in extractions:
        engines[e.engine] = engines.get(e.engine, 0) + 1

    return {
        "n_scored": n,
        "n_hits": len(hits),
        "agreement": round(agreement, 3),
        "misses": misses,
        "confusion": confusion,
        "unlabelled": unlabelled,
        "missing_extraction": missing_extraction,
        "engines": engines,
    }


def report(result: Dict[str, object]) -> None:
    n, hits = result["n_scored"], result["n_hits"]
    engines = result["engines"]

    if not n:
        print("\nNothing scored yet -- the answer key has no filled-in rows.")
        print("Open data/gold.csv and fill the true_territory column.")
        print("Valid values:")
        for k in taxonomy.CLAIM_TERRITORIES:
            print("  %s" % k)
        return

    print("\n\033[1mClaude agreed with the human label on %d of %d ads (%.0f%%)\033[0m"
          % (hits, n, 100 * float(result["agreement"])))
    print("  extraction engine: %s" % engines)

    if "claude" not in engines:
        print("\n  \033[1mWARNING\033[0m: these extractions came from the keyword")
        print("  fallback, not Claude. This number is not a measure of Claude.")
        print("  Re-run:  python3 -m teardown analyze --engine claude --no-cache")

    if result["misses"]:
        print("\n\033[1mDisagreements\033[0m")
        for brand, text, truth, got in result["misses"]:
            print("  %-13s %-42s human=%-22s model=%s" % (brand, text, truth, got))

    if result["confusion"]:
        print("\n\033[1mSystematic confusions\033[0m (human -> what the model said)")
        for truth, gots in sorted(result["confusion"].items(), key=lambda kv: -sum(kv[1].values())):
            for got, c in sorted(gots.items(), key=lambda kv: -kv[1]):
                print("  %-24s -> %-24s %dx" % (truth, got, c))

    if result["unlabelled"]:
        print("\n  %d rows in the answer key are still blank." % result["unlabelled"])
    if result["missing_extraction"]:
        print("  %d labelled ads have no extraction (re-run analyze)." % result["missing_extraction"])
