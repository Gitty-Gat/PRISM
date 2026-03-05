"""Generate baseline comparison visualizations.

Outputs to:
- results/REALDATA_EXPANDED_VALIDATION/prism_showcase_comparison/

Stdlib only; SVG + PNG via ImageMagick.
"""

from __future__ import annotations

import csv
import os
import subprocess

BASE = os.path.join("results", "REALDATA_EXPANDED_VALIDATION")
OUT = os.path.join(BASE, "prism_showcase_comparison")


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


def main():
    ensure(OUT)
    inp = os.path.join(BASE, "comparison", "model_comparison.csv")
    rows = list(csv.DictReader(open(inp, "r", encoding="utf-8")))

    # Filter to a representative config for slice plot: 60m RAW RAW_N sequential
    sel = [r for r in rows if r["window_length_min"] == "60" and r["weighting_method"] == "RAW" and r["dependence_method"] == "RAW_N" and r["posterior_mode"] == "sequential_update"]
    sel = sorted(sel, key=lambda r: r["time_slice"])

    W,H=1600,900; margin=160
    x0,x1=margin,W-margin; y0,y1=margin,H-margin
    svg=svg_header(W,H)
    svg+=text(80,70,"PRISM vs imbalance estimator (by slice) — 60m RAW RAW_N",size=30)

    if sel:
        gap=(x1-x0)/len(sel)
        barw=gap*0.22
        for i,r in enumerate(sel):
            sl=r['time_slice']
            prism=float(r['prism_mean'])
            imb=float(r['imbalance_p'])
            x=x0+i*gap+gap*0.2
            # prism bar
            svg+=f"<rect x='{x:.1f}' y='{(y1-prism*(y1-y0)):.1f}' width='{barw:.1f}' height='{(prism*(y1-y0)):.1f}' fill='#00e5ff' opacity='0.85'/>\n"
            # imb bar
            svg+=f"<rect x='{(x+barw*1.3):.1f}' y='{(y1-imb*(y1-y0)):.1f}' width='{barw:.1f}' height='{(imb*(y1-y0)):.1f}' fill='#ffb300' opacity='0.85'/>\n"
            svg+=text(x+barw,y1+30,sl,fill='#e0e0e0',size=18,anchor='middle')

        svg+=text(W-40,120,"PRISM",fill="#00e5ff",size=22,anchor='end')
        svg+=text(W-40,150,"imbalance",fill="#ffb300",size=22,anchor='end')

    svg+=text(margin,H-40,"y: probability",size=22)
    svg+=svg_footer()
    out=os.path.join(OUT,"H_VIZ1_prism_vs_imbalance_by_slice.svg")
    open(out,'w',encoding='utf-8').write(svg)
    convert_svg(out)

    # Scatter: PRISM vs imbalance across all rows
    svg=svg_header(W,H)
    svg+=text(80,70,"PRISM mean vs imbalance estimator (all configs)",size=30)
    # points
    for r in rows[:: max(1,len(rows)//4000)]:
        prism=float(r['prism_mean'])
        imb=float(r['imbalance_p'])
        x=x0+imb*(x1-x0)
        y=y0+(1-prism)*(y1-y0)
        svg+=f"<circle cx='{x:.1f}' cy='{y:.1f}' r='2' fill='#76ff03' opacity='0.35'/>\n"
    svg+=text(margin,H-40,"x: imbalance_p   y: PRISM mean",size=22)
    svg+=svg_footer()
    out2=os.path.join(OUT,"H_VIZ2_scatter_prism_vs_imbalance.svg")
    open(out2,'w',encoding='utf-8').write(svg)
    convert_svg(out2)

    print('OK:', OUT)


if __name__=='__main__':
    main()
