"""Build results/FINAL_EXPERIMENT_SUMMARY.csv

Unifies:
- REALDATA_GRID_RUN analysis/global_experiment_table.csv
- REALDATA_EXPANDED_VALIDATION analysis/global_experiment_table.csv
- Predictive metrics summary from predictive/baseline_prediction_comparison.csv

Stdlib only.
"""

from __future__ import annotations

import csv
import os


def read_csv(path: str) -> list[dict]:
    return list(csv.DictReader(open(path, "r", encoding="utf-8")))


def main() -> None:
    out_path = os.path.join("results", "FINAL_EXPERIMENT_SUMMARY.csv")

    rows = []

    # Grid
    g = read_csv(os.path.join("results", "REALDATA_GRID_RUN", "analysis", "global_experiment_table.csv"))
    for r in g:
        rows.append(
            {
                "campaign": "REALDATA_GRID_RUN",
                "experiment_id": r.get("experiment_id"),
                "time_slice": r.get("time_slice", ""),
                "window_length": r.get("window_length_min"),
                "weighting_method": r.get("weighting_method"),
                "dependence_method": r.get("dependence_method"),
                "posterior_mean": r.get("posterior_mean"),
                "posterior_variance": r.get("posterior_variance"),
                "credible_interval_width": r.get("ci90_width_normapprox"),
                "trade_count": r.get("trade_count"),
                "effective_sample_size": r.get("effective_sample_size"),
                "prediction_horizon": "",
                "prediction_accuracy_metrics": "",
            }
        )

    # Expanded
    e = read_csv(os.path.join("results", "REALDATA_EXPANDED_VALIDATION", "analysis", "global_experiment_table.csv"))
    for r in e:
        rows.append(
            {
                "campaign": "REALDATA_EXPANDED_VALIDATION",
                "experiment_id": r.get("experiment_id"),
                "time_slice": r.get("time_slice", ""),
                "window_length": r.get("window_length_min"),
                "weighting_method": r.get("weighting_method"),
                "dependence_method": r.get("dependence_method"),
                "posterior_mean": r.get("posterior_mean"),
                "posterior_variance": r.get("posterior_variance"),
                "credible_interval_width": r.get("credible_interval_width"),
                "trade_count": r.get("trade_count"),
                "effective_sample_size": r.get("effective_sample_size"),
                "prediction_horizon": "",
                "prediction_accuracy_metrics": "",
            }
        )

    # Predictive summary (attach to campaign-level pseudo-row)
    pred_path = os.path.join(
        "results", "REALDATA_EXPANDED_VALIDATION", "predictive", "baseline_prediction_comparison.csv"
    )
    if os.path.exists(pred_path):
        pred = read_csv(pred_path)
        for r in pred:
            rows.append(
                {
                    "campaign": "PREDICTIVE_EVAL",
                    "experiment_id": r.get("model"),
                    "time_slice": "",
                    "window_length": "",
                    "weighting_method": "",
                    "dependence_method": "",
                    "posterior_mean": "",
                    "posterior_variance": "",
                    "credible_interval_width": "",
                    "trade_count": "",
                    "effective_sample_size": "",
                    "prediction_horizon": r.get("horizon_min"),
                    "prediction_accuracy_metrics": f"brier={r.get('brier')};log_loss={r.get('log_loss')};ece={r.get('ece')};n={r.get('n')}",
                }
            )

    cols = [
        "campaign",
        "experiment_id",
        "time_slice",
        "window_length",
        "weighting_method",
        "dependence_method",
        "posterior_mean",
        "posterior_variance",
        "credible_interval_width",
        "trade_count",
        "effective_sample_size",
        "prediction_horizon",
        "prediction_accuracy_metrics",
    ]

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in cols})

    print("OK:", out_path, "rows=", len(rows))


if __name__ == "__main__":
    main()
