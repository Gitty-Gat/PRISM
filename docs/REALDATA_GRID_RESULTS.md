# REALDATA_GRID_RESULTS (Demonstration / proxy evidence)

## Scope
This document summarizes the **real-data grid campaign** over ES futures trade prints.

**Important:** These experiments are **illustrative** and based on **proxy evidence** from microstructure. They do not validate the paper’s theorems and do not support dominance claims.

## Campaign design
- Dataset: Databento `GLBX.MDP3`
- Schema: `trades`
- Symbol: `ES.FUT` (stype_in: `parent`)
- Grid factors (v1):
  - time windows: 1, 5, 15, 30, 60 minutes
  - weighting: RAW, SIZE_WEIGHTED, CAPPED, SUBLINEAR, IMBALANCE_ADJUSTED (trade-flow proxy)
  - dependence: RAW_N vs EFFECTIVE_N_STAR (weight-based ESS)
  - posterior mode: sequential_update (default campaign) + optional single/rolling extensions

## Observed behaviors (expected demo patterns)
- Weighting strongly affects evidence strength and posterior speed.
- Dependence adjustment (n*) shrinks effective evidence and generally prevents extreme posteriors.
- Sequential updates reveal when posterior mass becomes concentrated.

## Limitations
- No ground-truth p_true on real markets.
- Trade direction can be explicit or inferred; inference uncertainty must be tracked.
- Regimes are latent and unobserved.

## Where results live
- `results/REALDATA_GRID_RUN/<experiment_id>/`
- `results/REALDATA_GRID_RUN/prism_showcase/`
