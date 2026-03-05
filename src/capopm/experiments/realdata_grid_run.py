"""REALDATA_GRID_RUN (bounded campaign runner).

Runs a grid of evidence weighting + dependence adjustment + posterior update modes
on a fixed Databento download per time window.

This is a *demonstration/proxy* campaign: no paper claims.

Network discipline:
- preflight cost via metadata.get_cost
- download each time window once; reuse locally for many experiment cells

NOTE: requires DATABENTO_API_KEY in environment and PRISM_DATABENTO_LIVE=1.
"""

from __future__ import annotations

import csv
import json
import os
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple

from ..likelihood import counts_from_trade_tape
from ..realdata.schema import EvidenceTapeEntry
from ..realdata.trade_reconstruction import reconstruct_trades
from ..realdata.evidence import trades_to_evidence_tape, evidence_meta_to_dict
from ..realdata.diagnostics import build_diagnostics, write_adapter_diagnostics
from ..realdata.evidence_weighting import get_weight_fn
from ..realdata.dependence import ess_weights, apply_dependence_adjustment
from ..realdata.posterior_update import update_single_window, update_sequential, update_rolling

from ..realdata.databento.client import DatabentoHistoricalClient
from ..realdata.databento.cost_guard import Budget, require_budget_ok
from ..realdata.databento.schemas import CostRequest, TimeseriesRequest
from ..realdata.databento.transport import LiveTransport
from ..realdata.databento.validation import validate_request
from ..realdata.databento.ingest import parse_trades_csv


SCENARIO_NAME = "REALDATA_GRID_RUN"


def _ensure_dir(p: str) -> None:
    os.makedirs(p, exist_ok=True)


def _sha256_file(path: str) -> str:
    import hashlib

    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_json(path: str, payload: Dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def _write_hashes(out_dir: str, artifact_paths: List[str]) -> Dict[str, str]:
    hashes = {}
    for p in artifact_paths:
        if os.path.exists(p):
            hashes[os.path.basename(p)] = _sha256_file(p)
    _write_json(os.path.join(out_dir, "artifact_hashes.json"), hashes)
    return hashes


def _append_manifest(entry: Dict) -> None:
    manifest_path = "PAPER_RUN_MANIFEST.json"
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception:
        manifest = {}
    runs = manifest.get("paper_runs") if isinstance(manifest, dict) else None
    if not isinstance(runs, list):
        runs = []
    runs.append(entry)
    out = {**(manifest if isinstance(manifest, dict) else {}), "paper_runs": runs}
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)


def _download_trades_csv(
    *,
    dataset: str,
    symbols: str,
    stype_in: str,
    start: str,
    end: str,
    results_dir: str,
    budget: Budget,
) -> Tuple[bytes, float]:
    os.environ["PRISM_PROBE_RESULTS_DIR"] = results_dir
    transport = LiveTransport()
    client = DatabentoHistoricalClient(transport=transport)

    cost_req = CostRequest(dataset=dataset, schema="trades", symbols=symbols, stype_in=stype_in, start=start, end=end)
    est_cost = client.get_cost(cost_req)
    require_budget_ok(est_cost, budget=budget)

    ts_req = TimeseriesRequest(
        dataset=dataset,
        schema="trades",
        symbols=symbols,
        stype_in=stype_in,
        stype_out="instrument_id",
        start=start,
        end=end,
    )
    validate_request(ts_req, encoding="csv", compression="none", require_end=True)
    resp = client.get_range_raw(ts_req, encoding="csv", compression="none")
    return resp.body, float(est_cost)


