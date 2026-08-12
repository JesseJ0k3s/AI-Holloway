"""Turn whitespace into ad concepts -- the "so what" at the end of the demo.

The analysis says nobody is claiming X. This writes the ads that would claim
it, grounded in what the competition is actually saying so the output is a
wedge rather than generic copy.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import llm, taxonomy
from .schema import Matrix

SYSTEM = """You are a direct-response copywriter briefed by a competitive analyst.

You will be given: a fitness apparel brand, a messaging territory that its \
competitors are NOT occupying, and the actual claims those competitors ARE \
running right now.

Write Google search ads that plant a flag in the empty territory. Constraints:
- Headlines: 30 characters MAX, hard limit. Descriptions: 90 characters MAX.
- Every concept must be defensibly different from the competitor claims shown.
- No superlatives you cannot substantiate ("the best", "#1") unless a proof point supports it.
- Name the proof point the brand would need to make the claim credible. If the \
  brand would have to invent a capability to say this, say so plainly in `requires`.

Return ONLY a JSON array of 3 objects:
[{"headline":"...","description":"...","territory":"...","audience":"...",
  "angle":"one sentence on why this wins","requires":"the proof/capability needed",
  "risk":"the main reason this could fail"}]"""


def concepts_for_whitespace(
    matrix: Matrix,
    for_brand: str,
    top_n: int = 3,
    verbose: bool = True,
) -> List[Dict[str, Any]]:
    """Generate concepts for the top-N emptiest territories."""
    if not llm.have_key():
        if verbose:
            print("  no ANTHROPIC_API_KEY -> skipping concept generation")
        return []

    gaps = [w for w in matrix.whitespace if w["territory"] != "unclassified"][:top_n]
    out: List[Dict[str, Any]] = []

    for gap in gaps:
        rival_claims = _rival_claims(matrix, gap["territory"])
        prompt = _brief(for_brand, gap, rival_claims)
        try:
            raw = llm.complete_json(prompt, system=SYSTEM, max_tokens=1200, temperature=0.7)
        except llm.LLMUnavailable as e:
            if verbose:
                print("  ! concept generation failed for %s: %s" % (gap["territory"], e))
            continue

        if isinstance(raw, dict):
            raw = raw.get("concepts") or [raw]

        for c in raw if isinstance(raw, list) else []:
            if not isinstance(c, dict):
                continue
            c["for_brand"] = for_brand
            c["gap_territory"] = gap["territory"]
            c["opportunity_score"] = gap["opportunity_score"]
            c["generated"] = True  # dashboard badges this as AI-written, not a real ad
            out.append(c)

        if verbose:
            print("  concepts for %-24s (score %.0f)" % (gap["territory"], gap["opportunity_score"]))

    return out


def _rival_claims(matrix: Matrix, territory: str, limit: int = 12) -> List[str]:
    """The loudest claims competitors are actually running, for contrast."""
    claims = []
    for ex in matrix.extractions:
        if ex.get("claim_verbatim"):
            claims.append("%s: %s" % (ex["brand"], ex["claim_verbatim"]))
    return claims[:limit]


def _brief(brand: str, gap: Dict[str, Any], rival_claims: List[str]) -> str:
    territory = gap["territory"]
    return (
        "BRAND: %s\n"
        "EMPTY TERRITORY: %s -- %s\n"
        "Opportunity score: %s/100\n"
        "Brands already here: %s\n"
        "Brands absent: %s\n"
        "Why it is open: %s\n\n"
        "WHAT COMPETITORS ARE ACTUALLY RUNNING RIGHT NOW:\n%s\n\n"
        "Write 3 search ad concepts for %s that own the empty territory."
        % (
            brand,
            territory,
            taxonomy.CLAIM_TERRITORIES.get(territory, ""),
            gap["opportunity_score"],
            ", ".join(gap["brands_present"]) or "nobody",
            ", ".join(gap["brands_absent"][:8]) or "-",
            gap["reasoning"],
            "\n".join("  - " + c for c in rival_claims) or "  (none captured)",
            brand,
        )
    )
