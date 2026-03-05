"""Expanded visualization suite for REALDATA_GRID_RUN.

Outputs SVG + PNG (via ImageMagick convert) in:
- results/REALDATA_GRID_RUN/prism_showcase/

No matplotlib.
"""

from __future__ import annotations

import glob
import json
import os
import subprocess
from math import exp, lgamma, log, sqrt

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BASE = os.path.join(REPO_ROOT, "results", "REALDATA_GRID_RUN")
OUT = os.path.join(BASE, "prism_showcase")
VID = os.path.join(BASE, "videos")


def ensure(p: str):
    os.makedirs(p, exist_ok=True)


def convert_svg(svg_path: str):
    base = os.path.splitext(svg_path)[0]
    subprocess.run(["convert", svg_path, base + ".png"], check=False)


def svg_header(w=1600, h=900):
    return f"""<svg xmlns='http://www.w3.org/2000/svg' width='{w}' height='{h}' viewBox='0 0 {w} {h}'>
<rect width='100%' height='100%' fill='black'/>
"""


def svg_footer():
    return "</svg>\n"


def text(x, y, s, fill="#e0e0e0", size=28, anchor="start"):
    s = s.replace("&", "&amp;").replace("<", "&lt;")
    return f"<text x='{x}' y='{y}' fill='{fill}' font-family='DejaVu Sans' font-size='{size}' text-anchor='{anchor}'>{s}</text>\n"


def polyline(points, stroke="#00e5ff", width=3, opacity=1.0):
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return f"<polyline points='{pts}' fill='none' stroke='{stroke}' stroke-width='{width}' opacity='{opacity}'/>\n"


def polygon(points, fill="#00e5ff", opacity=0.15):
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return f"<polygon points='{pts}' fill='{fill}' opacity='{opacity}'/>\n"


def beta_mean_var(a: float, b: float) -> tuple[float, float]:
    s = a + b
    if s <= 0:
        return 0.5, 0.0
    m = a / s
    v = (a * b) / (s * s * (s + 1.0))
    return m, v


def beta_pdf(x: float, a: float, b: float) -> float:
    if x <= 0.0 or x >= 1.0:
        return 0.0
    log_norm = lgamma(a) + lgamma(b) - lgamma(a + b)
    return exp((a - 1) * log(x) + (b - 1) * log(1 - x) - log_norm)


def normal_ci(mean: float, var: float, z: float = 1.645) -> tuple[float, float]:
    sd = sqrt(max(var, 0.0))
    lo = max(0.0, mean - z * sd)
    hi = min(1.0, mean + z * sd)
    return lo, hi


def load_summary(exp_id: str) -> dict:
    p = os.path.join(BASE, exp_id, "summary.json")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def pick_rep_exp(window_min: int = 1, weighting: str = "RAW", dep: str = "RAW_N") -> str:
    pat = os.path.join(BASE, f"W{window_min}m__{weighting}__{dep}__sequential_update")
    if os.path.exists(pat):
        return os.path.basename(pat)
    # fallback: first matching
    for d in glob.glob(os.path.join(BASE, f"W{window_min}m__*__{dep}__sequential_update")):
        return os.path.basename(d)
    raise RuntimeError("No experiment directories found")


def viz1_posterior_evolution(exp_id: str) -> str:
    s = load_summary(exp_id)
    pts = s.get("posterior_points", [])
    if len(pts) < 2:
        raise RuntimeError("Not enough posterior points")

    W, H = 1600, 900
    margin = 120
    x0, x1 = margin, W - margin
    y0, y1 = margin, H - margin

    means = []
    lows = []
    highs = []
    for p in pts:
        a = float(p["alpha"])
        b = float(p["beta"])
        m, v = beta_mean_var(a, b)
        lo, hi = normal_ci(m, v)
        means.append(m)
        lows.append(lo)
        highs.append(hi)

    n = len(means)
    xscale = (x1 - x0) / max(1, n - 1)

    def y_map(val: float) -> float:
        return y0 + (1.0 - val) * (y1 - y0)

    mean_pts = [(x0 + i * xscale, y_map(means[i])) for i in range(n)]
    band_pts = [(x0 + i * xscale, y_map(highs[i])) for i in range(n)] + [
        (x0 + i * xscale, y_map(lows[i])) for i in reversed(range(n))
    ]

    svg = svg_header(W, H)
    svg += text(80, 70, f"Posterior evolution (normal CI approx) — {exp_id}", size=30)
    svg += polygon(band_pts, fill="#00e5ff", opacity=0.18)
    svg += polyline(mean_pts, stroke="#00e5ff", width=4, opacity=0.95)
    svg += text(margin, H - 40, "x: sequential time buckets   y: posterior mean with 90% band (normal approx)", size=22)
    svg += svg_footer()

    out = os.path.join(OUT, f"VIZ1_posterior_evolution__{exp_id}.svg")
    with open(out, "w", encoding="utf-8") as f:
        f.write(svg)
    convert_svg(out)
    return out


