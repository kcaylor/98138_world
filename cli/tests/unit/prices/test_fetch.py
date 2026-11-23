"""The BrickLink price-guide fetch loop (011 T030; FR-005, FR-008 to FR-010; research R2, R4, R6, R7, R9).

Fake opener, sleep, monotonic clock, wall clock and nonce; no network.
"""

import json
import urllib.error
from decimal import Decimal

import pytest

from lego_image_processor.prices.api_config import load_api_config
from lego_image_processor.prices.credentials import credentials_from_env
from lego_image_processor.prices.fetch import (AuthError, DailyLimitError, FetchInterrupted,
                                               FetchResult, PriceFetchError, ProgressMismatchError,
                                               fetch_snapshot, make_lot_set, progress_path_for)
from lego_image_processor.prices.lots import named_lots, recipe_lots
from lego_image_processor.prices.snapshot import load_snapshot

from .fakeapi import LEAK_ENV, FakeBrickLink, FakeTime, Nonces, Reply, fixture, leaks

CREDS = credentials_from_env(LEAK_ENV)
TWO = named_lots(["98138:140", "6141:1"])       # plate White (4073/1), tile Earth Blue (98138/63)
WHITE, EARTH = ("4073", 1), ("98138", 63)


def run(tmp_path, lots=TWO, opener=None, time=None, name="snap.json", kind="named", **kw):
    time = time or FakeTime()
    opener = opener if opener is not None else FakeBrickLink(time=time)
    out = tmp_path / name
    kw.setdefault("echo", lambda line: None)
    result = fetch_snapshot(lots, CREDS, output=out, lot_set=make_lot_set(kind, lots), opener=opener,
                            sleep=time.sleep, clock=time.clock, now=time.now, nonce=Nonces(), **kw)
    return result, opener, time


def g(guide, *key):
    return key + (guide,)


# --- requests ------------------------------------------------------------------------------------

def test_two_gets_per_lot_with_the_documented_parameters(tmp_path):
    result, opener, time = run(tmp_path)
    assert isinstance(result, FetchResult)
    api = load_api_config()
    reqs = opener.requests
    assert len(reqs) == 4
    assert [r["base"] for r in reqs] == [api.base_url + "/items/PART/4073/price"] * 2 + \
                                        [api.base_url + "/items/PART/98138/price"] * 2
    for r, (color, guide) in zip(reqs, [(1, "sold"), (1, "stock"), (63, "sold"), (63, "stock")]):
        assert r["method"] == "GET"
        assert r["query"] == [("color_id", str(color)), ("guide_type", guide), ("new_or_used", "N"),
                              ("currency_code", "USD"), ("vat", "N")]
        assert r["timeout"] == 30
        assert r["headers"]["User-agent"] == "lego-image-processor (parts prices fetch)"
        assert r["headers"]["Authorization"].startswith('OAuth realm="", oauth_consumer_key=')
        assert r["oauth"]["oauth_consumer_key"] == LEAK_ENV["BRICKLINK_CONSUMER_KEY"]
        assert r["oauth"]["oauth_token"] == LEAK_ENV["BRICKLINK_TOKEN_VALUE"]
        assert r["oauth"]["oauth_signature_method"] == "HMAC-SHA1"
        assert r["oauth"]["oauth_version"] == "1.0"
        # Wall clock, not the monotonic pacing clock (which is ~5000 s here).
        assert r["oauth"]["oauth_timestamp"] == str(int(r["now"].timestamp()))
        assert int(r["oauth"]["oauth_timestamp"]) != int(r["clock"])
    assert len({r["oauth"]["oauth_nonce"] for r in reqs}) == 4


def test_signature_verifies(tmp_path):
    from lego_image_processor.prices.oauth1 import signed_parameters

    _, opener, _ = run(tmp_path)
    r = opener.requests[0]
    expect = signed_parameters("GET", r["base"], r["query"], CREDS, nonce=r["oauth"]["oauth_nonce"],
                               timestamp=int(r["oauth"]["oauth_timestamp"]))
    assert dict(expect)["oauth_signature"] == r["oauth"]["oauth_signature"]


def test_requests_are_paced(tmp_path):
    _, opener, _ = run(tmp_path, interval=1.0)
    starts = [r["clock"] for r in opener.requests]
    assert all(b - a >= 1.0 - 1e-9 for a, b in zip(starts, starts[1:]))
    _, opener, _ = run(tmp_path, name="b.json", interval=2.5,
                       time=FakeTime(), opener=None)
    starts = [r["clock"] for r in opener.requests]
    assert all(b - a >= 2.5 - 1e-9 for a, b in zip(starts, starts[1:]))


