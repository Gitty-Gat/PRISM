"""Build prediction_dataset.csv and prediction_results.csv from existing artifacts.

Inputs (artifact-only):
- results/REALDATA_EXPANDED_VALIDATION/downloads/<slice>/W<m>m/raw_trades.csv
- results/REALDATA_EXPANDED_VALIDATION/S*__W*m__*__*__*/summary.json

Outputs:
- results/REALDATA_EXPANDED_VALIDATION/predictive/prediction_dataset.csv
- results/REALDATA_EXPANDED_VALIDATION/predictive/prediction_results.csv

Outcome definition (proxy):
- future_price_direction(h) = 1 if last_trade_price(t+h) - last_trade_price(t) > 0 else 0

Forecast probability:
- p = posterior_mean at time t (from posterior_points alpha/beta)

Credible intervals:
- computed via Beta quantiles using pricing.beta_ppf_approx

No new API calls.
"""

from __future__ import annotations

import csv
import json
import os
from glob import glob

from src.capopm.pricing import beta_ppf


def beta_mean_var(a: float, b: float):
    s = a + b
    if s <= 0:
        return 0.5, 0.0
    m = a / s
    v = (a * b) / (s * s * (s + 1.0))
    return m, v


def load_last_trade_price_series(raw_csv_path: str):
    # returns sorted list of (ts_ns, price)
    import csv as _csv
    import datetime as _dt

    rows = []
    with open(raw_csv_path, "r", encoding="utf-8", errors="replace") as f:
        rdr = _csv.DictReader(f)
        for r in rdr:
            ts = r.get("ts_event") or r.get("ts_recv") or r.get("ts") or r.get("timestamp")
            px = r.get("price") or r.get("px")
            if not ts or px is None:
                continue
            # ns int or ISO
            try:
                ts_ns = int(ts) if ts.isdigit() else int(_dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp() * 1e9)
            except Exception:
                continue
            try:
                price = float(px)
            except Exception:
                continue
            rows.append((ts_ns, price))
    rows.sort(key=lambda x: x[0])
    # compress to last price at each timestamp
    out = []
    last_ts = None
    last_px = None
    for ts, px in rows:
        if last_ts is None or ts != last_ts:
            if last_ts is not None:
                out.append((last_ts, last_px))
            last_ts = ts
            last_px = px
        else:
            last_px = px
    if last_ts is not None:
        out.append((last_ts, last_px))
    return out


def price_at_or_before(series, t_ns: int):
    # binary search
    lo, hi = 0, len(series) - 1
    if hi < 0:
        return None
    if t_ns < series[0][0]:
        return series[0][1]
    if t_ns >= series[hi][0]:
        return series[hi][1]
    while lo <= hi:
        mid = (lo + hi) // 2
        if series[mid][0] <= t_ns:
            lo = mid + 1
        else:
            hi = mid - 1
    return series[max(0, hi)][1]


