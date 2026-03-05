"""Ingestion pipeline: raw Databento response -> canonical L3Event -> evidence tape.

For probes we start with `schema=trades` and attempt to parse CSV.
This is intentionally conservative and heavily logged.
"""

from __future__ import annotations

import csv
import io
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

from ..schema import L3Event
from ..adapter import _to_side


def parse_trades_csv(body: bytes, *, instrument_id_fallback: str = "UNKNOWN") -> Iterator[L3Event]:
    """Parse a Databento CSV trades response into canonical L3Event.

    This is best-effort because exact column names can vary. We look for:
    - timestamp: ts_recv / ts_event / ts
    - price: price / px
    - size: size / qty
    - side: side / aggressor_side
    - trade_id: trade_id / id
    - instrument_id: instrument_id / symbol

    If side cannot be determined, `side=None` (downstream must handle).
    """

    text = body.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        def pick(*keys: str) -> Optional[str]:
            for k in keys:
                if k in row and row[k] not in (None, ""):
                    return row[k]
            return None

        ts_raw = pick("ts_recv", "ts_event", "ts", "timestamp", "timestamp_ns")
        if ts_raw is None:
            continue
        # Databento pretty timestamps may be ISO; otherwise ns int.
        ts_ns: int
        if ts_raw.isdigit():
            ts_ns = int(ts_raw)
        else:
            # Minimal ISO parser: accept 'YYYY-MM-DDTHH:MM:SS[.frac]'
            # For probe we avoid full datetime libs; unsupported format => skip.
            try:
                import datetime as _dt

                dt = _dt.datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                ts_ns = int(dt.timestamp() * 1e9)
            except Exception:
                continue

        px_raw = pick("price", "px") or "0"
        sz_raw = pick("size", "qty") or "0"
        side_raw = pick("side", "aggressor_side")
        order_id = pick("order_id")
        trade_id = pick("trade_id", "id")
        inst = pick("instrument_id", "symbol", "raw_symbol") or instrument_id_fallback

        try:
            price = float(px_raw)
            size = float(sz_raw)
        except Exception:
            continue

        if size < 0:
            continue

        side = _to_side(side_raw)
        yield L3Event(
            timestamp_ns=ts_ns,
            event_type="TRADE",
            price=price,
            size=size,
            side=side,
            order_id=order_id,
            trade_id=trade_id,
            instrument_id=str(inst),
        )
