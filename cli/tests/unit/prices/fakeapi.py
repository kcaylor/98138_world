"""A fake BrickLink price-guide API for the fetch tests (011 T030, T034, T036). No network.

``FakeBrickLink`` is an ``opener(request, timeout)``: it records each request (URL, query,
headers, timeout, the fake clock time), answers from a script of outcomes per (item, color,
guide), from the fixture files, or with deterministic synthetic prices. ``FakeTime`` supplies
``sleep``, a monotonic ``clock`` and a wall-clock ``now`` that move together but differ in value.
Values are synthetic; they are not BrickLink data.
"""

from __future__ import annotations

import io
import json
import urllib.error
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from email.message import Message
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlsplit

API_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "prices" / "api"
START = datetime(2026, 12, 1, 18, 2, 10, tzinfo=timezone.utc)

LEAK_ENV = {"BRICKLINK_CONSUMER_KEY": "CK-leakcheck-7f3a0c11",
            "BRICKLINK_CONSUMER_SECRET": "CS-leakcheck-91be/+=x",
            "BRICKLINK_TOKEN_VALUE": "TV-leakcheck-2c44 a&b",
            "BRICKLINK_TOKEN_SECRET": "TS-leakcheck-d0e8%7e"}


def fixture(name: str) -> str:
    return (API_DIR / name).read_text(encoding="utf-8")


class FakeTime:
    def __init__(self, start: datetime = START, monotonic: float = 5000.0):
        self.start, self.mono0, self.t = start, monotonic, 0.0
        self.sleeps = []

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.t += max(0.0, seconds)

    def clock(self) -> float:
        return self.mono0 + self.t

    def now(self) -> datetime:
        return self.start + timedelta(seconds=self.t)


class Nonces:
    def __init__(self):
        self.n = 0

    def __call__(self) -> str:
        self.n += 1
        return f"nonce{self.n:04d}"


class FakeResponse:
    def __init__(self, status: int, body: bytes, headers=None):
        self.status = status
        self.headers = _headers(headers)
        self._body = body
        self.closed = False

    def read(self) -> bytes:
        return self._body

    def close(self) -> None:
        self.closed = True


def _headers(headers) -> Message:
    m = Message()
    for k, v in (headers or {}).items():
        m[k] = str(v)
    return m


def ok(**data):
    return {"meta": {"description": "OK", "message": "OK", "code": 200}, "data": data}


def synthetic(item_no: str, color_id: int, guide: str) -> dict:
    """Deterministic, valid figures for any lot."""
    k = (int(color_id) * 7 + len(item_no) * 3) % 60
    avg = Decimal("0.0400") + Decimal(k) / 10000 + (Decimal("0.0050") if guide == "stock" else 0)
    return ok(item={"no": item_no, "type": "PART"}, new_or_used="N", currency_code="USD",
              min_price="0.0100", max_price="0.9000" if guide == "sold" else "1.8000",
              avg_price=str(avg + Decimal("0.0100")), qty_avg_price=str(avg),
              unit_quantity=100 + int(color_id), total_quantity=10000 + int(color_id), price_detail=[])


class Reply:
    """One scripted outcome: an HTTP status, a body (dict, text or fixture name) and headers."""

    def __init__(self, status=200, body=None, headers=None, file=None):
        self.status, self.body, self.headers, self.file = status, body, headers or {}, file


class FakeBrickLink:
    """``opener(request, timeout)`` with a per-lot script.

    ``script[(item_no, color_id, guide)]`` is a list of outcomes used in order (then the default):
    a ``Reply``, an exception instance (raised), or a fixture file name (HTTP 200).
    ``fail_after=n`` raises ``fail_with`` on every request after the first ``n``.
    """

    def __init__(self, script=None, time: FakeTime = None, latency: float = 0.0, fail_after=None,
                 fail_with=None, default=synthetic):
        self.script = {k: list(v) for k, v in (script or {}).items()}
        self.time, self.latency = time, latency
        self.fail_after, self.fail_with = fail_after, fail_with
        self.default = default
        self.requests = []

    # What the tests inspect -------------------------------------------------------------------
    @property
    def signatures(self):
        return [r["oauth"].get("oauth_signature") for r in self.requests]

    @property
    def authorization_headers(self):
        return [r["headers"].get("Authorization") for r in self.requests]

    def __call__(self, request, timeout=None):
        parts = urlsplit(request.full_url)
        query = parse_qsl(parts.query, keep_blank_values=True)
        auth = request.get_header("Authorization") or ""
        oauth = {}
        if auth.startswith("OAuth "):
            for field in auth[len("OAuth "):].split(", "):
                k, v = field.split("=", 1)
                oauth[k] = unquote(v.strip('"'))
        record = {"url": request.full_url, "path": parts.path, "base": f"{parts.scheme}://{parts.netloc}{parts.path}",
                  "query": query, "method": request.get_method(), "timeout": timeout,
                  "headers": dict(request.header_items()), "oauth": oauth,
                  "clock": None if self.time is None else self.time.clock(),
                  "now": None if self.time is None else self.time.now()}
        self.requests.append(record)
        if self.time is not None and self.latency:
            self.time.t += self.latency
        if self.fail_after is not None and len(self.requests) > self.fail_after:
            raise self.fail_with
        segs = parts.path.split("/")
        item_no = segs[-2]
        q = dict(query)
        key = (item_no, int(q["color_id"]), q["guide_type"])
        queue = self.script.get(key)
        outcome = queue.pop(0) if queue else None
        if outcome is None:
            outcome = Reply(200, self.default(*key))
        if isinstance(outcome, BaseException):
            raise outcome
        if isinstance(outcome, str):
            outcome = Reply(200, file=outcome)
        body = outcome.body
        if outcome.file is not None:
            body = fixture(outcome.file)
        if isinstance(body, dict):
            body = json.dumps(body)
        body = (body or "").replace("{CONSUMER_KEY}", oauth.get("oauth_consumer_key", ""))
        raw = body.encode("utf-8")
        if outcome.status >= 400:
            raise urllib.error.HTTPError(request.full_url, outcome.status, "error",
                                         _headers(outcome.headers), io.BytesIO(raw))
        return FakeResponse(outcome.status, raw, outcome.headers)


def leaks(text: str, opener: FakeBrickLink, env=LEAK_ENV):
    """Every secret-looking string from ``env`` and the opener's requests found in ``text``."""
    from lego_image_processor.prices.oauth1 import percent_encode

    needles = set()
    for v in env.values():
        needles |= {v, percent_encode(v)}
    for r in opener.requests:
        if r["oauth"].get("oauth_signature"):
            sig = r["oauth"]["oauth_signature"]
            needles |= {sig, percent_encode(sig)}
        if r["headers"].get("Authorization"):
            needles.add(r["headers"]["Authorization"])
    needles.add("oauth_signature")
    needles.add("Authorization: OAuth")
    return sorted(n for n in needles if n and n in text)
