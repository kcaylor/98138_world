"""Fetch a BrickLink price-guide snapshot (feature 011, US2; research R1, R4, R6 to R9).

The only code in this package that uses the network. For each lot it makes two signed GET
requests (guide types ``sold`` then ``stock``), one at a time and at least ``interval`` seconds
apart, retries 429, 5xx and network errors with backoff, and stops on rejected credentials
(exit 7), the daily limit or exhausted retries (exit 5) with the finished lots kept in a progress
file. Credentials go only into the ``Authorization`` header built for each request; nothing that
is printed, raised or written contains them (error text from BrickLink is redacted too).
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlencode

from .api_config import ApiConfig, load_api_config
from .credentials import Credentials
from .lots import LotRef
from .oauth1 import authorization_header, percent_encode
from .snapshot import (ERROR_NOT_FOUND, FIGURE_KEYS, PRICE_KEYS, QUERY, PriceSnapshot, SnapshotError,
                       SnapshotLot, build_snapshot, parse_figures, parse_snapshot_lot, snapshot_to_json)

USER_AGENT = "lego-image-processor (parts prices fetch)"
TIMEOUT_S = 30
GUIDE_TYPES = ("sold", "stock")
PROGRESS_FORMAT = "price-progress-1"
RETRY_AFTER_CAP_S = 60
_FOUR_PLACES = Decimal("0.0001")

# --- error classification (research R7; strings to recheck against the live documentation) ----
RETRY_STATUSES = frozenset({429})            # plus every 5xx
AUTH_STATUSES = frozenset({401, 403})
NOT_FOUND_STATUS = 404
NOT_FOUND_CODES = ("RESOURCE_NOT_FOUND",)
DAILY_LIMIT_MARKERS = ("daily", "per day", "quota", "24 hours")
AUTH_HINTS = (
    ("TOKEN_IP_MISMATCHED",
     "The token is bound to another IP address: check the token's IP address setting on "
     "BrickLink's API registration page (it must allow this machine's public IP address)."),
    ("CONSUMER_KEY",
     "Check BRICKLINK_CONSUMER_KEY and BRICKLINK_CONSUMER_SECRET against BrickLink's API "
     "registration page."),
    ("TOKEN",
     "Check BRICKLINK_TOKEN_VALUE and BRICKLINK_TOKEN_SECRET against the access token on BrickLink's "
     "API registration page."),
)
AUTH_DEFAULT_HINT = ("Check that the four BRICKLINK_* variables hold the values from BrickLink's API "
                     "registration page, that the token allows this machine's IP address, and that "
                     "this machine's clock is correct (requests are signed with the current time).")
MAX_DETAIL_CHARS = 300

Opener = Callable[..., Any]


class PriceFetchError(Exception):
    """A fetch stopped (exit 5). ``done``/``total`` lots and the progress file are attached."""

    exit_code = 5

    def __init__(self, message: str):
        super().__init__(message)
        self.done = 0
        self.total = 0
        self.progress_path: Optional[Path] = None
        self.partial_path: Optional[Path] = None


class AuthError(PriceFetchError):
    """BrickLink rejected the credentials (401/403, for example a token bound to another IP)."""

    exit_code = 7


class DailyLimitError(PriceFetchError):
    """BrickLink's daily request limit was reached; resume tomorrow."""


class FetchInterrupted(PriceFetchError):
    """Ctrl-C; progress kept."""

    exit_code = 130


class ProgressMismatchError(PriceFetchError):
    """``resume`` without a usable progress file for these parameters (exit 1, no request made)."""

    exit_code = 1


@dataclass(frozen=True)
class FetchResult:
    snapshot: PriceSnapshot
    fetched: int
    reused: int
    path: Path
    progress_path: Path


# --- helpers -----------------------------------------------------------------------------------

def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def default_opener(request: urllib.request.Request, timeout: float = TIMEOUT_S):
    return urllib.request.urlopen(request, timeout=timeout)  # noqa: S310 (cited https base URL)


def default_nonce() -> str:
    return secrets.token_hex(16)


def default_sleep(seconds: float) -> None:
    time.sleep(seconds)


def default_clock() -> float:
    return time.monotonic()


