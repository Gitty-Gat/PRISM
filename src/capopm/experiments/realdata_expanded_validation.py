"""REALDATA_EXPANDED_VALIDATION campaign (Phase F).

Constraints:
- Uses Databento GLBX.MDP3 trades only.
- Budget cap: $50 total.
- Preflights cost via metadata.get_cost for every download.
- Avoid redundant calls: download once per (slice, window) and reuse locally.

This campaign is **proxy evidence** only.
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
from ..realdata.posterior_update import update_sequential, update_rolling

from ..realdata.databento.client import DatabentoHistoricalClient
from ..realdata.databento.cost_guard import Budget, require_budget_ok
from ..realdata.databento.schemas import CostRequest, TimeseriesRequest
from ..realdata.databento.transport import LiveTransport
from ..realdata.databento.validation import validate_request
from ..realdata.databento.ingest import parse_trades_csv


SCENARIO_NAME = "REALDATA_EXPANDED_VALIDATION_RUN"


def _ensure(p: str) -> None:
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
    out_dir: str,
    budget: Budget,
) -> Tuple[bytes, float]:
    os.environ["PRISM_PROBE_RESULTS_DIR"] = out_dir
    transport = LiveTransport()
    client = DatabentoHistoricalClient(transport=transport)

    cost_req = CostRequest(dataset=dataset, schema="trades", symbols=symbols, stype_in=stype_in, start=start, end=end)
    est_cost = float(client.get_cost(cost_req))
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
    return resp.body, est_cost


def run_realdata_expanded_validation(
    *,
    dataset: str = "GLBX.MDP3",
    symbols: str = "ES.FUT",
    stype_in: str = "parent",
    # Base date/time (UTC) used to define relative slices.
    base_date: str = "2024-01-03",
    max_total_cost_usd: float = 50.0,
) -> Dict:
    if os.environ.get("PRISM_DATABENTO_LIVE") != "1":
        raise RuntimeError("Expanded validation requires PRISM_DATABENTO_LIVE=1")

    base_dir = os.path.join("results", "REALDATA_EXPANDED_VALIDATION")
    _ensure(base_dir)

    budget = Budget(total_usd=float(max_total_cost_usd), probe_usd=float(max_total_cost_usd))
    total_cost = 0.0

    # Window set in minutes; session defined as 390 minutes (6.5 hours).
    windows_min = [1, 5, 15, 30, 60, 120, 240, 390]

    # Five distinct time slices (UTC) for ES day session, relative to 14:30 start.
    # (These are intentionally simple and deterministic.)
    slice_specs = [
        ("open", f"{base_date}T14:30"),
        ("mid_1", f"{base_date}T16:00"),
        ("mid_2", f"{base_date}T18:00"),
        ("late", f"{base_date}T20:30"),
        ("post", f"{base_date}T21:30"),
    ]

    # Weighting methods: full set, but campaign is bounded by selective coverage.
    weight_full = ["RAW", "SIZE_WEIGHTED", "CAPPED", "SUBLINEAR", "IMBALANCE_ADJUSTED"]
    weight_core = ["RAW", "SUBLINEAR"]
    dep_modes = ["RAW_N", "EFFECTIVE_N_STAR"]

    # Posterior modes: sequential always; rolling only for windows >= 60.
    posterior_seq = "sequential_update"
    posterior_roll = "rolling_update"

    experiments = []

    campaign_log = os.path.join(base_dir, "run_log.txt")
    with open(campaign_log, "w", encoding="utf-8") as f:
        f.write(f"dataset={dataset} symbols={symbols} base_date={base_date}\n")
        f.write(f"windows_min={windows_min}\n")
        f.write(f"slices={slice_specs}\n")
        f.write("Design: core weights (RAW,SUBLINEAR) for all windows; rolling for >=60; full weights only on 60m.\n")

    for slice_name, start_utc in slice_specs:
        start_dt = datetime.fromisoformat(start_utc).replace(tzinfo=timezone.utc)

        for w_min in windows_min:
            end_dt = start_dt + timedelta(minutes=int(w_min))
            start_s = start_dt.strftime("%Y-%m-%dT%H:%M")
            end_s = end_dt.strftime("%Y-%m-%dT%H:%M")

            dl_dir = os.path.join(base_dir, "downloads", slice_name, f"W{w_min}m")
            _ensure(dl_dir)

            raw_csv_path = os.path.join(dl_dir, "raw_trades.csv")
            if os.path.exists(raw_csv_path):
                raw_csv = open(raw_csv_path, "rb").read()
                est_cost = 0.0
            else:
                raw_csv, est_cost = _download_trades_csv(
                    dataset=dataset,
                    symbols=symbols,
                    stype_in=stype_in,
                    start=start_s,
                    end=end_s,
                    out_dir=dl_dir,
                    budget=budget,
                )
                open(raw_csv_path, "wb").write(raw_csv)

            total_cost += float(est_cost)

            # Parse -> trades -> base evidence tape
            events = list(parse_trades_csv(raw_csv, instrument_id_fallback=symbols))
            trades, recon_diag = reconstruct_trades(events)
            base_tape, meta = trades_to_evidence_tape(
                trades,
                instrument=(events[0].instrument_id if events else symbols),
                source=f"databento:{dataset}:trades",
                adapter_version="databento_phase_f_v1",
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
                tape_len=len(base_tape),
            )

            # Determine which weightings to run
            weightings = list(weight_core)
            if w_min == 60:
                weightings = list(weight_full)

            for wm in weightings:
                wfn = get_weight_fn(wm, {"cap": 10.0, "sublinear_kind": "sqrt", "q0": 1.0, "w_max": 10.0})
                weighted_tape: List[EvidenceTapeEntry] = []
                weights = []
                for tr in base_tape:
                    size = float(wfn(float(getattr(tr, "size"))))
                    if size <= 0:
                        continue
                    weights.append(size)
                    weighted_tape.append(
                        EvidenceTapeEntry(
                            timestamp_ns=int(getattr(tr, "timestamp_ns")),
                            side=getattr(tr, "side"),
                            size=size,
                            implied_yes_before=float(getattr(tr, "implied_yes_before", 0.5)),
                        )
                    )

                y_raw, n_raw = counts_from_trade_tape(weighted_tape)
                ess = ess_weights(weights)

                for dm in dep_modes:
                    y_adj, n_adj, dep_diag = apply_dependence_adjustment(y_raw, n_raw, mode=dm, ess=ess)

                    # sequential always
                    pts_seq = update_sequential(1.0, 1.0, weighted_tape, bucket_ns=1_000_000_000)
                    exp_id = f"S{slice_name}__W{w_min}m__{wm}__{dm}__{posterior_seq}"
                    out_dir = os.path.join(base_dir, exp_id)
                    _ensure(out_dir)

                    write_adapter_diagnostics(os.path.join(out_dir, "adapter_diagnostics.json"), adapter_diag)

                    summary = {
                        "experiment_id": exp_id,
                        "scenario_name": SCENARIO_NAME,
                        "slice": slice_name,
                        "dataset": dataset,
                        "symbols": symbols,
                        "window_minutes": w_min,
                        "start": start_s,
                        "end": end_s,
                        "estimated_cost_usd_for_window_download": est_cost,
                        "weighting_mode": wm,
                        "dependence_mode": dm,
                        "dependence_diag": dep_diag,
                        "posterior_mode": posteriorior_seq if False else posterior_seq,
                        "realdata": evidence_meta_to_dict(meta),
                        "evidence_counts": {"y_raw": y_raw, "n_raw": n_raw, "y_used": y_adj, "n_used": n_adj, "ess_w": ess},
                        "posterior_points": [asdict(p) for p in pts_seq],
                        "note": "Expanded validation (Phase F): demonstration/proxy evidence only.",
                    }
                    _write_json(os.path.join(out_dir, "summary.json"), summary)

                    metrics_path = os.path.join(out_dir, "metrics_aggregated.csv")
                    with open(metrics_path, "w", newline="", encoding="utf-8") as f:
                        w = csv.writer(f)
                        w.writerow(["experiment_id", "p_hat_last", "alpha_last", "beta_last", "n_used", "y_used", "ess_w"])
                        if pts_seq:
                            last = pts_seq[-1]
                            w.writerow([exp_id, last.p_hat, last.alpha, last.beta, n_adj, y_adj, ess])

                    with open(os.path.join(out_dir, "reliability_capopm.csv"), "w", newline="", encoding="utf-8") as f:
                        csv.writer(f).writerows([["note"], ["placeholder: proxy evidence; no outcomes"]])
                    with open(os.path.join(out_dir, "tests.csv"), "w", newline="", encoding="utf-8") as f:
                        csv.writer(f).writerows([["note"], ["placeholder"]])

                    run_log = os.path.join(out_dir, "run_log.txt")
                    with open(run_log, "w", encoding="utf-8") as f:
                        f.write(json.dumps({"exp_id": exp_id, "window_download_cost": est_cost, "slice": slice_name}, indent=2))

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
                            "experiment": "REALDATA_EXPANDED_VALIDATION",
                            "scenario_name": SCENARIO_NAME,
                            "experiment_id": exp_id,
                            "tier": "REALDATA",
                            "dataset": dataset,
                            "schema": "trades",
                            "symbols": symbols,
                            "slice": slice_name,
                            "start": start_s,
                            "end": end_s,
                            "estimated_cost_usd_window": est_cost,
                            "results_dir": out_dir,
                            "artifact_hashes": hashes,
                        }
                    )
                    experiments.append(exp_id)

                    # rolling only for >=60m
                    if w_min >= 60:
                        pts_roll = update_rolling(1.0, 1.0, weighted_tape, window_ns=min(w_min, 60) * 60_000_000_000)
                        exp_id2 = f"S{slice_name}__W{w_min}m__{wm}__{dm}__{posterior_roll}"
                        out_dir2 = os.path.join(base_dir, exp_id2)
                        _ensure(out_dir2)
                        write_adapter_diagnostics(os.path.join(out_dir2, "adapter_diagnostics.json"), adapter_diag)
                        summary2 = {
                            **summary,
                            "experiment_id": exp_id2,
                            "posterior_mode": posterior_roll,
                            "posterior_points": [asdict(p) for p in pts_roll],
                        }
                        _write_json(os.path.join(out_dir2, "summary.json"), summary2)
                        metrics_path2 = os.path.join(out_dir2, "metrics_aggregated.csv")
                        with open(metrics_path2, "w", newline="", encoding="utf-8") as f:
                            w = csv.writer(f)
                            w.writerow(["experiment_id", "p_hat_last", "alpha_last", "beta_last", "n_used", "y_used", "ess_w"])
                            if pts_roll:
                                last = pts_roll[-1]
                                w.writerow([exp_id2, last.p_hat, last.alpha, last.beta, n_adj, y_adj, ess])
                        with open(os.path.join(out_dir2, "reliability_capopm.csv"), "w", newline="", encoding="utf-8") as f:
                            csv.writer(f).writerows([["note"], ["placeholder: proxy evidence; no outcomes"]])
                        with open(os.path.join(out_dir2, "tests.csv"), "w", newline="", encoding="utf-8") as f:
                            csv.writer(f).writerows([["note"], ["placeholder"]])
                        run_log2 = os.path.join(out_dir2, "run_log.txt")
                        with open(run_log2, "w", encoding="utf-8") as f:
                            f.write(json.dumps({"exp_id": exp_id2, "window_download_cost": est_cost, "slice": slice_name}, indent=2))
                        artifact_paths2 = [
                            os.path.join(out_dir2, "summary.json"),
                            os.path.join(out_dir2, "adapter_diagnostics.json"),
                            metrics_path2,
                            os.path.join(out_dir2, "reliability_capopm.csv"),
                            os.path.join(out_dir2, "tests.csv"),
                            run_log2,
                        ]
                        hashes2 = _write_hashes(out_dir2, artifact_paths2)
                        _append_manifest(
                            {
                                "experiment": "REALDATA_EXPANDED_VALIDATION",
                                "scenario_name": SCENARIO_NAME,
                                "experiment_id": exp_id2,
                                "tier": "REALDATA",
                                "dataset": dataset,
                                "schema": "trades",
                                "symbols": symbols,
                                "slice": slice_name,
                                "start": start_s,
                                "end": end_s,
                                "estimated_cost_usd_window": est_cost,
                                "results_dir": out_dir2,
                                "artifact_hashes": hashes2,
                            }
                        )
                        experiments.append(exp_id2)

    campaign_summary = {
        "scenario_name": SCENARIO_NAME,
        "dataset": dataset,
        "symbols": symbols,
        "windows_min": windows_min,
        "slices": [s for s, _ in slice_specs],
        "total_estimated_cost_usd": total_cost,
        "n_experiments": len(experiments),
        "note": "Phase F expanded campaign. Proxy evidence only.",
    }
    _write_json(os.path.join(base_dir, "summary.json"), campaign_summary)
    _write_hashes(base_dir, [os.path.join(base_dir, "summary.json"), campaign_log])
    return campaign_summary
