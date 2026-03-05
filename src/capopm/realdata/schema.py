"""Canonical schemas for Stage B.4 real-data ingestion.

These dataclasses are designed to be:
- minimal but explicit
- deterministic/serializable
- compatible with the existing CAPOPM evidence interface

Core compatibility target:
- `src/capopm/likelihood.py::counts_from_trade_tape(trade_tape)` expects objects with:
  - `trade.size` (float > 0)
  - `trade.side` ("YES" | "NO")
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional, Dict, Any


Side = Literal["BUY", "SELL"]
YesNoSide = Literal["YES", "NO"]


@dataclass(frozen=True)
class L3Event:
    """Canonical L3 event.

    Fields match the requested contract.
    Units are normalized by the adapter:
    - timestamp_ns: int nanoseconds since epoch
    - price: float (native price units, e.g. dollars)
    - size: float (native size units, e.g. shares/contracts)
    """

    timestamp_ns: int
    event_type: str
    price: float
    size: float
    side: Optional[Side]
    order_id: Optional[str]
    trade_id: Optional[str]
    instrument_id: str


@dataclass(frozen=True)
class ReconstructedTrade:
    """Reconstructed trade (execution) derived from L3 events."""

    timestamp_ns: int
    side: Side
    size: float
    price: Optional[float] = None
    # confidence is a deterministic scalar in [0,1]
    confidence: float = 1.0
    source: str = "explicit"  # "explicit" | "inferred"


@dataclass(frozen=True)
class EvidenceTapeEntry:
    """CAPOPM-compatible evidence tape entry.

    Required for `counts_from_trade_tape`:
    - side in {YES, NO}
    - size > 0

    We additionally store timestamp_ns to support sequential/dynamic extensions
    and auditing.

    Stage 1 behavioral weighting optionally uses `implied_yes_before`; if you
    later want Stage 1 on real data without modifying core, populate it.
    """

    timestamp_ns: int
    side: YesNoSide
    size: float
    implied_yes_before: float = 0.5


@dataclass(frozen=True)
class EvidenceTapeV1:
    """Versioned evidence contract: capopm.realdata.evidence.v1."""

    version: str  # must be "capopm.realdata.evidence.v1"
    instrument: str
    source: str
    adapter_version: str
    events_processed: int
    trades_reconstructed: int
    diagnostics_summary: Dict[str, Any]