def viz2_evidence_vs_posterior(exp_id: str) -> str:
    s = load_summary(exp_id)
    pts = s.get("posterior_points", [])
    if len(pts) < 2:
        raise RuntimeError("Not enough posterior points")

    # We approximate cumulative evidence strength by cumulative (alpha+beta) growth.
    strengths = [float(p["alpha"]) + float(p["beta"]) for p in pts]
    means = [float(p["p_hat"]) for p in pts]

    W, H = 1600, 900
    margin = 120
    x0, x1 = margin, W - margin
    y0, y1 = margin, H - margin

    smin, smax = min(strengths), max(strengths)

    def x_map(val: float) -> float:
        if smax <= smin:
            return x0
        return x0 + (val - smin) / (smax - smin) * (x1 - x0)

    def y_map(val: float) -> float:
        return y0 + (1.0 - val) * (y1 - y0)

    pts_xy = [(x_map(strengths[i]), y_map(means[i])) for i in range(len(means))]

    svg = svg_header(W, H)
    svg += text(80, 70, f"Evidence accumulation vs posterior mean — {exp_id}", size=30)
    svg += polyline(pts_xy, stroke="#76ff03", width=4, opacity=0.95)
    svg += text(margin, H - 40, "x: cumulative evidence strength proxy (alpha+beta)   y: posterior mean", size=22)
    svg += svg_footer()

    out = os.path.join(OUT, f"VIZ2_evidence_vs_posterior__{exp_id}.svg")
    with open(out, "w", encoding="utf-8") as f:
        f.write(svg)
    convert_svg(out)
    return out


