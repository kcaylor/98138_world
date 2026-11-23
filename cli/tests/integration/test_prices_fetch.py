"""`parts prices fetch` end to end with a mocked BrickLink API (011 T036; US2-1 to US2-5, FR-006,
FR-023, SC-004, SC-005). No network: the opener, sleep and clocks in prices.fetch are replaced."""

import json
import logging
import urllib.error

import pytest
from click.testing import CliRunner

from lego_image_processor.cli.main import cli
from lego_image_processor.kit import load_official_design
from lego_image_processor.kit.source import DISCLAIMER
from lego_image_processor.prices import fetch as fetch_mod
from lego_image_processor.prices import load_snapshot, recipe_lots

from ..unit.prices.fakeapi import LEAK_ENV, FakeBrickLink, FakeTime, Nonces, Reply, leaks


class Api:
    def __init__(self, monkeypatch):
        self.time = FakeTime()
        self.opener = FakeBrickLink(time=self.time, latency=0.2)
        self.openers = [self.opener]
        monkeypatch.setattr(fetch_mod, "default_opener", lambda req, timeout=None: self.opener(req, timeout))
        monkeypatch.setattr(fetch_mod, "default_sleep", self.time.sleep)
        monkeypatch.setattr(fetch_mod, "default_clock", self.time.clock)
        monkeypatch.setattr(fetch_mod, "utc_now", self.time.now)
        monkeypatch.setattr(fetch_mod, "default_nonce", Nonces())

    def use(self, opener):
        opener.time = self.time
        opener.latency = 0.2
        self.opener = opener
        self.openers.append(opener)
        return opener


@pytest.fixture
def api(monkeypatch):
    return Api(monkeypatch)


@pytest.fixture
def runner():
    return CliRunner()


def _fetch(runner, *args):
    return runner.invoke(cli, ["parts", "prices", "fetch", *map(str, args)], env=LEAK_ENV)


def test_default_run_writes_a_snapshot_parts_estimate_uses(runner, api, tmp_path):
    out = tmp_path / "bricklink_price_guide.json"
    r = _fetch(runner, "-o", out)
    assert r.exit_code == 0, r.output
    assert len(api.opener.requests) == 38                                    # 19 lots x 2
    snap = load_snapshot(out)
    assert snap.complete and len(snap.lots) == 19 and snap.lot_set["kind"] == "recipes"
    assert {l.lot.key for l in snap.lots} == {l.key for l in recipe_lots()}
    assert "Wrote price snapshot" in r.output and r.output.rstrip().endswith(DISCLAIMER)
    # SC-004: at most one request per second of (fake) time.
    starts = [q["clock"] for q in api.opener.requests]
    assert all(b - a >= 1.0 - 1e-9 for a, b in zip(starts, starts[1:]))
    assert api.time.t < 5 * 60
    # US2-4: parts estimate prices the official layout from the fetched snapshot.
    layout = tmp_path / "official.json"
    layout.write_text(load_official_design().to_layout().to_json(), encoding="utf-8")
    e = runner.invoke(cli, ["parts", "estimate", str(layout), "--prices", str(out), "--format", "json",
                            "--as-of", "2026-12-02"])
    assert e.exit_code == 0, e.output
    d = json.loads(e.output)
    assert d["estimates"]["full"]["complete"] is True
    assert d["estimates"]["full"]["pieces"] == 10240


def test_interrupted_then_resumed(runner, api, tmp_path):
    out = tmp_path / "snap.json"
    api.use(FakeBrickLink(fail_after=14, fail_with=urllib.error.URLError("connection refused")))
    r = _fetch(runner, "-o", out, "--max-attempts", "2")
    assert r.exit_code == 5, r.output
    assert "7 of 19 lots saved in" in r.output and "--resume" in r.output
    assert not out.exists()
    second = api.use(FakeBrickLink())
    r = _fetch(runner, "-o", out, "--max-attempts", "2", "--resume")
    assert r.exit_code == 0, r.output
    assert len(second.requests) == 24                                        # 12 lots x 2
    snap = load_snapshot(out)
    assert snap.complete and len(snap.lots) == 19
    assert not (tmp_path / "snap.progress.json").exists()


SCENARIOS = {
    "success": lambda: FakeBrickLink(),
    "429": lambda: FakeBrickLink({("98138", 63, "sold"): [Reply(429, file="error_429.json")] * 2}),
    "5xx exhaustion": lambda: FakeBrickLink({("98138", 63, "sold"): [Reply(502, "bad gateway")] * 5}),
    "401": lambda: FakeBrickLink({("4073", 1, "sold"): [Reply(401, file="error_401_signature.json")]}),
    "ip mismatch": lambda: FakeBrickLink({("98138", 63, "stock"): [Reply(401, file="error_401_token_ip.json")]}),
    "ip mismatch http 200": lambda: FakeBrickLink({("98138", 63, "stock"): [Reply(200, file="error_401_token_ip.json")]}),
    "daily limit": lambda: FakeBrickLink({("98138", 63, "sold"): [Reply(429, file="error_daily_limit.json")]}),
    "network failure": lambda: FakeBrickLink(fail_after=4, fail_with=urllib.error.URLError(
        "[Errno 61] Connection refused")),
    "KeyboardInterrupt": lambda: FakeBrickLink(fail_after=4, fail_with=KeyboardInterrupt()),
}


@pytest.mark.parametrize("name", list(SCENARIOS))
def test_no_credential_leaks(runner, api, tmp_path, caplog, name):
    caplog.set_level(logging.DEBUG)
    out = tmp_path / "snap.json"
    lots = ["--lot", "98138:140", "--lot", "6141:1", "--lot", "98138:321"]
    api.use(SCENARIOS[name]())
    first = _fetch(runner, "-o", out, *lots, "--write-partial")
    # Resume (or rerun) after the stop, as the owner would.
    api.use(FakeBrickLink())
    resumed = _fetch(runner, "-o", out, *lots, "--resume" if first.exit_code in (5, 7, 130) else "-q")
    text = first.output + resumed.output + caplog.text + repr(first.exception) + repr(resumed.exception)
    for p in tmp_path.rglob("*"):
        if p.is_file():
            text += p.read_text(encoding="utf-8")
    received = [o for o in api.openers if o.requests]
    assert received and sum(len(o.requests) for o in received) >= 1
    for opener in api.openers:
        assert leaks(text, opener) == [], name
    assert first.output.rstrip().endswith(DISCLAIMER)
