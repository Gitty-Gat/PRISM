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


def _load_campaign(repo_root: str, campaign: str) -> dict:
    base = os.path.join(repo_root, "results", campaign)
    analysis = os.path.join(base, "analysis")

    global_table = _read_csv(os.path.join(analysis, "global_experiment_table.csv"))
    posterior_metrics = _read_csv(os.path.join(analysis, "posterior_metrics.csv"))
    evidence_stats = _read_csv(os.path.join(analysis, "evidence_statistics.csv"))

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
        experiments[exp_id] = {"experiment_id": exp_id, "global": row, "summary": summary, "hash_check": verify}

    window_lengths = sorted({r.get("window_length_min") for r in global_table if r.get("window_length_min")})
    weighting = sorted({r.get("weighting_method") for r in global_table if r.get("weighting_method")})
    dependence = sorted({r.get("dependence_method") for r in global_table if r.get("dependence_method")})
    slices = sorted({r.get("time_slice") for r in global_table if r.get("time_slice")})
    posterior_modes = sorted({r.get("posterior_mode") for r in global_table if r.get("posterior_mode")})

    public_state = {
        "campaign": campaign,
        "n_experiments": len(global_table),
        "window_lengths": window_lengths,
        "weighting_methods": weighting,
        "dependence_methods": dependence,
        "time_slices": slices,
        "posterior_modes": posterior_modes,
        "experiment_ids": [r["experiment_id"] for r in global_table],
        "tables": {
            "global_experiment_table": global_table,
            "posterior_metrics": posterior_metrics,
            "evidence_statistics": evidence_stats,
        },
    }
    return {"public_state": public_state, "experiments": experiments}


def load_dashboard_state(repo_root: str) -> dict:
    campaigns = ["REALDATA_GRID_RUN", "REALDATA_EXPANDED_VALIDATION"]
    loaded = {}
    for c in campaigns:
        # Only load campaigns that exist
        if os.path.exists(os.path.join(repo_root, "results", c, "analysis")):
            loaded[c] = _load_campaign(repo_root, c)

    # Default campaign
    default = "REALDATA_GRID_RUN" if "REALDATA_GRID_RUN" in loaded else next(iter(loaded.keys()))

    public_state = {
        "campaigns": list(loaded.keys()),
        "default_campaign": default,
        "campaign_states": {k: v["public_state"] for k, v in loaded.items()},
    }
    experiments = {k: v["experiments"] for k, v in loaded.items()}
    return {"public_state": public_state, "experiments": experiments}
