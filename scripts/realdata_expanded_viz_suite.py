"""Visualization suite for REALDATA_EXPANDED_VALIDATION.

Outputs SVG + PNG (via ImageMagick convert) in:
- results/REALDATA_EXPANDED_VALIDATION/prism_showcase/

Stdlib only.
"""

from __future__ import annotations

import csv
import json
import os
import subprocess
from glob import glob
from math import exp, lgamma, log, sqrt

BASE = os.path.join("results", "REALDATA_EXPANDED_VALIDATION")
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


def beta_mean_var(a: float, b: float):
    s = a + b
    if s <= 0:
        return 0.5, 0.0
    m = a / s
    v = (a * b) / (s * s * (s + 1.0))
    return m, v


def normal_ci(m: float, v: float, z: float = 1.645):
    sd = sqrt(max(v, 0.0))
    lo = max(0.0, m - z * sd)
    hi = min(1.0, m + z * sd)
    return lo, hi


def beta_pdf(x: float, a: float, b: float) -> float:
    if x <= 0.0 or x >= 1.0:
        return 0.0
    log_norm = lgamma(a) + lgamma(b) - lgamma(a + b)
    return exp((a - 1) * log(x) + (b - 1) * log(1 - x) - log_norm)


def pick_rep_exp() -> str:
    # prefer open, 60m, RAW, RAW_N, sequential
    p = os.path.join(BASE, "Sopen__W60m__RAW__RAW_N__sequential_update")
    if os.path.exists(p):
        return os.path.basename(p)
    ds = glob(os.path.join(BASE, "S*__W60m__RAW__RAW_N__sequential_update"))
    if ds:
        return os.path.basename(sorted(ds)[0])
    ds = glob(os.path.join(BASE, "S*__W1m__RAW__RAW_N__sequential_update"))
    return os.path.basename(sorted(ds)[0])


def load_summary(exp_id: str) -> dict:
    return json.load(open(os.path.join(BASE, exp_id, "summary.json"), "r", encoding="utf-8"))


def viz_posterior_evolution(exp_id: str) -> str:
    s = load_summary(exp_id)
    pts = s.get("posterior_points", [])
    means, lows, highs = [], [], []
    for p in pts:
        a, b = float(p["alpha"]), float(p["beta"])
        m, v = beta_mean_var(a, b)
        lo, hi = normal_ci(m, v)
        means.append(m); lows.append(lo); highs.append(hi)

    W,H=1600,900; margin=120
    x0,x1=margin,W-margin; y0,y1=margin,H-margin
    n=len(means)
    xscale=(x1-x0)/max(1,n-1)
    def y(v): return y0+(1-v)*(y1-y0)
    mean_pts=[(x0+i*xscale,y(means[i])) for i in range(n)]
    band=[(x0+i*xscale,y(highs[i])) for i in range(n)] + [(x0+i*xscale,y(lows[i])) for i in reversed(range(n))]

    svg=svg_header(W,H)
    svg+=text(80,70,f"Posterior evolution — {exp_id}",size=30)
    svg+=polygon(band,fill="#00e5ff",opacity=0.18)
    svg+=polyline(mean_pts,stroke="#00e5ff",width=4,opacity=0.95)
    svg+=text(margin,H-40,"x: time bucket   y: posterior mean with 90% band (normal approx)",size=22)
    svg+=svg_footer()

    out=os.path.join(OUT,f"G_VIZ1_posterior_evolution__{exp_id}.svg")
    open(out,'w',encoding='utf-8').write(svg)
    convert_svg(out)
    return out


