"""The data contract for the whole pipeline.

THIS FILE IS THE INTERFACE BETWEEN ALL FIVE WORKSTREAMS. Everyone codes against
these shapes, so nobody has to wait for anybody else's code to exist.

Pipeline stages and who owns what:

    Ad          -> produced by teardown/sources/*      (Workstream 1: Ingestion)
    Extraction  -> produced by teardown/extract.py     (Workstream 2: Extraction)
    Matrix      -> produced by teardown/matrix.py      (Workstream 3: Analysis)
                -> consumed by dashboard/index.html    (Workstream 4: Dashboard)

If you need to change a field here, say so in the group chat BEFORE you push.
Changing this file breaks other people's work; changing anything else does not.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "1.0"


# --------------------------------------------------------------------------
# Stage 1: a single ad, normalized across whatever source it came from
# --------------------------------------------------------------------------


@dataclass
class Ad:
    """One ad creative, normalized.

    Google Ads Transparency Center search ads are text: a headline and a
    description. Other sources may fill in more fields; anything unknown stays
    None rather than being guessed at.
    """

    brand: str  # canonical brand name, e.g. "lululemon"
    platform: str  # "google_search", "google_display", "meta", ...
    headline: str  # the ad's primary line
    body: str = ""  # description / secondary copy

    ad_id: str = ""  # source's own id; we generate one if absent
    advertiser_id: str = ""  # e.g. Google advertiser id (AR...)
    cta: Optional[str] = None
    landing_url: Optional[str] = None
    creative_type: str = "text"  # text | image | video
    media_url: Optional[str] = None

    first_seen: Optional[str] = None  # ISO date, from the transparency center
    last_seen: Optional[str] = None
    still_running: Optional[bool] = None
    regions: List[str] = field(default_factory=list)  # e.g. ["US"]

    # PROVENANCE IS NOT OPTIONAL. The dashboard badges anything that is not
    # real captured data, so we never show the class a fake ad as if it were
    # something the brand is actually running.
    #   "api"         - pulled from a live API (SerpApi et al)
    #   "captured"    - a human read it off the Transparency Center and logged it
    #   "placeholder" - invented scaffolding data, for wiring the pipeline only
    provenance: str = "placeholder"
    captured_at: Optional[str] = None  # ISO timestamp of when we pulled it
    source_url: Optional[str] = None  # link back so claims are auditable
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.ad_id:
            self.ad_id = self.fingerprint()

    def fingerprint(self) -> str:
        """Stable id from the copy itself, so re-captures dedupe cleanly."""
        raw = "|".join([self.brand, self.platform, self.headline, self.body])
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]

    @property
    def full_text(self) -> str:
        return (self.headline + "\n" + self.body).strip()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Ad":
        known = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**known)


# --------------------------------------------------------------------------
# Stage 2: what Claude read out of a single ad
# --------------------------------------------------------------------------


@dataclass
class Extraction:
    """Structured messaging read of one ad. One Extraction per Ad."""

    ad_id: str
    brand: str

    # The single most important output: which messaging territory this ad
    # is playing in. Must be a value from taxonomy.CLAIM_TERRITORIES.
    primary_claim_territory: str = "unclassified"
    secondary_claim_territories: List[str] = field(default_factory=list)

    # Verbatim claim, quoted from the ad. Never paraphrased -- we want to be
    # able to point at the exact words on a slide.
    claim_verbatim: str = ""

    audiences: List[str] = field(default_factory=list)  # taxonomy.AUDIENCES
    proof_points: List[str] = field(default_factory=list)  # taxonomy.PROOF_TYPES
    proof_verbatim: List[str] = field(default_factory=list)

    funnel_stage: str = "consideration"  # awareness | consideration | conversion
    tone: str = "unclassified"  # taxonomy.TONES
    has_offer: bool = False
    offer_verbatim: str = ""

    confidence: float = 0.0  # 0..1, how sure the extractor was
    engine: str = "mock"  # "claude" | "mock" -- how this was produced
    rationale: str = ""  # one line, for spot-checking in the dashboard

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Extraction":
        known = {k: v for k, v in d.items() if k in cls.__dataclass_fields__}
        return cls(**known)


# --------------------------------------------------------------------------
# Stage 3: the aggregate the dashboard renders
# --------------------------------------------------------------------------


@dataclass
class Cell:
    """One cell of the brand x claim-territory matrix."""

    brand: str
    territory: str
    count: int = 0
    share_of_brand: float = 0.0  # what % of this brand's ads live here
    example_ad_ids: List[str] = field(default_factory=list)
    example_claims: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Whitespace:
    """A gap: a territory (optionally x audience) nobody is credibly occupying."""

    territory: str
    audience: Optional[str] = None
    total_ads: int = 0  # how many ads across all brands land here
    brands_present: List[str] = field(default_factory=list)
    brands_absent: List[str] = field(default_factory=list)
    opportunity_score: float = 0.0  # 0..100, higher = emptier
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Matrix:
    """Everything the dashboard needs, in one JSON blob."""

    schema_version: str = SCHEMA_VERSION
    generated_at: str = ""
    brands: List[str] = field(default_factory=list)
    territories: List[str] = field(default_factory=list)
    audiences: List[str] = field(default_factory=list)

    cells: List[Dict[str, Any]] = field(default_factory=list)
    audience_matrix: List[Dict[str, Any]] = field(default_factory=list)
    proof_frequency: List[Dict[str, Any]] = field(default_factory=list)
    whitespace: List[Dict[str, Any]] = field(default_factory=list)
    concepts: List[Dict[str, Any]] = field(default_factory=list)

    ads: List[Dict[str, Any]] = field(default_factory=list)
    extractions: List[Dict[str, Any]] = field(default_factory=list)

    # Honesty metadata, surfaced in the dashboard header.
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
