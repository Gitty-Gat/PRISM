"""Real-data experiment configs (Stage B.4).

This module registers smoke scenarios that validate the adapter boundary:

L3 adapter -> trade reconstruction -> evidence tape -> counts_from_trade_tape -> capopm_pipeline

Hard constraints:
- Do not modify Bayesian core.
- Keep this as experiment/adaptor wiring only.
"""

from __future__ import annotations

import csv
import json
import os
from typing import Dict, List, Tuple

import random

from ..likelihood import counts_from_trade_tape, beta_binomial_update
from ..pricing import posterior_prices
from ..metrics.scoring import brier, log_score, mae_prob
from ..invariant_runtime import InvariantContext, reset_invariant_context, set_invariant_context, stable_config_hash

from ..realdata.adapter import ADAPTER_VERSION, parse_jsonl_events
from ..realdata.trade_reconstruction import reconstruct_trades
from ..realdata.evidence import trades_to_evidence_tape, evidence_meta_to_dict
from ..realdata.diagnostics import build_diagnostics, write_adapter_diagnostics


SCENARIO_NAME = "REALDATA_L3_ADAPTER_SANITY"


def _results_dir() -> str:
    return os.path.join("results", SCENARIO_NAME)


def _write_summary(path: str, payload: Dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def run_realdata_l3_adapter_sanity(
    *,
    data_path: str = os.path.join("data", "test_l3", "sample_events.jsonl"),
    seed: int = 123,
) -> Dict:
    """Smoke scenario: adapter + reconstruction + evidence + CAPOPM compatibility.

    This is intentionally lightweight (<5s) and deterministic.

    Artifacts written under results/REALDATA_L3_ADAPTER_SANITY/:
      - summary.json
      - metrics_aggregated.csv
      - reliability_capopm.csv
      - tests.csv (placeholder)
      - adapter_diagnostics.json
    """

    os.makedirs(_results_dir(), exist_ok=True)

    # --- Adapter + reconstruction ---
    events = list(parse_jsonl_events(data_path))
    trades, recon_diag = reconstruct_trades(events)
    tape, meta = trades_to_evidence_tape(
        trades,
        instrument=(events[0].instrument_id if events else "UNKNOWN"),
        source="data/test_l3",
        adapter_version=ADAPTER_VERSION,
        implied_yes_before_default=0.5,
    )

    # Fill meta with counts/diagnostics.
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
    write_adapter_diagnostics(os.path.join(_results_dir(), "adapter_diagnostics.json"), adapter_diag)

    # --- Evidence -> Bayesian update (core-compatible seam) ---
    # NOTE: This smoke scenario intentionally avoids importing numpy so it can run
    # in minimal environments. It validates the *adapter boundary* by using the
    # same evidence counts interface (`counts_from_trade_tape`) and the same
    # conjugate update math (`beta_binomial_update`).
    #
    # When numpy is available, a future scenario can call `posterior.capopm_pipeline`
    # without changing the adapter layer.

    rng = random.Random(seed)
    p_true = 0.5
    outcome = 1 if rng.random() < p_true else 0

    y, n = counts_from_trade_tape(tape)

    # Minimal Beta(1,1) prior for smoke. (Does not claim paper alignment.)
    alpha0, beta0 = 1.0, 1.0
    alpha_post, beta_post = beta_binomial_update(alpha0, beta0, y, n)
    p_hat, _ = posterior_prices(alpha_post, beta_post)

    cfg_snapshot = {
        "scenario_name": SCENARIO_NAME,
        "seed": seed,
        "data_path": data_path,
        "prior": {"alpha0": alpha0, "beta0": beta0},
        "realdata": evidence_meta_to_dict(meta),
    }
    cfg_hash = stable_config_hash(cfg_snapshot)
    ctx_token = set_invariant_context(
        InvariantContext(experiment_id="REALDATA", scenario_name=SCENARIO_NAME, run_seed=seed, config_hash=cfg_hash)
    )
    try:
        # No additional invariants to record here; core invariants are inside beta_binomial_update.
        pass
    finally:
        reset_invariant_context(ctx_token)

    # --- Metrics + reliability ---
    metrics = {
        "brier": brier(p_true, p_hat),
        "log_score": log_score(p_hat, outcome),
        "mae_prob": mae_prob(p_true, p_hat),
        "p_hat": p_hat,
        "y": y,
        "n": n,
    }

    metrics_path = os.path.join(_results_dir(), "metrics_aggregated.csv")
    with open(metrics_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["scenario_name", "model", "brier", "log_score", "mae_prob", "p_hat", "y", "n"])
        w.writerow([SCENARIO_NAME, "capopm", metrics["brier"], metrics["log_score"], metrics["mae_prob"], metrics["p_hat"], y, n])

    # Reliability artifact (placeholder): full ECE/reliability requires numpy.
    rel_diag = {
        "status": "SKIPPED",
        "reason": "numpy_not_available",
        "n_samples": 1,
    }
    rel_path = os.path.join(_results_dir(), "reliability_capopm.csv")
    with open(rel_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["scenario_name", "model", "note"])
        w.writerow([SCENARIO_NAME, "capopm", "placeholder: reliability not computed (numpy not available)"])

    # Placeholder tests file (no baselines in smoke).
    tests_path = os.path.join(_results_dir(), "tests.csv")
    with open(tests_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["scenario_name", "model", "note"])
        w.writerow([SCENARIO_NAME, "capopm", "Smoke-only: no paired baselines executed."])

    summary = {
        "scenario_name": SCENARIO_NAME,
        "seed": seed,
        "config_hash": cfg_hash,
        "realdata": evidence_meta_to_dict(meta),
        "adapter_diagnostics_file": "adapter_diagnostics.json",
        "metrics": metrics,
        "reliability_diagnostics": rel_diag,
        "note": "Smoke scenario validates adapter->evidence->counts_from_trade_tape compatibility. Not a paper claim validation.",
    }
    _write_summary(os.path.join(_results_dir(), "summary.json"), summary)

    return summary
