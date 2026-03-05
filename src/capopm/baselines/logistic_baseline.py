"""Lightweight logistic regression baseline (no ML deps).

IMPORTANT: This is a *descriptive proxy* baseline.
Because we do not have outcome labels in the real-data proxy setting, the
"training" target defaults to PRISM's posterior_mean for a given dataset.
This yields a smoothed parametric approximation of PRISM behavior, not a
predictive model.

Features (suggested):
- imbalance p = y/n
- log(trade_count+1)
- log(evidence_strength+1)

We fit via simple gradient descent with L2 regularization.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def sigmoid(z: float) -> float:
    if z >= 0:
        ez = math.exp(-z)
        return 1.0 / (1.0 + ez)
    ez = math.exp(z)
    return ez / (1.0 + ez)


@dataclass
class LogisticModel:
    w0: float
    w1: float
    w2: float
    w3: float

    def predict(self, x1: float, x2: float, x3: float) -> float:
        z = self.w0 + self.w1 * x1 + self.w2 * x2 + self.w3 * x3
        return sigmoid(z)


def fit_logistic(
    X: list[tuple[float, float, float]],
    y: list[float],
    *,
    lr: float = 0.1,
    steps: int = 2000,
    l2: float = 1e-3,
) -> LogisticModel:
    # initialize
    w0 = 0.0
    w1 = 0.0
    w2 = 0.0
    w3 = 0.0

    n = len(X)
    if n == 0:
        return LogisticModel(0.0, 0.0, 0.0, 0.0)

    for _ in range(steps):
        g0 = g1 = g2 = g3 = 0.0
        for (x1, x2, x3), yt in zip(X, y):
            p = sigmoid(w0 + w1 * x1 + w2 * x2 + w3 * x3)
            # squared error loss gradient (stable; target is continuous)
            err = (p - yt)
            dp = p * (1.0 - p)
            g = 2.0 * err * dp
            g0 += g
            g1 += g * x1
            g2 += g * x2
            g3 += g * x3

        # L2
        g0 += l2 * w0
        g1 += l2 * w1
        g2 += l2 * w2
        g3 += l2 * w3

        w0 -= lr * (g0 / n)
        w1 -= lr * (g1 / n)
        w2 -= lr * (g2 / n)
        w3 -= lr * (g3 / n)

    return LogisticModel(w0, w1, w2, w3)
