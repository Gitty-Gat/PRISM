"""Real-data (Stage B.4) adapter layer for CAPOPM.

Stage B.4 rules (from AGENTS_STAGE_B.md):
- Ingestion must be isolated in an adapter layer.
- Produce canonical event streams.
- Evidence builder must be versioned and auditable.
- No changes to Bayesian core.

This package provides:
- Canonical L3 event schema (`schema.py`)
- Adapter/parsers to canonical events (`adapter.py`)
- Trade reconstruction (`trade_reconstruction.py`)
- Evidence tape builder compatible with `likelihood.counts_from_trade_tape` (`evidence.py`)
- Diagnostics emission (`diagnostics.py`)
"""

from .schema import L3Event, ReconstructedTrade, EvidenceTapeEntry, EvidenceTapeV1
