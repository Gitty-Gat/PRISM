"""Reproduce PRISM analysis outputs from saved artifacts (no API calls).

This script:
- recomputes aggregation tables for grid + expanded campaigns
- regenerates visualization suites (grid, expanded, predictive, comparisons)
- rebuilds FINAL_EXPERIMENT_SUMMARY.csv

It does not execute Databento downloads.

Usage:
  python3 scripts/reproduce_prism_results.py
"""

from __future__ import annotations

import os
import subprocess
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> None:
    os.chdir(REPO_ROOT)

    # Aggregations
    run([sys.executable, "scripts/realdata_grid_aggregate.py"])
    run([sys.executable, "scripts/realdata_expanded_aggregate.py"])

    # Viz suites
    run([sys.executable, "scripts/realdata_grid_viz_suite.py"])
    run([sys.executable, "scripts/realdata_expanded_viz_suite.py"])
    run([sys.executable, "scripts/realdata_grid_animation_frames.py"])
    run([sys.executable, "scripts/realdata_expanded_animation_frames.py"])

    # Baseline comparisons + viz
    if os.path.exists("results/REALDATA_EXPANDED_VALIDATION/analysis/global_experiment_table.csv"):
        run([sys.executable, "scripts/build_expanded_comparison_dataset.py"])
        run([sys.executable, "scripts/run_expanded_baseline_comparison.py"])
        run([sys.executable, "scripts/baseline_comparison_viz.py"])

    # Predictive evaluation + viz
    if os.path.exists("results/REALDATA_EXPANDED_VALIDATION/summary.json"):
        run([sys.executable, "scripts/build_predictive_dataset.py"])
        run([sys.executable, "scripts/run_predictive_evaluation.py"])
        run([sys.executable, "scripts/predictive_viz_suite.py"])

    # Unified summary
    run([sys.executable, "scripts/build_final_experiment_summary.py"])

    print("OK: reproduction completed")


if __name__ == "__main__":
    main()
