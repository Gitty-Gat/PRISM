"""Minimal Databento historical client (subset) using Transport.

Implements two endpoints (per SDK source):
- POST https://hist.databento.com/v0/metadata.get_cost
- POST https://hist.databento.com/v0/timeseries.get_range

We intentionally keep parsing permissive and store raw bytes for auditability.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, Optional

from .schemas import CostRequest, TimeseriesRequest
from .transport import API_VERSION, HIST_GATEWAY, HttpResponse, Transport


class DatabentoClientError(RuntimeError):
    pass


@dataclass
class DatabentoHistoricalClient:
    transport: Transport

    def _url(self, endpoint: str) -> str:
        return f"{HIST_GATEWAY}/v{API_VERSION}/{endpoint}"

    def get_cost(self, req: CostRequest) -> float:
        url = self._url("metadata.get_cost")
        data: Dict[str, str] = {
            "dataset": req.dataset,
            "start": req.start,
            "symbols": req.symbols,
            "schema": req.schema,
            "stype_in": req.stype_in,
            "stype_out": "instrument_id",
        }
        if req.end is not None:
            data["end"] = req.end
        if req.limit is not None:
            data["limit"] = str(int(req.limit))
        resp = self.transport.post_form(url, data, basic_auth=True)
        try:
            payload = json.loads(resp.body.decode("utf-8"))
        except Exception as exc:
            raise DatabentoClientError(f"Non-JSON cost response status={resp.status}") from exc
        if isinstance(payload, (int, float)):
            return float(payload)
        # Some variants return {"cost": x}
        if isinstance(payload, dict) and "cost" in payload:
            return float(payload["cost"])
        raise DatabentoClientError(f"Unexpected cost payload: {payload}")

    def get_range_raw(self, req: TimeseriesRequest, *, encoding: str = "csv", compression: str = "none") -> HttpResponse:
        url = self._url("timeseries.get_range")
        data: Dict[str, str] = {
            "dataset": req.dataset,
            "start": req.start,
            "symbols": req.symbols,
            "schema": req.schema,
            "stype_in": req.stype_in,
            "stype_out": req.stype_out,
            # NOTE: SDK forces dbn+zstd; we request CSV/JSON for minimal parsing.
            "encoding": encoding,
            "compression": compression,
        }
        if req.end is not None:
            data["end"] = req.end
        if req.limit is not None:
            data["limit"] = str(int(req.limit))
        return self.transport.post_form(url, data, basic_auth=True)