def main() -> None:
    base = os.path.join("results", "REALDATA_EXPANDED_VALIDATION")
    out_dir = os.path.join(base, "predictive")
    os.makedirs(out_dir, exist_ok=True)

    horizons_min = [1, 5, 15]
    horizons_ns = [h * 60 * 1_000_000_000 for h in horizons_min]

    # load experiment summaries
    exp_dirs = sorted(glob(os.path.join(base, "S*__W*m__*__*__*")))

    dataset_rows = []
    result_rows = []

    series_cache = {}

    for d in exp_dirs:
        s = json.load(open(os.path.join(d, "summary.json"), "r", encoding="utf-8"))
        exp_id = s.get("experiment_id")
        slice_name = s.get("slice")
        wmin = int(s.get("window_minutes"))
        wm = s.get("weighting_mode")
        dm = s.get("dependence_mode")
        pm = s.get("posterior_mode")
        ev = s.get("evidence_counts", {})
        ess = float(ev.get("ess_w", 0.0))
        trade_count = (s.get("realdata", {}) or {}).get("trades_reconstructed")
        evidence_strength = float(ev.get("n_used", 0.0))

        # raw trades series for this slice/window
        raw_path = os.path.join(base, "downloads", slice_name, f"W{wmin}m", "raw_trades.csv")
        if not os.path.exists(raw_path):
            continue
        cache_key = (slice_name, wmin)
        if cache_key not in series_cache:
            series_cache[cache_key] = load_last_trade_price_series(raw_path)
        series = series_cache[cache_key]
        if not series:
            continue

        pts = s.get("posterior_points", [])
        # Stage I predictive dataset: one forecast per experiment at the final time point.
        # (This keeps runtime bounded while remaining artifact-based and reproducible.)
        if not pts:
            continue
        for p in [pts[-1]]:
            t_ns = int(p.get("t_ns"))
            a = float(p.get("alpha"))
            b = float(p.get("beta"))
            mean, var = beta_mean_var(a, b)
            q05 = beta_ppf(0.05, a, b)
            q95 = beta_ppf(0.95, a, b)
            ciw = float(q95 - q05)

            base_price = price_at_or_before(series, t_ns)
            if base_price is None:
                continue

            dataset_rows.append(
                {
                    "timestamp_ns": t_ns,
                    "experiment_id": exp_id,
                    "time_slice": slice_name,
                    "window_length_min": wmin,
                    "weighting_method": wm,
                    "dependence_method": dm,
                    "posterior_mode": pm,
                    "posterior_mean": mean,
                    "posterior_variance": var,
                    "credible_interval_width": ciw,
                    "effective_sample_size": ess,
                    "trade_count": trade_count,
                    "evidence_strength": evidence_strength,
                }
            )

            # build outcomes per horizon
            for hmin, hns in zip(horizons_min, horizons_ns):
                future_price = price_at_or_before(series, t_ns + hns)
                if future_price is None:
                    continue
                outcome = 1 if (future_price - base_price) > 0 else 0
                result_rows.append(
                    {
                        "timestamp_ns": t_ns,
                        "experiment_id": exp_id,
                        "time_slice": slice_name,
                        "window_length_min": wmin,
                        "weighting_method": wm,
                        "dependence_method": dm,
                        "posterior_mode": pm,
                        "prediction_probability": mean,
                        "actual_outcome": outcome,
                        "prediction_horizon_min": hmin,
                        "posterior_variance": var,
                        "credible_interval_width": ciw,
                        "effective_sample_size": ess,
                        "trade_count": trade_count,
                        "evidence_strength": evidence_strength,
                    }
                )

    ds_path = os.path.join(out_dir, "prediction_dataset.csv")
    ds_cols = [
        "timestamp_ns",
        "experiment_id",
        "time_slice",
        "window_length_min",
        "weighting_method",
        "dependence_method",
        "posterior_mode",
        "posterior_mean",
        "posterior_variance",
        "credible_interval_width",
        "effective_sample_size",
        "trade_count",
        "evidence_strength",
    ]
    with open(ds_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=ds_cols)
        w.writeheader()
        for r in dataset_rows:
            w.writerow(r)

    res_path = os.path.join(out_dir, "prediction_results.csv")
    res_cols = [
        "timestamp_ns",
        "experiment_id",
        "time_slice",
        "window_length_min",
        "weighting_method",
        "dependence_method",
        "posterior_mode",
        "prediction_probability",
        "actual_outcome",
        "prediction_horizon_min",
        "posterior_variance",
        "credible_interval_width",
        "effective_sample_size",
        "trade_count",
        "evidence_strength",
    ]
    with open(res_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=res_cols)
        w.writeheader()
        for r in result_rows:
            w.writerow(r)

    print("OK:", ds_path, "rows=", len(dataset_rows))
    print("OK:", res_path, "rows=", len(result_rows))


if __name__ == "__main__":
    main()
