"""Generate black-background showcase figures from REALDATA grid artifacts.

No numpy/matplotlib dependency: emits SVG and uses ImageMagick convert for PNG/PDF.

Usage:
  python3 scripts/generate_realdata_grid_viz.py
"""

from __future__ import annotations

import glob
import json
import os
import subprocess
from math import exp, lgamma

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RESULTS = os.path.join(REPO_ROOT, "results", "REALDATA_GRID_RUN")
OUT = os.path.join(RESULTS, "prism_showcase")
FIG = os.path.join(RESULTS, "figures")


def ensure(p: str):
    os.makedirs(p, exist_ok=True)


def svg_header(w=1600, h=900):
    return f"""<svg xmlns='http://www.w3.org/2000/svg' width='{w}' height='{h}' viewBox='0 0 {w} {h}'>
<rect width='100%' height='100%' fill='black'/>
"""


def svg_footer():
    return "</svg>\n"


def polyline(points, stroke="#00e5ff", width=3, opacity=1.0):
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return f"<polyline points='{pts}' fill='none' stroke='{stroke}' stroke-width='{width}' opacity='{opacity}'/>\n"


def text(x, y, s, fill="#e0e0e0", size=28, anchor="start"):
    s = s.replace("&", "&amp;").replace("<", "&lt;")
    return f"<text x='{x}' y='{y}' fill='{fill}' font-family='DejaVu Sans' font-size='{size}' text-anchor='{anchor}'>{s}</text>\n"


def beta_pdf(x, a, b):
    if x <= 0 or x >= 1:
        return 0.0
    log_norm = lgamma(a) + lgamma(b) - lgamma(a + b)
    return exp((a - 1) * (0 if x <= 0 else __import__("math").log(x)) + (b - 1) * __import__("math").log(1 - x) - log_norm)


def load_experiments():
    exps = []
    for p in glob.glob(os.path.join(RESULTS, "W*m__*", "summary.json")):
        with open(p, "r", encoding="utf-8") as f:
            exps.append(json.load(f))
    return exps


def convert_all(svg_path: str):
    base = os.path.splitext(svg_path)[0]
    subprocess.run(["convert", svg_path, base + ".png"], check=False)
    subprocess.run(["convert", svg_path, base + ".pdf"], check=False)


def fig_index(entries):
    with open(os.path.join(OUT, "FIGURE_INDEX.md"), "w", encoding="utf-8") as f:
        f.write("# FIGURE_INDEX\n\n")
        for name, src in entries:
            f.write(f"- **{name}** ← `{src}`\n")


def main():
    ensure(OUT)
    ensure(FIG)

    exps = load_experiments()
    if not exps:
        print("No experiments found under results/REALDATA_GRID_RUN/*/summary.json")
        return

    # Pick a representative subset: 1m window, RAW_N, sequential_update across weighting modes.
    subset = [e for e in exps if e.get("window_minutes") == 1 and e.get("dependence_mode") == "RAW_N" and e.get("posterior_mode") == "sequential_update"]
    subset = sorted(subset, key=lambda d: d.get("weighting_mode"))

    # Visualization 4: weighting comparison trajectories
    W, H = 1600, 900
    margin = 100
    svg = svg_header(W, H)
    svg += text(80, 70, "Posterior trajectories (1m, sequential, RAW_N) — weighting comparison", size=30)

    colors = {
        "RAW": "#00e5ff",
        "SIZE_WEIGHTED": "#ffb300",
        "CAPPED": "#76ff03",
        "SUBLINEAR": "#ff1744",
        "IMBALANCE_ADJUSTED": "#b388ff",
    }

    fig_entries = []

    for e in subset:
        pts = e.get("posterior_points", [])
        if len(pts) < 2:
            continue
        pvals = [float(p["p_hat"]) for p in pts]
        tvals = list(range(len(pvals)))
        xscale = (W - 2 * margin) / max(1, (len(pvals) - 1))
        yscale = (H - 2 * margin)
        points = [(margin + i * xscale, margin + (1 - p) * yscale) for i, p in enumerate(pvals)]
        mode = e.get("weighting_mode")
        svg += polyline(points, stroke=colors.get(mode, "#00e5ff"), width=3, opacity=0.9)
        svg += text(W - 30, margin + 40 + 30 * list(colors.keys()).index(mode), mode, fill=colors.get(mode, "#e0e0e0"), size=22, anchor="end")

    svg += text(margin, H - 40, "x: time buckets (1s)    y: posterior mean p_hat", size=22)
    svg += svg_footer()
    out_path = os.path.join(OUT, "VIZ4_weighting_comparison.svg")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    convert_all(out_path)
    fig_entries.append(("VIZ4_weighting_comparison", "subset: W1m__*__RAW_N__sequential_update"))

    fig_index(fig_entries)
    print("Wrote showcase figures to", OUT)


if __name__ == "__main__":
    main()
