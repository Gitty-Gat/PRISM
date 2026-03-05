"""Download plan definitions for Databento probes.

A plan is an auditable intent: dataset/schema/symbols/time window + estimated cost.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .schemas import SchemaName


@dataclass(frozen=True)
class DownloadPlan:
    plan_id: str
    dataset: str
    schema: SchemaName
    symbols: str
    stype_in: str
    stype_out: str
    start: str
    end: str
    limit: Optional[int] = None
    estimated_cost_usd: Optional[float] = None
    estimated_rows: Optional[int] = None
    encoding: str = "csv"
    compression: str = "none"
