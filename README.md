# PRISM / CAPOPM — Reproducible Synthetic + Real-Data (Proxy Evidence)

PRISM is a reproducible research codebase for evaluating CAPOPM-style Bayesian inference under:
- **synthetic DGPs** (paper suite), and
- **real-market proxy evidence** derived from market microstructure.

**Important posture:** real-market results in this repo are *illustrative / demonstration / proxy evidence only* and are not sufficient to claim theoretical validation or dominance.

---

## Project overview
PRISM provides:
- a governance-first pipeline (static policy gates + audits)
- artifact-based reproducibility (hashes + manifest)
- real-data adapter layers that do **not** modify the Bayesian core

This repository currently includes:
- Stage B synthetic harness (A/B/C tiers)
- Stage B.4 Databento integration (probe + campaigns)
- real-data experiment campaigns:
  - `REALDATA_GRID_RUN` (~50 experiments, ~$0.28)
  - `REALDATA_EXPANDED_VALIDATION` (300 experiments, ~$2.86)
- dashboard UI for interactive exploration

## PRISM architecture

```
Synthetic experiments (A/B/C tiers)
  run_paper_suite.py
    -> src/capopm/experiments/*
      -> src/capopm/experiments/runner.py
        -> results/<scenario>/{summary.json,metrics_aggregated.csv,tests.csv,reliability_*.csv,audit.json}

Real-data (Stage B.4)
  Databento -> src/capopm/realdata/* -> evidence tape
    -> counts_from_trade_tape()  (core seam)
    -> (demo) beta_binomial_update + posterior_prices (no core edits)
    -> results/REALDATA_*/*
```

### Core “frozen” Bayesian modules
Do not edit (governance constraint):
- `src/capopm/likelihood.py`
- `src/capopm/posterior.py`
- `src/capopm/pricing.py`

---

## Experiment campaigns
### REALDATA_GRID_RUN (bounded ≤ $20)
- Command:
  - `PRISM_DATABENTO_LIVE=1 python3 scripts/run_experiment.py --scenario REALDATA_GRID_RUN`
- Outputs:
  - `results/REALDATA_GRID_RUN/`

### REALDATA_EXPANDED_VALIDATION (bounded ≤ $50)
- Command:
  - `PRISM_DATABENTO_LIVE=1 python3 scripts/run_experiment.py --scenario REALDATA_EXPANDED_VALIDATION_RUN`
- Outputs:
  - `results/REALDATA_EXPANDED_VALIDATION/`

### Databento live probe (single request)
- Command:
  - `PRISM_DATABENTO_LIVE=1 python3 scripts/run_databento_live_probe.py`
- Outputs:
  - `results/DATABENTO_LIVE_PROBE/`

---

## Synthetic paper suite
Entry point:
- `python run_paper_suite.py --tier paper`

Outputs:
- `results/<scenario>/summary.json`
- `results/<scenario>/metrics_aggregated.csv`
- `results/<scenario>/tests.csv`
- `results/<scenario>/reliability_<model>.csv`
- `results/<scenario>/audit.json`

Governance gates:
- AST policy gate: `scripts/forbidden_ast_check.py` + `forbidden_policy.txt`
- Audit criteria: `src/capopm/experiments/audit.py` + `audit_contracts.py`

---

## 3) Real-data (Stage B.4) — Adapter layer
### Adapter package
- `src/capopm/realdata/`
  - `schema.py` (canonical schemas)
  - `adapter.py` (fixture parser; provider adapters live elsewhere)
  - `trade_reconstruction.py` (explicit fills first; deterministic inference optional)
  - `evidence.py` (emits CAPOPM-compatible evidence tape)
  - `diagnostics.py`

**Compatibility target:** the adapter must emit tape entries compatible with:
- `src/capopm/likelihood.py::counts_from_trade_tape()`

That means each entry provides:
- `side ∈ {YES, NO}`
- `size > 0`
- timestamp (`timestamp_ns`)

### Evidence contract versioning
- `capopm.realdata.evidence.v1` (see `EvidenceTapeV1` in `src/capopm/realdata/schema.py`)

### Real-data adapter docs
- `docs/REALDATA_ADAPTER.md`

---

## Predictive evaluation (proxy)
Predictive evaluation is performed on **proxy outcomes** defined from future trade-price direction.

