"""CLI contract for `parts estimate` (011 T018; contracts/cli.md, US1-5 to US1-8)."""

import json
import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from lego_image_processor.cli.main import cli
from lego_image_processor.kit import load_official_design
from lego_image_processor.kit.source import DISCLAIMER
from lego_image_processor.prices import wording

from ..unit.parts.layouts import LAND_ELEVATION, make_grid

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "prices" / "bricklink_price_guide.json"
BASE = ["--prices", str(FIXTURE), "--as-of", "2026-12-05"]


def _last(output: str) -> str:
    return output.rstrip("\n").splitlines()[-1]


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def layouts(tmp_path):
    out = {}
    for name, grid in (("official", load_official_design().to_layout()), ("elev", make_grid(LAND_ELEVATION))):
        p = tmp_path / f"{name}.json"
        p.write_text(grid.to_json(), encoding="utf-8")
        out[name] = p
    return out


def _estimate(runner, *args, env=None):
    return runner.invoke(cli, ["parts", "estimate", *map(str, args)], env=env)


def test_table(runner, layouts):
    r = _estimate(runner, layouts["official"], *BASE)
    assert r.exit_code == 0, r.output
    lines = r.output.splitlines()
    assert any(l.startswith("Every piece") and "$" in l for l in lines)
    assert any(l.startswith("On top of one kit") and "One kit covers every piece" in l for l in lines)
    assert wording.ESTIMATE_NOTE in lines and wording.ATTRIBUTION in lines
    assert _last(r.output) == DISCLAIMER


def test_json_stdout_matches_the_contract(runner, layouts):
    r = _estimate(runner, layouts["official"], *BASE, "--format", "json")
    assert r.exit_code == 0, r.output
    d = json.loads(r.output)
    assert list(d) == ["format_version", "kind", "kit", "layout", "snapshot", "staleness",
                       "estimates", "notes", "estimate_note", "attribution", "disclaimer"]
    assert d["disclaimer"] == DISCLAIMER and d["kind"] == "price-estimate"
    assert set(d["estimates"]) == {"full", "one_kit"}
    full = d["estimates"]["full"]
    assert set(full) == {"kind", "label", "owned_kits", "totals", "whole_dollars", "pieces", "lots",
                         "by_basis", "complete", "nothing_to_buy", "lines", "unpriced"}
    assert d["snapshot"]["path"] == str(FIXTURE) and d["snapshot"]["packaged"] is False
    assert d["staleness"] == {"as_of": "2026-12-05", "age_days": 4, "threshold_days": 90, "stale": False}
    assert d["layout"]["path"] == str(layouts["official"])
    assert d["estimates"]["one_kit"]["nothing_to_buy"] is True


def test_output_file_is_deterministic(runner, layouts, tmp_path):
    a, b = tmp_path / "e1.json", tmp_path / "e2.json"
    r = _estimate(runner, layouts["official"], *BASE, "-o", a)
    assert r.exit_code == 0, r.output
    lines = r.output.rstrip("\n").splitlines()
    assert len(lines) == 2 and lines[0].startswith(f"Wrote price estimate {a}") and lines[1] == DISCLAIMER
    assert _estimate(runner, layouts["official"], *BASE, "-o", b).exit_code == 0
    assert a.read_bytes() == b.read_bytes()
    assert json.loads(a.read_text(encoding="utf-8"))["disclaimer"] == DISCLAIMER


def test_lines_option(runner, layouts):
    r = _estimate(runner, layouts["elev"], *BASE, "--lines")
    assert r.exit_code == 0, r.output
    assert "Every piece, by lot:" in r.output and "On top of one kit, by lot:" in r.output
    assert "4073 / White (1)" in r.output


def test_quiet(runner, layouts, tmp_path):
    r = _estimate(runner, layouts["official"], *BASE, "-q")
    assert r.exit_code == 0 and r.output == ""
    out = tmp_path / "q.json"
    r = _estimate(runner, layouts["official"], *BASE, "-q", "-o", out)
    assert r.exit_code == 0 and r.output == "" and out.is_file()


