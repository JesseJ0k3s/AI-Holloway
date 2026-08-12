# Capturing Real Ads from the Google Ads Transparency Center

This is the highest-value 90 minutes in the project. Everything downstream is only as
good as this data — and it needs no coding, no accounts, and no API keys.

**Target: 8–12 ads per brand × 12 brands ≈ 100–140 ads.** Two people, ~90 minutes.

---

## Setup (once)

```bash
cp data/capture.example.csv data/capture.csv
```

Open `data/capture.csv` in Excel, Numbers, or Google Sheets. Delete the example row.

> Sharing a Google Sheet and exporting to CSV at the end is usually faster for two
> people working at once. Just keep the column headers exactly as they are.

---

## The loop

1. Go to **https://adstransparency.google.com**
2. Search the brand (e.g. `lululemon`). Set **Region: United States**.
3. Filter **Format → Text** — those are search ads, the ones we want.
4. For each ad: copy the headline and description **exactly**, and grab the URL from
   your browser's address bar after clicking into the creative.
5. Paste one row per ad into `data/capture.csv`.

---

## Field notes from the first capture run

These were learned the hard way on 2026-08-12. They will save you an hour.

### Skip the search — go straight to the ad grid

The filters are URL parameters, so you can bookmark a brand's text ads directly:

```
https://adstransparency.google.com/advertiser/<ADVERTISER_ID>?region=US&format=TEXT
```

All twelve advertiser IDs are confirmed and pinned in `teardown/taxonomy.py`. You should
not need to look any of these up again:

| Brand | Advertiser ID | Legal entity (as listed) | Based in |
|---|---|---|---|
| lululemon | `AR01614014350098432001` | lululemon athletica canada inc. | Canada |
| Nike | `AR16735076323512287233` | Nike, Inc. | US |
| Alo Yoga | `AR10871259591425916929` | COLOR IMAGE APPAREL, INC. | US |
| Vuori | `AR04810021938799837185` | Vuori, Inc. | US |
| On | `AR01566006373894848513` | On AG | Switzerland |
| Under Armour | `AR16916677161513910273` | Under Armour, Inc. | US |
| Gymshark | `AR01822115136316375041` | Gymshark USA Inc | US |
| Arc'teryx | `AR17137590075693989889` | ARC'TERYX Equipment (Amer Sports Canada) | Canada |
| Patagonia | `AR13494478831020408833` | PATAGONIA, INC. | US |
| Tracksmith | `AR02037031623316209665` | Tracksmith Corporation | US |
| New Balance | `AR04323445746671026177` | New Balance Athletic Shoe, Inc. | US |
| Fabletics | `AR03556834903704207361` | Just Fabulous, Inc. | US |

Three of these are **not** what a name search returns, and each would have quietly put
the wrong market in the matrix:

- **Alo Yoga** — searching "Alo Yoga" returns only *Alo Yoga México*. The US advertiser
  is **COLOR IMAGE APPAREL, INC.**, which shares no words with the brand name.
- **Fabletics** — searching "Fabletics" returns only *FABLETICS LTD* (UK, ~5 ads). The
  US advertiser is **Just Fabulous, Inc.**, the JustFab/TechStyle operating company.
  Found by searching the *domain* `fabletics.com` instead of the brand.
- **New Balance** — two US entities. *New Balance Athletics, Inc.* has ~55 ads;
  *New Balance Athletic Shoe, Inc.* has ~2K. Pick by ad count, not by name.

Foreign-registered entities are normal and correct: lululemon (Canada), On
(Switzerland) and Arc'teryx (Canada) all serve the US market. `Based in` is where the
company is registered; the `region` filter is what controls where the ads ran.

Two brands are flagged **"multiple advertiser accounts have a similar name"** (Nike,
Under Armour). Clicking those does not open an advertiser page — it renders a merged
result set. Read the advertiser ID off the ad cards instead; for both, one account ran
the overwhelming majority of loaded ads (Nike 40/40, Under Armour 37/40).

### ⚠️ Picking the wrong advertiser entity is the #1 way to corrupt this dataset

Big brands have **many** advertiser accounts, and the top search result is frequently
the wrong one. Real examples hit during setup:

- Searching `Alo Yoga` returned **Alo Yoga México** first — Mexico-based, wrong market.
- Searching `Nike` returns `Nike, Inc.` flagged *"Multiple advertiser accounts have a
  similar name."*
- lululemon's main entity is **lululemon athletica canada inc.** (Vancouver HQ) — a
  Canadian legal entity that is nonetheless the right one for US-served ads.