- Theory/metric mapping:
  - `docs/THEORY_METRIC_ALIGNMENT.md`
- Predictive report:
  - `docs/PREDICTIVE_EVALUATION.md`
- Predictive outputs:
  - `results/REALDATA_EXPANDED_VALIDATION/predictive/`
- Predictive figures:
  - `results/REALDATA_EXPANDED_VALIDATION/prism_showcase_predictive/`

---

## Databento integration (probe + campaigns)
Databento SDK source is vendored locally for reference:
- `docs/databento/databento-python/`

Databento integration lives under:
- `src/capopm/realdata/databento/`

Key guardrails:
- default is **MockTransport** (no network)
- live calls require `PRISM_DATABENTO_LIVE=1`
- all live calls must preflight `metadata.get_cost` and enforce budget caps

### Live probe (single request)
- runner: `scripts/run_databento_live_probe.py`
- outputs: `results/DATABENTO_LIVE_PROBE/*` and raw response under `data/databento/live_probe/<timestamp>/raw.csv`

### Real-data grid campaign (bounded ≤ $20)
- scenario: `REALDATA_GRID_RUN`
- runner:
  - `PRISM_DATABENTO_LIVE=1 python3 scripts/run_experiment.py --scenario REALDATA_GRID_RUN`

Design note (budget): downloads each time window once (5 live calls), then runs ~50 local grid cells.

### Expanded validation campaign (bounded ≤ $50)
- Scenario: `REALDATA_EXPANDED_VALIDATION_RUN`
- Command:
  - `PRISM_DATABENTO_LIVE=1 python3 scripts/run_experiment.py --scenario REALDATA_EXPANDED_VALIDATION_RUN`
- Robustness tests:
  - `python3 scripts/run_realdata_robustness_tests.py`

Docs:
- `docs/REALDATA_EXPANDED_VALIDATION.md`

## Baseline model comparisons (illustrative)
Baselines live in:
- `src/capopm/baselines/`

Comparison artifacts:
- `results/REALDATA_EXPANDED_VALIDATION/comparison/`
- `results/REALDATA_EXPANDED_VALIDATION/prism_showcase_comparison/`

Report:
- `docs/BASELINE_MODEL_COMPARISON.md`

---

## 5) Visualizations
This repo intentionally avoids heavy plotting dependencies in the default runtime.

Generate black-background showcase figures from grid artifacts:
- `python3 scripts/realdata_grid_viz_suite.py`
- `python3 scripts/realdata_grid_animation_frames.py`

Outputs:
- `results/REALDATA_GRID_RUN/prism_showcase/` (PNG + SVG)
- `results/REALDATA_GRID_RUN/videos/posterior_learning.gif` (animation fallback)

Note: PDF export may be blocked by local ImageMagick security policy.

## Reproducibility instructions
Rebuild analyses + figures from saved artifacts (no Databento calls):

```bash
python3 scripts/reproduce_prism_results.py
```

Repro guide:
- `docs/REPRODUCIBILITY.md`

Artifact audit:
- `docs/RESEARCH_ARTIFACT_AUDIT.md`

---

## Interactive Dashboard
Run the local dashboard (reads artifacts only; no API calls):

- `python3 dashboard/run_dashboard.py`

Then open:
- <http://127.0.0.1:8050/>

Docs:
- `docs/PRISM_DASHBOARD.md`

### Example figures
- `paper/figures/fig4_temporal_robustness.png`
- `paper/figures/fig5_weighting_variance_heatmap.png`
- `paper/figures/fig7_predictive_reliability.png`

---

## 6) Claim discipline / disclaimers (required)
- **Proxy evidence disclaimer:** microstructure evidence is not a literal YES/NO parimutuel venue.
- **Dependence disclaimer:** market events are dependent; interpret stability via effective sample size n* (ESS proxies).
- **Latent regime disclaimer:** regimes are unobserved; do not treat regime labels as ground truth.
- **No dominance disclaimer:** do not claim dominance / “empirically validated” from these runs.

---

## 7) Where to look
- Real-data probe artifacts: `results/DATABENTO_LIVE_PROBE/`
- Real-data grid artifacts: `results/REALDATA_GRID_RUN/`
- Real-data grid write-up: `docs/REALDATA_GRID_RESULTS.md`
- Synthetic paper suite registry: `PAPER_RUN_MANIFEST.json`