def test_stale_warning_same_figures(runner, layouts):
    fresh = json.loads(_estimate(runner, layouts["official"], *BASE, "--format", "json").output)
    r = _estimate(runner, layouts["official"], "--prices", FIXTURE, "--as-of", "2027-06-01")
    assert r.exit_code == 0
    assert "Warning: prices are from 2026-12-01, 182 days before 2027-06-01; they may be out of date." in r.output
    stale = json.loads(_estimate(runner, layouts["official"], "--prices", FIXTURE, "--as-of", "2027-06-01",
                                 "--format", "json").output)
    assert stale["staleness"]["stale"] is True
    assert stale["estimates"] == fresh["estimates"]


def test_incomplete_is_exit_0(runner, layouts):
    r = _estimate(runner, layouts["elev"], *BASE)
    assert r.exit_code == 0
    assert "Incomplete: 128 pieces in 1 color could not be priced:" in r.output
    assert "plate 6141 Dark Brown (LEGO 308): not in the price snapshot; 128 pieces" in r.output


@pytest.mark.parametrize("args", [["--stale-days", "0"], ["--kits", "1"], ["--as-of", "2026-13-01"],
                                  ["--format", "csv"]])
def test_usage_errors(runner, layouts, args):
    r = _estimate(runner, layouts["official"], *BASE, *args)
    assert r.exit_code == 2, r.output


def test_no_packaged_snapshot(runner, layouts, monkeypatch, tmp_path):
    monkeypatch.setattr(wording, "PACKAGED_SNAPSHOT_PATH", tmp_path / "absent.json")
    r = _estimate(runner, layouts["official"], "--as-of", "2026-12-05")
    assert r.exit_code == 1
    assert ("no price snapshot is packaged yet; pass --prices FILE or run "
            "`lego-image-processor parts prices fetch`") in r.output
    assert _last(r.output) == DISCLAIMER


def test_packaged_snapshot_is_the_default(runner, layouts, monkeypatch):
    monkeypatch.setattr(wording, "PACKAGED_SNAPSHOT_PATH", FIXTURE)
    r = _estimate(runner, layouts["official"], "--as-of", "2026-12-05", "--format", "json")
    assert r.exit_code == 0, r.output
    s = json.loads(r.output)["snapshot"]
    assert s["packaged"] is True and s["path"] is None


@pytest.mark.parametrize("content,needle", [
    (None, "cannot read"), (b"{nope", "not JSON"), (b'{"format_version": "2"}', "format_version")])
def test_bad_snapshot_writes_nothing(runner, layouts, tmp_path, content, needle):
    snap = tmp_path / "snap.json"
    if content is not None:
        snap.write_bytes(content)
    out = tmp_path / "e.json"
    r = _estimate(runner, layouts["official"], "--prices", snap, "--as-of", "2026-12-05", "-o", out)
    assert r.exit_code == 1 and needle in r.output and not out.exists()
    assert _last(r.output) == DISCLAIMER


def test_missing_output_directory(runner, layouts, tmp_path):
    r = _estimate(runner, layouts["official"], *BASE, "-o", tmp_path / "nope" / "e.json")
    assert r.exit_code == 1 and "does not exist" in r.output


