"""Aggregate extractions into the messaging matrix and find the whitespace.

Deliberately transparent arithmetic. Somebody in class will ask "how is the
opportunity score calculated?" and the answer needs to fit in one sentence,
not be "the AI decided." Every number here is reproducible by hand.
"""

from __future__ import annotations

import datetime as dt
from collections import Counter, defaultdict
from typing import Dict, List, Optional

from . import taxonomy
from .schema import Ad, Cell, Extraction, Matrix, Whitespace


def build(
    ads: List[Ad],
    extractions: List[Extraction],
    brands: Optional[List[str]] = None,
) -> Matrix:
    ads_by_id = {a.ad_id: a for a in ads}
    brands = brands or sorted({e.brand for e in extractions})
    territories = list(taxonomy.CLAIM_TERRITORIES.keys())
    audiences = list(taxonomy.AUDIENCES.keys())

    # ---- brand x territory -------------------------------------------------
    counts: Dict[str, Counter] = defaultdict(Counter)
    examples: Dict[str, List[Extraction]] = defaultdict(list)

    for ex in extractions:
        counts[ex.brand][ex.primary_claim_territory] += 1
        examples["%s|%s" % (ex.brand, ex.primary_claim_territory)].append(ex)

    brand_totals = {b: sum(counts[b].values()) for b in brands}
    territory_totals = Counter()
    for b in brands:
        for t, n in counts[b].items():
            territory_totals[t] += n
    grand_total = sum(territory_totals.values()) or 1

    cells: List[Cell] = []
    for b in brands:
        for t in territories:
            n = counts[b].get(t, 0)
            ex_list = sorted(
                examples.get("%s|%s" % (b, t), []), key=lambda e: -e.confidence
            )[:3]
            cells.append(
                Cell(
                    brand=b,
                    territory=t,
                    count=n,
                    share_of_brand=round(n / brand_totals[b], 4) if brand_totals.get(b) else 0.0,
                    example_ad_ids=[e.ad_id for e in ex_list],
                    example_claims=[e.claim_verbatim for e in ex_list if e.claim_verbatim],
                )
            )

    # ---- ownership index ---------------------------------------------------
    # How much a brand over- or under-indexes in a territory vs. the category.
    # index = (brand's share of its ads in T) / (category's share of ads in T)
    # 1.0 = at parity. 2.0 = twice as focused on T as the category is.
    ownership: List[Dict[str, object]] = []
    for b in brands:
        if not brand_totals.get(b):
            continue
        for t in territories:
            cat_share = territory_totals.get(t, 0) / grand_total
            brand_share = counts[b].get(t, 0) / brand_totals[b]
            if cat_share > 0 and brand_share > 0:
                ownership.append(
                    {
                        "brand": b,
                        "territory": t,
                        "index": round(brand_share / cat_share, 2),
                        "count": counts[b].get(t, 0),
                    }
                )
    ownership.sort(key=lambda r: -float(r["index"]))

    # ---- audience x territory ---------------------------------------------
    aud_cells: Dict[str, Counter] = defaultdict(Counter)
    aud_brands: Dict[str, set] = defaultdict(set)
    for ex in extractions:
        for a in ex.audiences:
            aud_cells[a][ex.primary_claim_territory] += 1
            aud_brands["%s|%s" % (a, ex.primary_claim_territory)].add(ex.brand)

    audience_matrix = []
    for a in audiences:
        for t in territories:
            n = aud_cells[a].get(t, 0)
            audience_matrix.append(
                {
                    "audience": a,
                    "territory": t,
                    "count": n,
                    "brands": sorted(aud_brands.get("%s|%s" % (a, t), [])),
                }
            )

    # ---- proof point frequency --------------------------------------------
    proof_total = Counter()
    proof_by_brand: Dict[str, Counter] = defaultdict(Counter)
    for ex in extractions:
        for p in ex.proof_points:
            proof_total[p] += 1
            proof_by_brand[p][ex.brand] += 1

    proof_frequency = [
        {
            "proof": p,
            "count": n,
            "share_of_ads": round(n / len(extractions), 4) if extractions else 0.0,
            "brands": dict(proof_by_brand[p]),
            "brand_count": len(proof_by_brand[p]),
            "label": taxonomy.PROOF_TYPES.get(p, p),
        }
        for p, n in proof_total.most_common()
    ]

    # ---- whitespace --------------------------------------------------------
    whitespace = find_whitespace(brands, territories, counts, territory_totals)

    # ---- honesty stats -----------------------------------------------------
    prov = Counter(a.provenance for a in ads)
    engines = Counter(e.engine for e in extractions)
    stats = {
        "n_ads": len(ads),
        "n_brands": len([b for b in brands if brand_totals.get(b)]),
        "n_extractions": len(extractions),
        "provenance": dict(prov),
        "engine": dict(engines),
        "mean_confidence": round(
            sum(e.confidence for e in extractions) / len(extractions), 3
        )
        if extractions
        else 0.0,
        "ads_per_brand": {b: brand_totals.get(b, 0) for b in brands},
        "unclassified": sum(c.get("unclassified", 0) for c in counts.values()),
        "ownership_index": ownership[:25],
    }

    return Matrix(
        generated_at=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        brands=brands,
        territories=territories,
        audiences=audiences,
        cells=[c.to_dict() for c in cells],
        audience_matrix=audience_matrix,
        proof_frequency=proof_frequency,
        whitespace=[w.to_dict() for w in whitespace],
        concepts=[],
        ads=[ads_by_id[e.ad_id].to_dict() for e in extractions if e.ad_id in ads_by_id],
        extractions=[e.to_dict() for e in extractions],
        stats=stats,
    )


def find_whitespace(
    brands: List[str],
    territories: List[str],
    counts: Dict[str, Counter],
    territory_totals: Counter,
) -> List[Whitespace]:
    """Rank territories by how empty they are.

    opportunity_score = 100 * (0.6 * brand_emptiness + 0.4 * volume_emptiness)

      brand_emptiness  = 1 - (brands active in T / total brands)
      volume_emptiness = 1 - (ads in T / ads in the most crowded territory)

    Weighted toward brand count because a territory one brand shouts about is
    more contestable than one that five brands each mention twice.
    """
    active_brands = [b for b in brands if sum(counts[b].values()) > 0]
    n_brands = len(active_brands) or 1
    busiest = max(territory_totals.values()) if territory_totals else 1

    out: List[Whitespace] = []
    for t in territories:
        present = sorted([b for b in active_brands if counts[b].get(t, 0) > 0])
        absent = sorted([b for b in active_brands if counts[b].get(t, 0) == 0])
        total = territory_totals.get(t, 0)

        brand_emptiness = 1.0 - (len(present) / n_brands)
        volume_emptiness = 1.0 - (total / busiest) if busiest else 1.0
        score = 100.0 * (0.6 * brand_emptiness + 0.4 * volume_emptiness)

        if not present:
            reason = "No brand in the set is making this claim at all."
        elif len(present) == 1:
            reason = "%s is alone here -- contestable, or a signal it does not work." % present[0]
        elif len(present) <= max(2, n_brands // 3):
            reason = "Only %d of %d brands play here." % (len(present), n_brands)
        else:
            reason = "Crowded: %d of %d brands are already claiming this." % (len(present), n_brands)

        out.append(
            Whitespace(
                territory=t,
                total_ads=total,
                brands_present=present,
                brands_absent=absent,
                opportunity_score=round(score, 1),
                reasoning=reason,
            )
        )

    out.sort(key=lambda w: -w.opportunity_score)
    return out
