# PREDICTIVE_EVALUATION (Stage I)

## Scope and posture
This stage performs **illustrative** predictive evaluation on real-data proxy evidence.

- No dominance claims.
- No theorem validation claims.
- Outcomes are defined from future trade-price direction (proxy mid).

## Theory alignment
See:
- `docs/THEORY_METRIC_ALIGNMENT.md`

Key aligned quantities:
- posterior mean/variance (Proposition 5)
- Beta credible intervals (quantiles via pricing.beta_ppf_approx)
- posterior predictive mean probability (Theorem 9 / Proposition 6)
- Brier score and predictive log-likelihood/log loss (Appendix references)

## Data construction
Scripts:
- `scripts/build_predictive_dataset.py`
  - outputs `prediction_dataset.csv` and `prediction_results.csv`

Outcome:
- `future_price_direction(h) = 1{ last_trade_price(t+h) > last_trade_price(t) }`
for horizons h ∈ {1m,5m,15m}.

## Evaluation
Script:
- `scripts/run_predictive_evaluation.py`

Outputs:
- `results/REALDATA_EXPANDED_VALIDATION/predictive/baseline_prediction_comparison.csv`
- `results/REALDATA_EXPANDED_VALIDATION/predictive/calibration_curves.csv`

Includes:
- Brier score
- predictive log loss (negative predictive log-likelihood)
- calibration error (ECE)
- prediction variance proxy (via spread in predicted probabilities)

## Visuals
Script:
- `scripts/predictive_viz_suite.py`

Outputs:
- `results/REALDATA_EXPANDED_VALIDATION/prism_showcase_predictive/`
  - reliability diagrams
  - brier comparison bars
  - calibration comparison (PRISM vs imbalance vs logistic)
  - sharpness histogram
  - uncertainty diagnostics (variance vs error, variance vs evidence strength)

## Limitations
- Proxy outcomes based on trade prices are not ground truth event settlements.
- Trade signing and dependence complicate calibration interpretation.
- Credible intervals are Beta-based; calibration error is descriptive.
