# The 8-Minute Demo

Owned by WS5. Rehearse it twice on Day 2, timed.

**The one thing to remember:** the class has seen plenty of "we asked ChatGPT and it
said things" demos. What makes this different is that every claim on screen traces back
to an ad a real brand is really running, and you can click through to prove it. Lean on
that hard.

---

## Structure

**0:00 — The problem (45s)**
Don't open the tool. Open with the question.

> "A brand manager at Vuori wants to know what they're up against. Today that means an
> intern with 40 browser tabs, three days, and a slide deck that's stale the moment it's
> finished. We built the thing that does it in four minutes."

**0:45 — What we pulled (60s)**
Show the KPI row and the provenance banner.

> "N live search ads. 12 brands. Pulled from Google's Ads Transparency Center — these
> are ads running right now, not a case study from 2019."

Point at the provenance badge. **Say the honesty line out loud:**
> "Every ad here is tagged with where it came from. Nothing on this screen is invented."

That sentence buys you credibility for the whole rest of the demo.

**1:45 — The matrix (2 min) — the core**
The heatmap. Let it sit for three seconds before you talk.

> "Rows are brands. Columns are what they're claiming. Dark means they're pushing hard."

Then read one row and one column aloud — a specific finding beats a general one:
> "Patagonia is the only brand in twelve making a sustainability argument in search."

**Now click a cell.** This is the moment the demo earns trust:
> "And I can prove it — here are the actual ads behind that number."

**3:45 — Proof points (60s)**
> "Across all N ads, free shipping shows up X times. That's not a differentiator
> anymore, that's a tollbooth. What almost nobody uses is [Y] — one brand, that's it."

**4:45 — The whitespace (90s)**
The ranked gap list.

> "Here's the argument nobody in this category is making."

Explain the score in one sentence — you'll get asked:
> "Sixty percent how many brands are absent, forty percent how little volume is there.
> Plain arithmetic. The AI classified the ads; division did the rest."

**6:15 — The payoff (90s)**
The generated concepts tab.

> "So we asked it to write the ads nobody is running — briefed on exactly what the
> competition is saying, so it writes a wedge and not a platitude."

Read one concept aloud, including the `requires` line:
> "And notice it tells us what proof Vuori would need to actually make this claim
> credible. It's not just copy, it's a brief."

**7:45 — Land it (15s)**
> "Four minutes, twelve competitors, and a recommendation with the receipts attached."

---

## Q&A prep

**"How accurate is the AI's classification?"**
Have the number ready. *"We hand-labeled 20 ads and Claude agreed on 17."* This is the
question most likely to be asked and the easiest to win.

**"Couldn't you just do this manually?"**
Yes — in about three days, and it'd be stale immediately. Re-running this is one
command.

**"What about Meta/TikTok/YouTube?"**
Real limitation, own it. Search ads are one surface. The ingestion layer is adapter-
based specifically so another platform is a new file, not a rewrite.

**"Does ad presence equal spend?"**
No, and we don't claim it does. We measure what they're *saying*, not what they're
paying. That's a stated limit, in the README.

**"What if the AI is wrong about an ad?"**
Every cell links to the verbatim copy, and the All Ads tab shows the whole set. A human
can overrule any call. That's a design decision, not an accident.

---

## Rules for the room

**Screenshots for the deck, live tool for one moment only.** Pick the cell-click as your
live beat. Everything else is a slide. Live navigation is where demos die.

**Open `dist/teardown.html` from the local disk.** One file, zero dependencies, no wifi.
Have it on a USB stick and in your email.

**Turn the wifi off during the dress rehearsal.** If it still works, you're safe.

**Don't demo the code.** Nobody wants to watch a terminal. If someone asks how it works,
the README diagram is one slide.
