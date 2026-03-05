# THEORY_METRIC_ALIGNMENT (Stage I — mandatory)

This document maps quantities referenced in `THEORY_APPENDIX.MD` to the **exact empirical computations** used in the real‑data proxy evaluation.

**Scope note:** the real‑data pipeline is proxy evidence. Any predictive evaluation uses a *proxy outcome* (`future_price_direction` from trade-price changes) and must be presented as illustrative.

---

## 1) Posterior mean (Proposition 5)
**Theory quantity:**
- Posterior mean: \( \mu = \alpha_{post} / (\alpha_{post}+\beta_{post}) \)

**Empirical computation:**
- From stored posterior points: `posterior_points[*].alpha`, `posterior_points[*].beta`.
- Compute mean as above.

**Implementation (code):**
- `src/capopm/likelihood.py::beta_binomial_update` (produces alpha_post/beta_post)
- `src/capopm/pricing.py::posterior_prices` (returns posterior mean price)
- Aggregation scripts:
  - `scripts/realdata_expanded_aggregate.py` (final mean from last alpha/beta)

---

## 2) Posterior variance (Proposition 5)
**Theory quantity:**
- Beta variance: \( \mathrm{Var}(p) = \alpha\beta / [(\alpha+\beta)^2(\alpha+\beta+1)] \)

**Empirical computation:**
- Same closed form from last `alpha`, `beta`.

**Implementation:**
- `scripts/realdata_expanded_aggregate.py:beta_mean_var`

---

## 3) Credible intervals (Section 2: “credible interval construction”)
**Theory quantity:**
- Credible intervals should be derived from the **Beta posterior**.

**Empirical computation (Stage I):**
- Use Beta quantiles, e.g. 90% CI = `[q(0.05), q(0.95)]`.

**Implementation:**
- `src/capopm/pricing.py::beta_ppf` (internal Beta PPF approximation)
- `src/capopm/pricing.py::credible_intervals` (if used)

**Constraint:**
- Do **not** use normal-approx bands for Stage I metrics (allowed for visualization only). Stage I metrics must use Beta quantiles.

---

## 4) Likelihood / evidence aggregation (Theorem 8, Theorem 9, Proposition 7/8)
**Theory quantity:**
- Beta–Binomial conjugate update driven by YES/NO evidence counts (i.i.d. or mixing-adjusted proxy).

**Empirical computation:**
- Evidence tape entries satisfy `side ∈ {YES,NO}`, `size>0`.
- Counts are computed by summing sizes:
  - y = sum(size for YES)
  - n = sum(size for all)

**Implementation:**
- `src/capopm/likelihood.py::counts_from_trade_tape`
- Evidence construction:
  - `src/capopm/realdata/evidence.py` (BUY→YES, SELL→NO)

---

## 5) Posterior predictive distribution (Theorem 9; Proposition 6)
**Theory quantity:**
- Posterior predictive for Bernoulli/digital payoff is Beta–Binomial marginal.
- For a single Bernoulli event, the predictive mean probability equals posterior mean.

**Empirical computation (Stage I forecast probability):**
- `prediction_probability = posterior_mean`

**Implementation:**
- Derived from posterior mean computed above.

---

## 6) Predictive scoring metrics (Appendix allows Brier + predictive log likelihood)
**Theory metrics referenced:**
- Brier score on synthetic markets (Assumption 1 / Proposition 6 references Brier)
- Predictive log-likelihood / log loss (Theorem 9)

**Empirical computation (Stage I):**
- For outcome `o ∈ {0,1}` and prediction p:
  - Brier: `(p - o)^2`
  - Log loss: `- [ o*log(p) + (1-o)*log(1-p) ]` with safe clamping

**Implementation:**
- `src/capopm/metrics/scoring.py::{brier, log_loss}` (if present)
- If not present for log loss, Stage I will implement a local equivalent with clamping, but must be explicitly tied to Theorem 9 “predictive log-likelihood” definition.

---

## 7) Dependence via effective sample size n* (Assumption 5; Proposition 18)
**Theory quantity:**
- Replace raw n with effective n* for concentration narratives.

**Empirical computation:**
- ESS proxy from weights: `(Σw)^2 / Σ(w^2)`
- Used to shrink (y,n) while preserving y/n ratio.

**Implementation:**
- `src/capopm/realdata/dependence.py::{ess_weights, apply_dependence_adjustment}`

---

## 8) Forbidden / disallowed metrics
Per Proxy Policy Summary:
- No dominance over baselines
- No “empirically validated” language

Stage I uses:
- Brier
- predictive log loss
- reliability / calibration error

These are allowed as descriptive diagnostics when presented conservatively.
