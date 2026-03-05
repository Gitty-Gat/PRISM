"""Compute baseline comparisons vs PRISM for expanded validation.

Outputs:
- results/REALDATA_EXPANDED_VALIDATION/comparison/model_comparison.csv

Baselines:
- imbalance estimator p=y/n
- naive beta baseline with alpha=1+y, beta=1+(n-y)
- logistic baseline fitted to PRISM posterior_mean (descriptive proxy)

No external dependencies.
"""

from __future__ import annotations

import csv
import math
import os

from src.capopm.baselines.imbalance_estimator import imbalance_probability
from src.capopm.baselines.beta_baseline import beta_mean_var
from src.capopm.baselines.logistic_baseline import fit_logistic


def safe_float(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default


def main() -> None:
    base = os.path.join("results", "REALDATA_EXPANDED_VALIDATION")
    inp = os.path.join(base, "comparison", "comparison_dataset.csv")
    out_dir = os.path.join(base, "comparison")
    os.makedirs(out_dir, exist_ok=True)

    rows = list(csv.DictReader(open(inp, "r", encoding="utf-8")))

    # Build features and target for logistic fit (target = PRISM mean)
    X = []
    y = []
    for r in rows:
        p = safe_float(r.get("posterior_mean"), 0.5)
        n = safe_float(r.get("evidence_strength"), 0.0)
        yy = p * n
        imb = imbalance_probability(yy, n)
        tc = safe_float(r.get("trade_count"), 0.0)
        x1 = imb
        x2 = math.log1p(max(tc, 0.0))
        x3 = math.log1p(max(n, 0.0))
        X.append((x1, x2, x3))
        y.append(p)

    model = fit_logistic(X, y, lr=0.2, steps=1500, l2=1e-3)

    out_path = os.path.join(out_dir, "model_comparison.csv")
    cols = [
        "experiment_id",
        "time_slice",
        "window_length_min",
        "weighting_method",
        "dependence_method",
        "posterior_mode",
        "prism_mean",
        "prism_var",
        "imbalance_p",
        "beta_baseline_mean",
        "beta_baseline_var",
        "logistic_p",
        "abs_diff_imb",
        "abs_diff_beta",
        "abs_diff_logistic",
        "var_ratio_beta_to_prism",
    ]

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()

        for r in rows:
            prism_m = safe_float(r.get("posterior_mean"), 0.5)
            prism_v = safe_float(r.get("posterior_variance"), 0.0)
            n = safe_float(r.get("evidence_strength"), 0.0)
            y_used = safe_float(r.get("posterior_mean"), 0.5) * n
            sells = max(0.0, n - y_used)

            imb = imbalance_probability(y_used, n)
            beta_m, beta_v = beta_mean_var(1.0 + y_used, 1.0 + sells)

            tc = safe_float(r.get("trade_count"), 0.0)
            x1 = imb
            x2 = math.log1p(max(tc, 0.0))
            x3 = math.log1p(max(n, 0.0))
            logp = model.predict(x1, x2, x3)

            w.writerow(
                {
                    "experiment_id": r.get("experiment_id"),
                    "time_slice": r.get("time_slice"),
                    "window_length_min": r.get("window_length_min"),
                    "weighting_method": r.get("weighting_method"),
                    "dependence_method": r.get("dependence_method"),
                    "posterior_mode": r.get("posterior_mode"),
                    "prism_mean": prism_m,
                    "prism_var": prism_v,
                    "imbalance_p": imb,
                    "beta_baseline_mean": beta_m,
                    "beta_baseline_var": beta_v,
                    "logistic_p": logp,
                    "abs_diff_imb": abs(prism_m - imb),
                    "abs_diff_beta": abs(prism_m - beta_m),
                    "abs_diff_logistic": abs(prism_m - logp),
                    "var_ratio_beta_to_prism": (beta_v / prism_v) if prism_v > 0 else "",
                }
            )

    # write model params
    with open(os.path.join(out_dir, "logistic_model.json"), "w", encoding="utf-8") as f:
        import json

        json.dump({"w0": model.w0, "w1": model.w1, "w2": model.w2, "w3": model.w3}, f, indent=2)

    print("OK:", out_path, "rows=", len(rows))


if __name__ == "__main__":
    main()
