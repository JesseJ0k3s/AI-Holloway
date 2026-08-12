"""CLI for the messaging teardown pipeline.

    python3 -m teardown ingest  --source manual --save
    python3 -m teardown analyze --engine claude
    python3 -m teardown build
    python3 -m teardown run                      # all three, the demo command

Run `python3 -m teardown run` with no API keys at all and you still get a
working dashboard. That is on purpose.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import webbrowser
from typing import List, Optional

from . import extract, generate, matrix as matrix_mod, sources, taxonomy
from .schema import Ad, Extraction, Matrix
from .sources import fixtures

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_JSON = os.path.join(ROOT, "data", "out", "matrix.json")
TEMPLATE = os.path.join(ROOT, "dashboard", "index.html")
DIST = os.path.join(ROOT, "dist", "teardown.html")


def _banner(msg: str) -> None:
    print("\n\033[1m%s\033[0m" % msg)


# --------------------------------------------------------------------------


def cmd_ingest(args: argparse.Namespace) -> List[Ad]:
    _banner("1. Ingesting ads (source=%s)" % args.source)
    fn = sources.get(args.source)
    brands = args.brands.split(",") if args.brands else None
    ads = fn(brands=brands, region=args.region)

    print("  -> %d ads across %d brands" % (len(ads), len({a.brand for a in ads})))

    if args.save and ads:
        path = fixtures.write(ads, slug=args.source + "_capture")
        print("  saved to %s" % os.path.relpath(path, ROOT))
    return ads


def cmd_analyze(args: argparse.Namespace) -> Matrix:
    _banner("2. Reading the ads")
    ads = fixtures.fetch(brands=args.brands.split(",") if args.brands else None)
    if not ads:
        raise SystemExit(
            "No ads found in data/ads/.\n"
            "  Run:  python3 -m teardown ingest --source manual --save\n"
            "  (or --source serpapi, or use the seed file to test the pipeline)"
        )
    print("  %d ads loaded" % len(ads))

    extractions = extract.extract_all(ads, engine=args.engine, use_cache=not args.no_cache)

    _banner("3. Building the matrix")
    m = matrix_mod.build(ads, extractions)
    print("  %d brands x %d territories" % (len(m.brands), len(m.territories)))
    top = m.whitespace[0] if m.whitespace else None
    if top:
        print("  biggest gap: %s (score %.0f) -- %s" % (
            top["territory"], top["opportunity_score"], top["reasoning"]))

    if args.generate_for:
        _banner("4. Generating ad concepts for %s" % args.generate_for)
        m.concepts = generate.concepts_for_whitespace(m, for_brand=args.generate_for)
        print("  %d concepts" % len(m.concepts))

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        fh.write(m.to_json())
    print("\n  wrote %s" % os.path.relpath(OUT_JSON, ROOT))
    return m


def cmd_build(args: argparse.Namespace) -> str:
    """Inline matrix.json into the HTML so the result is one double-clickable file.

    No local web server, no CORS, no 'it works on my machine'. Airplane-proof.
    """
    _banner("Building dashboard")
    if not os.path.exists(OUT_JSON):
        raise SystemExit("No matrix.json yet. Run:  python3 -m teardown analyze")
    if not os.path.exists(TEMPLATE):
        raise SystemExit("Missing dashboard/index.html")

    with open(OUT_JSON, "r", encoding="utf-8") as fh:
        data = fh.read()
    with open(TEMPLATE, "r", encoding="utf-8") as fh:
        html = fh.read()

    marker = "/*__TEARDOWN_DATA__*/null"
    if marker not in html:
        raise SystemExit("dashboard/index.html is missing the %s marker" % marker)

    # </script> inside the JSON would close the tag early.
    html = html.replace(marker, data.replace("</", "<\\/"))

    os.makedirs(os.path.dirname(DIST), exist_ok=True)
    with open(DIST, "w", encoding="utf-8") as fh:
        fh.write(html)

    size_kb = os.path.getsize(DIST) / 1024
    print("  wrote %s (%.0f KB, self-contained)" % (os.path.relpath(DIST, ROOT), size_kb))
    print("  open it with:  open dist/teardown.html")
    return DIST


def cmd_run(args: argparse.Namespace) -> None:
    if args.source != "fixtures":
        cmd_ingest(args)
    cmd_analyze(args)
    path = cmd_build(args)
    if args.open:
        webbrowser.open("file://" + path)


def cmd_taxonomy(args: argparse.Namespace) -> None:
    for title, d in (
        ("CLAIM TERRITORIES", taxonomy.CLAIM_TERRITORIES),
        ("AUDIENCES", taxonomy.AUDIENCES),
        ("PROOF TYPES", taxonomy.PROOF_TYPES),
        ("TONES", taxonomy.TONES),
    ):
        print("\n\033[1m%s\033[0m" % title)
        for k, v in d.items():
            print("  %-24s %s" % (k, v))
    print("\n\033[1mBRANDS (%d)\033[0m" % len(taxonomy.BRANDS))
    for b, meta in taxonomy.BRANDS.items():
        print("  %-16s %s" % (b, meta["archetype"]))


def cmd_stats(args: argparse.Namespace) -> None:
    ads = fixtures.fetch()
    if not ads:
        print("No ads captured yet.")
        return
    from collections import Counter

    by_brand = Counter(a.brand for a in ads)
    by_prov = Counter(a.provenance for a in ads)
    print("\n\033[1m%d ads captured\033[0m" % len(ads))
    print("\nBy brand:")
    for b in taxonomy.BRANDS:
        n = by_brand.get(b, 0)
        bar = "#" * min(n, 40)
        flag = "" if n >= 5 else "   <- needs more"
        print("  %-16s %3d %s%s" % (b, n, bar, flag))
    unknown = {b: n for b, n in by_brand.items() if b not in taxonomy.BRANDS}
    if unknown:
        print("\nUnrecognized brand labels (fix aliases in taxonomy.py):")
        for b, n in unknown.items():
            print("  %-16s %3d" % (b, n))
    print("\nProvenance: %s" % dict(by_prov))


# --------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> None:
    p = argparse.ArgumentParser(prog="teardown", description="Competitive ad messaging teardown")
    sub = p.add_subparsers(dest="cmd")

    def common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--source", default="fixtures", choices=sorted(sources.SOURCES))
        sp.add_argument("--brands", default="", help="comma-separated subset")
        sp.add_argument("--region", default="US")
        sp.add_argument("--engine", default="auto", choices=["auto", "claude", "mock"])
        sp.add_argument("--no-cache", action="store_true")
        sp.add_argument("--save", action="store_true", help="persist ingested ads to data/ads/")
        sp.add_argument("--generate-for", default="", help="brand to write whitespace concepts for")
        sp.add_argument("--open", action="store_true", help="open the dashboard when done")

    for name, fn in (
        ("ingest", cmd_ingest),
        ("analyze", cmd_analyze),
        ("build", cmd_build),
        ("run", cmd_run),
    ):
        sp = sub.add_parser(name)
        common(sp)
        sp.set_defaults(func=fn)

    sub.add_parser("taxonomy").set_defaults(func=cmd_taxonomy)
    sub.add_parser("stats").set_defaults(func=cmd_stats)

    args = p.parse_args(argv)
    if not getattr(args, "func", None):
        p.print_help()
        sys.exit(0)
    args.func(args)


if __name__ == "__main__":
    main()
