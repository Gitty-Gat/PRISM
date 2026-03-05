"""Evidence weighting modes for real-data trade tapes (Stage B.4).

These functions operate *only* on adapter-layer objects and output sizes that
feed `counts_from_trade_tape()`.

No dominance posture: prefer capped/sublinear transforms over linear raw size.
"""

from __future__ import annotations

import math
from typing import Callable, Dict


def weight_raw(_: float) -> float:
    return 1.0


def weight_size(size: float) -> float:
    return float(size)


def weight_capped(size: float, *, cap: float = 10.0) -> float:
    return float(min(float(size), float(cap)))


def weight_sublinear_sqrt(size: float) -> float:
    return float(math.sqrt(max(float(size), 0.0)))


def weight_sublinear_log(size: float, *, q0: float = 1.0, w_max: float = 10.0) -> float:
    x = max(float(size), 0.0)
    q0 = max(float(q0), 1e-12)
    w = math.log1p(x / q0)
    return float(min(w, float(w_max)))


def get_weight_fn(mode: str, cfg: Dict) -> Callable[[float], float]:
    mode = str(mode).upper()
    if mode == "RAW":
        return weight_raw
    if mode == "SIZE_WEIGHTED":
        return weight_size
    if mode == "CAPPED":
        cap = float(cfg.get("cap", 10.0))
        return lambda s: weight_capped(s, cap=cap)
    if mode == "SUBLINEAR":
        kind = str(cfg.get("sublinear_kind", "sqrt")).lower()
        if kind == "sqrt":
            return weight_sublinear_sqrt
        q0 = float(cfg.get("q0", 1.0))
        w_max = float(cfg.get("w_max", 10.0))
        return lambda s: weight_sublinear_log(s, q0=q0, w_max=w_max)
    if mode == "IMBALANCE_ADJUSTED":
        # Placeholder: true imbalance needs MBP. For trades-only, we treat
        # imbalance as signed-flow magnitude weighting.
        return weight_sublinear_log
    raise ValueError(f"Unknown weighting mode: {mode}")
