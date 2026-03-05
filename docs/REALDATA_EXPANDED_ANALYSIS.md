# REALDATA_EXPANDED_ANALYSIS (Phase G)

## Scope and posture
This report analyzes **REALDATA_EXPANDED_VALIDATION** artifacts.

**Conservative posture:** results are **illustrative** and based on **proxy evidence** from signed trade flow. They do not validate paper theorems and do not support dominance claims.

## Campaign summary
- Output root: `results/REALDATA_EXPANDED_VALIDATION/`
- Slices: open, mid_1, mid_2, late, post
- Windows (minutes): 1, 5, 15, 30, 60, 120, 240, session (~390)
- Posterior modes: sequential_update (all), rolling_update (>=60m)

## Aggregated datasets
Generated under `results/REALDATA_EXPANDED_VALIDATION/analysis/`:
- `global_experiment_table.csv`
- `posterior_metrics.csv`
- `evidence_statistics.csv`

Computed fields include:
- `credible_interval_width` (90% normal approximation)
- `posterior_volatility` (std(p_hat) across posterior_points)
- `learning_rate` (linear slope of p_hat vs time index)

## Key descriptive findings (proxy)
1) **Time horizon**
   - Longer windows typically lead to more concentrated posteriors (lower variance, narrower intervals).
2) **Temporal robustness**
   - Comparing fixed-config outputs across slices (open vs mid vs late) highlights whether the proxy evidence stream is time-of-day sensitive.
3) **Weighting sensitivity**
   - SIZE_WEIGHTED tends to be the most aggressive; CAPPED/SUBLINEAR are stabilizers.
4) **Dependence adjustment**
   - N* (ESS shrink) provides a conservative guardrail against over-concentration when evidence is strongly clustered.

## Robustness tests
- Input: `results/REALDATA_EXPANDED_VALIDATION/robustness/robustness_report.json`
- Interpreted as descriptive stability metrics (variance across slices by config).

## Visualizations
Generated under:
- `results/REALDATA_EXPANDED_VALIDATION/prism_showcase/`

Figures include:
- Posterior evolution (band)
- Density snapshots
- Temporal slice comparison
- Variance heatmap (window × weighting)

## Limitations
- No outcomes; reliability/calibration is not interpreted.
- Dependence correction uses ESS proxies.
- Credible intervals use normal approximation.