def test_latency_counts_toward_the_interval(tmp_path):
    time = FakeTime()
    opener = FakeBrickLink(time=time, latency=0.4)
    run(tmp_path, opener=opener, time=time)
    assert time.sleeps and all(abs(s - 0.6) < 1e-9 for s in time.sleeps)


# --- parsing -------------------------------------------------------------------------------------

def test_figures_from_the_fixtures_exact(tmp_path):
    script = {g("sold", *WHITE): ["price_4073_1_sold.json"], g("stock", *WHITE): ["price_4073_1_stock.json"],
              g("sold", *EARTH): ["price_98138_63_sold_numbers.json"],
              g("stock", *EARTH): ["price_98138_63_stock.json"]}
    time = FakeTime()
    result, _, _ = run(tmp_path, opener=FakeBrickLink(script, time=time), time=time)
    white, earth = result.snapshot.lots
    assert white.sold.qty_avg_price == Decimal("0.0385") and white.sold.avg_price == Decimal("0.0612")
    assert (white.sold.min_price, white.sold.max_price) == (Decimal("0.0100"), Decimal("0.5000"))
    assert (white.sold.unit_quantity, white.sold.total_quantity) == (1204, 380211)
    assert white.stock.qty_avg_price == Decimal("0.0450")
    # JSON numbers parsed without binary rounding.
    assert earth.sold.qty_avg_price == Decimal("0.069") and earth.sold.avg_price == Decimal("0.091")
    text = (tmp_path / "snap.json").read_text()
    assert "price_detail" not in text and "seller_country_code" not in text
    assert '"qty_avg_price": "0.069"' in text


def test_no_sales_is_null_and_stock_fallback(tmp_path):
    time = FakeTime()
    script = {g("sold", *EARTH): ["no_sales.json"]}
    result, _, _ = run(tmp_path, opener=FakeBrickLink(script, time=time), time=time)
    earth = result.snapshot.lots[1]
    assert earth.sold is None and earth.stock is not None and earth.basis == "stock"


def test_more_than_four_places_rounded_half_up(tmp_path):
    time = FakeTime()
    body = json.loads(fixture("price_4073_1_sold.json"))
    body["data"]["qty_avg_price"] = "0.038450"
    result, _, _ = run(tmp_path, opener=FakeBrickLink({g("sold", *WHITE): [Reply(200, body)]}, time=time), time=time)
    assert result.snapshot.lots[0].sold.qty_avg_price == Decimal("0.0385")


@pytest.mark.parametrize("mutate, words", [
    (lambda d: d["data"].pop("qty_avg_price"), "qty_avg_price"),
    (lambda d: d["data"].__setitem__("currency_code", "EUR"), "currency"),
    (lambda d: d["data"].__setitem__("min_price", "0.0000"), "min_price"),
    (lambda d: d["data"].__setitem__("qty_avg_price", "9.0000"), "qty_avg_price"),
])
def test_unexpected_data_stops_with_exit_5(tmp_path, mutate, words):
    body = json.loads(fixture("price_4073_1_sold.json"))
    mutate(body)
    time = FakeTime()
    with pytest.raises(PriceFetchError) as info:
        run(tmp_path, opener=FakeBrickLink({g("sold", *WHITE): [Reply(200, body)]}, time=time), time=time)
    assert info.value.exit_code == 5 and words in str(info.value)
    assert "plate 6141 White" in str(info.value)


# --- retries --------------------------------------------------------------------------------------

@pytest.mark.parametrize("failure", [
    Reply(429, file="error_429.json"), Reply(503, "Service Unavailable"), Reply(500, "{}"),
    urllib.error.URLError("connection reset"), TimeoutError("timed out"), ConnectionResetError(),
    Reply(200, file="error_429.json"),                       # meta.code 429 under HTTP 200
    Reply(200, "<html>maintenance</html>"),                  # not JSON
])
def test_retried_then_succeeds(tmp_path, failure):
    time = FakeTime()
    opener = FakeBrickLink({g("sold", *WHITE): [failure, failure]}, time=time)
    result, _, _ = run(tmp_path, opener=opener, time=time)
    assert len(opener.requests) == 6 and result.snapshot.complete
    assert 2 in time.sleeps and 4 in time.sleeps and 8 not in time.sleeps


