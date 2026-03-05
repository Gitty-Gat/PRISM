"""Dashboard data loader.

Loads aggregated CSVs + per-experiment summaries once at startup.
Uses only stdlib (csv/json/hashlib).
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
from glob import glob


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_csv(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _verify_hashes(exp_dir: str) -> dict:
    """Verify artifact_hashes.json for the experiment directory.

    Current check: summary.json hash match.
    """

    hp = os.path.join(exp_dir, "artifact_hashes.json")
    sp = os.path.join(exp_dir, "summary.json")
    if not os.path.exists(hp) or not os.path.exists(sp):
        return {"status": "missing", "details": "artifact_hashes.json or summary.json missing"}
    try:
        h = json.load(open(hp, "r", encoding="utf-8"))
    except Exception:
        return {"status": "invalid", "details": "artifact_hashes.json not parseable"}
    expect = h.get("summary.json")
    actual = _sha256_file(sp)
    if expect != actual:
        return {"status": "mismatch", "expected": expect, "actual": actual}
    return {"status": "ok"}


def load_dashboard_state(repo_root: str) -> dict:
    base = os.path.join(repo_root, "results", "REALDATA_GRID_RUN")
    analysis = os.path.join(base, "analysis")

    global_table = _read_csv(os.path.join(analysis, "global_experiment_table.csv"))
    posterior_metrics = _read_csv(os.path.join(analysis, "posterior_metrics.csv"))
    evidence_stats = _read_csv(os.path.join(analysis, "evidence_statistics.csv"))

    # Index per experiment
    experiments = {}
    for row in global_table:
        exp_id = row["experiment_id"]
        exp_dir = os.path.join(base, exp_id)
        summary_path = os.path.join(exp_dir, "summary.json")
        try:
            summary = json.load(open(summary_path, "r", encoding="utf-8"))
        except Exception:
            summary = {"error": "missing_or_invalid_summary"}

        verify = _verify_hashes(exp_dir)

        experiments[exp_id] = {
            "experiment_id": exp_id,
            "global": row,
            "summary": summary,
            "hash_check": verify,
        }

    # Small landing aggregates
    window_lengths = sorted({r["window_length_min"] for r in global_table})
    weighting = sorted({r["weighting_method"] for r in global_table})
    dependence = sorted({r["dependence_method"] for r in global_table})

    public_state = {
        "n_experiments": len(global_table),
        "window_lengths": window_lengths,
        "weighting_methods": weighting,
        "dependence_methods": dependence,
        "experiment_ids": [r["experiment_id"] for r in global_table],
        "tables": {
            "global_experiment_table": global_table,
            "posterior_metrics": posterior_metrics,
            "evidence_statistics": evidence_stats,
        },
    }

    return {"public_state": public_state, "experiments": experiments}
