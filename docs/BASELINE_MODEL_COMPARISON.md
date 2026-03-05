# BASELINE_MODEL_COMPARISON (Stage H)

## Scope and posture
This document provides **illustrative** baseline comparisons using **proxy evidence** outputs from `REALDATA_EXPANDED_VALIDATION`.

**Important:**
- No predictive claims.
- No theorem validation claims.
- Comparisons are descriptive and meant to highlight behavioral differences in estimators under the same evidence stream.

## Comparison dataset
Built from:
- `results/REALDATA_EXPANDED_VALIDATION/analysis/global_experiment_table.csv`

Output:
- `results/REALDATA_EXPANDED_VALIDATION/comparison/comparison_dataset.csv`

## Baselines implemented
Location: `src/capopm/baselines/`

1) **Imbalance estimator**
- `p = buy_volume / (buy_volume + sell_volume)`
- In our mapping: `buy_volume` corresponds to evidence YES weight.

2) **Naive Beta baseline**
- `alpha = 1 + buys`, `beta = 1 + sells`
- Analytic mean/variance.

3) **Logistic baseline (descriptive)**
- Lightweight logistic regression fitted to approximate PRISM posterior mean using:
  - imbalance
  - log(trade_count+1)
  - log(evidence_strength+1)

Because real-data outcomes are not available in this proxy setting, this is a **parametric smoother** of PRISM outputs, not a predictive classifier.

## Metrics
Computed in:
- `results/REALDATA_EXPANDED_VALIDATION/comparison/model_comparison.csv`

Includes:
- absolute mean differences vs PRISM
- variance ratio (beta baseline vs PRISM)

## Visual diagnostics
Generated under:
- `results/REALDATA_EXPANDED_VALIDATION/prism_showcase_comparison/`

## How to reproduce
```bash
python3 scripts/build_expanded_comparison_dataset.py
python3 scripts/run_expanded_baseline_comparison.py
python3 scripts/baseline_comparison_viz.py
```

## Limitations
- All results are conditional on the proxy evidence mapping BUY→YES, SELL→NO.
- Dependence effects are only partially addressed by ESS proxies.
- No calibration/reliability interpretations without outcomes.
