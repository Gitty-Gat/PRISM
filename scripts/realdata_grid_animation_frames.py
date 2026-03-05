"""Generate posterior learning animation frames for one representative experiment.

Outputs PNG frames under:
- results/REALDATA_GRID_RUN/videos/posterior_learning_frames/

If ffmpeg is unavailable, you can create a GIF via ImageMagick:
- convert -delay 5 -loop 0 frame_*.png posterior_learning.gif

(We do not auto-create MP4 here.)
"""

from __future__ import annotations

import glob
import json
import os
import subprocess
from math import exp, lgamma, log

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BASE = os.path.join(REPO_ROOT, "results", "REALDATA_GRID_RUN")
VID = os.path.join(BASE, "videos")
FRAMES = os.path.join(VID, "posterior_learning_frames")


def ensure(p: str):
    os.makedirs(p, exist_ok=True)


def beta_pdf(x: float, a: float, b: float) -> float:
    if x <= 0.0 or x >= 1.0:
        return 0.0
    log_norm = lgamma(a) + lgamma(b) - lgamma(a + b)
    return exp((a - 1) * log(x) + (b - 1) * log(1 - x) - log_norm)


def svg_frame(exp_id: str, idx: int, pts: list[dict]) -> str:
    W, H = 1280, 720
    margin = 90
    x0, x1 = margin, W - margin
    y0, y1 = margin, H - margin

    a = float(pts[idx]["alpha"])
    b = float(pts[idx]["beta"])
    p_hat = float(pts[idx]["p_hat"])

    xs = [i / 400.0 for i in range(1, 400)]
    ys = [beta_pdf(x, a, b) for x in xs]
    ymax = max(ys) or 1.0

    def x_map(x: float) -> float:
        return x0 + x * (x1 - x0)

    def y_map(y: float) -> float:
        return y1 - (y / ymax) * (y1 - y0)

    pts_xy = " ".join(f"{x_map(xs[i]):.1f},{y_map(ys[i]):.1f}" for i in range(len(xs)))

    svg = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{W}' height='{H}' viewBox='0 0 {W} {H}'>",
        "<rect width='100%' height='100%' fill='black'/>",
        f"<text x='60' y='60' fill='#e0e0e0' font-family='DejaVu Sans' font-size='26'>Posterior learning — {exp_id}</text>",
        f"<text x='60' y='95' fill='#b0b0b0' font-family='DejaVu Sans' font-size='18'>frame {idx+1}/{len(pts)}  alpha={a:.1f} beta={b:.1f}  p_hat={p_hat:.5f}</text>",
        f"<polyline points='{pts_xy}' fill='none' stroke='#00e5ff' stroke-width='3' opacity='0.95' />",
        # mean marker
        f"<line x1='{x_map(p_hat):.1f}' y1='{y0:.1f}' x2='{x_map(p_hat):.1f}' y2='{y1:.1f}' stroke='#ffb300' stroke-width='2' opacity='0.9' />",
        "</svg>",
    ]
    return "\n".join(svg)


def pick_rep_exp() -> str:
    # Prefer 1m RAW RAW_N sequential
    d = os.path.join(BASE, "W1m__RAW__RAW_N__sequential_update")
    if os.path.exists(d):
        return os.path.basename(d)
    # fallback: any
    ds = glob.glob(os.path.join(BASE, "W*m__*__*__sequential_update"))
    if not ds:
        raise RuntimeError("No experiments found")
    return os.path.basename(sorted(ds)[0])


def main():
    ensure(VID)
    ensure(FRAMES)

    exp_id = pick_rep_exp()
    with open(os.path.join(BASE, exp_id, "summary.json"), "r", encoding="utf-8") as f:
        s = json.load(f)
    pts = s.get("posterior_points", [])
    if len(pts) < 5:
        print("Not enough points for animation")
        return

    # Downsample to at most 120 frames
    step = max(1, len(pts) // 120)
    frame_pts = pts[::step]

    for i in range(len(frame_pts)):
        svg = svg_frame(exp_id, i, frame_pts)
        svg_path = os.path.join(FRAMES, f"frame_{i:04d}.svg")
        png_path = os.path.join(FRAMES, f"frame_{i:04d}.png")
        with open(svg_path, "w", encoding="utf-8") as f:
            f.write(svg)
        subprocess.run(["convert", svg_path, png_path], check=False)

    # Build GIF (viewable) as fallback
    gif_path = os.path.join(VID, "posterior_learning.gif")
    subprocess.run(["convert", "-delay", "5", "-loop", "0", os.path.join(FRAMES, "frame_*.png"), gif_path], check=False)

    print("OK: wrote frames to", FRAMES)
    print("OK: wrote GIF to", gif_path)


if __name__ == "__main__":
    main()
