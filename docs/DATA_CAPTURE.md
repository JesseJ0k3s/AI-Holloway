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
