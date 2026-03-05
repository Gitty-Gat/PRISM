"""Databento (or JSONL fixtures) -> canonical L3Event stream.

This module is intentionally narrow: parsing + unit normalization only.
Trade reconstruction and evidence mapping happen elsewhere.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Iterable, Iterator, Optional

from .schema import L3Event, Side


ADAPTER_VERSION = "realdata_adapter_v1"


def _to_side(val: Optional[str]) -> Optional[Side]:
    if val is None:
        return None
    v = str(val).upper()
    if v in {"BUY", "B"}:
        return "BUY"  # type: ignore[return-value]
    if v in {"SELL", "S"}:
        return "SELL"  # type: ignore[return-value]
    return None


def parse_jsonl_events(path: str) -> Iterator[L3Event]:
    """Parse a deterministic JSONL file into canonical L3Event records.

    Expected per-line keys (requested contract):
    - timestamp_ns, event_type, price, size, side, order_id, trade_id, instrument_id

    This function is used for the repo-included smoke dataset under `data/test_l3/`.
    """

    with open(path, "r", encoding="utf-8") as f:
        for line_no, raw in enumerate(f, start=1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except Exception as exc:
                raise ValueError(f"Invalid JSON on line {line_no}: {exc}") from exc

            ts = int(obj["timestamp_ns"])
            event_type = str(obj["event_type"])
            price = float(obj.get("price", 0.0))
            size = float(obj.get("size", 0.0))
            side = _to_side(obj.get("side"))
            order_id = obj.get("order_id")
            trade_id = obj.get("trade_id")
            instrument_id = str(obj.get("instrument_id", "UNKNOWN"))

            if ts <= 0:
                raise ValueError(f"timestamp_ns must be positive (line {line_no})")
            if size < 0:
                raise ValueError(f"size must be nonnegative (line {line_no})")

            yield L3Event(
                timestamp_ns=ts,
                event_type=event_type,
                price=price,
                size=size,
                side=side,
                order_id=str(order_id) if order_id is not None else None,
                trade_id=str(trade_id) if trade_id is not None else None,
                instrument_id=instrument_id,
            )


def event_to_dict(ev: L3Event) -> dict:
    return asdict(ev)


# Placeholder for Databento integration.
# In Stage B.4 we keep the interface stable; provider-specific parsing should
# live behind a function that yields canonical L3Event.

def databento_to_events(records: Iterable[object]) -> Iterator[L3Event]:
    """Adapter stub for Databento records.

    Not implemented in the smoke phase; intentionally left as a narrow surface.

    Requirements when implemented:
    - deterministic parsing
    - explicit unit normalization (timestamp/price/size)
    - strict field presence checks
    """

    raise NotImplementedError("Databento adapter not implemented in smoke dataset phase")