def _stamp(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def progress_path_for(output: Path) -> Path:
    """``<output stem>.progress.json`` next to the output (R9)."""
    output = Path(output)
    return output.with_name(f"{output.stem}.progress.json")


def make_lot_set(kind: str, lots: Sequence[LotRef]) -> Dict[str, Any]:
    """The snapshot's ``lot_set`` block; for ``recipes`` with each bundled recipe's SHA-256."""
    recipes: List[Dict[str, str]] = []
    if kind == "recipes":
        from ..maps.recipe import bundled_recipes
        recipes = [{"id": rid, "sha256": hashlib.sha256(Path(p).read_bytes()).hexdigest()}
                   for rid, p in sorted(bundled_recipes().items())]
    return {"kind": kind, "recipes": recipes, "count": len(lots)}


def query_for(lot: LotRef, guide: str) -> List[Tuple[str, str]]:
    """Request parameters, in URL order (R4): worldwide, VAT excluded, new parts, USD."""
    return [("color_id", str(lot.bricklink_color_id)), ("guide_type", guide),
            ("new_or_used", QUERY["new_or_used"]), ("currency_code", QUERY["currency_code"]),
            ("vat", QUERY["vat"])]


def fingerprint(api: ApiConfig, lots: Sequence[LotRef]) -> str:
    blob = {"api": api.fingerprint_block(),
            "query": {k: v for k, v in QUERY.items()},
            "lots": [l.spec for l in lots]}
    canon = json.dumps(blob, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def _write_atomic(path: Path, text: str, suffix: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.stem}.", suffix=suffix)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


class _Redactor:
    """Removes credential values (and their percent-encoded forms) from text BrickLink returns."""

    def __init__(self, credentials: Credentials):
        values = [credentials.consumer_key, credentials.consumer_secret, credentials.token_value,
                  credentials.token_secret]
        forms = set()
        for v in values:
            forms |= {v, percent_encode(v)}
        self._forms = sorted((f for f in forms if f), key=len, reverse=True)

    def __call__(self, text: str) -> str:
        for f in self._forms:
            text = text.replace(f, "<redacted>")
        return text


# --- one request -------------------------------------------------------------------------------

@dataclass
class _Reply:
    status: int
    headers: Any
    body: bytes


@dataclass
class _Outcome:
    kind: str                      # ok | not_found | retry | auth | daily | error
    data: Any = None
    detail: str = ""
    retry_after: Optional[float] = None


def _meta_detail(meta: Dict[str, Any]) -> str:
    description = str(meta.get("description") or "").strip()
    return description or str(meta.get("message") or "").strip()


def _retry_after(headers) -> Optional[float]:
    raw = headers.get("Retry-After") if headers is not None else None
    if raw is None:
        return None
    try:
        return max(0.0, min(float(str(raw).strip()), RETRY_AFTER_CAP_S))
    except ValueError:
        return None          # an HTTP date: use the backoff schedule instead


def classify(status: int, body: bytes, headers=None) -> _Outcome:
    """HTTP status first, then BrickLink's ``meta.code`` (errors may come under HTTP 200; R7)."""
    payload = None
    try:
        payload = json.loads(body.decode("utf-8"), parse_float=Decimal) if body else None
    except (UnicodeDecodeError, json.JSONDecodeError):
        payload = None
    meta = payload.get("meta") if isinstance(payload, dict) and isinstance(payload.get("meta"), dict) else {}
    code = status
    if status == 200 and meta.get("code") is not None:
        try:
            code = int(meta["code"])
        except (TypeError, ValueError):
            code = 200
    detail = _meta_detail(meta) or (f"HTTP {code}" if code != 200 else "")
    text = f"{meta.get('message', '')} {meta.get('description', '')}".lower()
    if code != 200 and any(m in text for m in DAILY_LIMIT_MARKERS):
        return _Outcome("daily", detail=detail)
    if code in AUTH_STATUSES:
        return _Outcome("auth", detail=detail)
    if code == NOT_FOUND_STATUS or str(meta.get("message", "")).upper() in NOT_FOUND_CODES:
        return _Outcome("not_found", detail=detail)
    if code in RETRY_STATUSES or 500 <= code <= 599:
        return _Outcome("retry", detail=f"HTTP {code}" + (f" ({detail})" if detail != f"HTTP {code}" else ""),
                        retry_after=_retry_after(headers))
    if code != 200:
        return _Outcome("error", detail=f"HTTP {code}" + (f" ({detail})" if detail != f"HTTP {code}" else ""))
    if not isinstance(payload, dict):
        return _Outcome("retry", detail="a response that is not JSON (is bricklink.com in maintenance?)")
    data = payload.get("data")
    if not isinstance(data, dict):
        return _Outcome("error", detail="a response without a data object")
    return _Outcome("ok", data=data)


def _price(v: Any, where: str) -> str:
    if isinstance(v, bool):
        raise SnapshotError(f"{where}: not a price")
    try:
        d = v if isinstance(v, Decimal) else Decimal(str(v)) if isinstance(v, (str, int)) else None
    except InvalidOperation:
        d = None
    if d is None or not d.is_finite():
        raise SnapshotError(f"{where}: not a price ({v!r})")
    if d.as_tuple().exponent < -4:
        d = d.quantize(_FOUR_PLACES, rounding=ROUND_HALF_UP)
    return format(d, "f")


def parse_guide(data: Dict[str, Any], guide: str):
    """The figures of one price-guide response, or None when it has no data (``unit_quantity == 0``)."""
    for k in FIGURE_KEYS:
        if k not in data:
            raise SnapshotError(f"data.{k}: missing")
    if data.get("currency_code", "USD") != QUERY["currency_code"]:
        raise SnapshotError(f"data.currency_code: expected {QUERY['currency_code']}, got {data['currency_code']!r}")
    if data.get("new_or_used", "N") != QUERY["new_or_used"]:
        raise SnapshotError(f"data.new_or_used: expected N, got {data['new_or_used']!r}")
    units = data["unit_quantity"]
    if units == 0:
        return None
    figures = {k: _price(data[k], f"data.{k}") for k in PRICE_KEYS}
    figures["unit_quantity"] = units
    figures["total_quantity"] = data["total_quantity"]
    return parse_figures(figures, f"data ({guide})")


class _Client:
    def __init__(self, api: ApiConfig, credentials: Credentials, *, opener: Opener, sleep, clock, now,
                 nonce, interval: float, max_attempts: int):
        self.api, self.credentials = api, credentials
        self.opener, self.sleep, self.clock, self.now, self.nonce = opener, sleep, clock, now, nonce
        self.interval, self.max_attempts = interval, max_attempts
        self.redact = _Redactor(credentials)
        self._last_start: Optional[float] = None

    def _pace(self) -> None:
        if self._last_start is not None:
            wait = self.interval - (self.clock() - self._last_start)
            if wait > 0:
                self.sleep(wait)
        self._last_start = self.clock()

    def _send(self, url: str, query: List[Tuple[str, str]]) -> _Reply:
        self._pace()
        header = authorization_header("GET", url, query, self.credentials, nonce=self.nonce(),
                                      timestamp=int(self.now().timestamp()), realm=self.api.realm)
        request = urllib.request.Request(f"{url}?{urlencode(query)}", method="GET",
                                         headers={"Authorization": header, "User-Agent": USER_AGENT,
                                                  "Accept": "application/json"})
        del header
        try:
            response = self.opener(request, timeout=TIMEOUT_S)
        except urllib.error.HTTPError as exc:
            try:
                body = exc.read() or b""
            except Exception:  # noqa: BLE001 - a broken error body is just empty
                body = b""
            return _Reply(exc.code, exc.headers, body)
        try:
            status = getattr(response, "status", None) or response.getcode()
            return _Reply(int(status), getattr(response, "headers", None), response.read() or b"")
        finally:
            close = getattr(response, "close", None)
            if close is not None:
                close()

    def get(self, lot: LotRef, guide: str) -> _Outcome:
        url = self.api.price_guide_url(lot.bricklink_item_type, lot.bricklink_item_no)
        query = query_for(lot, guide)
        last = ""
        for attempt in range(1, self.max_attempts + 1):
            try:
                reply = self._send(url, query)
                outcome = classify(reply.status, reply.body, reply.headers)
            except (urllib.error.URLError, OSError) as exc:
                reason = getattr(exc, "reason", None) or exc.__class__.__name__
                outcome = _Outcome("retry", detail=f"network error ({self.redact(str(reason))})")
            outcome.detail = self.redact(outcome.detail)[:MAX_DETAIL_CHARS]
            if outcome.kind != "retry":
                return outcome
            last = outcome.detail
            if attempt < self.max_attempts:
                delay = outcome.retry_after if outcome.retry_after is not None else min(2 ** attempt, RETRY_AFTER_CAP_S)
                self.sleep(delay)
        raise PriceFetchError(f"BrickLink API {last} for {lot.label} ({guide}) after "
                              f"{self.max_attempts} attempt{'s' if self.max_attempts != 1 else ''}")


def _auth_message(detail: str) -> str:
    upper = detail.upper()
    hint = next((h for marker, h in AUTH_HINTS if marker in upper), AUTH_DEFAULT_HINT)
    return f"BrickLink rejected the credentials ({detail or 'no details given'}). {hint}"


def _fetch_lot(client: _Client, lot: LotRef) -> SnapshotLot:
    figures: Dict[str, Any] = {}
    for guide in GUIDE_TYPES:
        outcome = client.get(lot, guide)
        if outcome.kind == "auth":
            raise AuthError(_auth_message(outcome.detail))
        if outcome.kind == "daily":
            raise DailyLimitError(f"BrickLink's daily request limit was reached ({outcome.detail}); "
                                  "try again tomorrow")
        if outcome.kind == "not_found":
            return SnapshotLot(lot=lot, sold=None, stock=None, retrieved_at=_stamp(client.now()),
                               error=ERROR_NOT_FOUND)
        if outcome.kind == "error":
            raise PriceFetchError(f"BrickLink API returned {outcome.detail} for {lot.label} ({guide}); "
                                  "check the API details in bricklink_api.json")
        try:
            figures[guide] = parse_guide(outcome.data, guide)
        except SnapshotError as exc:
            raise PriceFetchError(f"unexpected BrickLink response for {lot.label} ({guide}): "
                                  f"{client.redact(str(exc))}") from None
    return SnapshotLot(lot=lot, sold=figures["sold"], stock=figures["stock"],
                       retrieved_at=_stamp(client.now()))


# --- progress ----------------------------------------------------------------------------------

def _describe_lot_set(ls: Dict[str, Any]) -> str:
    return f"{ls.get('kind')}, {ls.get('count')} lots"


def _load_progress(path: Path, fp: str, lot_set: Dict[str, Any], lots: Sequence[LotRef],
                   now: str) -> Tuple[str, List[SnapshotLot]]:
    if not path.is_file():
        raise ProgressMismatchError(f"--resume: no progress file {path}; run without --resume to start")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("format") != PROGRESS_FORMAT:
            raise ValueError(f"format is not {PROGRESS_FORMAT!r}")
        saved_fp, started, saved_set, raw = (data["fingerprint"], data["started_at"], data["lot_set"],
                                             data["lots"])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ProgressMismatchError(f"--resume: progress file {path} cannot be used ({exc}); run "
                                    "without --resume to start over") from None
    if saved_fp != fp:
        if saved_set != lot_set:
            what = (f"the lot set differs (progress: {_describe_lot_set(saved_set)}; now: "
                    f"{_describe_lot_set(lot_set)})")
        else:
            what = "the BrickLink API settings or query parameters differ (bricklink_api.json changed)"
        raise ProgressMismatchError(f"--resume: progress file {path} was made with other parameters: "
                                    f"{what}. Repeat the options of the stopped run, or run without "
                                    "--resume to start over")
    wanted = {l.key for l in lots}
    out = []
    try:
        for i, r in enumerate(raw):
            lot = parse_snapshot_lot(r, f"lots[{i}]", started, now)
            if lot.lot.key not in wanted:
                raise SnapshotError(f"lots[{i}]: lot {lot.lot.spec} is not in this lot set")
            out.append(lot)
    except (SnapshotError, TypeError) as exc:
        raise ProgressMismatchError(f"--resume: progress file {path} cannot be used ({exc}); run "
                                    "without --resume to start over") from None
    return started, out


def _save_progress(path: Path, fp: str, started: str, lot_set: Dict[str, Any],
                   lots: List[SnapshotLot]) -> None:
    data = {"format": PROGRESS_FORMAT, "fingerprint": fp, "started_at": started,
            "lot_set": lot_set, "lots": [l.to_dict() for l in sorted(lots, key=lambda l: l.lot.sort_key)]}
    _write_atomic(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n", ".progress.json")


# --- the loop ----------------------------------------------------------------------------------

def fetch_snapshot(lots: Sequence[LotRef], credentials: Credentials, *, output: Path,
                   lot_set: Dict[str, Any], resume: bool = False, write_partial: bool = False,
                   interval: float = 1.0, max_attempts: int = 5, api: Optional[ApiConfig] = None,
                   opener: Optional[Opener] = None, sleep=None, clock=None, now=None, nonce=None,
                   echo: Optional[Callable[[str], None]] = None) -> FetchResult:
    """Fetch the price guide of ``lots`` and write the snapshot ``output`` (contracts/library-api.md)."""
    from .. import __version__
    from .text import progress_line

    if not isinstance(credentials, Credentials):
        raise TypeError("credentials must be a Credentials object")
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")
    api = api or load_api_config()
    output = Path(output)
    sleep = sleep or default_sleep
    clock = clock or default_clock
    now = now or utc_now
    nonce = nonce or default_nonce
    echo = echo or (lambda line: None)
    lots = tuple(sorted({l.key: l for l in lots}.values(), key=lambda l: l.sort_key))
    if lot_set.get("count") != len(lots):
        raise ValueError("lot_set.count must equal the number of lots")
    progress = progress_path_for(output)
    fp = fingerprint(api, lots)

    done: List[SnapshotLot] = []
    if resume:
        started, done = _load_progress(progress, fp, lot_set, lots, _stamp(now()))
        echo(f"Resuming: {len(done)} of {len(lots)} lots from {progress}")
    else:
        if progress.exists():
            echo(f"Replacing an earlier progress file {progress} (use --resume to continue it)")
        started = _stamp(now())
    reused = len(done)
    have = {l.lot.key for l in done}
    client = _Client(api, credentials, opener=opener or default_opener, sleep=sleep, clock=clock,
                     now=now, nonce=nonce, interval=interval, max_attempts=max_attempts)

    def stop(exc: PriceFetchError) -> PriceFetchError:
        exc.done, exc.total, exc.progress_path = len(done), len(lots), progress
        if write_partial and not isinstance(exc, (AuthError, ProgressMismatchError)):
            snap = build_snapshot(api_block=api.snapshot_block(), tool_version=__version__,
                                  started_at=started, finished_at=_stamp(now()), lot_set=lot_set,
                                  lots=done)
            _write_atomic(output, snapshot_to_json(snap), ".tmp")
            exc.partial_path = output
        return exc

    for index, lot in enumerate(lots, start=1):
        if lot.key in have:
            continue
        try:
            entry = _fetch_lot(client, lot)
        except PriceFetchError as exc:
            raise stop(exc) from None
        except KeyboardInterrupt:
            raise stop(FetchInterrupted("interrupted")) from None
        done.append(entry)
        _save_progress(progress, fp, started, lot_set, done)
        echo(progress_line(index, len(lots), entry))

    snap = build_snapshot(api_block=api.snapshot_block(), tool_version=__version__, started_at=started,
                          finished_at=_stamp(now()), lot_set=lot_set, lots=done)
    _write_atomic(output, snapshot_to_json(snap), ".tmp")
    if progress.exists():
        progress.unlink()
    return FetchResult(snapshot=snap, fetched=len(done) - reused, reused=reused, path=output,
                       progress_path=progress)


__all__ = ["fetch_snapshot", "FetchResult", "PriceFetchError", "AuthError", "DailyLimitError",
           "FetchInterrupted", "ProgressMismatchError", "make_lot_set", "progress_path_for",
           "classify", "parse_guide", "default_opener", "utc_now", "USER_AGENT", "TIMEOUT_S"]
