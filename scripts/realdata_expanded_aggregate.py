"""Aggregate REALDATA_EXPANDED_VALIDATION outputs into analysis tables.

Outputs:
- results/REALDATA_EXPANDED_VALIDATION/analysis/global_experiment_table.csv
- results/REALDATA_EXPANDED_VALIDATION/analysis/posterior_metrics.csv
- results/REALDATA_EXPANDED_VALIDATION/analysis/evidence_statistics.csv

Computed extras:
- credible_interval_width (90% normal approx)
- posterior_volatility (std dev of p_hat over posterior_points)
- learning_rate (approx slope of p_hat vs time index)

Stdlib only.
"""

from __future__ import annotations

import csv
import json
import math
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
    sd = math.sqrt(max(var, 0.0))
    lo = max(0.0, mean - z * sd)
    hi = min(1.0, mean + z * sd)
    return hi - lo


def std(vals: list[float]) -> float:
    if len(vals) < 2:
        return 0.0
    m = sum(vals) / len(vals)
    v = sum((x - m) ** 2 for x in vals) / (len(vals) - 1)
    return math.sqrt(max(v, 0.0))


def learning_rate(p: list[float]) -> float:
    # slope of p_hat vs index using simple linear regression
    n = len(p)
    if n < 2:
        return 0.0
    xs = list(range(n))
    mx = (n - 1) / 2.0
    my = sum(p) / n
    num = sum((xs[i] - mx) * (p[i] - my) for i in range(n))
    den = sum((xs[i] - mx) ** 2 for i in range(n))
    if den <= 0:
        return 0.0
    return num / den


def parse_experiment_dir(d: str) -> dict:
    s = json.load(open(os.path.join(d, "summary.json"), "r", encoding="utf-8"))

    exp_id = s.get("experiment_id") or os.path.basename(d)
    slice_name = s.get("slice")
    window = int(s.get("window_minutes"))
    wm = s.get("weighting_mode")
    dm = s.get("dependence_mode")
    pm = s.get("posterior_mode")

    ev = s.get("evidence_counts", {})
    y_used = float(ev.get("y_used", 0.0))
    n_used = float(ev.get("n_used", 0.0))
    ess_w = float(ev.get("ess_w", 0.0))

    rd = s.get("realdata", {})
    trade_count = rd.get("trades_reconstructed")
    events_processed = rd.get("events_processed")

    pts = s.get("posterior_points", [])
    pvals = [float(p.get("p_hat")) for p in pts] if pts else []
    last = pts[-1] if pts else None
    if last:
        a = float(last.get("alpha"))
        b = float(last.get("beta"))
        p_last = float(last.get("p_hat"))
    else:
        a, b, p_last = 1.0, 1.0, 0.5

    mean, var = beta_mean_var(a, b)
    ci90 = normal_ci_width(mean, var)
    vol = std(pvals)
    lr = learning_rate(pvals)

    return {
        "experiment_id": exp_id,
        "time_slice": slice_name,
        "window_length_min": window,
        "weighting_method": wm,
        "dependence_method": dm,
        "posterior_mode": pm,
        "posterior_mean": mean,
        "posterior_variance": var,
        "credible_interval_width": ci90,
        "posterior_volatility": vol,
        "learning_rate": lr,
        "alpha_last": a,
        "beta_last": b,
        "p_hat_last": p_last,
        "effective_sample_size": ess_w,
        "evidence_strength": n_used,
        "n_used": n_used,
        "y_used": y_used,
        "trade_count": trade_count,
        "events_processed": events_processed,
    }


def main() -> None:
    base = os.path.join("results", "REALDATA_EXPANDED_VALIDATION")
    out = os.path.join(base, "analysis")
    os.makedirs(out, exist_ok=True)

    exp_dirs = sorted(glob(os.path.join(base, "S*__W*m__*__*__*")))
    rows = [parse_experiment_dir(d) for d in exp_dirs]

    global_path = os.path.join(out, "global_experiment_table.csv")
    global_cols = [
        "experiment_id",
        "time_slice",
        "window_length_min",
        "weighting_method",
        "dependence_method",
        "posterior_mode",
        "posterior_mean",
        "posterior_variance",
        "credible_interval_width",
        "posterior_volatility",
        "learning_rate",
        "effective_sample_size",
        "trade_count",
        "events_processed",
        "evidence_strength",
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
        "credible_interval_width",
        "posterior_volatility",
        "learning_rate",
    ]
    with open(posterior_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=post_cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k) for k in post_cols})

    evidence_path = os.path.join(out, "evidence_statistics.csv")
    ev_cols = [
        "experiment_id",
        "time_slice",
        "window_length_min",
        "weighting_method",
        "dependence_method",
        "posterior_mode",
        "n_used",
        "y_used",
        "evidence_strength",
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