def test_bad_layout_as_parts_list(runner, tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{nope", encoding="utf-8")
    r = _estimate(runner, bad, *BASE)
    expected = runner.invoke(cli, ["parts", "list", str(bad)])
    assert r.exit_code == 1 == expected.exit_code
    assert r.output == expected.output
    r = _estimate(runner, tmp_path / "absent.json", *BASE)
    assert r.exit_code == 1 and "cannot read layout" in r.output


def test_no_credentials_needed(runner, layouts):
    env = {k: None for k in os.environ if k.startswith("BRICKLINK_")}
    env.update({"BRICKLINK_CONSUMER_KEY": None, "BRICKLINK_TOKEN_SECRET": None})
    r = _estimate(runner, layouts["official"], *BASE, env=env)
    assert r.exit_code == 0, r.output


# --- `parts prices fetch` (011 T034; contracts/cli.md; US2-5 to US2-9) ------------------------------

from lego_image_processor.prices import fetch as fetch_mod  # noqa: E402

from ..unit.prices.fakeapi import LEAK_ENV, FakeBrickLink, FakeTime, Nonces, Reply, leaks  # noqa: E402


@pytest.fixture
def api(monkeypatch):
    """Patch the network, sleep and clocks in prices.fetch; return a holder for the fake opener."""
    class Holder:
        time = FakeTime()
        opener = FakeBrickLink(time=time)

        def use(self, opener):
            opener.time = self.time
            self.opener = opener
            return opener
    h = Holder()
    monkeypatch.setattr(fetch_mod, "default_opener", lambda req, timeout=None: h.opener(req, timeout))
    monkeypatch.setattr(fetch_mod, "default_sleep", h.time.sleep)
    monkeypatch.setattr(fetch_mod, "default_clock", h.time.clock)
    monkeypatch.setattr(fetch_mod, "utc_now", h.time.now)
    monkeypatch.setattr(fetch_mod, "default_nonce", Nonces())
    return h


def _fetch(runner, *args, env=LEAK_ENV):
    return runner.invoke(cli, ["parts", "prices", "fetch", *map(str, args)], env=env)


TWO_LOTS = ["--lot", "98138:140", "--lot", "6141:1"]


@pytest.mark.parametrize("missing", ["BRICKLINK_TOKEN_SECRET", "BRICKLINK_CONSUMER_KEY"])
def test_fetch_missing_variable(runner, api, tmp_path, missing):
    env = {**LEAK_ENV, missing: None}
    r = _fetch(runner, "-o", tmp_path / "s.json", *TWO_LOTS, env=env)
    assert r.exit_code == 1
    assert f"Error: missing environment variable(s): {missing}" in r.output
    assert api.opener.requests == [] and _last(r.output) == DISCLAIMER
    assert leaks(r.output, api.opener) == []


def test_fetch_empty_variable_counts_as_missing(runner, api, tmp_path):
    r = _fetch(runner, "-o", tmp_path / "s.json", env={**LEAK_ENV, "BRICKLINK_TOKEN_VALUE": ""})
    assert r.exit_code == 1 and "BRICKLINK_TOKEN_VALUE" in r.output and api.opener.requests == []


def test_fetch_output_required(runner, api):
    assert _fetch(runner, *TWO_LOTS).exit_code == 2


def test_fetch_named_lots(runner, api, tmp_path):
    out = tmp_path / "s.json"
    r = _fetch(runner, "-o", out, *TWO_LOTS)
    assert r.exit_code == 0, r.output
    assert len(api.opener.requests) == 4
    snap = json.loads(out.read_text())
    assert snap["lot_set"] == {"kind": "named", "recipes": [], "count": 2} and snap["complete"] is True
    lines = r.output.splitlines()
    assert lines[0] == ("Note: BrickLink API details in bricklink_api.json are not yet checked against "
                        "the live documentation.")
    assert lines[1].startswith("[1/2] plate 6141 White (BrickLink 4073 / White, color 1): sold ")
    assert lines[2].startswith("[2/2] tile 98138 Earth Blue (BrickLink 98138 / Dark Blue, color 63)")
    assert any(l.startswith(f"Wrote price snapshot {out}: 2 lots (complete);") for l in lines)
    assert "Review the file, then commit it." in lines and wording.ATTRIBUTION in lines
    assert _last(r.output) == DISCLAIMER
    assert leaks(r.output + out.read_text(), api.opener) == []


def test_fetch_lot_with_all_colors_is_usage(runner, api, tmp_path):
    r = _fetch(runner, "-o", tmp_path / "s.json", "--all-colors", "--lot", "98138:140")
    assert r.exit_code == 2 and api.opener.requests == []


@pytest.mark.parametrize("spec", ["98138", "98138:999", "3001:1", "x:y"])
def test_fetch_bad_lot(runner, api, tmp_path, spec):
    r = _fetch(runner, "-o", tmp_path / "s.json", "--lot", spec)
    assert r.exit_code == 1 and "Error: lot" in r.output and api.opener.requests == []
    assert _last(r.output) == DISCLAIMER


@pytest.mark.parametrize("args", [["--interval", "0.4"], ["--max-attempts", "0"], ["--max-attempts", "11"]])
def test_fetch_option_ranges(runner, api, tmp_path, args):
    assert _fetch(runner, "-o", tmp_path / "s.json", *TWO_LOTS, *args).exit_code == 2


def test_fetch_missing_output_directory(runner, api, tmp_path):
    r = _fetch(runner, "-o", tmp_path / "nope" / "s.json", *TWO_LOTS)
    assert r.exit_code == 1 and "does not exist" in r.output and api.opener.requests == []


def test_fetch_all_colors(runner, api, tmp_path):
    out = tmp_path / "s.json"
    r = _fetch(runner, "-o", out, "--all-colors", "-q")
    assert r.exit_code == 0, r.output
    # every cited color of the plate, the round tile and (feature 016) the square tile 3070b,
    # which BrickLink files as item 3070 (part_numbers.json)
    from lego_image_processor.kit.part_colors import load_part_colors
    from lego_image_processor.kit.part_numbers import load_part_numbers
    n = 84 + len(load_part_colors().for_part("3070b"))
    assert len(api.opener.requests) == 2 * n
    snap = json.loads(out.read_text())
    assert snap["lot_set"]["kind"] == "all-cited" and len(snap["lots"]) == n
    square = [l for l in snap["lots"] if l["part_id"] == "3070b"]
    assert square and {l["bricklink"]["item_no"] for l in square} == {load_part_numbers().get("3070b").bricklink_item_no}
    assert [l["part_id"] for l in snap["lots"]][-len(square):] == ["3070b"] * len(square)


def test_fetch_square_tile_lot(runner, api, tmp_path):
    # feature 016 (contracts/cli.md): `--lot 3070b:26` is accepted; the request asks BrickLink for
    # item 3070 (part_numbers.json). The fake API only; nothing here reaches BrickLink.
    from lego_image_processor.kit.part_numbers import load_part_numbers
    out = tmp_path / "s.json"
    r = _fetch(runner, "-o", out, "--lot", "3070b:26", "-q")
    assert r.exit_code == 0, r.output
    item = load_part_numbers().get("3070b").bricklink_item_no
    assert {q["path"].split("/items/PART/")[1].split("/")[0] for q in api.opener.requests} == {item}
    snap = json.loads(out.read_text())
    assert [(l["part_id"], l["lego_color_id"], l["bricklink"]["item_no"]) for l in snap["lots"]] == \
        [("3070b", 26, item)]
    assert _last(r.output) == DISCLAIMER


def test_fetch_5xx_exhaustion(runner, api, tmp_path):
    api.use(FakeBrickLink({("98138", 63, "sold"): [Reply(503, "busy")] * 5}))
    out = tmp_path / "s.json"
    r = _fetch(runner, "-o", out, *TWO_LOTS, "--interval", "2")
    assert r.exit_code == 5
    assert "after 5 attempts" in r.output and "1 of 2 lots saved in" in r.output
    assert (f"Resume with: lego-image-processor parts prices fetch -o {out} --resume --lot 98138:140 "
            "--lot 6141:1 --interval 2") in r.output
    assert not out.exists() and (tmp_path / "s.progress.json").exists()
    assert _last(r.output) == DISCLAIMER


def test_fetch_daily_limit(runner, api, tmp_path):
    api.use(FakeBrickLink({("98138", 63, "sold"): [Reply(429, file="error_daily_limit.json")]}))
    r = _fetch(runner, "-o", tmp_path / "s.json", *TWO_LOTS)
    assert r.exit_code == 5 and "try again tomorrow" in r.output and "--resume" in r.output


def test_fetch_ip_mismatch(runner, api, tmp_path):
    api.use(FakeBrickLink({("4073", 1, "sold"): [Reply(401, file="error_401_token_ip.json")]}))
    out = tmp_path / "s.json"
    r = _fetch(runner, "-o", out, *TWO_LOTS, "--write-partial")
    assert r.exit_code == 7
    assert "Error: BrickLink rejected the credentials (TOKEN_IP_MISMATCHED" in r.output
    assert "IP address setting" in r.output and "no snapshot written" in r.output
    assert not out.exists() and len(api.opener.requests) == 1
    assert leaks(r.output, api.opener) == [] and _last(r.output) == DISCLAIMER


def test_fetch_resume_mismatch(runner, api, tmp_path):
    out = tmp_path / "s.json"
    r = _fetch(runner, "-o", out, *TWO_LOTS, "--resume")
    assert r.exit_code == 1 and "no progress file" in r.output
    api.use(FakeBrickLink({("98138", 63, "sold"): [Reply(503, "busy")] * 5}))
    assert _fetch(runner, "-o", out, *TWO_LOTS).exit_code == 5
    r = _fetch(runner, "-o", out, "--lot", "98138:140", "--resume")
    assert r.exit_code == 1 and "lot set differs" in r.output
    before = len(api.opener.requests)
    r = _fetch(runner, "-o", out, *TWO_LOTS, "--resume")
    assert r.exit_code == 0, r.output
    assert "Resuming: 1 of 2 lots" in r.output and len(api.opener.requests) - before == 2


def test_fetch_compare_default_is_the_existing_output(runner, api, tmp_path):
    out = tmp_path / "s.json"
    assert _fetch(runner, "-o", out, *TWO_LOTS).exit_code == 0
    first = json.loads(out.read_text())
    api.use(FakeBrickLink({("98138", 63, "sold"): ["price_98138_63_sold.json"]}))
    r = _fetch(runner, "-o", out, *TWO_LOTS)
    assert r.exit_code == 0, r.output
    since = first["retrieved"]["finished_at"][:10]
    assert f"Largest changes in unit average since {since}:" in r.output
    assert "  tile 98138 Earth Blue (140): $" in r.output
    assert "  plate 6141 White (1): $" in r.output


def test_fetch_compare_option_and_first_snapshot(runner, api, tmp_path, monkeypatch):
    monkeypatch.setattr(wording, "PACKAGED_SNAPSHOT_PATH", tmp_path / "none.json")
    r = _fetch(runner, "-o", tmp_path / "a.json", *TWO_LOTS)
    assert "Largest changes in unit average: none (first snapshot)." in r.output
    r = _fetch(runner, "-o", tmp_path / "b.json", *TWO_LOTS, "--compare", FIXTURE)
    assert r.exit_code == 0 and "Largest changes in unit average since 2026-12-01:" in r.output
    r = _fetch(runner, "-o", tmp_path / "c.json", *TWO_LOTS, "--compare", tmp_path / "missing.json")
    assert r.exit_code == 1 and "cannot read price snapshot" in r.output


def test_fetch_quiet_prints_only_the_summary(runner, api, tmp_path):
    out = tmp_path / "s.json"
    r = _fetch(runner, "-o", out, *TWO_LOTS, "-q")
    assert r.exit_code == 0
    lines = r.output.splitlines()
    assert lines[0].startswith(f"Wrote price snapshot {out}:")
    assert not any(l.startswith(("[", "Note:")) for l in lines)
    assert lines[-1] == DISCLAIMER


def test_fetch_ctrl_c(runner, api, tmp_path):
    api.use(FakeBrickLink(fail_after=3, fail_with=KeyboardInterrupt()))
    out = tmp_path / "s.json"
    r = _fetch(runner, "-o", out, *TWO_LOTS)
    assert r.exit_code == 130
    assert "interrupted; 1 of 2 lots saved in" in r.output and "--resume" in r.output
    assert _last(r.output) == DISCLAIMER and (tmp_path / "s.progress.json").exists()