def test_retry_after_is_used_and_capped(tmp_path):
    time = FakeTime()
    opener = FakeBrickLink({g("sold", *WHITE): [Reply(429, file="error_429.json", headers={"Retry-After": "7"}),
                                                Reply(429, file="error_429.json", headers={"Retry-After": "600"})]},
                           time=time)
    run(tmp_path, opener=opener, time=time)
    assert 7 in time.sleeps and 60 in time.sleeps and 2 not in time.sleeps


def test_exhausted_retries_stop_with_progress(tmp_path):
    time = FakeTime()
    opener = FakeBrickLink({g("sold", *EARTH): [Reply(503, "busy")] * 10}, time=time)
    with pytest.raises(PriceFetchError) as info:
        run(tmp_path, opener=opener, time=time, max_attempts=5)
    e = info.value
    assert type(e) is PriceFetchError and e.exit_code == 5
    assert "after 5 attempts" in str(e) and "HTTP 503" in str(e)
    assert (e.done, e.total) == (1, 2) and e.progress_path == progress_path_for(tmp_path / "snap.json")
    assert [s for s in time.sleeps if s >= 2] == [2, 4, 8, 16]
    assert len(opener.requests) == 2 + 5
    assert not (tmp_path / "snap.json").exists()
    prog = json.loads(e.progress_path.read_text())
    assert prog["format"] == "price-progress-1" and len(prog["lots"]) == 1


def test_max_attempts_one_means_no_retry(tmp_path):
    time = FakeTime()
    opener = FakeBrickLink({g("sold", *WHITE): [Reply(503, "busy")]}, time=time)
    with pytest.raises(PriceFetchError):
        run(tmp_path, opener=opener, time=time, max_attempts=1)
    assert len(opener.requests) == 1


# --- stops ----------------------------------------------------------------------------------------

@pytest.mark.parametrize("reply", [Reply(401, file="error_401_token_ip.json"),
                                   Reply(200, file="error_401_token_ip.json")])
def test_ip_mismatch_is_an_auth_error(tmp_path, reply):
    time = FakeTime()
    opener = FakeBrickLink({g("stock", *EARTH): [reply]}, time=time)
    with pytest.raises(AuthError) as info:
        run(tmp_path, opener=opener, time=time)
    e = info.value
    assert e.exit_code == 7 and len(opener.requests) == 4     # no retry
    msg = str(e)
    assert msg.startswith("BrickLink rejected the credentials (TOKEN_IP_MISMATCHED")
    assert "IP address setting" in msg and "203.0.113.7" in msg
    assert LEAK_ENV["BRICKLINK_CONSUMER_KEY"] not in msg and "<redacted>" in msg
    assert not (tmp_path / "snap.json").exists()
    assert (e.done, e.total) == (1, 2) and e.progress_path.exists()


@pytest.mark.parametrize("reply", [Reply(401, file="error_401_signature.json"), Reply(403, "{}"),
                                   Reply(403, "forbidden")])
def test_other_auth_errors(tmp_path, reply):
    time = FakeTime()
    opener = FakeBrickLink({g("sold", *WHITE): [reply]}, time=time)
    with pytest.raises(AuthError) as info:
        run(tmp_path, opener=opener, time=time, write_partial=True)
    assert "BRICKLINK_" in str(info.value) and "clock" in str(info.value)
    assert len(opener.requests) == 1
    assert not (tmp_path / "snap.json").exists()             # never a partial on auth errors


def test_daily_limit(tmp_path):
    time = FakeTime()
    opener = FakeBrickLink({g("sold", *EARTH): [Reply(429, file="error_daily_limit.json")]}, time=time)
    with pytest.raises(DailyLimitError) as info:
        run(tmp_path, opener=opener, time=time)
    assert info.value.exit_code == 5 and "try again tomorrow" in str(info.value)
    assert len(opener.requests) == 3                          # no retry


def test_not_found_lot_continues(tmp_path):
    time = FakeTime()
    opener = FakeBrickLink({g("sold", *WHITE): [Reply(404, file="not_found.json")]}, time=time)
    result, _, _ = run(tmp_path, opener=opener, time=time)
    white = result.snapshot.lots[0]
    assert white.error == "not found" and white.sold is None and white.stock is None
    assert result.snapshot.complete and len(opener.requests) == 3   # no stock request after 404


