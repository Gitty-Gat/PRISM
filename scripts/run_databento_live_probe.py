"""Execute exactly one Databento historical probe (Stage B.4).

Guardrails:
- Requires PRISM_DATABENTO_LIVE=1
- Preflights cost via metadata.get_cost and hard-fails if > $2

Outputs under:
- data/databento/live_probe/<timestamp>/raw.csv
- results/DATABENTO_LIVE_PROBE/{summary.json, adapter_diagnostics.json, evidence_tape.json, artifact_hashes.json, run_log.txt}

Also appends metadata to PAPER_RUN_MANIFEST.json.

NOTE:
- We request encoding=csv, compression=none. If server returns non-CSV, abort.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

# Ensure repo root on path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.capopm.realdata.databento.client import DatabentoHistoricalClient
from src.capopm.realdata.databento.cost_guard import require_budget_ok
from src.capopm.realdata.databento.schemas import CostRequest, TimeseriesRequest
from src.capopm.realdata.databento.transport import LiveTransport
from src.capopm.realdata.databento.ingest import parse_trades_csv

from src.capopm.realdata.trade_reconstruction import reconstruct_trades
from src.capopm.realdata.evidence import trades_to_evidence_tape, evidence_meta_to_dict
from src.capopm.realdata.diagnostics import build_diagnostics, write_adapter_diagnostics
from src.capopm.likelihood import counts_from_trade_tape, beta_binomial_update
from src.capopm.pricing import posterior_prices


SCENARIO = "DATABENTO_LIVE_PROBE"

# Probe target (must match workspace/prism-director/DATABENTO_PROBE_TARGET.md)
PROBE = {
    "dataset": "GLBX.MDP3",
    "schema": "trades",
    "symbols": "ES.FUT",
    "stype_in": "parent",
    "stype_out": "raw_symbol",
    "start": "2024-01-03T14:30:00Z",
    "end": "2024-01-03T14:31:00Z",
    "encoding": "csv",
    "compression": "none",
    "limit": None,
}


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    live_dir = os.path.join("data", "databento", "live_probe", ts)
    os.makedirs(live_dir, exist_ok=True)

    results_dir = os.path.join("results", SCENARIO)
    os.makedirs(results_dir, exist_ok=True)

    run_log_path = os.path.join(results_dir, "run_log.txt")
    with open(run_log_path, "w", encoding="utf-8") as log:
        log.write(f"probe_ts={ts}\n")
        log.write(json.dumps(PROBE, indent=2) + "\n")

    transport = LiveTransport()
    client = DatabentoHistoricalClient(transport=transport)

    # --- Cost preflight ---
    cost_req = CostRequest(
        dataset=PROBE["dataset"],
        schema=PROBE["schema"],
        symbols=PROBE["symbols"],
        stype_in=PROBE["stype_in"],
        start=PROBE["start"],
        end=PROBE["end"],
        limit=PROBE["limit"],
    )
    est_cost = client.get_cost(cost_req)
    require_budget_ok(est_cost)

    with open(run_log_path, "a", encoding="utf-8") as log:
        log.write(f"estimated_cost_usd={est_cost}\n")

    # --- Download ---
    ts_req = TimeseriesRequest(
        dataset=PROBE["dataset"],
        schema=PROBE["schema"],
        symbols=PROBE["symbols"],
        stype_in=PROBE["stype_in"],
        stype_out=PROBE["stype_out"],
        start=PROBE["start"],
        end=PROBE["end"],
        limit=PROBE["limit"],
    )
    resp = client.get_range_raw(ts_req, encoding=PROBE["encoding"], compression=PROBE["compression"])

    raw_path = os.path.join(live_dir, "raw.csv")
    with open(raw_path, "wb") as f:
        f.write(resp.body)

    # Basic CSV sanity
    head = resp.body[:200].decode("utf-8", errors="replace")
    if "," not in head or "\n" not in head:
        raise SystemExit("Response does not look like CSV; aborting probe")

    # --- Parse -> canonical events -> reconstruct -> evidence tape ---
    events = list(parse_trades_csv(resp.body, instrument_id_fallback=PROBE["symbols"]))
    trades, recon_diag = reconstruct_trades(events)
    tape, meta = trades_to_evidence_tape(
        trades,
        instrument=(events[0].instrument_id if events else PROBE["symbols"]),
        source=f"databento:{PROBE['dataset']}:{PROBE['schema']}",
        adapter_version="databento_live_v1",
        implied_yes_before_default=0.5,
    )

    meta = type(meta)(
        **{
            **meta.__dict__,
            "events_processed": len(events),
            "diagnostics_summary": {
                "explicit_trades": recon_diag.get("explicit_trades"),
                "inferred_trades": recon_diag.get("inferred_trades"),
                "unmatched_trade_events": recon_diag.get("unmatched_trade_events"),
            },
        }
    )

    adapter_diag = build_diagnostics(
        meta=meta,
        reconstruction_diag=recon_diag,
        events_processed=len(events),
        tape_len=len(tape),
    )
    adapter_diag_path = os.path.join(results_dir, "adapter_diagnostics.json")
    write_adapter_diagnostics(adapter_diag_path, adapter_diag)

    # Evidence tape JSON
    tape_path = os.path.join(results_dir, "evidence_tape.json")
    with open(tape_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "meta": evidence_meta_to_dict(meta),
                "tape": [t.__dict__ for t in tape],
            },
            f,
            indent=2,
        )

    # --- Minimal posterior smoke (Beta(1,1) update) ---
    y, n = counts_from_trade_tape(tape)
    alpha_post, beta_post = beta_binomial_update(1.0, 1.0, y, n)
    p_hat, _ = posterior_prices(alpha_post, beta_post)

    summary = {
        "scenario_name": SCENARIO,
        "probe_ts": ts,
        "estimated_cost_usd": est_cost,
        "request": PROBE,
        "realdata": evidence_meta_to_dict(meta),
        "evidence_counts": {"y": y, "n": n},
        "smoke_posterior": {"alpha_post": alpha_post, "beta_post": beta_post, "p_hat": p_hat},
        "note": "Live probe validates Databento transport+mapping. Not a paper claim validation.",
    }
    summary_path = os.path.join(results_dir, "summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # --- Hashes ---
    artifacts = [summary_path, adapter_diag_path, tape_path, run_log_path]
    hashes = {os.path.basename(p): sha256_file(p) for p in artifacts}
    hashes[os.path.relpath(raw_path, REPO_ROOT)] = sha256_file(raw_path)
    hashes_path = os.path.join(results_dir, "artifact_hashes.json")
    with open(hashes_path, "w", encoding="utf-8") as f:
        json.dump(hashes, f, indent=2)

    # Append to PAPER_RUN_MANIFEST.json (minimal, append-only)
    manifest_path = os.path.join(REPO_ROOT, "PAPER_RUN_MANIFEST.json")
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception:
        manifest = {}
    runs = manifest.get("paper_runs") if isinstance(manifest, dict) else None
    if not isinstance(runs, list):
        runs = []
    runs.append(
        {
            "experiment": "DATABENTO",
            "scenario_name": SCENARIO,
            "tier": "REALDATA",
            "dataset": PROBE["dataset"],
            "schema": PROBE["schema"],
            "symbols": PROBE["symbols"],
            "start": PROBE["start"],
            "end": PROBE["end"],
            "estimated_cost_usd": est_cost,
            "results_dir": results_dir,
            "artifact_hashes": hashes,
        }
    )
    manifest_out = {
        **(manifest if isinstance(manifest, dict) else {}),
        "paper_runs": runs,
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_out, f, indent=2)

    print(f"OK: live probe complete. estimated_cost=${est_cost:.4f} artifacts={results_dir}")


if __name__ == "__main__":
    main()
