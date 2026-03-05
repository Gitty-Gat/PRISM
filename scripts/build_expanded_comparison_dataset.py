"""Build comparison_dataset.csv for REALDATA_EXPANDED_VALIDATION.

Input:
- results/REALDATA_EXPANDED_VALIDATION/analysis/global_experiment_table.csv

Output:
- results/REALDATA_EXPANDED_VALIDATION/comparison/comparison_dataset.csv
"""

from __future__ import annotations

import csv
import os


def main() -> None:
    base = os.path.join("results", "REALDATA_EXPANDED_VALIDATION")
    inp = os.path.join(base, "analysis", "global_experiment_table.csv")
    out_dir = os.path.join(base, "comparison")
    os.makedirs(out_dir, exist_ok=True)

    rows = list(csv.DictReader(open(inp, "r", encoding="utf-8")))

    cols = [
        "experiment_id",
        "time_slice",
        "window_length_min",
        "weighting_method",
        "dependence_method",
        "posterior_mode",
        "posterior_mean",
        "posterior_variance",
        "trade_count",
        "effective_sample_size",
        "evidence_strength",
    ]

    out_path = os.path.join(out_dir, "comparison_dataset.csv")
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in cols})

    print("OK:", out_path, "rows=", len(rows))


if __name__ == "__main__":
    main()
