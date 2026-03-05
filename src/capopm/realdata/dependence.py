"""Dependence adjustments for real-data evidence streams.

We cannot assume i.i.d. microstructure events; we provide conservative ESS
(effective sample size) proxies.
"""

from __future__ import annotations

from typing import Iterable, Tuple


def ess_weights(weights: Iterable[float]) -> float:
    """Weight-based ESS: (sum w)^2 / sum w^2."""

    s1 = 0.0
    s2 = 0.0
    for w in weights:
        w = float(w)
        if w < 0:
            continue
        s1 += w
        s2 += w * w
    if s2 <= 0.0:
        return 0.0
    return (s1 * s1) / s2


def apply_dependence_adjustment(y: float, n: float, *, mode: str, ess: float | None = None) -> Tuple[float, float, dict]:
    """Return adjusted (y,n) and diagnostics.

    Modes:
    - RAW_N: no change
    - EFFECTIVE_N_STAR: shrink evidence totals so n becomes ess (preserving y/n ratio)

    This is a *proxy* adjustment for stability demos.
    """

    mode_u = str(mode).upper()
    if mode_u == "RAW_N":
        return float(y), float(n), {"mode": mode_u, "ess": ess}

    if mode_u == "EFFECTIVE_N_STAR":
        if ess is None:
            raise ValueError("ess required for EFFECTIVE_N_STAR")
        ess = float(max(ess, 0.0))
        if n <= 0.0:
            return 0.0, 0.0, {"mode": mode_u, "ess": ess, "note": "n<=0"}
        frac = float(y) / float(n)
        n_star = ess
        y_star = frac * n_star
        return y_star, n_star, {"mode": mode_u, "ess": ess, "shrink_factor": (n_star / n)}

    raise ValueError(f"Unknown dependence mode: {mode}")