def run_realdata_grid_run(
    *,
    dataset: str = "GLBX.MDP3",
    symbols: str = "ES.FUT",
    stype_in: str = "parent",
    start_utc: str = "2024-01-03T14:30",
    windows_min: List[int] | None = None,
    weighting_modes: List[str] | None = None,
    dependence_modes: List[str] | None = None,
    posterior_modes: List[str] | None = None,
    max_total_cost_usd: float = 20.0,
) -> Dict:
    """Run the bounded campaign.

    Returns a top-level campaign summary.
    """

    if os.environ.get("PRISM_DATABENTO_LIVE") != "1":
        raise RuntimeError("REALDATA_GRID_RUN requires PRISM_DATABENTO_LIVE=1")

    windows_min = windows_min or [1, 5, 15, 30, 60]
    weighting_modes = weighting_modes or ["RAW", "SIZE_WEIGHTED", "CAPPED", "SUBLINEAR", "IMBALANCE_ADJUSTED"]
    dependence_modes = dependence_modes or ["RAW_N", "EFFECTIVE_N_STAR"]
    # Keep campaign bounded (~60 cells): run sequential updates everywhere, and allow
    # users to extend to rolling/single via explicit args.
    posterior_modes = posterior_modes or ["sequential_update"]

    base_dir = os.path.join("results", SCENARIO_NAME)
    _ensure_dir(base_dir)

    campaign_log = os.path.join(base_dir, "run_log.txt")
    with open(campaign_log, "w", encoding="utf-8") as f:
        f.write(f"dataset={dataset} symbols={symbols} start={start_utc}\n")
        f.write(f"windows_min={windows_min}\n")
        f.write(f"weighting_modes={weighting_modes}\n")
        f.write(f"dependence_modes={dependence_modes}\n")
        f.write(f"posterior_modes={posterior_modes}\n")

    budget = Budget(total_usd=float(max_total_cost_usd), probe_usd=float(max_total_cost_usd))
    total_cost = 0.0
    experiments = []

    # Parse start/end
    start_dt = datetime.fromisoformat(start_utc).replace(tzinfo=timezone.utc)

    for w_min in windows_min:
        end_dt = start_dt + timedelta(minutes=int(w_min))
        start_s = start_dt.strftime("%Y-%m-%dT%H:%M")
        end_s = end_dt.strftime("%Y-%m-%dT%H:%M")

        window_dir = os.path.join(base_dir, f"WINDOW_{w_min}m")
        _ensure_dir(window_dir)

        raw_csv, est_cost = _download_trades_csv(
            dataset=dataset,
            symbols=symbols,
            stype_in=stype_in,
            start=start_s,
            end=end_s,
            results_dir=window_dir,
            budget=budget,
        )
        total_cost += est_cost
        with open(os.path.join(window_dir, "raw_trades.csv"), "wb") as f:
            f.write(raw_csv)

        events = list(parse_trades_csv(raw_csv, instrument_id_fallback=symbols))
        trades, recon_diag = reconstruct_trades(events)

        # Base tape uses BUY->YES / SELL->NO and default implied_yes_before.
        base_tape, meta = trades_to_evidence_tape(
            trades,
            instrument=(events[0].instrument_id if events else symbols),
            source=f"databento:{dataset}:trades",
            adapter_version="databento_campaign_v1",
            implied_yes_before_default=0.5,
        )

        # Build adapter diagnostics once per window.
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
            tape_len=len(base_tape),
        )
        write_adapter_diagnostics(os.path.join(window_dir, "adapter_diagnostics.json"), adapter_diag)

        # Run grid cells purely locally from base_tape
        for wm in weighting_modes:
            wfn = get_weight_fn(wm, {"cap": 10.0, "sublinear_kind": "sqrt", "q0": 1.0, "w_max": 10.0})
            weighted_tape: List[EvidenceTapeEntry] = []
            weights = []
            for tr in base_tape:
                size = wfn(float(getattr(tr, "size")))
                if size <= 0:
                    continue
                weights.append(size)
                weighted_tape.append(
                    EvidenceTapeEntry(
                        timestamp_ns=int(getattr(tr, "timestamp_ns")),
                        side=getattr(tr, "side"),
                        size=float(size),
                        implied_yes_before=float(getattr(tr, "implied_yes_before", 0.5)),
                    )
                )

            y_raw, n_raw = counts_from_trade_tape(weighted_tape)
            ess = ess_weights(weights)

            for dm in dependence_modes:
                y_adj, n_adj, dep_diag = apply_dependence_adjustment(y_raw, n_raw, mode=dm, ess=ess)

                for pm in posterior_modes:
                    exp_id = f"W{w_min}m__{wm}__{dm}__{pm}"
                    out_dir = os.path.join(base_dir, exp_id)
                    _ensure_dir(out_dir)

                    # Posterior points
                    if pm == "single_window":
                        pts = update_single_window(1.0, 1.0, y_adj, n_adj, int(end_dt.timestamp() * 1e9))
                    elif pm == "sequential_update":
                        pts = update_sequential(1.0, 1.0, weighted_tape, bucket_ns=1_000_000_000)
                    elif pm == "rolling_window":
                        pts = update_rolling(1.0, 1.0, weighted_tape, window_ns=min(w_min, 15) * 60_000_000_000)
                    else:
                        raise ValueError(pm)

                    # Write summary
                    summary = {
                        "experiment_id": exp_id,
                        "scenario_name": SCENARIO_NAME,
                        "dataset": dataset,
                        "symbols": symbols,
                        "window_minutes": w_min,
                        "start": start_s,
                        "end": end_s,
                        "estimated_cost_usd_for_window_download": est_cost,
                        "weighting_mode": wm,
                        "dependence_mode": dm,
                        "dependence_diag": dep_diag,
                        "posterior_mode": pm,
                        "realdata": evidence_meta_to_dict(meta),
                        "evidence_counts": {"y_raw": y_raw, "n_raw": n_raw, "y_used": y_adj, "n_used": n_adj, "ess_w": ess},
                        "posterior_points": [asdict(p) for p in pts],
                        "note": "Demonstration / proxy evidence only. No paper claims.",
                    }
                    _write_json(os.path.join(out_dir, "summary.json"), summary)

                    # Minimal metrics csv (for campaign rollups)
                    metrics_path = os.path.join(out_dir, "metrics_aggregated.csv")
                    with open(metrics_path, "w", newline="", encoding="utf-8") as f:
                        w = csv.writer(f)
                        w.writerow(["experiment_id", "p_hat_last", "alpha_last", "beta_last", "n_used", "y_used", "ess_w"])
                        if pts:
                            last = pts[-1]
                            w.writerow([exp_id, last.p_hat, last.alpha, last.beta, n_adj, y_adj, ess])

                    # Placeholders to satisfy artifact contract
                    with open(os.path.join(out_dir, "reliability_capopm.csv"), "w", newline="", encoding="utf-8") as f:
                        csv.writer(f).writerows([["note"], ["placeholder: requires outcomes; proxy demo only"]])
                    with open(os.path.join(out_dir, "tests.csv"), "w", newline="", encoding="utf-8") as f:
                        csv.writer(f).writerows([["note"], ["placeholder"]])
                    write_adapter_diagnostics(os.path.join(out_dir, "adapter_diagnostics.json"), adapter_diag)

                    # Hashes and run log
                    run_log = os.path.join(out_dir, "run_log.txt")
                    with open(run_log, "w", encoding="utf-8") as f:
                        f.write(json.dumps({"exp_id": exp_id, "window_download_cost": est_cost}, indent=2))

                    artifact_paths = [
                        os.path.join(out_dir, "summary.json"),
                        os.path.join(out_dir, "adapter_diagnostics.json"),
                        metrics_path,
                        os.path.join(out_dir, "reliability_capopm.csv"),
                        os.path.join(out_dir, "tests.csv"),
                        run_log,
                    ]
                    hashes = _write_hashes(out_dir, artifact_paths)

                    _append_manifest(
                        {
                            "experiment": "REALDATA_GRID_RUN",
                            "scenario_name": SCENARIO_NAME,
                            "experiment_id": exp_id,
                            "tier": "REALDATA",
                            "dataset": dataset,
                            "schema": "trades",
                            "symbols": symbols,
                            "start": start_s,
                            "end": end_s,
                            "estimated_cost_usd_window": est_cost,
                            "results_dir": out_dir,
                            "artifact_hashes": hashes,
                        }
                    )

                    experiments.append(exp_id)

    campaign_summary = {
        "scenario_name": SCENARIO_NAME,
        "dataset": dataset,
        "symbols": symbols,
        "windows_min": windows_min,
        "weighting_modes": weighting_modes,
        "dependence_modes": dependence_modes,
        "posterior_modes": posterior_modes,
        "total_estimated_cost_usd": total_cost,
        "n_experiments": len(experiments),
        "note": "Campaign estimates cost per window download; grid cells reuse downloads locally.",
    }

    _write_json(os.path.join(base_dir, "summary.json"), campaign_summary)
    hashes = _write_hashes(base_dir, [os.path.join(base_dir, "summary.json"), campaign_log])
    _append_manifest(
        {
            "experiment": "REALDATA_GRID_RUN",
            "scenario_name": SCENARIO_NAME,
            "tier": "REALDATA",
            "results_dir": base_dir,
            "total_estimated_cost_usd": total_cost,
            "n_experiments": len(experiments),
            "artifact_hashes": hashes,
        }
    )

    return campaign_summary