def viz7_density_snapshots(exp_id: str) -> str:
    s = load_summary(exp_id)
    pts = s.get("posterior_points", [])
    if len(pts) < 3:
        raise RuntimeError("Not enough posterior points")

    idxs = [0, len(pts) // 2, len(pts) - 1]
    colors = ["#00e5ff", "#ffb300", "#ff1744"]

    W, H = 1600, 900
    margin = 120
    x0, x1 = margin, W - margin
    y0, y1 = margin, H - margin

    # Build density curves
    xs = [i / 300.0 for i in range(1, 300)]
    curves = []
    ymax = 1e-9
    for j, idx in enumerate(idxs):
        a = float(pts[idx]["alpha"])
        b = float(pts[idx]["beta"])
        ys = [beta_pdf(x, a, b) for x in xs]
        ymax = max(ymax, max(ys))
        curves.append((ys, colors[j], idx))

    def x_map(x: float) -> float:
        return x0 + x * (x1 - x0)

    def y_map_density(y: float) -> float:
        # map density to screen y
        return y1 - (y / ymax) * (y1 - y0)

    svg = svg_header(W, H)
    svg += text(80, 70, f"Posterior density snapshots — {exp_id}", size=30)

    for ys, col, idx in curves:
        pts_xy = [(x_map(xs[i]), y_map_density(ys[i])) for i in range(len(xs))]
        svg += polyline(pts_xy, stroke=col, width=4, opacity=0.95)
        svg += text(W - 40, 120 + 30 * idxs.index(idx), f"t_index={idx}", fill=col, size=22, anchor="end")

    svg += text(margin, H - 40, "x: probability   y: Beta density (scaled)", size=22)
    svg += svg_footer()

    out = os.path.join(OUT, f"VIZ7_density_snapshots__{exp_id}.svg")
    with open(out, "w", encoding="utf-8") as f:
        f.write(svg)
    convert_svg(out)
    return out


def viz5_variance_vs_ess(window_min: int = 1) -> str:
    # Compare RAW_N vs N* for each weighting mode at a window
    rows = []
    for d in glob.glob(os.path.join(BASE, f"W{window_min}m__*__*__sequential_update")):
        s = load_summary(os.path.basename(d))
        ev = s.get("evidence_counts", {})
        ess = float(ev.get("ess_w", 0.0))
        pts = s.get("posterior_points", [])
        last = pts[-1] if pts else None
        if not last:
            continue
        a = float(last["alpha"])
        b = float(last["beta"])
        m, v = beta_mean_var(a, b)
        rows.append((ess, v, s.get("weighting_mode"), s.get("dependence_mode")))

    if not rows:
        raise RuntimeError("No rows")

    W, H = 1600, 900
    margin = 120
    x0, x1 = margin, W - margin
    y0, y1 = margin, H - margin

    ess_vals = [r[0] for r in rows]
    var_vals = [r[1] for r in rows]
    xmin, xmax = min(ess_vals), max(ess_vals)
    ymin, ymax = min(var_vals), max(var_vals)

    def x_map(x: float) -> float:
        if xmax <= xmin:
            return x0
        return x0 + (x - xmin) / (xmax - xmin) * (x1 - x0)

    def y_map(y: float) -> float:
        if ymax <= ymin:
            return y1
        return y1 - (y - ymin) / (ymax - ymin) * (y1 - y0)

    colors = {"RAW_N": "#00e5ff", "EFFECTIVE_N_STAR": "#ffb300"}

    svg = svg_header(W, H)
    svg += text(80, 70, f"Posterior variance vs effective sample size — window {window_min}m", size=30)

    for ess, v, wm, dm in rows:
        col = colors.get(dm, "#e0e0e0")
        svg += f"<circle cx='{x_map(ess):.1f}' cy='{y_map(v):.1f}' r='5' fill='{col}' opacity='0.85'/>\n"

    svg += text(W - 40, 120, "RAW_N", fill=colors["RAW_N"], size=22, anchor="end")
    svg += text(W - 40, 150, "N*", fill=colors["EFFECTIVE_N_STAR"], size=22, anchor="end")
    svg += text(margin, H - 40, "x: ESS_w (proxy n*)   y: posterior variance", size=22)
    svg += svg_footer()

    out = os.path.join(OUT, f"VIZ5_variance_vs_ess__W{window_min}m.svg")
    with open(out, "w", encoding="utf-8") as f:
        f.write(svg)
    convert_svg(out)
    return out


def viz4_weighting_variance_compare(window_min: int = 1, dep: str = "RAW_N") -> str:
    # one point per weighting mode: last variance
    modes = ["RAW", "SIZE_WEIGHTED", "CAPPED", "SUBLINEAR", "IMBALANCE_ADJUSTED"]
    vals = []
    for m in modes:
        exp_id = pick_rep_exp(window_min, m, dep)
        s = load_summary(exp_id)
        pts = s.get("posterior_points", [])
        last = pts[-1]
        a = float(last["alpha"])
        b = float(last["beta"])
        mean, var = beta_mean_var(a, b)
        ciw = normal_ci(mean, var)[1] - normal_ci(mean, var)[0]
        vals.append((m, var, ciw, exp_id))

    W, H = 1600, 900
    margin = 120
    x0, x1 = margin, W - margin
    y0, y1 = margin, H - margin

    vmax = max(v for _, v, _, _ in vals) or 1.0
    cmax = max(c for _, _, c, _ in vals) or 1.0

    barw = (x1 - x0) / len(vals) * 0.6
    gap = (x1 - x0) / len(vals)

    svg = svg_header(W, H)
    svg += text(80, 70, f"Variance + 90% CI width by weighting ({window_min}m, {dep})", size=30)

    for i, (m, var, ciw, exp_id) in enumerate(vals):
        x = x0 + i * gap + gap * 0.2
        h1 = (var / vmax) * (y1 - y0)
        h2 = (ciw / cmax) * (y1 - y0)
        # variance bar
        svg += f"<rect x='{x:.1f}' y='{(y1-h1):.1f}' width='{barw:.1f}' height='{h1:.1f}' fill='#00e5ff' opacity='0.7'/>\n"
        # ci width bar overlay
        svg += f"<rect x='{(x+barw*0.65):.1f}' y='{(y1-h2):.1f}' width='{(barw*0.35):.1f}' height='{h2:.1f}' fill='#ffb300' opacity='0.7'/>\n"
        svg += text(x + barw / 2, y1 + 30, m, fill="#e0e0e0", size=18, anchor="middle")

    svg += text(margin, H - 40, "cyan: posterior variance   amber: CI width (normal approx)", size=22)
    svg += svg_footer()

    out = os.path.join(OUT, f"VIZ4b_weighting_variance__W{window_min}m__{dep}.svg")
    with open(out, "w", encoding="utf-8") as f:
        f.write(svg)
    convert_svg(out)
    return out


def viz4_weighting_trajectory_compare(window_min: int = 1, dep: str = "RAW_N") -> str:
    # Similar to earlier VIZ4 but for given window/dep.
    modes = ["RAW", "SIZE_WEIGHTED", "CAPPED", "SUBLINEAR", "IMBALANCE_ADJUSTED"]
    colors = {
        "RAW": "#00e5ff",
        "SIZE_WEIGHTED": "#ffb300",
        "CAPPED": "#76ff03",
        "SUBLINEAR": "#ff1744",
        "IMBALANCE_ADJUSTED": "#b388ff",
    }

    series = []
    max_len = 0
    for m in modes:
        exp_id = pick_rep_exp(window_min, m, dep)
        s = load_summary(exp_id)
        pts = s.get("posterior_points", [])
        pvals = [float(p["p_hat"]) for p in pts]
        max_len = max(max_len, len(pvals))
        series.append((m, pvals, exp_id))

    W, H = 1600, 900
    margin = 120
    x0, x1 = margin, W - margin
    y0, y1 = margin, H - margin

    xscale = (x1 - x0) / max(1, max_len - 1)

    def y_map(v: float) -> float:
        return y0 + (1.0 - v) * (y1 - y0)

    svg = svg_header(W, H)
    svg += text(80, 70, f"Posterior trajectories — weighting comparison ({window_min}m, {dep})", size=30)

    for i, (m, pvals, exp_id) in enumerate(series):
        pts_xy = [(x0 + j * xscale, y_map(pvals[j])) for j in range(len(pvals))]
        svg += polyline(pts_xy, stroke=colors[m], width=3, opacity=0.9)
        svg += text(W - 40, 120 + 28 * i, m, fill=colors[m], size=20, anchor="end")

    svg += text(margin, H - 40, "x: sequential time buckets   y: posterior mean p_hat", size=22)
    svg += svg_footer()

    out = os.path.join(OUT, f"VIZ4_weighting_trajectories__W{window_min}m__{dep}.svg")
    with open(out, "w", encoding="utf-8") as f:
        f.write(svg)
    convert_svg(out)
    return out


def viz3_surface_heatmap(exp_id: str) -> str:
    # 2D heatmap proxy for the requested 3D surface: time vs evidence strength -> p_hat
    s = load_summary(exp_id)
    pts = s.get("posterior_points", [])
    if len(pts) < 5:
        raise RuntimeError("Not enough points")

    W, H = 1600, 900
    margin = 120
    x0, x1 = margin, W - margin
    y0, y1 = margin, H - margin

    strengths = [float(p["alpha"]) + float(p["beta"]) for p in pts]
    pvals = [float(p["p_hat"]) for p in pts]
    smin, smax = min(strengths), max(strengths)

    def x_map(i: int) -> float:
        return x0 + i / max(1, len(pts) - 1) * (x1 - x0)

    def y_map(strength: float) -> float:
        if smax <= smin:
            return y1
        # higher strength at bottom
        return y0 + (strength - smin) / (smax - smin) * (y1 - y0)

    def color(p: float) -> str:
        # simple blue->magenta ramp
        r = int(255 * p)
        b = int(255 * (1 - p))
        g = 40
        return f"rgb({r},{g},{b})"

    svg = svg_header(W, H)
    svg += text(80, 70, f"Posterior surface proxy (time × evidence strength) — {exp_id}", size=30)

    # draw thick polyline with colored segments
    for i in range(len(pts) - 1):
        xA, yA = x_map(i), y_map(strengths[i])
        xB, yB = x_map(i + 1), y_map(strengths[i + 1])
        svg += f"<line x1='{xA:.1f}' y1='{yA:.1f}' x2='{xB:.1f}' y2='{yB:.1f}' stroke='{color(pvals[i])}' stroke-width='6' opacity='0.9'/>\n"

    svg += text(margin, H - 40, "x: time bucket   y: evidence strength proxy (alpha+beta)   color: posterior mean", size=22)
    svg += svg_footer()

    out = os.path.join(OUT, f"VIZ3_surface_proxy__{exp_id}.svg")
    with open(out, "w", encoding="utf-8") as f:
        f.write(svg)
    convert_svg(out)
    return out


def write_index(entries: list[dict]):
    path = os.path.join(OUT, "FIGURE_INDEX.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("# FIGURE_INDEX (REALDATA_GRID_RUN)\n\n")
        for e in entries:
            f.write(f"- **{e['name']}** — {e['desc']}\n")
            f.write(f"  - source: `{e['source']}`\n")
            f.write(f"  - reproduce: `{e['repro']}`\n")


def main():
    ensure(OUT)
    ensure(VID)

    rep = pick_rep_exp(1, "RAW", "RAW_N")

    entries = []
    entries.append(
        {
            "name": "VIZ1_posterior_evolution",
            "desc": "Posterior mean over time with 90% band (normal approximation)",
            "source": rep,
            "repro": "python3 scripts/realdata_grid_viz_suite.py",
        }
    )
    viz1_posterior_evolution(rep)

    entries.append(
        {
            "name": "VIZ2_evidence_vs_posterior",
            "desc": "Evidence strength proxy (alpha+beta) vs posterior mean",
            "source": rep,
            "repro": "python3 scripts/realdata_grid_viz_suite.py",
        }
    )
    viz2_evidence_vs_posterior(rep)

    entries.append(
        {
            "name": "VIZ3_surface_proxy",
            "desc": "Surface proxy: time × evidence strength colored by posterior mean",
            "source": rep,
            "repro": "python3 scripts/realdata_grid_viz_suite.py",
        }
    )
    viz3_surface_heatmap(rep)

    entries.append(
        {
            "name": "VIZ4_weighting_trajectories",
            "desc": "Posterior trajectories for all weighting modes (RAW_N)",
            "source": "W1m__*__RAW_N__sequential_update",
            "repro": "python3 scripts/realdata_grid_viz_suite.py",
        }
    )
    viz4_weighting_trajectory_compare(1, "RAW_N")

    entries.append(
        {
            "name": "VIZ4b_weighting_variance",
            "desc": "Posterior variance + CI width by weighting mode",
            "source": "W1m__*__RAW_N__sequential_update",
            "repro": "python3 scripts/realdata_grid_viz_suite.py",
        }
    )
    viz4_weighting_variance_compare(1, "RAW_N")

    entries.append(
        {
            "name": "VIZ5_variance_vs_ess",
            "desc": "Scatter of posterior variance vs ESS_w comparing RAW_N vs N*",
            "source": "W1m__*__*__sequential_update",
            "repro": "python3 scripts/realdata_grid_viz_suite.py",
        }
    )
    viz5_variance_vs_ess(1)

    entries.append(
        {
            "name": "VIZ7_density_snapshots",
            "desc": "Beta density curves at early/mid/late points",
            "source": rep,
            "repro": "python3 scripts/realdata_grid_viz_suite.py",
        }
    )
    viz7_density_snapshots(rep)

    # Reliability plot is not meaningful without outcomes; intentionally omitted.

    write_index(entries)
    print("OK: wrote expanded showcase set to", OUT)


if __name__ == "__main__":
    main()
