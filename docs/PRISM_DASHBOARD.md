# PRISM_DASHBOARD

## What it is
A lightweight, dependency-free local dashboard for exploring `REALDATA_GRID_RUN` artifacts.

- Reads only from `results/REALDATA_GRID_RUN/`
- Uses the aggregated CSVs under `results/REALDATA_GRID_RUN/analysis/`
- Loads per-experiment `summary.json` and verifies `artifact_hashes.json` at startup
- **Does not** call Databento
- **Does not** modify results

## How to run
From repo root:

```bash
python3 -m dashboard.run_dashboard
# or
python3 dashboard/run_dashboard.py
```

Then open:
- <http://127.0.0.1:8050/>

## Features
- Filters:
  - window length
  - weighting method
  - dependence method
  - experiment id
- Panels:
  - posterior mean trajectory with a 90% band (normal approximation)
  - evidence strength proxy vs posterior mean
  - interactive 3D-ish surface view (time × strength × p_hat) with mouse drag rotate
  - posterior density snapshots (normal approximation for visualization)

## Reproducibility safeguards
- At load time, each experiment directory’s `artifact_hashes.json` is checked against `summary.json` SHA256.
- If mismatch is found, the UI shows a warning.

## Notes / limitations
- This dashboard is implemented with **stdlib-only** Python + vanilla browser JS.
- No Plotly/Dash/Streamlit is used because those packages are not installed in the runtime.
- “Credible intervals” and “density snapshots” use approximations (normal), not SciPy quantiles.
- Results remain **proxy evidence**; do not use dashboard screenshots to make paper claims.
