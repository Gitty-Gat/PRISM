# LIMITATIONS (Required claim discipline)

This repository includes real-market experiments based on **proxy evidence** derived from market microstructure. The following limitations must be kept explicit in any write-up.

## 1) Trade independence / i.i.d. assumptions
- Microstructure events (trades, quote updates) are **not i.i.d.**.
- Trades are temporally clustered, autocorrelated, and influenced by hidden participant strategies.
- Any concentration or convergence narrative must be framed in terms of **effective sample size** (n\*) rather than raw counts.

## 2) Order flow aggregation assumptions
- The adapter reduces a high-dimensional order-driven market into a binary evidence stream (YES/NO) with weights.
- This aggregation is a modeling choice; different weightings can change posterior concentration materially.
- Evidence transforms should be capped/sublinear to avoid implicit dominance claims from very large prints.

## 3) Limited event definitions (proxy outcome)
- Predictive evaluation defines outcomes using **future trade-price direction** over a horizon.
- This is a proxy label, not a contract settlement outcome.
- Results should be described as demonstration of pipeline mechanics, not a claim of tradable forecasting edge.

## 4) Market microstructure noise
- Trade prints can include off-exchange prints, auctions, and other non-comparable events depending on dataset.
- Trade direction (BUY/SELL aggressor) can be explicit or inferred; inference uncertainty must be logged.
- Spread dynamics, price discreteness, and timestamp jitter can introduce measurement noise.

## 5) Latent regimes are unobserved
- Regime/mode mixtures are latent. Real data does not provide ground-truth regime labels.
- Real-data plots should not claim "regime identification" or "truth recovery".

## 6) No dominance / no theorem validation from real data
- Real-data results are **illustrative** and **proxy evidence**.
- Do not claim dominance over baselines.
- Do not claim empirical validation of theorems without satisfying the paper’s audit criteria and testability regime.

## 7) Practical reproducibility limits
- Figures can be regenerated from artifacts using `scripts/reproduce_prism_results.py`.
- Some outputs (e.g., PDF conversion) may depend on local ImageMagick security policy.
