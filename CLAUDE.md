# Project conventions for Claude Code

Read this before making changes. It exists so five people working in parallel get
consistent help.

## What this is

A competitive ad messaging teardown for fitness apparel. Pipeline:

    sources/*.py  ->  extract.py  ->  matrix.py  ->  dashboard/index.html
        Ad            Extraction       Matrix          (data inlined)

`teardown/schema.py` defines all three shapes and is **the contract between five
workstreams**. Changing it breaks other people's in-flight work — flag it clearly in
your response if a request requires a schema change, and prefer additive fields.

## Hard constraints

**No third-party dependencies.** Standard library only, in both Python and the
dashboard. Five laptops, 2.5 days, non-engineers — `pip install` is a failure mode, not
a convenience. The Claude client is hand-rolled in `llm.py` for exactly this reason.
Don't add `requests`, `pandas`, `anthropic`, or any JS framework or CDN link.

**Python 3.9 compatible.** No `match`, no `X | Y` unions at runtime, no `tomllib`. The
target is stock macOS Python.

**The pipeline must always produce a dashboard.** Every external dependency needs a
fallback: no API key → mock extraction engine; no network → committed fixtures. Never
introduce a step that can hard-fail the demo.

**The dashboard is one self-contained file.** `python3 -m teardown build` inlines
`matrix.json` into `dist/teardown.html`. No local server, no `fetch()`, no external
assets. It has to open by double-clicking on a stranger's laptop.

## Honesty rules — these are not negotiable

**Never invent ad copy and present it as real.** Every `Ad` carries `provenance`
(`captured` / `api` / `placeholder`), and the dashboard badges it. If you add sample
data for testing, it is `placeholder` and it says so in `notes`.

**Never scrape the Ads Transparency Center's internal RPC endpoint.** It violates
Google's ToS and it is fragile. Live data comes from a licensed API (SerpApi) or from a
human with a browser.

**Verbatim means verbatim.** `claim_verbatim` and `proof_verbatim` must be exact
substrings of the ad copy. The whole product's credibility rests on being able to point
at the actual words.

**Generated ad concepts are badged as generated.** They are proposals, never presented
as ads anyone is running.

## Style

- Match the surrounding code. Plain, readable Python — teammates who don't code much
  have to read this.
- Comments explain *why*, not *what*. The existing comments are the reference.
- Analysis math stays simple enough to defend on a slide. If a metric can't be
  explained in one sentence, it's the wrong metric.
- Taxonomy labels in `taxonomy.py` are strategy, not code — a marketer owns that file.
  Suggest edits, don't restructure it.

## Colors and charts

The dashboard uses a pre-validated palette (single-hue sequential blue for the heatmap,
categorical slot 1 for single-series bars). Don't swap in a rainbow ramp, don't color
nominal bars by magnitude, and keep the printed number in every heatmap cell — nothing
may be encoded by color alone.

## Useful commands

```bash
python3 -m teardown run --open          # full pipeline + open dashboard
python3 -m teardown stats               # per-brand capture progress
python3 -m teardown taxonomy            # print the category definitions
python3 -m teardown analyze --engine claude --no-cache
python3 tests/test_smoke.py             # fast sanity check
```
