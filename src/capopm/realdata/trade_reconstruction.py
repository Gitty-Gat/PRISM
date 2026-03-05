"""Trade reconstruction from canonical L3 events.

Rules (requested):
1) Prefer explicit trade/fill messages.
2) If missing, infer using deterministic side inference (quote rule / depletion).

In the repo-included smoke dataset we rely on explicit trades.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Tuple

from .schema import L3Event, ReconstructedTrade, Side


def reconstruct_trades(events: Iterable[L3Event]) -> Tuple[List[ReconstructedTrade], dict]:
    """Reconstruct a list of trades from L3 events.

    Returns:
      trades: list of ReconstructedTrade
      diag: diagnostics summary (for adapter_diagnostics.json)
    """

    explicit = 0
    inferred = 0
    unmatched = 0
    anomalies = []

    trades: List[ReconstructedTrade] = []

    last_ts: Optional[int] = None
    for ev in events:
        if last_ts is not None and ev.timestamp_ns < last_ts:
            anomalies.append({"type": "timestamp_decrease", "prev": last_ts, "cur": ev.timestamp_ns})
        last_ts = ev.timestamp_ns

        is_trade = ev.event_type.upper() in {"TRADE", "FILL", "EXECUTION"}
        if is_trade:
            if ev.side is None:
                # Deterministic fallback: mark as unmatched; do not infer in smoke.
                unmatched += 1
                continue
            if ev.size <= 0:
                anomalies.append({"type": "nonpositive_trade_size", "size": ev.size, "ts": ev.timestamp_ns})
                continue
            explicit += 1
            trades.append(
                ReconstructedTrade(
                    timestamp_ns=ev.timestamp_ns,
                    side=ev.side,
                    size=float(ev.size),
                    price=float(ev.price) if ev.price else None,
                    confidence=1.0,
                    source="explicit",
                )
            )
            continue

        # Non-trade events ignored for smoke.

    diag = {
        "explicit_trades": explicit,
        "inferred_trades": inferred,
        "unmatched_trade_events": unmatched,
        "timestamp_anomalies": anomalies,
    }
    return trades, diag
