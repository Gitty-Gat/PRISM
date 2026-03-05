"""Posterior update modes for real-data demos.

This stays outside the Bayesian core; it uses the exposed conjugate update
functions from likelihood/pricing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Tuple

from ..likelihood import beta_binomial_update
from ..pricing import posterior_prices


@dataclass(frozen=True)
class PosteriorPoint:
    t_ns: int
    alpha: float
    beta: float
    p_hat: float


def update_single_window(alpha0: float, beta0: float, y: float, n: float, t_ns: int) -> List[PosteriorPoint]:
    a, b = beta_binomial_update(alpha0, beta0, y, n)
    p, _ = posterior_prices(a, b)
    return [PosteriorPoint(t_ns=t_ns, alpha=a, beta=b, p_hat=p)]


def update_sequential(alpha0: float, beta0: float, tape: Iterable, *, bucket_ns: int = 1_000_000_000) -> List[PosteriorPoint]:
    """Sequential update by time buckets. Tape entries must include timestamp_ns, side, size."""

    points: List[PosteriorPoint] = []
    a, b = float(alpha0), float(beta0)
    cur_bucket = None
    y = 0.0
    n = 0.0

    def flush(t_ns: int):
        nonlocal a, b, y, n
        if n <= 0:
            return
        a, b = beta_binomial_update(a, b, y, n)
        p, _ = posterior_prices(a, b)
        points.append(PosteriorPoint(t_ns=t_ns, alpha=a, beta=b, p_hat=p))
        y = 0.0
        n = 0.0

    for tr in tape:
        ts = int(getattr(tr, "timestamp_ns"))
        bucket = ts - (ts % bucket_ns)
        if cur_bucket is None:
            cur_bucket = bucket
        if bucket != cur_bucket:
            flush(cur_bucket)
            cur_bucket = bucket

        size = float(getattr(tr, "size"))
        side = getattr(tr, "side")
        if side == "YES":
            y += size
        n += size

    if cur_bucket is not None:
        flush(cur_bucket)

    return points


def update_rolling(alpha0: float, beta0: float, tape: List, *, window_ns: int = 60_000_000_000, step_ns: int = 1_000_000_000) -> List[PosteriorPoint]:
    """Rolling-window posterior with fixed prior each step."""

    tape_sorted = sorted(tape, key=lambda tr: int(getattr(tr, "timestamp_ns")))
    if not tape_sorted:
        return []
    t0 = int(getattr(tape_sorted[0], "timestamp_ns"))
    t1 = int(getattr(tape_sorted[-1], "timestamp_ns"))

    points: List[PosteriorPoint] = []
    left = 0
    right = 0
    y = 0.0
    n = 0.0

    # Precompute prefix? For simplicity small runs: two-pointer with recompute.
    t = t0
    while t <= t1:
        start = t - window_ns
        # Advance left
        while left < len(tape_sorted) and int(getattr(tape_sorted[left], "timestamp_ns")) < start:
            left += 1
        # Advance right
        while right < len(tape_sorted) and int(getattr(tape_sorted[right], "timestamp_ns")) <= t:
            right += 1

        y = 0.0
        n = 0.0
        for i in range(left, right):
            tr = tape_sorted[i]
            size = float(getattr(tr, "size"))
            if getattr(tr, "side") == "YES":
                y += size
            n += size

        if n > 0:
            a, b = beta_binomial_update(alpha0, beta0, y, n)
            p, _ = posterior_prices(a, b)
            points.append(PosteriorPoint(t_ns=t, alpha=a, beta=b, p_hat=p))

        t += step_ns

    return points