def test_not_found_under_http_200(tmp_path):
    time = FakeTime()
    opener = FakeBrickLink({g("stock", *WHITE): [Reply(200, file="not_found.json")]}, time=time)
    result, _, _ = run(tmp_path, opener=opener, time=time)
    assert result.snapshot.lots[0].error == "not found" and result.snapshot.lots[0].sold is None


def test_bad_request_stops_exit_5(tmp_path):
    time = FakeTime()
    opener = FakeBrickLink({g("sold", *WHITE): [Reply(400, file="error_400.json")]}, time=time)
    with pytest.raises(PriceFetchError) as info:
        run(tmp_path, opener=opener, time=time)
    assert info.value.exit_code == 5 and "PARAMETER_MISSING_OR_INVALID" in str(info.value)
    assert len(opener.requests) == 1


def test_keyboard_interrupt_keeps_progress(tmp_path):
    time = FakeTime()
    opener = FakeBrickLink(time=time, fail_after=3, fail_with=KeyboardInterrupt())
    with pytest.raises(FetchInterrupted) as info:
        run(tmp_path, opener=opener, time=time)
    assert info.value.exit_code == 130 and (info.value.done, info.value.total) == (1, 2)
    assert info.value.progress_path.exists()


# --- progress, partial, resume ------------------------------------------------------------------

def test_progress_rewritten_after_each_lot_and_deleted_on_completion(tmp_path):
    seen = []
    out = tmp_path / "snap.json"
    prog = progress_path_for(out)
    assert prog.name == "snap.progress.json"

    def echo(line):
        if prog.exists():
            seen.append(len(json.loads(prog.read_text())["lots"]))
    result, _, _ = run(tmp_path, echo=echo)
    assert seen == [1, 2]
    assert not prog.exists() and result.progress_path == prog
    assert [p.name for p in tmp_path.iterdir()] == ["snap.json"]


def test_progress_file_shape(tmp_path):
    time = FakeTime()
    opener = FakeBrickLink({g("sold", *EARTH): [Reply(503, "x")] * 5}, time=time)
    with pytest.raises(PriceFetchError) as info:
        run(tmp_path, opener=opener, time=time)
    prog = json.loads(info.value.progress_path.read_text())
    assert list(prog) == ["format", "fingerprint", "started_at", "lot_set", "lots"]
    assert len(prog["fingerprint"]) == 64 and prog["started_at"] == "2026-12-01T18:02:10Z"
    assert prog["lot_set"] == {"kind": "named", "recipes": [], "count": 2}
    assert prog["lots"][0]["part_id"] == "6141"


def test_write_partial(tmp_path):
    time = FakeTime()
    opener = FakeBrickLink({g("sold", *EARTH): [Reply(503, "x")] * 5}, time=time)
    with pytest.raises(PriceFetchError) as info:
        run(tmp_path, opener=opener, time=time, write_partial=True)
    assert info.value.partial_path == tmp_path / "snap.json"
    snap = load_snapshot(tmp_path / "snap.json")
    assert snap.complete is False and len(snap.lots) == 1 and snap.lot_set["count"] == 2


def test_stop_leaves_an_existing_output_untouched(tmp_path):
    out = tmp_path / "snap.json"
    out.write_text("previous complete snapshot", encoding="utf-8")
    time = FakeTime()
    opener = FakeBrickLink({g("sold", *EARTH): [Reply(503, "x")] * 5}, time=time)
    with pytest.raises(PriceFetchError):
        run(tmp_path, opener=opener, time=time)
    assert out.read_text(encoding="utf-8") == "previous complete snapshot"


def test_resume_skips_saved_lots(tmp_path):
    time = FakeTime()
    opener = FakeBrickLink({g("sold", *EARTH): [Reply(503, "x")] * 5}, time=time)
    with pytest.raises(PriceFetchError):
        run(tmp_path, opener=opener, time=time)
    time2 = FakeTime(start=FakeTime().start.replace(hour=19))
    opener2 = FakeBrickLink(time=time2)
    result, _, _ = run(tmp_path, opener=opener2, time=time2, resume=True)
    assert len(opener2.requests) == 2 and all("98138" in r["path"] for r in opener2.requests)
    assert (result.fetched, result.reused) == (1, 1)
    snap = result.snapshot
    assert snap.complete and snap.retrieved["started_at"] == "2026-12-01T18:02:10Z"
    assert snap.retrieved["finished_at"].startswith("2026-12-01T19:")
    assert not result.progress_path.exists()


