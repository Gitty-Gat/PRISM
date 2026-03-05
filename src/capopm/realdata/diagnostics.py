"""Diagnostics helpers for real-data adapter runs."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Dict, List

from .schema import EvidenceTapeV1


def build_diagnostics(
    *,
    meta: EvidenceTapeV1,
    reconstruction_diag: Dict[str, Any],
    events_processed: int,
    tape_len: int,
) -> Dict[str, Any]:
    """Assemble adapter_diagnostics.json payload."""

    return {
        "evidence_contract": meta.version,
        "instrument": meta.instrument,
        "source": meta.source,
        "adapter_version": meta.adapter_version,
        "events_processed": int(events_processed),
        "trades_reconstructed": int(meta.trades_reconstructed),
        "tape_len": int(tape_len),
        "reconstruction": reconstruction_diag,
    }


def write_adapter_diagnostics(path: str, payload: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
