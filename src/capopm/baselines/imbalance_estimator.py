"""Trade-imbalance probability estimator.

p = buy_volume / (buy_volume + sell_volume)

In our proxy evidence mapping, buy_volume corresponds to y_used (YES evidence)
when BUY->YES and SELL->NO.
"""

from __future__ import annotations


def imbalance_probability(y: float, n: float) -> float:
    y = float(y)
    n = float(n)
    if n <= 0.0:
        return 0.5
    p = y / n
    return max(0.0, min(1.0, p))