**Before you capture, check the "Based in" line and the ad count.** The right entity is
almost always the one with by far the most ads. `Based in` is where the *company* is
registered, not where the ads run — the `region=US` filter is what controls that.

### Selecting the ad text: you have an advantage over automation

Ad creatives render inside sandboxed cross-origin iframes, so no script can read them —
but **you can still select the text with your mouse and copy it.** That gives you exact
verbatim copy with zero retyping. Use it. Do not retype ads by hand and do not transcribe
them from a screenshot; both introduce silent errors, and `claim_verbatim` has to be an
exact substring or the extraction quietly degrades.

### Make the window tall

The grid is virtualized and awkward to scroll. Maximize the window (or make it very
tall) and you can see 15–20 ads at once, which makes the copy-paste loop much faster.

### What "~5K ads" means

That count is all creatives ever recorded, not what's live today. The grid loads ~40–80
at a time. Take the first 8–12 readable text ads per brand and move on — you are
sampling the messaging, not auditing the account.

Then:

```bash
python3 -m teardown ingest --source manual --save
```

```bash
python3 -m teardown stats
```

`stats` prints a per-brand bar chart and flags any brand with fewer than 5 ads.

---

## Columns

| Column | Required | Notes |
|---|---|---|
| `brand` | **yes** | Use the exact label from `teardown/taxonomy.py` (`lululemon`, `Nike`, `Alo Yoga`, …). Aliases are auto-matched, but exact is safer. |
| `headline` | **yes** | Verbatim. Do not clean up, do not paraphrase. |
| `body` | no | The description line, verbatim. |
| `landing_url` | no | The destination domain shown on the ad. |
| `first_seen` / `last_seen` | no | Shown on the creative. `YYYY-MM-DD`. Nice for "running since" claims. |
| `region` | no | Defaults to `US`. |
| `source_url` | no | **Grab this.** It's what makes every claim auditable in the demo. |
| `captured_by` | no | Your name, so questions find the right person. |
| `platform` | no | Defaults to `google_search`. |

---

## Rules that matter

**Copy verbatim. Never paraphrase.** The extraction quotes exact substrings back into
the matrix. If you retype an ad in your own words, the analysis is analyzing you.

**Watch for commas.** Ad copy contains them. If you're editing the CSV in a text
editor, wrap the field in double quotes: `"Save 20%, today only"`. A spreadsheet
handles this automatically — another reason to use one.

**Take what you get.** If a brand is only running three text ads, that's a finding, not
a failure. Log the three. "Tracksmith runs almost no search advertising" is a real
insight about the category.

**Don't rebalance the set.** Nike will have far more ads than Tracksmith. That's
reality; the `% of brand` view in the dashboard normalizes for it.

**Skip empty shells.** Image-only or video ads with no readable text tell us nothing
about messaging. Text ads only.

---

## Splitting the work

Assign by brand so two people never touch the same rows:

| Person | Brands |
|---|---|
| A | lululemon, Nike, Alo Yoga, Vuori, On, Under Armour |
| B | Gymshark, Arc'teryx, Patagonia, Tracksmith, New Balance, Fabletics |

Keep separate files (`capture_a.csv`, `capture_b.csv`) and point the importer at each:

```bash
python3 -c "from teardown.sources import manual, fixtures; fixtures.write(manual.fetch(csv_path='data/capture_a.csv'), 'capture_a')"
```

Or just merge into one sheet at the end. Either is fine.

---

## When you're done

```bash
python3 -m teardown stats
```

Then delete the synthetic seed file — it exists only so the pipeline runs before real
data lands:

```bash
rm data/ads/000_seed_placeholder.json
```

Re-run and confirm the dashboard's provenance banner shows **zero placeholder rows**:

```bash
python3 -m teardown run --open
```

Commit `data/ads/` and `data/capture.csv`. That committed data is what makes the
classroom demo work with the wifi off.

---

## If you want to try the live API instead

SerpApi offers a licensed Google Ads Transparency Center endpoint, free tier ≈100
searches/month:

```bash
export SERPAPI_KEY=your_key_here && python3 -m teardown ingest --source serpapi --save
```

Field names vary by ad format, so expect to adjust the mapping in
`teardown/sources/serpapi.py`. **Timebox this to 30 minutes.** Manual capture is the
critical path; the API is a bonus that makes a nice line in the demo ("and it can
refresh itself"), not something worth losing an afternoon to.
