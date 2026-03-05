"""Databento dataset/schema identifiers and lightweight parsing helpers.

We avoid importing the Databento SDK directly (not installed). Instead we:
- replicate the relevant endpoint contracts from the SDK source under docs/
- parse CSV/JSON responses in a permissive way.

Schema strings per Databento docs / SDK:
- trades
- mbp-1
- mbp-10
- mbo
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional


SchemaName = Literal["trades", "mbp-1", "mbp-10", "mbo"]


@dataclass(frozen=True)
class TimeseriesRequest:
    dataset: str
    schema: SchemaName
    symbols: str
    stype_in: str = "raw_symbol"
    stype_out: str = "instrument_id"
    start: str = ""
    end: Optional[str] = None
    limit: Optional[int] = None


@dataclass(frozen=True)
class CostRequest:
    dataset: str
    schema: SchemaName
    symbols: str
    stype_in: str = "raw_symbol"
    start: str = ""
    end: Optional[str] = None
    limit: Optional[int] = None
