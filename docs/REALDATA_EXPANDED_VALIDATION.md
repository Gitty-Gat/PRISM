# REALDATA_EXPANDED_VALIDATION (Phase F)

## Scope and posture
This expanded campaign tests stability of PRISM-style proxy inference over longer time horizons and multiple time slices.

**Conservative posture:** results are **illustrative** and based on **proxy evidence** from signed trade flow. They do not validate paper theorems and do not support dominance claims.

## Design
- Dataset: Databento `GLBX.MDP3` `trades`
- Symbol: `ES.FUT`
- Time horizons: 1m, 5m, 15m, 30m, 60m, 120m, 240m, session (~390m)
- Slices: 5 fixed UTC start times (open/mid/late/post)
- Weighting:
  - Core: RAW and SUBLINEAR across all windows
  - Full weighting sweep (RAW, SIZE_WEIGHTED, CAPPED, SUBLINEAR, IMBALANCE_ADJUSTED) at 60m
- Dependence: RAW_N vs EFFECTIVE_N_STAR (ESS_w shrink)
- Posterior modes:
  - sequential_update everywhere
  - rolling_update for windows >= 60m

## How to run
```bash
PRISM_DATABENTO_LIVE=1 python3 scripts/run_experiment.py --scenario REALDATA_EXPANDED_VALIDATION_RUN
python3 scripts/run_realdata_robustness_tests.py
```

## Outputs
- Results: `results/REALDATA_EXPANDED_VALIDATION/`
- Robustness report: `results/REALDATA_EXPANDED_VALIDATION/robustness/robustness_report.json`

## Limitations
- No outcomes; reliability/calibration plots are not interpreted.
- Dependence corrections are heuristic ESS proxies.
- Results must be interpreted as demonstrations of pipeline stability only.
