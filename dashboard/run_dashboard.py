"""PRISM interactive dashboard (no external dependencies).

Runs a lightweight local HTTP server that serves an HTML/JS dashboard.

Usage:
  python3 dashboard/run_dashboard.py

Then open:
  http://127.0.0.1:8050/

Constraints:
- Reads artifacts only (results/REALDATA_GRID_RUN)
- No Databento calls
- No writes to results
"""

from __future__ import annotations

import argparse
import http.server
import json
import os
import socketserver
import sys
from urllib.parse import urlparse, parse_qs

# Ensure repo root on sys.path for both module and script invocation.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

try:
    # When invoked as a module: python3 -m dashboard.run_dashboard
    from .data_loader import load_dashboard_state
except Exception:
    # When invoked as a script: python3 dashboard/run_dashboard.py
    from dashboard.data_loader import load_dashboard_state


class Handler(http.server.SimpleHTTPRequestHandler):
    # dashboard root is /repo/prism/PRISM/dashboard; we want to serve from repo root

    def __init__(self, *args, state=None, repo_root=None, **kwargs):
        self.state = state
        self.repo_root = repo_root
        super().__init__(*args, directory=repo_root, **kwargs)

    def _send_json(self, payload, status=200):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/state":
            return self._send_json(self.state["public_state"])
        if parsed.path == "/api/experiment":
            q = parse_qs(parsed.query)
            exp_id = (q.get("id") or [""])[0]
            campaign = (q.get("campaign") or [self.state["public_state"]["default_campaign"]])[0]
            exp = (self.state["experiments"].get(campaign) or {}).get(exp_id)
            if not exp:
                return self._send_json({"error": "unknown_experiment", "id": exp_id}, status=404)
            return self._send_json(exp)

        # Serve dashboard index at /
        if parsed.path == "/":
            self.path = "/dashboard/static/index.html"
        return super().do_GET()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8050)
    args = ap.parse_args()

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    state = load_dashboard_state(repo_root)

    handler = lambda *a, **kw: Handler(*a, state=state, repo_root=repo_root, **kw)

    with socketserver.TCPServer((args.host, args.port), handler) as httpd:
        print(f"PRISM dashboard running on http://{args.host}:{args.port}/")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
