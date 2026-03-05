"""Local semantic validation to prevent 422s before making live calls."""

from __future__ import annotations

import re
from dataclasses import asdict
from typing import Optional

from .schemas import TimeseriesRequest, SchemaName


class RequestValidationError(ValueError):
    pass


_ALLOWED_SCHEMAS = {"trades", "mbp-1", "mbp-10", "mbo"}
_ALLOWED_STYPE_IN = {"raw_symbol", "parent", "instrument_id"}
_ALLOWED_STYPE_OUT = {"instrument_id"}
_ALLOWED_ENCODING = {"csv", "json", "dbn"}
_ALLOWED_COMPRESSION = {"none", "zstd"}

# Accept: YYYY-MM-DDTHH:MM[:SS[.fff]][Z]
_TS_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z)?$")


def validate_request(
    req: TimeseriesRequest,
    *,
    encoding: str,
    compression: str,
    require_end: bool = True,
) -> None:
    if not req.dataset or not isinstance(req.dataset, str):
        raise RequestValidationError("dataset must be a non-empty string")
    if not req.symbols or not isinstance(req.symbols, str):
        raise RequestValidationError("symbols must be a non-empty string")

    schema = str(req.schema)
    if schema not in _ALLOWED_SCHEMAS:
        raise RequestValidationError(f"schema must be one of {sorted(_ALLOWED_SCHEMAS)}")

    if req.stype_in not in _ALLOWED_STYPE_IN:
        raise RequestValidationError(f"stype_in must be one of {sorted(_ALLOWED_STYPE_IN)}")

    # To avoid symbology-combo 422s, constrain to instrument_id output (SDK default).
    if req.stype_out not in _ALLOWED_STYPE_OUT:
        raise RequestValidationError("stype_out must be 'instrument_id' for probe")

    if not req.start or not isinstance(req.start, str) or not _TS_RE.match(req.start):
        raise RequestValidationError(
            "start must be RFC3339-like (e.g., 2024-01-03T14:30 or 2024-01-03T14:30:00Z)"
        )
    if require_end:
        if not req.end or not isinstance(req.end, str) or not _TS_RE.match(req.end):
            raise RequestValidationError(
                "end must be RFC3339-like (e.g., 2024-01-03T14:31)"
            )

    if encoding not in _ALLOWED_ENCODING:
        raise RequestValidationError(f"encoding must be one of {sorted(_ALLOWED_ENCODING)}")
    if compression not in _ALLOWED_COMPRESSION:
        raise RequestValidationError(f"compression must be one of {sorted(_ALLOWED_COMPRESSION)}")

    # Conservative combination rules:
    if encoding in {"csv", "json"} and compression != "none":
        raise RequestValidationError("csv/json encodings require compression='none'")

    if req.limit is not None and int(req.limit) <= 0:
        raise RequestValidationError("limit must be positive if provided")
