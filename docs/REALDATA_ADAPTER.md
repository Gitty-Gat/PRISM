# REALDATA_ADAPTER (Stage B.4)

## Purpose
Provide a **strict adapter layer** that converts real-market L3/L2 order book data into a CAPOPM-compatible **evidence trade tape** without modifying the Bayesian core.

Stage B.4 rules (governance):
- ingestion isolated
- canonical event stream
- versioned, auditable evidence builder
- no changes to Bayesian core

---

## Architecture (high level)

```
Databento / Fixture (L3/MBO)
  -> adapter.py (parse + normalize)
    -> canonical L3Event stream
      -> trade_reconstruction.py (explicit fills first; deterministic inference optional)
        -> ReconstructedTrade list
          -> evidence.py (BUY->YES, SELL->NO; size weighting)
            -> EvidenceTapeEntry[] + EvidenceTapeV1 metadata
              -> likelihood.counts_from_trade_tape()
                -> posterior.capopm_pipeline()
```

---

## Canonical schemas
- `src/capopm/realdata/schema.py`
  - `L3Event` (timestamp_ns, event_type, price, size, side, order_id, trade_id, instrument_id)
  - `ReconstructedTrade`
  - `EvidenceTapeEntry` (CAPOPM-compatible: side YES/NO, size>0, timestamp_ns)
  - `EvidenceTapeV1` metadata contract (`capopm.realdata.evidence.v1`)

---

## Evidence contract: capopm.realdata.evidence.v1
Required metadata fields:
- version
- instrument
- source
- adapter_version
- events_processed
- trades_reconstructed
- diagnostics_summary

All evidence tapes must be accompanied by `adapter_diagnostics.json`.

---

## Diagnostics
`adapter_diagnostics.json` includes:
- inferred vs explicit trade counts
- unmatched events
- timestamp anomalies
- (planned) confidence proxies and normalization warnings

**Proxy-evidence disclaimer:** these diagnostics characterize adapter behavior only; they do not validate paper theorems.

---

## Experiment integration
Smoke experiment:
- `src/capopm/experiments/real_data_config.py`
  - scenario: `REALDATA_L3_ADAPTER_SANITY`
  - reads fixture: `data/test_l3/sample_events.jsonl`
  - writes artifacts under `results/REALDATA_L3_ADAPTER_SANITY/`

### CLI execution
Use the unified runner:
- `python scripts/run_experiment.py --scenario REALDATA_L3_ADAPTER_SANITY`

This writes the artifacts and appends an entry to `PAPER_RUN_MANIFEST.json` with artifact hashes.

Artifacts:
- `summary.json`
- `metrics_aggregated.csv`
- `reliability_capopm.csv`
- `tests.csv`
- `adapter_diagnostics.json`

---

## Notes / limitations
- The smoke dataset uses explicit trade events only.
- Databento parsing is stubbed; implement provider-specific parsing behind the canonical `L3Event` stream.
- This layer is **not** a claim validation; it is an integration sanity check.

## Required disclaimers (Stage B.4)
- **Proxy evidence disclaimer:** L3 microstructure is not a literal parimutuel YES/NO venue; BUY→YES / SELL→NO is a *proxy evidence mapping*.
- **Dependence / n\* disclaimer:** L3 events are dependent and clustered; raw counts/volume are not i.i.d. draws. Any concentration claims must be framed in terms of effective sample size (n\*).
- **Latent regime disclaimer:** regimes are not observed in real markets; do not treat regime labels as ground truth.
- **No dominance disclaimer:** do not claim dominance / empirical validation / puzzle resolution based on these runs.
