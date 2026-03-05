"""Evidence tape generation for CAPOPM from reconstructed trades.

Outputs a tape compatible with `likelihood.counts_from_trade_tape`.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from .schema import EvidenceTapeEntry, EvidenceTapeV1, ReconstructedTrade


def trades_to_evidence_tape(
    trades: List[ReconstructedTrade],
    *,
    instrument: str,
    source: str,
    adapter_version: str,
    implied_yes_before_default: float = 0.5,
) -> Tuple[List[EvidenceTapeEntry], EvidenceTapeV1]:
    """Convert reconstructed trades to CAPOPM evidence tape.

    Mapping:
    - BUY -> YES
    - SELL -> NO
    - size is passed through (must be >0)

    Returns:
      tape: list[EvidenceTapeEntry]
      meta: EvidenceTapeV1 metadata
    """

    tape: List[EvidenceTapeEntry] = []
    for tr in trades:
        if tr.size <= 0:
            continue
        side = "YES" if tr.side == "BUY" else "NO"
        tape.append(
            EvidenceTapeEntry(
                timestamp_ns=tr.timestamp_ns,
                side=side,  # type: ignore[arg-type]
                size=float(tr.size),
                implied_yes_before=float(implied_yes_before_default),
            )
        )

    meta = EvidenceTapeV1(
        version="capopm.realdata.evidence.v1",
        instrument=instrument,
        source=source,
        adapter_version=adapter_version,
        events_processed=0,  # caller fills
        trades_reconstructed=len(trades),
        diagnostics_summary={},
    )
    return tape, meta


def evidence_meta_to_dict(meta: EvidenceTapeV1) -> Dict:
    return {
        "version": meta.version,
        "instrument": meta.instrument,
        "source": meta.source,
        "adapter_version": meta.adapter_version,
        "events_processed": meta.events_processed,
        "trades_reconstructed": meta.trades_reconstructed,
        "diagnostics_summary": meta.diagnostics_summary,
    }
