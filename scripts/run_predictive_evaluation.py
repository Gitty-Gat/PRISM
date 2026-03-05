"""Run predictive evaluation + calibration diagnostics (Stage I).

Inputs:
- results/REALDATA_EXPANDED_VALIDATION/predictive/prediction_results.csv

Outputs:
- results/REALDATA_EXPANDED_VALIDATION/predictive/prediction_metrics.csv
- results/REALDATA_EXPANDED_VALIDATION/predictive/calibration_curves.csv
- results/REALDATA_EXPANDED_VALIDATION/predictive/baseline_prediction_comparison.csv

Baselines are computed from the same evidence stream, using:
- imbalance estimator (p=y/n)
- beta baseline (mean of Beta(1+y, 1+(n-y)))
- logistic smoother (from Stage H fit; parametric approximation)

No external deps.
"""

from __future__ import annotations

import csv
import json
import math
import os
from collections import defaultdict

import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.capopm.baselines.imbalance_estimator import imbalance_probability
from src.capopm.baselines.beta_baseline import beta_mean_var


def clamp(p: float, eps: float = 1e-12) -> float:
    return max(eps, min(1.0 - eps, float(p)))


def brier(p: float, y: int) -> float:
    return (float(p) - float(y)) ** 2


def log_loss(p: float, y: int) -> float:
    p = clamp(p)
    if y == 1:
        return -math.log(p)
    return -math.log(1.0 - p)


def load_logistic_model(path: str):
    obj = json.load(open(path, "r", encoding="utf-8"))
    return obj


def sigmoid(z: float) -> float:
    if z >= 0:
        ez = math.exp(-z)
        return 1.0 / (1.0 + ez)
    ez = math.exp(z)
    return ez / (1.0 + ez)


def logistic_predict(model, x1, x2, x3):
    z = model["w0"] + model["w1"] * x1 + model["w2"] * x2 + model["w3"] * x3
    return sigmoid(z)


def calibration_bins(rows, *, n_bins: int = 10):
    # equal-width bins on [0,1]
    bins = [{"count": 0, "sum_p": 0.0, "sum_y": 0.0} for _ in range(n_bins)]
    for r in rows:
        p = float(r["p"])
        y = int(r["y"])
        idx = min(n_bins - 1, max(0, int(p * n_bins)))
        b = bins[idx]
        b["count"] += 1
        b["sum_p"] += p
        b["sum_y"] += y
    out = []
    for i, b in enumerate(bins):
        lo = i / n_bins
        hi = (i + 1) / n_bins
        if b["count"] == 0:
            out.append({"bin_low": lo, "bin_high": hi, "count": 0, "mean_pred": "", "mean_outcome": ""})
        else:
            out.append(
                {
                    "bin_low": lo,
                    "bin_high": hi,
                    "count": b["count"],
                    "mean_pred": b["sum_p"] / b["count"],
                    "mean_outcome": b["sum_y"] / b["count"],
                }
            )
    return out


def ece(curve) -> float:
    tot = sum(int(r["count"]) for r in curve if r["count"] != 0)
    if tot <= 0:
        return 0.0
    acc = 0.0
    for r in curve:
        if not r["count"]:
            continue
        c = int(r["count"])
        acc += (c / tot) * abs(float(r["mean_pred"]) - float(r["mean_outcome"]))
    return acc


def main() -> None:
    base = os.path.join("results", "REALDATA_EXPANDED_VALIDATION", "predictive")
    inp = os.path.join(base, "prediction_results.csv")

    rows = list(csv.DictReader(open(inp, "r", encoding="utf-8")))

    # Load logistic model parameters if present
    model_path = os.path.join("results", "REALDATA_EXPANDED_VALIDATION", "comparison", "logistic_model.json")
    model = None
    if os.path.exists(model_path):
        model = load_logistic_model(model_path)

    # Evaluate by model type and horizon
    metrics = []
    curves = []

    def eval_model(name: str, pred_fn):
        by_h = defaultdict(list)
        for r in rows:
            horizon = int(r["prediction_horizon_min"])
            y = int(r["actual_outcome"])
            p = float(pred_fn(r))
            by_h[horizon].append({"p": p, "y": y})

        for h, items in sorted(by_h.items()):
            bs = sum(brier(it["p"], it["y"]) for it in items) / len(items)
            ll = sum(log_loss(it["p"], it["y"]) for it in items) / len(items)
            curve = calibration_bins(items, n_bins=10)
            _ece = ece(curve)
            metrics.append({"model": name, "horizon_min": h, "brier": bs, "log_loss": ll, "ece": _ece, "n": len(items)})
            for row in curve:
                curves.append({"model": name, "horizon_min": h, **row})

    # PRISM forecast
    eval_model("PRISM", lambda r: clamp(float(r["prediction_probability"])))

    # Baselines (computed from evidence_strength and posterior_mean => proxy buys)
    def baseline_imb(r):
        n = float(r["evidence_strength"])
        buys = float(r["prediction_probability"]) * n
        return clamp(imbalance_probability(buys, n))

    def baseline_beta(r):
        n = float(r["evidence_strength"])
        buys = float(r["prediction_probability"]) * n
        sells = max(0.0, n - buys)
        m, _ = beta_mean_var(1.0 + buys, 1.0 + sells)
        return clamp(m)

    def baseline_logistic(r):
        if model is None:
            return clamp(0.5)
        n = float(r["evidence_strength"])
        buys = float(r["prediction_probability"]) * n
        imb = imbalance_probability(buys, n)
        tc = float(r.get("trade_count") or 0.0)
        x1 = imb
        x2 = math.log1p(max(tc, 0.0))
        x3 = math.log1p(max(n, 0.0))
        return clamp(logistic_predict(model, x1, x2, x3))

    eval_model("imbalance", baseline_imb)
    eval_model("beta_baseline", baseline_beta)
    eval_model("logistic", baseline_logistic)

    metrics_path = os.path.join(base, "baseline_prediction_comparison.csv")
    with open(metrics_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["model", "horizon_min", "brier", "log_loss", "ece", "n"])
        w.writeheader()
        for m in metrics:
            w.writerow(m)

    curve_path = os.path.join(base, "calibration_curves.csv")
    with open(curve_path, "w", newline="", encoding="utf-8") as f:
        cols = ["model", "horizon_min", "bin_low", "bin_high", "count", "mean_pred", "mean_outcome"]
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for c in curves:
            w.writerow({k: c.get(k) for k in cols})

    print("OK:", metrics_path)
    print("OK:", curve_path)


if __name__ == "__main__":
    main()
