"""Predictive visualization suite for Stage I.

Outputs to:
- results/REALDATA_EXPANDED_VALIDATION/prism_showcase_predictive/

Figures:
- reliability diagram (per horizon, PRISM)
- brier comparison bar chart (models)
- calibration curve comparison (PRISM vs baselines)
- prediction sharpness histogram (PRISM)
- uncertainty diagnostics:
  - variance vs forecast error
  - variance vs evidence strength

Stdlib only; SVG + PNG via ImageMagick.
"""

from __future__ import annotations

import csv
import os
import subprocess
from collections import defaultdict

BASE = os.path.join("results", "REALDATA_EXPANDED_VALIDATION")
PRED = os.path.join(BASE, "predictive")
OUT = os.path.join(BASE, "prism_showcase_predictive")


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


def main():
    ensure(OUT)

    pred_rows = list(csv.DictReader(open(os.path.join(PRED, "prediction_results.csv"), "r", encoding="utf-8")))

    # reliability diagram: PRISM only, per horizon
    curves = list(csv.DictReader(open(os.path.join(PRED, "calibration_curves.csv"), "r", encoding="utf-8")))
    curves = [r for r in curves if r["model"] == "PRISM" and r["count"] not in ("0", "")]
    by_h = defaultdict(list)
    for r in curves:
        by_h[int(r["horizon_min"])].append(r)

    W,H=1600,900; margin=140
    x0,x1=margin,W-margin; y0,y1=margin,H-margin

    for h, rows in sorted(by_h.items()):
        svg=svg_header(W,H)
        svg+=text(80,70,f"Reliability diagram (PRISM) — horizon {h}m",size=30)
        # diagonal
        svg+=f"<line x1='{x0}' y1='{y1}' x2='{x1}' y2='{y0}' stroke='#555' stroke-width='2' opacity='0.7'/>\n"

        pts=[]
        for r in rows:
            mp=float(r['mean_pred']); mo=float(r['mean_outcome'])
            x=x0+mp*(x1-x0)
            y=y0+(1-mo)*(y1-y0)
            pts.append((x,y))
        pts=sorted(pts, key=lambda p: p[0])
        svg+=polyline(pts,stroke='#00e5ff',width=4,opacity=0.95)
        svg+=text(margin,H-40,"x: predicted probability   y: empirical frequency",size=22)
        svg+=svg_footer()
        out=os.path.join(OUT,f"I_VIZ1_reliability_PRISM_{h}m.svg")
        open(out,'w',encoding='utf-8').write(svg)
        convert_svg(out)

    # brier comparison bars
    metrics=list(csv.DictReader(open(os.path.join(PRED,'baseline_prediction_comparison.csv'),'r',encoding='utf-8')))
    # pick horizon 5m
    h=5
    msel=[r for r in metrics if int(r['horizon_min'])==h]
    msel=sorted(msel, key=lambda r: r['model'])
    vmax=max(float(r['brier']) for r in msel) if msel else 1.0

    svg=svg_header(W,H)
    svg+=text(80,70,f"Brier score comparison (horizon {h}m) — proxy outcome",size=30)
    gap=(x1-x0)/max(1,len(msel))
    barw=gap*0.6
    colors={'PRISM':'#00e5ff','imbalance':'#ffb300','beta_baseline':'#76ff03','logistic':'#ff1744'}
    for i,r in enumerate(msel):
        b=float(r['brier'])
        x=x0+i*gap+gap*0.2
        hpx=(b/vmax)*(y1-y0)
        svg+=f"<rect x='{x:.1f}' y='{(y1-hpx):.1f}' width='{barw:.1f}' height='{hpx:.1f}' fill='{colors.get(r['model'],'#888')}' opacity='0.85'/>\n"
        svg+=text(x+barw/2,y1+30,r['model'],fill='#e0e0e0',size=16,anchor='middle')
    svg+=text(margin,H-40,"lower is better (descriptive only)",size=22)
    svg+=svg_footer()
    out=os.path.join(OUT,f"I_VIZ2_brier_comparison_{h}m.svg")
    open(out,'w',encoding='utf-8').write(svg)
    convert_svg(out)

    # calibration comparison curves for horizon 5m
    h = 5
    csel = [r for r in list(csv.DictReader(open(os.path.join(PRED, "calibration_curves.csv"), "r", encoding="utf-8"))) if int(r['horizon_min']) == h and r['count'] not in ('0','') and r['model'] in ('PRISM','imbalance','logistic')]
    by_model = defaultdict(list)
    for r in csel:
        by_model[r['model']].append((float(r['mean_pred']), float(r['mean_outcome'])))
    for k in by_model:
        by_model[k] = sorted(by_model[k], key=lambda x: x[0])

    svg = svg_header(W,H)
    svg += text(80,70,f"Calibration curves comparison (horizon {h}m)",size=30)
    x0,x1=margin,W-margin; y0,y1=margin,H-margin
    # diagonal
    svg += f"<line x1='{x0}' y1='{y1}' x2='{x1}' y2='{y0}' stroke='#555' stroke-width='2' opacity='0.7'/>\n"
    colors={'PRISM':'#00e5ff','imbalance':'#ffb300','logistic':'#ff1744'}
    for m, pts in by_model.items():
        line=[(x0+p*(x1-x0), y0+(1-o)*(y1-y0)) for p,o in pts]
        if line:
            svg += polyline(line, stroke=colors[m], width=4, opacity=0.9)
    svg += text(W-40,120,'PRISM',fill=colors['PRISM'],size=22,anchor='end')
    svg += text(W-40,150,'imbalance',fill=colors['imbalance'],size=22,anchor='end')
    svg += text(W-40,180,'logistic',fill=colors['logistic'],size=22,anchor='end')
    svg += text(margin,H-40,"x: predicted probability   y: empirical frequency",size=22)
    svg += svg_footer()
    out = os.path.join(OUT, "I_VIZ3_calibration_comparison_5m.svg")
    open(out,'w',encoding='utf-8').write(svg)
    convert_svg(out)

    # sharpness histogram (PRISM predictions, horizon 5m)
    pvals=[float(r['prediction_probability']) for r in pred_rows if int(r['prediction_horizon_min'])==h]
    bins=[0]*10
    for p in pvals:
        idx=min(9,max(0,int(p*10)))
        bins[idx]+=1
    vmax=max(bins) if bins else 1
    svg=svg_header(W,H)
    svg+=text(80,70,f"Prediction sharpness (PRISM, horizon {h}m)",size=30)
    gap=(x1-x0)/10; barw=gap*0.75
    for i,cnt in enumerate(bins):
        x=x0+i*gap+gap*0.125
        hpx=(cnt/max(1,vmax))*(y1-y0)
        svg+=f"<rect x='{x:.1f}' y='{(y1-hpx):.1f}' width='{barw:.1f}' height='{hpx:.1f}' fill='#76ff03' opacity='0.85'/>\n"
        svg+=text(x+barw/2,y1+28,f"{i/10:.1f}",fill='#aaa',size=14,anchor='middle')
    svg+=text(margin,H-40,"x: predicted probability bins   y: count",size=22)
    svg+=svg_footer()
    out=os.path.join(OUT,"I_VIZ4_sharpness_hist_5m.svg")
    open(out,'w',encoding='utf-8').write(svg)
    convert_svg(out)

    # uncertainty diagnostics (PRISM only, horizon 5m)
    urows=[r for r in pred_rows if int(r['prediction_horizon_min'])==h]
    # variance vs abs error scatter
    svg=svg_header(W,H)
    svg+=text(80,70,f"Uncertainty diagnostic: posterior variance vs |forecast error| ({h}m)",size=30)
    xvals=[float(r['posterior_variance']) for r in urows]
    yvals=[abs(float(r['prediction_probability'])-int(r['actual_outcome'])) for r in urows]
    xmin,xmax=min(xvals or [0.0]),max(xvals or [1.0])
    ymin,ymax=min(yvals or [0.0]),max(yvals or [1.0])
    for xv,yv in zip(xvals,yvals):
        x=x0 + ((xv-xmin)/(xmax-xmin+1e-18))*(x1-x0)
        y=y1 - ((yv-ymin)/(ymax-ymin+1e-18))*(y1-y0)
        svg+=f"<circle cx='{x:.1f}' cy='{y:.1f}' r='2' fill='#b388ff' opacity='0.4'/>\n"
    svg+=text(margin,H-40,"x: posterior variance   y: |p - outcome|",size=22)
    svg+=svg_footer()
    out=os.path.join(OUT,"I_VIZ5_variance_vs_error_5m.svg")
    open(out,'w',encoding='utf-8').write(svg)
    convert_svg(out)

    # variance vs evidence strength
    svg=svg_header(W,H)
    svg+=text(80,70,f"Uncertainty diagnostic: posterior variance vs evidence strength ({h}m)",size=30)
    xvals=[float(r['evidence_strength']) for r in urows]
    yvals=[float(r['posterior_variance']) for r in urows]
    xmin,xmax=min(xvals or [0.0]),max(xvals or [1.0])
    ymin,ymax=min(yvals or [0.0]),max(yvals or [1.0])
    for xv,yv in zip(xvals,yvals):
        x=x0 + ((xv-xmin)/(xmax-xmin+1e-18))*(x1-x0)
        y=y1 - ((yv-ymin)/(ymax-ymin+1e-18))*(y1-y0)
        svg+=f"<circle cx='{x:.1f}' cy='{y:.1f}' r='2' fill='#00e5ff' opacity='0.35'/>\n"
    svg+=text(margin,H-40,"x: evidence strength   y: posterior variance",size=22)
    svg+=svg_footer()
    out=os.path.join(OUT,"I_VIZ6_variance_vs_strength_5m.svg")
    open(out,'w',encoding='utf-8').write(svg)
    convert_svg(out)

    print('OK:', OUT)


if __name__=='__main__':
    main()
