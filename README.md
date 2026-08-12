# AI-Holloway — Competitive Messaging Teardown

> **The assignment:** *"Pulls the ads a set of competitors are actually running right
> now and turns them into a messaging matrix — what each brand is claiming, which
> audiences they're addressing, which proof points recur, and where nobody is playing."*

Pulls the search ads a set of competitors are **actually running right now**, and turns
them into a messaging matrix: what each brand claims, who they're talking to, which
proof points recur — and where nobody is playing.

Then it writes the ads for the empty space.

**Category:** fitness apparel · **Source:** Google Ads Transparency Center
**Competitive set (12):** lululemon, Nike, Alo Yoga, Vuori, On, Under Armour, Gymshark,
Arc'teryx, Patagonia, Tracksmith, New Balance, Fabletics

---

## Quickstart (60 seconds, no API keys, no installs)

```bash
python3 -m teardown run --open
```

That runs the whole pipeline on the committed seed data and opens a self-contained
dashboard at `dist/teardown.html`. No `pip install`, no `npm`, no virtualenv, no
local server. If you have Python 3, it works.

> The seed data is **synthetic placeholder copy**, and the dashboard says so in red.
> Replacing it with real captured ads is Day 1's job — see
> [docs/DATA_CAPTURE.md](docs/DATA_CAPTURE.md).

Other commands:

```bash
python3 -m teardown stats
```

```bash
python3 -m teardown taxonomy
```

---

## How it works

```
  ingest              extract              aggregate            render
┌──────────┐      ┌─────────────┐      ┌────────────┐      ┌─────────────┐
│ Ads Trans│      │   Claude    │      │  messaging │      │  dashboard  │
│ -parency │ ───► │ reads each  │ ───► │   matrix   │ ───► │  + generated│
│  Center  │  Ad  │     ad      │  Ex  │ + whitespace│ JSON │  ad concepts│
└──────────┘      └─────────────┘      └────────────┘      └─────────────┘
 sources/*.py       extract.py            matrix.py          dashboard/
                                          generate.py
```

Each stage hands the next a **fixed data shape** defined in
[`teardown/schema.py`](teardown/schema.py) — `Ad` → `Extraction` → `Matrix`.
That file is the contract. It is why five people can build five pieces at once.

### The five moving parts

| File | What it does | Owned by |
|---|---|---|
| `teardown/sources/` | Get ads from the Transparency Center | Workstream 1 |
| `teardown/extract.py` | Claude reads claims / audiences / proof | Workstream 2 |
| `teardown/matrix.py` | Aggregation + whitespace scoring | Workstream 3 |
| `dashboard/index.html` | The demo surface | Workstream 4 |
| `teardown/taxonomy.py` | The strategic categories everything sorts into | Workstream 5 |

---

## Getting real ad data

**Google Ads Transparency Center has no official public API.** This is the single
biggest risk to the project, so the ingestion layer has three adapters and the demo
never depends on any one of them working.

| Adapter | Command | Needs | Notes |
|---|---|---|---|
| **manual** | `--source manual` | a browser and 90 minutes | Log real ads into `data/capture.csv`. **Start here.** No accounts, no keys, works on day 1. |
| **serpapi** | `--source serpapi` | `SERPAPI_KEY` | A licensed commercial API for the Transparency Center. Free tier ≈100 searches/month. |
| **fixtures** | `--source fixtures` | nothing | Reads whatever is committed in `data/ads/`. **This is what you demo on.** |

Everything you ingest with `--save` lands in `data/ads/` and gets committed, so the
classroom demo runs offline.

We deliberately do **not** scrape the Transparency Center's internal endpoint. It
violates Google's Terms of Service and it breaks without warning — which, on a
Thursday morning in front of the class, is the same thing as not working.

### Provenance is enforced, not assumed

Every ad carries a `provenance` field — `captured`, `api`, or `placeholder` — and
the dashboard badges it in the header. Synthetic scaffolding data can never be
mistaken for something a brand is really running. Say this out loud in the demo;
it's the difference between a class project and a credible analysis.

---

## Turning on Claude

Without a key the pipeline uses a keyword-rule fallback so it always produces a
dashboard. With a key, Claude does the real reading:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

```bash
python3 -m teardown run --engine claude --generate-for "Vuori" --open
```

Extractions are cached to `data/extracted/` by ad fingerprint, so re-running is
free and the demo is reproducible. **Commit the cache** — it means the live demo
makes zero network calls.

---

## Working as a team of five

The rule that makes this work: **nobody edits the same file.** The schema is frozen
first, everyone codes against it, and integration is nearly free.

```bash
git clone https://github.com/JesseJ0k3s/AI-Holloway.git
```

```bash
git checkout -b ws3-whitespace-scoring
```

Then open Claude Code *in your own file* and let it work there. Full hour-by-hour
plan and role assignments: **[docs/WORKPLAN.md](docs/WORKPLAN.md)**.

One hard rule: **changing `teardown/schema.py` breaks everyone else.** Propose it in
the group chat first. Changing any other file breaks nobody.

---

## Repo map

```
teardown/
  schema.py        THE CONTRACT — Ad, Extraction, Matrix
  taxonomy.py      claim territories, audiences, proof types, brand list
  sources/         fixtures.py · serpapi.py · manual.py
  extract.py       Claude reads the ads (+ mock fallback)
  matrix.py        aggregation, ownership index, whitespace scoring
  generate.py      whitespace → new ad concepts
  llm.py           stdlib Claude client (no SDK dependency)
  __main__.py      CLI
dashboard/
  index.html       template; data is inlined at build time
data/
  ads/             captured ads (committed — this is the demo dataset)
  extracted/       cached Claude reads (committed — reproducible)
  capture.csv      the manual capture sheet
dist/
  teardown.html    the built, self-contained dashboard
docs/
  WORKPLAN.md      2.5-day plan, five roles
  DATA_CAPTURE.md  how to log ads from the Transparency Center
  DEMO_SCRIPT.md   what to say in the eight minutes
```

---

## What the analysis actually computes

**Ownership index** — a brand's share of its own ads in a territory ÷ the category's
share of all ads in that territory. Above 1.0 means the brand over-indexes there.
This is what separates "Patagonia mentions sustainability" from "Patagonia owns
sustainability."

**Opportunity score** — `100 × (0.6 × share of brands absent + 0.4 × share of ad
volume missing vs. the busiest territory)`. Weighted toward brand count because a
territory one brand shouts about is more contestable than one five brands each
mention twice.

Both are deliberately simple arithmetic you can defend on a slide. When someone asks
"how did the AI decide that?", the answer is that it didn't — Claude classified the
ads, and plain division did the rest.

## Known limits (say these before you're asked)

- Search text ads only. Brand messaging on Meta, TikTok and YouTube may differ.
- A snapshot, not a trend. We see what's running now, not what changed.
- Ad *presence* is not ad *spend*. Two ads and two hundred look the same here.
- Claude's classification is a judgment call. Every cell links to the verbatim copy
  so a human can overrule it — that's why the "All ads" tab exists.