def viz_density_snapshots(exp_id: str) -> str:
    s = load_summary(exp_id)
    pts = s.get("posterior_points", [])
    if len(pts) < 3:
        return ""
    idxs=[0,len(pts)//2,len(pts)-1]
    cols=["#00e5ff","#ffb300","#ff1744"]
    xs=[i/300.0 for i in range(1,300)]

    curves=[]; ymax=1e-9
    for j,idx in enumerate(idxs):
        a,b=float(pts[idx]['alpha']),float(pts[idx]['beta'])
        ys=[beta_pdf(x,a,b) for x in xs]
        ymax=max(ymax,max(ys))
        curves.append((ys,cols[j],idx))

    W,H=1600,900; margin=120
    x0,x1=margin,W-margin; y0,y1=margin,H-margin
    def x(v): return x0+v*(x1-x0)
    def y(v): return y1-(v/ymax)*(y1-y0)

    svg=svg_header(W,H)
    svg+=text(80,70,f"Posterior density snapshots — {exp_id}",size=30)
    for ys,col,idx in curves:
        pts_xy=[(x(xs[i]),y(ys[i])) for i in range(len(xs))]
        svg+=polyline(pts_xy,stroke=col,width=4,opacity=0.95)
        svg+=text(W-40,120+30*idxs.index(idx),f"t_index={idx}",fill=col,size=22,anchor='end')
    svg+=text(margin,H-40,"x: probability   y: Beta density (scaled)",size=22)
    svg+=svg_footer()

    out=os.path.join(OUT,f"G_VIZ7_density_snapshots__{exp_id}.svg")
    open(out,'w',encoding='utf-8').write(svg)
    convert_svg(out)
    return out


def viz_temporal_robustness_mean() -> str:
    # mean posterior_mean by slice for a fixed config: W60m RAW RAW_N sequential
    slices=["open","mid_1","mid_2","late","post"]
    vals=[]
    for sl in slices:
        exp=f"S{sl}__W60m__RAW__RAW_N__sequential_update"
        if not os.path.exists(os.path.join(BASE,exp)):
            continue
        s=load_summary(exp)
        pts=s.get('posterior_points',[])
        v=float(pts[-1]['p_hat']) if pts else 0.5
        vals.append((sl,v,exp))

    W,H=1600,900; margin=140
    x0,x1=margin,W-margin; y0,y1=margin,H-margin
    svg=svg_header(W,H)
    svg+=text(80,70,"Temporal robustness (posterior mean by slice) — 60m RAW RAW_N",size=30)

    if vals:
        xs_gap=(x1-x0)/len(vals)
        barw=xs_gap*0.6
        for i,(sl,v,exp) in enumerate(vals):
            x=x0+i*xs_gap+xs_gap*0.2
            h=(v)*(y1-y0)
            svg+=f"<rect x='{x:.1f}' y='{(y1-h):.1f}' width='{barw:.1f}' height='{h:.1f}' fill='#76ff03' opacity='0.8'/>\n"
            svg+=text(x+barw/2,y1+30,sl,fill='#e0e0e0',size=18,anchor='middle')
        svg+=text(margin,H-40,"y: posterior mean at window end",size=22)

    svg+=svg_footer()
    out=os.path.join(OUT,"G_VIZ6_temporal_mean_by_slice.svg")
    open(out,'w',encoding='utf-8').write(svg)
    convert_svg(out)
    return out


def viz_heatmap_variance() -> str:
    # heatmap: window_length x weighting_method, color=posterior_variance (mean over slices, RAW_N, sequential)
    windows=[1,5,15,30,60,120,240,390]
    weights=["RAW","SIZE_WEIGHTED","CAPPED","SUBLINEAR","IMBALANCE_ADJUSTED"]

    # gather values where present
    grid={(w,wm):[] for w in windows for wm in weights}
    for sl in ["open","mid_1","mid_2","late","post"]:
        for w in windows:
            for wm in weights:
                exp=f"S{sl}__W{w}m__{wm}__RAW_N__sequential_update"
                p=os.path.join(BASE,exp,'summary.json')
                if not os.path.exists(p):
                    continue
                s=json.load(open(p,'r',encoding='utf-8'))
                pts=s.get('posterior_points',[])
                if not pts:
                    continue
                a=float(pts[-1]['alpha']); b=float(pts[-1]['beta'])
                _,var=beta_mean_var(a,b)
                grid[(w,wm)].append(var)

    vals=[(k,sum(v)/len(v)) for k,v in grid.items() if v]
    if not vals:
        return ""
    vmin=min(v for _,v in vals); vmax=max(v for _,v in vals)

    def color(v):
        # map log variance to color
        import math
        lv=math.log10(max(v,1e-20))
        lmin=math.log10(max(vmin,1e-20)); lmax=math.log10(max(vmax,1e-20))
        t=0 if lmax<=lmin else (lv-lmin)/(lmax-lmin)
        r=int(255*(1-t)); b=int(255*t); g=40
        return f"rgb({r},{g},{b})"

    W,H=1600,900; margin=200
    x0,x1=margin,W-margin; y0,y1=margin,H-margin
    cw=(x1-x0)/len(weights); ch=(y1-y0)/len(windows)

    svg=svg_header(W,H)
    svg+=text(80,70,"Stability heatmap: posterior variance (log-scaled color) — RAW_N sequential",size=30)

    for i,w in enumerate(windows):
        for j,wm in enumerate(weights):
            vlist=grid.get((w,wm),[])
            if not vlist:
                continue
            v=sum(vlist)/len(vlist)
            x=x0+j*cw; y=y0+i*ch
            svg+=f"<rect x='{x:.1f}' y='{y:.1f}' width='{cw:.1f}' height='{ch:.1f}' fill='{color(v)}' opacity='0.9' stroke='#111'/>\n"

    # axes labels
    for j,wm in enumerate(weights):
        svg+=text(x0+j*cw+cw/2,y0-20,wm,fill='#e0e0e0',size=16,anchor='middle')
    for i,w in enumerate(windows):
        svg+=text(x0-10,y0+i*ch+ch/2,f"{w}m",fill='#e0e0e0',size=16,anchor='end')

    svg+=text(margin,H-40,"rows: window length   cols: weighting method   color: posterior variance",size=22)
    svg+=svg_footer()

    out=os.path.join(OUT,"G_VIZ8_variance_heatmap.svg")
    open(out,'w',encoding='utf-8').write(svg)
    convert_svg(out)
    return out


def write_index(entries: list[dict]):
    path=os.path.join(OUT,"FIGURE_INDEX.md")
    with open(path,'w',encoding='utf-8') as f:
        f.write("# FIGURE_INDEX (REALDATA_EXPANDED_VALIDATION)\n\n")
        for e in entries:
            f.write(f"- **{e['name']}** — {e['desc']}\n")
            f.write(f"  - source: `{e['source']}`\n")
            f.write(f"  - reproduce: `{e['repro']}`\n")


def main():
    ensure(OUT); ensure(VID)
    rep=pick_rep_exp()
    entries=[]

    entries.append({"name":"G_VIZ1_posterior_evolution","desc":"Posterior mean over time with 90% band (normal approx)","source":rep,"repro":"python3 scripts/realdata_expanded_viz_suite.py"})
    viz_posterior_evolution(rep)

    entries.append({"name":"G_VIZ7_density_snapshots","desc":"Beta density snapshots (early/mid/late)","source":rep,"repro":"python3 scripts/realdata_expanded_viz_suite.py"})
    viz_density_snapshots(rep)

    entries.append({"name":"G_VIZ6_temporal_mean_by_slice","desc":"Temporal robustness: final posterior mean by slice (fixed config)","source":"S(open..post)__W60m__RAW__RAW_N__sequential_update","repro":"python3 scripts/realdata_expanded_viz_suite.py"})
    viz_temporal_robustness_mean()

    entries.append({"name":"G_VIZ8_variance_heatmap","desc":"Heatmap of posterior variance by window x weighting (RAW_N, sequential)","source":"aggregate over slices","repro":"python3 scripts/realdata_expanded_viz_suite.py"})
    viz_heatmap_variance()

    write_index(entries)
    print("OK: wrote expanded validation showcase to", OUT)


if __name__ == "__main__":
    main()
