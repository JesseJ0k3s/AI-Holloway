# 2.5-Day Workplan — Five People, No Idle Hands

The scaffold is already built and running. Nobody is blocked on anybody at hour zero.

**The mechanism that makes parallel work possible:** `teardown/schema.py` defines the
shape of the data at every stage, and the repo ships with working seed data. So the
dashboard person can build against a full `matrix.json` before a single real ad has
been captured, and the extraction person can test prompts before the dashboard exists.

---

## Roles

Pick these in the first ten minutes. Each person owns files nobody else touches.

### WS1 — Ad Capture Lead *(the critical path — most important role)*
**Owns:** `data/capture.csv`, `teardown/sources/manual.py`, `teardown/sources/serpapi.py`

Get 100+ real ads out of the Google Ads Transparency Center and into the repo. This is
the only workstream that gates the others' *quality* (not their progress), so it starts
first and finishes first. Recruit a second person for the capture sprint.

- Follow [DATA_CAPTURE.md](DATA_CAPTURE.md). Target ≥8 ads per brand, 12 brands.
- Try SerpApi's free tier in parallel — if it works, it's a great demo beat ("and it
  refreshes live"). If it doesn't, you've lost 30 minutes, not the project.
- **Done when:** `python3 -m teardown stats` shows ≥8 ads for every brand and zero
  `placeholder` rows.

### WS2 — Extraction & Prompt Lead
**Owns:** `teardown/extract.py` (the `SYSTEM` prompt especially)

Make Claude's read of each ad trustworthy. This is the most "AI" role.

- Hand-label 20 ads yourself first. That's your answer key.
- Run `--engine claude`, compare against your labels, tune the prompt, repeat.
- Track the number: "Claude agreed with a human marketer on X of 20 ads." **Put that
  number on a slide** — it's the single most credible thing in the whole presentation.
- **Done when:** agreement ≥80% and mean confidence >0.6.

### WS3 — Analysis Lead
**Owns:** `teardown/matrix.py`, `teardown/generate.py`

Turn labels into an argument.

- Sanity-check the whitespace scoring against intuition. If it says nobody claims
  performance in a fitness apparel set, the scoring is wrong — go find out why.
- Tune the ad-concept prompt in `generate.py` until the output is genuinely usable.
- Pick **one brand** to play strategist for (Vuori or Tracksmith are good — challengers
  with room to move). The recommendation is the payoff of the whole demo.
- **Done when:** the top 3 gaps survive the "would a CMO nod at this?" test.

### WS4 — Dashboard Lead
**Owns:** `dashboard/index.html`

Make it legible from the back of the room.

- It already works. Your job is polish, not construction.
- Test it **projected**, not on your laptop. Bump font sizes until it reads at 15 feet.
- Ideas if you have time: sort brands by ad volume, a "crowded vs. open" summary strip,
  a print stylesheet for a leave-behind.
- **Done when:** someone who's never seen it can read the main insight in 10 seconds.

### WS5 — Strategy & Narrative Lead
**Owns:** `teardown/taxonomy.py`, `docs/DEMO_SCRIPT.md`, the slides

The taxonomy is the strategic spine — if the categories are wrong, everything
downstream is wrong, no matter how good the code is. This role needs the best marketing
brain in the group, not the best coder. **You will barely write any Python.**

- Pressure-test the 12 claim territories against real captured ads. Merge any two that
  keep fighting over the same ads. Add anything real that's missing.
- Own the 8-minute story and run the rehearsals.
- **Done when:** <10% of ads land in `unclassified` and the story runs in 8 minutes.

---

## Schedule

### Day 1 — Morning (3 hrs) · Get real
| Who | What |
|---|---|
| All | 15 min: clone, run `python3 -m teardown run --open`, see it work. Assign roles. |
| WS1 + WS5 | **Capture sprint.** Two browsers, split the 12 brands, log ads. |
| WS2 | Hand-label 20 ads as the answer key. Get an `ANTHROPIC_API_KEY` working. |
| WS3 | Read `matrix.py`. Write down what you'd expect the whitespace to be *before* seeing it. |
| WS4 | Project the dashboard. List what's illegible. |

### Day 1 — Afternoon (3 hrs) · First real signal
- WS1: finish capture, `--save`, commit. **Delete the placeholder seed file.**
- WS2: first `--engine claude` run against the real data; score against the answer key.
- WS5: revise the taxonomy based on what the real ads actually say. This is the highest
  leverage hour of the project.
- WS3 + WS4: work against real data as soon as it lands.

**End of Day 1 gate:** a dashboard built from 100% real captured ads. If you have that,
you're ahead. Everything after this is sharpening.

### Day 2 — Morning (3 hrs) · Make it right
- WS2: prompt iteration to ≥80% agreement.
- WS3: whitespace tuning + ad concept generation.
- WS4: polish, projected.
- WS5: draft the 8-minute narrative. **First rehearsal at the end of this block**, with
  whatever exists. An ugly rehearsal on Day 2 beats a perfect one an hour before class.

### Day 2 — Afternoon (3 hrs) · Make it land
- Freeze the data. No new ads after this point.
- Full pipeline run with Claude. **Commit `data/extracted/`** so the demo is offline-safe.
- Rehearse twice, timed.
- Build slides around dashboard screenshots — do not live-navigate more than one tab.

### Day 3 — Morning (2 hrs) · Ship
- Final `python3 -m teardown run --engine claude --generate-for "<brand>"`.
- Copy `dist/teardown.html` to a USB stick and email it to yourselves. It's one file
  with zero dependencies — that's the whole point.
- Dress rehearsal on the actual room's projector if you can get in.
- **Stop building.** Last-minute changes are how demos die.

---

## Git without pain

Nobody needs to be a git expert. Four commands:

```bash
git pull origin main
```

```bash
git checkout -b ws3-my-thing
```

```bash
git add -A && git commit -m "WS3: tune whitespace scoring"
```

```bash
git push -u origin ws3-my-thing
```

Then open a Pull Request on GitHub and ask someone to merge it.

**Conflict insurance:**
- Stay in your own files (see Roles above).
- `git pull origin main` before you start each session.
- `teardown/schema.py` changes get announced in the group chat *first*.
- If you hit a merge conflict you don't understand, don't fight it — ask Claude Code:
  *"I have a merge conflict in X, explain what changed and help me resolve it."*

## Using Claude Code as a team

The repo has a `CLAUDE.md` that tells Claude Code the project conventions, so everyone
gets consistent help. Good prompts for this codebase:

- *"Read teardown/schema.py, then add a `sentiment` field end to end."*
- *"Our extraction disagrees with my labels on these 5 ads — here they are. Improve the SYSTEM prompt in extract.py."*
- *"Make the dashboard readable projected on a screen 15 feet away."*
- *"Write a smoke test that fails if any ad in data/ads/ still has provenance=placeholder."*

## Cut list — if you fall behind, drop these in order

1. SerpApi live integration (manual capture is enough)
2. The audience matrix tab
3. The ownership index card
4. Ad concept generation

**Never cut:** real captured data, the brand × territory matrix, the whitespace ranking.
Those three *are* the product.
