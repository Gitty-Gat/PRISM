"""Aggregate REALDATA_GRID_RUN experiment outputs into global analysis tables.

Outputs:
- results/REALDATA_GRID_RUN/analysis/global_experiment_table.csv
- results/REALDATA_GRID_RUN/analysis/posterior_metrics.csv
- results/REALDATA_GRID_RUN/analysis/evidence_statistics.csv

No heavy dependencies; pure Python.
"""

from __future__ import annotations

import csv
import json
import os
from glob import glob


def beta_mean_var(a: float, b: float) -> tuple[float, float]:
    a = float(a)
    b = float(b)
    s = a + b
    if s <= 0:
        return 0.5, 0.0
    mean = a / s
    var = (a * b) / (s * s * (s + 1.0))
    return mean, var


def normal_ci_width(mean: float, var: float, z: float = 1.645) -> float:
    # Clamp to [0,1] interval width under normal approximation.
    import math

    sd = math.sqrt(max(var, 0.0))
    lo = max(0.0, mean - z * sd)
    hi = min(1.0, mean + z * sd)
    return hi - lo


def parse_experiment_dir(d: str) -> dict:
    with open(os.path.join(d, "summary.json"), "r", encoding="utf-8") as f:
        s = json.load(f)

    exp_id = s.get("experiment_id") or os.path.basename(d)
    window = int(s.get("window_minutes"))
    wm = s.get("weighting_mode")
    dm = s.get("dependence_mode")
    pm = s.get("posterior_mode")

    # Evidence stats
    ev = s.get("evidence_counts", {})
    y_used = float(ev.get("y_used", 0.0))
    n_used = float(ev.get("n_used", 0.0))
    ess_w = float(ev.get("ess_w", 0.0))

    # Realdata metadata
    rd = s.get("realdata", {})
    trades_reconstructed = rd.get("trades_reconstructed")
    events_processed = rd.get("events_processed")

    pts = s.get("posterior_points", [])
    last = pts[-1] if pts else None
    if last:
        a = float(last.get("alpha"))
        b = float(last.get("beta"))
        p_hat = float(last.get("p_hat"))
    else:
        a, b, p_hat = 1.0, 1.0, 0.5

    mean, var = beta_mean_var(a, b)
    ci90 = normal_ci_width(mean, var, z=1.645)

    return {
        "experiment_id": exp_id,
        "window_length_min": window,
        "weighting_method": wm,
        "dependence_method": dm,
        "posterior_mode": pm,
        "posterior_mean": mean,
        "posterior_variance": var,
        "ci90_width_normapprox": ci90,
        "alpha_last": a,
        "beta_last": b,
        "p_hat_last": p_hat,
        "effective_sample_size": ess_w,
        "n_used": n_used,
        "y_used": y_used,
        "trade_count": trades_reconstructed,
        "events_processed": events_processed,
    }


def main() -> None:
    base = os.path.join("results", "REALDATA_GRID_RUN")
    out = os.path.join(base, "analysis")
    os.makedirs(out, exist_ok=True)

    exp_dirs = sorted(glob(os.path.join(base, "W*m__*__*__*")))
    rows = [parse_experiment_dir(d) for d in exp_dirs]

    # global table
    global_path = os.path.join(out, "global_experiment_table.csv")
    global_cols = [
        "experiment_id",
        "window_length_min",
        "weighting_method",
        "dependence_method",
        "posterior_mode",
        "posterior_mean",
        "posterior_variance",
        "ci90_width_normapprox",
        "effective_sample_size",
        "trade_count",
        "events_processed",
    ]
    with open(global_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=global_cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in global_cols})

    posterior_path = os.path.join(out, "posterior_metrics.csv")
    post_cols = [
        "experiment_id",
        "alpha_last",
        "beta_last",
        "p_hat_last",
        "posterior_mean",
        "posterior_variance",
        "ci90_width_normapprox",
    ]
    with open(posterior_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=post_cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in post_cols})

    evidence_path = os.path.join(out, "evidence_statistics.csv")
    ev_cols = [
        "experiment_id",
        "window_length_min",
        "weighting_method",
        "dependence_method",
        "n_used",
        "y_used",
        "effective_sample_size",
        "trade_count",
        "events_processed",
    ]
    with open(evidence_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ev_cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in ev_cols})

    print(f"OK: wrote {len(rows)} rows to {out}")


if __name__ == "__main__":
    main()
