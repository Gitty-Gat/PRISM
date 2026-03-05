"""Unified lightweight experiment runner.

Usage:
  python scripts/run_experiment.py --scenario REALDATA_L3_ADAPTER_SANITY

Design goals:
- consistent dispatch to scenario implementations
- minimal policy surface (no Bayesian-core edits)
- writes artifacts under results/<scenario>/
- updates PAPER_RUN_MANIFEST.json with scenario metadata + artifact hashes

Supported scenarios (initial):
- REALDATA_L3_ADAPTER_SANITY

Note:
- This runner is intentionally small; paper suite remains `run_paper_suite.py`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict

# Ensure repo root is on sys.path so `import src.*` works when invoked as a script.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _update_manifest(entry: Dict[str, Any]) -> None:
    """Append-only update of PAPER_RUN_MANIFEST.json (best-effort)."""

    manifest_path = "PAPER_RUN_MANIFEST.json"
    created_utc = datetime.utcnow().isoformat() + "Z"
    manifest = {
        "paper_runs": [entry],
        "created_utc": created_utc,
        "python_version": sys.version,
        "command": sys.argv,
        "ast_gate": {"checker_path": None, "status": "not_run"},
    }

    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                prev = json.load(f)
            if isinstance(prev, dict) and isinstance(prev.get("paper_runs"), list):
                manifest["paper_runs"] = prev["paper_runs"] + manifest["paper_runs"]
        except Exception:
            # do not fail experiment execution due to manifest read.
            pass

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Unified experiment runner")
    parser.add_argument("--scenario", required=True, help="Scenario name")
    args = parser.parse_args()

    scenario = str(args.scenario)

    if scenario == "REALDATA_L3_ADAPTER_SANITY":
        from src.capopm.experiments.real_data_config import SCENARIO_NAME, run_realdata_l3_adapter_sanity

        if scenario != SCENARIO_NAME:
            raise SystemExit(f"Scenario mismatch: {scenario} != {SCENARIO_NAME}")

        results = run_realdata_l3_adapter_sanity()
        results_dir = os.path.join("results", scenario)
        artifact_names = [
            "summary.json",
            "metrics_aggregated.csv",
            "reliability_capopm.csv",
            "tests.csv",
            "adapter_diagnostics.json",
        ]
        artifact_hashes = {}
        for name in artifact_names:
            path = os.path.join(results_dir, name)
            if os.path.exists(path):
                artifact_hashes[name] = _sha256_file(path)

        entry = {
            "experiment": "REALDATA",
            "scenario_name": scenario,
            "seed": results.get("seed"),
            "base_seed": results.get("seed"),
            "run_index": None,
            "sweep_params": {},
            "n_runs": 1,
            "tier": "REALDATA",
            "results_dir": results_dir,
            "summary_path": os.path.join(results_dir, "summary.json"),
            "audit_path": None,
            "audit_hash": None,
            "artifact_hashes": artifact_hashes,
        }
        _update_manifest(entry)
        print(f"OK: ran {scenario}; wrote artifacts to {results_dir}")
        return

    raise SystemExit(f"Unknown scenario: {scenario}")


if __name__ == "__main__":
    main()
