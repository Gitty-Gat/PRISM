"""Naive Beta baseline update.

alpha = alpha0 + buys
beta  = beta0 + sells

Mean/variance are analytic.
"""

from __future__ import annotations


def beta_update(alpha0: float, beta0: float, buys: float, sells: float) -> tuple[float, float]:
    return float(alpha0) + float(buys), float(beta0) + float(sells)


def beta_mean_var(alpha: float, beta: float) -> tuple[float, float]:
    a = float(alpha)
    b = float(beta)
    s = a + b
    if s <= 0:
        return 0.5, 0.0
    m = a / s
    v = (a * b) / (s * s * (s + 1.0))
    return m, v
