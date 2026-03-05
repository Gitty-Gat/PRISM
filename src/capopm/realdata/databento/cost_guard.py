"""Budget/cost guardrails for Databento historical probes.

Constraints:
- Total historical credits: $20
- Single probe cap: $2

We enforce:
1) mandatory cost preflight using metadata.get_cost
2) hard rejection if estimate exceeds caps
3) append-only logging for auditability

This module is pure-Python and does not perform network by itself.
"""

from __future__ import annotations

from dataclasses import dataclass


TOTAL_BUDGET_USD = 20.0
PROBE_BUDGET_USD = 2.0


@dataclass(frozen=True)
class Budget:
    total_usd: float = TOTAL_BUDGET_USD
    probe_usd: float = PROBE_BUDGET_USD


class BudgetExceeded(RuntimeError):
    pass


def require_budget_ok(estimated_cost_usd: float, *, budget: Budget = Budget()) -> None:
    if estimated_cost_usd is None:
        raise BudgetExceeded("Cost estimate missing")
    if estimated_cost_usd < 0:
        raise BudgetExceeded(f"Negative cost estimate: {estimated_cost_usd}")
    if estimated_cost_usd > budget.probe_usd:
        raise BudgetExceeded(
            f"Probe estimate ${estimated_cost_usd:.4f} exceeds probe cap ${budget.probe_usd:.2f}"
        )
    if estimated_cost_usd > budget.total_usd:
        raise BudgetExceeded(
            f"Estimate ${estimated_cost_usd:.4f} exceeds total budget ${budget.total_usd:.2f}"
        )
