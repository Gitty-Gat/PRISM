"""Run robustness tests on REALDATA_EXPANDED_VALIDATION artifacts.

Produces:
- results/REALDATA_EXPANDED_VALIDATION/robustness/robustness_report.json

No external deps.
"""

from __future__ import annotations

import json
import os
from glob import glob


def load_summaries(base: str) -> list[dict]:
    out = []
    for p in glob(os.path.join(base, "S*__W*m__*__*__*", "summary.json")):
        try:
            out.append(json.load(open(p, "r", encoding="utf-8")))
        except Exception:
            pass
    return out


def main() -> None:
    base = os.path.join("results", "REALDATA_EXPANDED_VALIDATION")
    sums = load_summaries(base)
    os.makedirs(os.path.join(base, "robustness"), exist_ok=True)

    # Posterior stability: variance of final p_hat across slices for each (window, weight, dep, mode)
    buckets = {}
    for s in sums:
        key = (s.get("window_minutes"), s.get("weighting_mode"), s.get("dependence_mode"), s.get("posterior_mode"))
        pts = s.get("posterior_points") or []
        if not pts:
            continue
        p_last = float(pts[-1].get("p_hat"))
        buckets.setdefault(key, []).append(p_last)

    stability = []
    for key, vals in buckets.items():
        if len(vals) < 2:
            continue
        m = sum(vals) / len(vals)
        var = sum((v - m) ** 2 for v in vals) / (len(vals) - 1)
        stability.append(
            {
                "window_minutes": key[0],
                "weighting_mode": key[1],
                "dependence_mode": key[2],
                "posterior_mode": key[3],
                "n_slices": len(vals),
                "mean_p_last": m,
                "var_p_last_across_slices": var,
            }
        )

    report = {
        "n_experiments": len(sums),
        "stability_by_config": stability,
        "notes": [
            "Proxy-evidence robustness only.",
            "This file is descriptive; not a dominance or validation claim.",
        ],
    }

    out_path = os.path.join(base, "robustness", "robustness_report.json")
    json.dump(report, open(out_path, "w", encoding="utf-8"), indent=2)
    print("OK:", out_path)


if __name__ == "__main__":
    main()
