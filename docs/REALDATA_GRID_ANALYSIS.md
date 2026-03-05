# REALDATA_GRID_ANALYSIS (Phase C)

## Scope and posture
This analysis summarizes behavior across the **REALDATA_GRID_RUN** campaign (50 experiments) using Databento `GLBX.MDP3` `trades` for `ES.FUT`.

**Conservative posture:** these results are **illustrative** and based on **proxy evidence** from signed trade flow. They do not validate any paper theorems and do not support dominance claims.

## Data and grid
- Dataset: `GLBX.MDP3`
- Schema: `trades`
- Symbol: `ES.FUT` (stype_in: `parent`)
- Grid:
  - windows (min): 1, 5, 15, 30, 60
  - weighting: RAW, SIZE_WEIGHTED, CAPPED, SUBLINEAR, IMBALANCE_ADJUSTED
  - dependence: RAW_N vs EFFECTIVE_N_STAR (ESS_w shrink)
  - posterior mode: sequential_update

## Aggregated outputs
Created under `results/REALDATA_GRID_RUN/analysis/`:
- `global_experiment_table.csv`
- `posterior_metrics.csv`
- `evidence_statistics.csv`

Columns include experiment_id, window_length, weighting, dependence, posterior mean/variance, ESS, and trade_count.

## Descriptive findings (proxy)
### 1) Window length effects
Posterior variance declines strongly as window length increases (expected under conjugate updating with increasing evidence).
Using the aggregated table’s final Beta parameters (variance computed analytically):
- 1m: mean variance ≈ **1.40e-7**
- 5m: mean variance ≈ **1.17e-8**
- 15m: mean variance ≈ **2.73e-9**
- 30m: mean variance ≈ **9.94e-10**
- 60m: mean variance ≈ **2.19e-10**

Interpretation (allowed): longer windows accumulate more proxy evidence, producing tighter posteriors.

### 2) Weighting scheme sensitivity
Across this particular ES window, all weighting modes push the posterior mean very close to 1 (BUY→YES evidence dominance in the chosen time slice). Mean posterior means by weighting:
- SIZE_WEIGHTED: **0.999956** (most aggressive)
- CAPPED: **0.999938**
- SUBLINEAR: **0.999895**
- IMBALANCE_ADJUSTED: **0.999855**
- RAW: **0.999828** (least aggressive here)

Interpretation (allowed): weighting transforms change the *effective evidence strength* and thus the concentration/trajectory.

### 3) Dependence adjustment effects (RAW_N vs N*)
In this run set, RAW_N and EFFECTIVE_N_STAR appear similar in *final* variance summaries when averaged globally; that’s consistent with the current N* implementation preserving the y/n ratio while shrinking totals and the fact that many posteriors are already extremely concentrated.

Interpretation (allowed): dependence correction is most informative when comparing **trajectories** and/or when evidence is not already saturating.

### 4) Reliability / calibration
A true calibration plot requires an empirical outcome definition. For this campaign, outcomes are not available by construction (proxy evidence only), so reliability is intentionally not interpreted.

## Visualizations
Generated under:
- `results/REALDATA_GRID_RUN/prism_showcase/`

Highlights:
- VIZ1 posterior evolution with an interval band (normal approximation)
- VIZ2 evidence accumulation vs posterior mean
- VIZ3 surface proxy (time × evidence strength colored by posterior mean)
- VIZ4/VIZ4b weighting comparison (trajectories and variance/CI width)
- VIZ5 dependence comparison via variance vs ESS scatter
- VIZ7 posterior density snapshots
- `videos/posterior_learning.gif` (animation fallback)

## Limitations
- This is **not** a claim-validation study.
- Trade direction is treated as proxy belief evidence (BUY→YES, SELL→NO); this mapping is a modeling choice.
- Microstructure events are dependent; ESS proxies are heuristic.
- Credible interval widths here use a normal approximation (no SciPy quantiles).
