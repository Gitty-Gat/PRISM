"""Transport abstraction for Databento API calls.

Default must be MockTransport to guarantee tests do not touch network.
LiveTransport uses urllib and basic auth with DATABENTO_API_KEY.

Gate for live usage:
- Environment variable PRISM_DATABENTO_LIVE=1 must be set, otherwise LiveTransport
  construction is rejected.
"""

from __future__ import annotations

import base64
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Dict, Optional, Tuple


HIST_GATEWAY = "https://hist.databento.com"
API_VERSION = 0


class TransportError(RuntimeError):
    pass


@dataclass
class HttpResponse:
    status: int
    headers: Dict[str, str]
    body: bytes


class Transport:
    def post_form(self, url: str, data: Dict[str, str], *, basic_auth: bool) -> HttpResponse:  # pragma: no cover
        raise NotImplementedError


class MockTransport(Transport):
    """Default transport: deterministic, no network."""

    def __init__(self, fixtures: Optional[Dict[Tuple[str, Tuple[Tuple[str, str], ...]], HttpResponse]] = None):
        self.fixtures = fixtures or {}

    def post_form(self, url: str, data: Dict[str, str], *, basic_auth: bool) -> HttpResponse:
        key = (url, tuple(sorted((k, str(v)) for k, v in data.items())))
        if key not in self.fixtures:
            raise TransportError(f"No mock fixture for request: {url} {sorted(data.keys())}")
        return self.fixtures[key]


class LiveTransport(Transport):
    """Live transport using urllib.

    WARNING: Makes real network calls.
    """

    def __init__(self, api_key: Optional[str] = None, timeout_s: int = 60):
        if os.environ.get("PRISM_DATABENTO_LIVE") != "1":
            raise TransportError("LiveTransport disabled. Set PRISM_DATABENTO_LIVE=1 to enable network calls.")
        self.api_key = api_key or os.environ.get("DATABENTO_API_KEY")
        if not self.api_key:
            raise ValueError("DATABENTO_API_KEY not set")
        self.timeout_s = timeout_s

    def _auth_header(self) -> str:
        token = base64.b64encode((self.api_key + ":").encode("utf-8")).decode("ascii")
        return f"Basic {token}"

    def post_form(self, url: str, data: Dict[str, str], *, basic_auth: bool) -> HttpResponse:
        encoded = urllib.parse.urlencode(data).encode("utf-8")
        req = urllib.request.Request(url=url, data=encoded, method="POST")
        req.add_header("User-Agent", "prism-stage-b4")
        if basic_auth:
            req.add_header("Authorization", self._auth_header())
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                body = resp.read()
                headers = {k.lower(): v for k, v in resp.headers.items()}
                return HttpResponse(status=int(resp.status), headers=headers, body=body)
        except Exception as exc:
            raise TransportError(str(exc)) from exc