def test_resume_without_progress(tmp_path):
    with pytest.raises(ProgressMismatchError) as info:
        run(tmp_path, resume=True)
    assert info.value.exit_code == 1 and "no progress file" in str(info.value)


def test_resume_with_a_different_lot_set(tmp_path):
    time = FakeTime()
    opener = FakeBrickLink({g("sold", *EARTH): [Reply(503, "x")] * 5}, time=time)
    with pytest.raises(PriceFetchError):
        run(tmp_path, opener=opener, time=time)
    other = named_lots(["98138:140", "6141:1", "98138:321"])
    opener2 = FakeBrickLink()
    with pytest.raises(ProgressMismatchError) as info:
        run(tmp_path, lots=other, opener=opener2, resume=True)
    assert "lot set" in str(info.value) and "2 lots" in str(info.value) and "3 lots" in str(info.value)
    assert opener2.requests == []


def test_resume_with_a_corrupt_progress_file(tmp_path):
    progress_path_for(tmp_path / "snap.json").write_text("{nope", encoding="utf-8")
    with pytest.raises(ProgressMismatchError) as info:
        run(tmp_path, resume=True)
    assert "progress file" in str(info.value)


def test_without_resume_an_old_progress_file_is_replaced(tmp_path):
    prog = progress_path_for(tmp_path / "snap.json")
    prog.write_text('{"old": true}', encoding="utf-8")
    lines = []
    result, opener, _ = run(tmp_path, echo=lines.append)
    assert len(opener.requests) == 4 and result.snapshot.complete and not prog.exists()
    assert any("Replacing" in l for l in lines)


# --- the written snapshot --------------------------------------------------------------------------

def test_snapshot_records_api_lot_set_and_times(tmp_path):
    result, _, time = run(tmp_path)
    snap = load_snapshot(tmp_path / "snap.json")
    api = load_api_config()
    assert snap.source["api"] == api.snapshot_block()
    assert snap.source["tool"]["command"] == "parts prices fetch"
    assert snap.lot_set == {"kind": "named", "recipes": [], "count": 2}
    assert snap.retrieved["started_at"] == "2026-12-01T18:02:10Z"
    assert snap.retrieved["started_at"] <= snap.lots[0].retrieved_at <= snap.lots[1].retrieved_at \
        <= snap.retrieved["finished_at"]
    assert result.path == tmp_path / "snap.json"


def test_recipe_lot_set_records_recipe_hashes():
    import hashlib

    from lego_image_processor.maps.recipe import bundled_recipes

    ls = make_lot_set("recipes", recipe_lots())
    assert ls["kind"] == "recipes" and ls["count"] == 19
    assert [r["id"] for r in ls["recipes"]] == sorted(bundled_recipes())
    for r in ls["recipes"]:
        assert r["sha256"] == hashlib.sha256(bundled_recipes()[r["id"]].read_bytes()).hexdigest()
    assert make_lot_set("all-cited", ())["recipes"] == []


def test_same_responses_and_times_give_identical_bytes(tmp_path):
    run(tmp_path, name="a.json")
    run(tmp_path, name="b.json")
    assert (tmp_path / "a.json").read_bytes() == (tmp_path / "b.json").read_bytes()


def test_progress_lines_are_echoed(tmp_path):
    lines = []
    run(tmp_path, echo=lines.append)
    assert lines == ["[1/2] plate 6141 White (BrickLink 4073 / White, color 1): sold 101 sales, stock 101 lots",
                     "[2/2] tile 98138 Earth Blue (BrickLink 98138 / Dark Blue, color 63): sold 163 sales, "
                     "stock 163 lots"]


def test_no_secret_in_any_file_or_message(tmp_path):
    lines = []
    run(tmp_path, echo=lines.append)
    time = FakeTime()
    opener = FakeBrickLink({g("sold", *EARTH): [Reply(401, file="error_401_token_ip.json")]}, time=time)
    with pytest.raises(AuthError) as info:
        run(tmp_path, name="c.json", opener=opener, time=time, echo=lines.append)
    text = "\n".join(lines) + str(info.value) + repr(info.value)
    text += "".join(p.read_text() for p in tmp_path.iterdir())
    assert leaks(text, opener) == []
