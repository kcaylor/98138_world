"""Map template maintainer tool (feature 016, T034; contracts/template-file.md, research R4, R5).

Offline and without pyproj: the generator runs on the study's ``Proj`` with a small numpy
plate-carrée transformer in place of pyproj's, and the command tests regenerate from the synthetic
Winkel layout of ``maptemplates.testing`` (the numpy forward formula and its Newton inverse). One
end-to-end Winkel test runs only with pyproj installed and the pinned ETOPO 2022 file cached.
"""

from __future__ import annotations

import json
import math
import re
from functools import lru_cache
from pathlib import Path

import numpy as np
import pytest
from click.testing import CliRunner
from PIL import Image

from lego_image_processor.templates import parse_template, winkel
from maptemplates import document, generate, review, testing
from maptemplates.__main__ import main

DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."
SPEC = generate.get_spec("winkel-tripel")
TEST_SOFTWARE = {"pyproj": "test (numpy)", "proj": "test (numpy)"}


# --- a numpy plate-carrée stand-in for pyproj ------------------------------------------------

class PlateCarreeTransformer:
    """``+proj=eqc +lon_0=…`` on the unit sphere with pyproj's ``transform`` signature. Like PROJ,
    the inverse wraps longitudes into -180..180 and does not refuse points outside the outline, so
    the study's forward round trip is what rejects them."""

    def __init__(self, lon_0: float = 11.1):
        self.lon_0 = lon_0

    def transform(self, a, b, direction="FORWARD", errcheck=False):
        a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
        if str(direction).upper().endswith("INVERSE"):
            lon = (np.degrees(a) + self.lon_0 + 180.0) % 360.0 - 180.0
            return lon, np.degrees(b)
        lam = np.radians((a - self.lon_0 + 180.0) % 360.0 - 180.0)
        with np.errstate(invalid="ignore"):
            phi = np.where(np.abs(b) <= 90.0, np.radians(b), np.inf)
        return lam, phi


# Plate carrée in a padded extent on a 32 x 16 board: the outline |x| <= pi lies at columns
# 1.55..30.45 and rows 0.775..15.225, so column 1 has half its subsamples on the globe and its
# centre (1.5) off it; column 0 and column 31 have none.
PAD = 16.0 / 14.45
EXTENT = (-math.pi * PAD, math.pi * PAD, -math.pi / 2 * PAD, math.pi / 2 * PAD)


def plate_carree(lon_0: float = 11.1):
    return generate.ExactProj("plate-carree (test)", "+proj=eqc", EXTENT,
                              transformer=PlateCarreeTransformer(lon_0))


class Elevation:
    """Land (100 m) where lon is in [-30, 60) and lat in [-40, 50), with a lake (-5 m) at
    lat 0..25, lon 5..40 (a few studs of water inside the land); ocean (-3000 m) elsewhere."""

    def at(self, lat, lon):
        lat, lon = np.asarray(lat, dtype=float), np.asarray(lon, dtype=float)
        land = (lon >= -30) & (lon < 60) & (lat >= -40) & (lat < 50)
        lake = (lat >= 0) & (lat < 25) & (lon >= 5) & (lon < 40)
        return np.where(lake, -5.0, np.where(land, 100.0, -3000.0))


@lru_cache(maxsize=1)
def small_candidate():
    return generate.generate(plate_carree(), Elevation(), width=32, height=16)


# --- the synthetic Winkel candidate (no pyproj; loadable by the package loader) ------------

@lru_cache(maxsize=1)
def synthetic_candidate():
    on, lat, lon, fit = testing.synthetic_layout()
    rl = np.vectorize(lambda v: np.nan if np.isnan(v) else document.round_location(v))
    land = on & testing._land_rule(rl(lat), rl(lon))
    classes = np.where(land, "L", np.where(on, "O", "M")).astype("U1")
    share = np.where(land, 0.875, np.where(on, 0.0625, 0.0))
    share[0:80:7, ::5] = np.where(on[0:80:7, ::5], 0.5, 0.0)   # a sprinkle of near-threshold studs
    return generate.Candidate(width=128, height=80, fit=fit, cover=on.astype(float), land_share=share,
                              classes=classes, lat=lat, lon=lon, any_on_globe=on.copy(),
                              check_points=winkel.check_points())


def synthetic_regenerated():
    return generate.Regenerated(candidate=synthetic_candidate(),
                                dataset=generate.dataset_block(generate.packaged_entry(SPEC.dataset_id)),
                                software=dict(TEST_SOFTWARE))


def synthetic_doc(corrections=(), confirmation=None, generated_on="2026-11-23"):
    r = synthetic_regenerated()
    return generate.build_document(SPEC, r.candidate, dataset=r.dataset, software=r.software,
                                   generated_on=generated_on, corrections=list(corrections),
                                   confirmation=confirmation)


# --- method -------------------------------------------------------------------------------

class TestMethod:
    def test_constants_are_the_studys(self):
        assert generate.SUPERSAMPLE == 4
        assert generate.ON_GLOBE_SHARE == 0.5 and generate.LAND_SHARE == 0.5
        assert generate.ROUND_TRIP_TOLERANCE == 1e-6
        assert generate.LAND_RULE == "elevation > 0 m"

    def test_fit_is_contain_with_the_given_extent(self):
        c = small_candidate()
        assert c.fit["mode"] == "contain" and c.fit["extent"] == list(EXTENT)
        assert c.fit["scale"] == pytest.approx(min(32 / (EXTENT[1] - EXTENT[0]), 16 / (EXTENT[3] - EXTENT[2])))
        assert c.fit["centre"] == [0.0, 0.0]

    def test_winkel_fit_equals_the_package_fit(self):
        fit = generate.board_fit(winkel.extent(), 128, 80)
        assert fit == winkel.fit(128, 80)

    def test_cover_counts_4x4_subsamples_and_round_trip_rejects_off_outline(self):
        c = small_candidate()
        assert c.cover.shape == (16, 32)
        assert np.allclose(c.cover * 16, np.round(c.cover * 16))
        assert (c.cover[:, 0] == 0).all() and (c.cover[:, 31] == 0).all()   # outside |x| <= pi
        assert c.cover[8, 1] == 0.5 and c.cover[8, 2] == 1.0
        assert c.cover[0, 8] == 0.25                                          # row 0: one row of 4 inside

    def test_on_globe_at_half_and_land_at_half(self):
        c = small_candidate()
        assert (c.classes[:, 1] != "M")[1:15].all()          # cover 0.5 is on the globe
        assert (c.classes[0] == "M").all() and (c.classes[:, 0] == "M").all()
        on = c.classes != "M"
        assert ((c.classes == "L") == (on & (c.land_share >= 0.5))).all()
        assert (c.classes == "L").any() and (c.classes == "O").any()

    def test_land_share_is_the_share_of_on_globe_subsamples_above_0_m(self):
        c = small_candidate()
        s = c.fit["scale"]
        off = (np.arange(4) + 0.5) / 4
        seen = set()
        for r in range(16):
            for col in range(32):
                sx, sy = np.meshgrid(col + off, r + off)
                x, y = (sx - 16) / s, (8 - sy) / s
                keep = (np.abs(x) <= math.pi) & (np.abs(y) <= math.pi / 2)
                if not keep.any():
                    continue
                lat = np.degrees(y[keep])
                lon = (np.degrees(x[keep]) + 11.1 + 180) % 360 - 180
                share = float((Elevation().at(lat, lon) > 0).mean())
                assert c.land_share[r, col] == pytest.approx(share), (r, col)
                if c.classes[r, col] != "M":
                    seen.add(c.classes[r, col])
                    assert (c.classes[r, col] == "L") == (share >= 0.5), (r, col)
        assert seen == {"L", "O"}

    def test_check_points_from_the_projection(self):
        c = small_candidate()
        assert len(c.check_points) == len(winkel.CHECK_POINTS) == 24
        lon, lat, x, y = c.check_points[1]
        assert (lon, lat) == winkel.CHECK_POINTS[1]
        assert x == pytest.approx(math.radians((lon - 11.1 + 180) % 360 - 180)) and y == pytest.approx(0.0)


# --- location rule -------------------------------------------------------------------------

class TestLocationRule:
    def test_inverse_of_the_stud_centre(self):
        c = small_candidate()
        s, (cx, cy) = c.fit["scale"], c.fit["centre"]
        r, col = 8, 10
        x, y = (col + 0.5 - 16) / s + cx, (8 - (r + 0.5)) / s + cy
        assert c.lat[r, col] == pytest.approx(math.degrees(y), abs=1e-12)
        assert c.lon[r, col] == pytest.approx((math.degrees(x) + 11.1 + 180) % 360 - 180, abs=1e-12)

    def test_spherical_mean_when_the_centre_is_outside(self):
        c = small_candidate()
        s = c.fit["scale"]
        r, col = 8, 1
        off = (np.arange(4) + 0.5) / 4
        sx, sy = np.meshgrid(col + off, r + off)
        x, y = (sx - 16) / s, (8 - sy) / s
        keep = np.abs(x) <= math.pi
        assert keep.sum() == 8 and abs((col + 0.5 - 16) / s) > math.pi
        la, lo = np.radians(np.degrees(y[keep])), np.radians(np.degrees(x[keep]) + 11.1)
        v = np.stack([np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)]).mean(axis=1)
        v /= np.linalg.norm(v)
        want_lat = math.degrees(math.asin(v[2]))
        want_lon = (math.degrees(math.atan2(v[1], v[0])) + 180) % 360 - 180
        assert c.lat[r, col] == pytest.approx(want_lat, abs=1e-9)
        assert c.lon[r, col] == pytest.approx(want_lon, abs=1e-9)
        assert -180 <= c.lon[r, col] <= 180

    def test_spherical_mean_helper(self):
        # across the antimeridian: the mean is on it, not at 0° (an arithmetic mean would be)
        lat, lon = generate.spherical_mean(np.array([10.0, 10.0]), np.array([179.0, -179.0]))
        assert abs(abs(lon) - 180.0) < 1e-9 and 10.0 < lat < 10.01
        assert generate.spherical_mean(np.array([0.0, 0.0]), np.array([10.0, 20.0])) == pytest.approx((0.0, 15.0))

    def test_studs_with_no_on_globe_sample_have_no_location(self):
        c = small_candidate()
        assert (~c.any_on_globe[:, 0]).all() and np.isnan(c.lat[:, 0]).all()
        assert c.any_on_globe[0, 8] and np.isfinite(c.lat[0, 8])   # margin, but some samples on the globe


# --- flags ---------------------------------------------------------------------------------

def _classes(rows):
    return np.array([list(r) for r in rows], dtype="U1")


class TestFlags:
    CLASSES = _classes([
        "MMMMMMMMMMMMMMMM",
        "MOOOOOOOOOOOOOOM",
        "MOLLLLLLOOOOOOOM",
        "MOLOOLLLOOOOOOOM",
        "MOLOOLOLOOOOOOOM",
        "MOLLLLLLOOOOOOOM",
        "MOOOOOOOOOOOOOOM",
        "MMMMMMMMMMMMMMMM",
    ])

    def test_water_not_connected_with_group_sizes(self):
        flags = generate.review_flags(self.CLASSES)
        water = [f for f in flags if f["reason"] == generate.FLAG_WATER]
        assert {(f["row"], f["col"]) for f in water} == {(3, 3), (3, 4), (4, 3), (4, 4), (4, 6)}
        sizes = {(f["row"], f["col"]): f["group_size"] for f in water}
        assert sizes[(3, 3)] == 4 and sizes[(4, 6)] == 1
        assert all(f["class"] == "ocean" for f in water)
        assert [f["group_size"] for f in water] == sorted((f["group_size"] for f in water), reverse=True)

    def test_diagonal_neighbours_are_not_connected(self):
        c = _classes(["OOOO", "OLLL", "OLOL", "OLLO"])
        groups = generate.water_groups(c)
        assert [len(g) for g in groups] == [1, 1]   # (2,2) and (3,3) touch only at a corner

    def test_land_share_flags_between_40_and_60_percent(self):
        share = np.zeros(self.CLASSES.shape)
        share[2, 2], share[2, 3], share[2, 4], share[1, 1] = 0.4, 0.6, 0.61, 0.39
        share[1, 2], share[0, 0] = 0.5, 0.5               # (0, 0) is margin: never flagged
        flags = generate.review_flags(self.CLASSES, share)
        near = [f for f in flags if f["reason"] == generate.FLAG_LAND_SHARE]
        assert {(f["row"], f["col"]) for f in near} == {(2, 2), (2, 3), (1, 2)}
        f = next(f for f in near if (f["row"], f["col"]) == (1, 2))
        assert f == {"row": 1, "col": 2, "class": "ocean", "land_share": 0.5, "reason": "land share 40-60%",
                     "group_size": None}

    def test_reason_strings_are_exact(self):
        assert generate.FLAG_LAND_SHARE == "land share 40-60%"
        assert generate.FLAG_WATER == "water not connected to the ocean"
        for f in generate.review_flags(self.CLASSES, np.full(self.CLASSES.shape, 0.5)):
            assert set(f) == {"row", "col", "class", "land_share", "reason", "group_size"}
            assert f["class"] in ("land", "ocean", "margin")

    def test_without_land_share_only_water_flags(self):
        flags = generate.review_flags(self.CLASSES)
        assert {f["reason"] for f in flags} == {generate.FLAG_WATER}
        assert all(f["land_share"] is None for f in flags)

    def test_flags_document(self):
        c = small_candidate()
        flags = generate.review_flags(c.classes, c.land_share)
        doc = review.flags_document("plate-carree", flags, classes=c.classes, lat=c.lat, lon=c.lon,
                                    of="candidate", generated_on="2026-11-23")
        assert doc["counts"][generate.FLAG_WATER] == sum(f["reason"] == generate.FLAG_WATER for f in flags)
        assert doc["groups"] and doc["groups"][0]["size"] == max(g["size"] for g in doc["groups"])
        assert list(doc)[-1] == "disclaimer" and doc["disclaimer"] == DISCLAIMER
        text = review.flags_text(doc)
        assert json.loads(text) == doc
        assert sum(1 for line in text.splitlines() if '"reason"' in line) == len(flags)   # one flag per line


# --- corrections ---------------------------------------------------------------------------

def _corr(row, col, cls, reason="test"):
    return {"row": row, "col": col, "class": cls, "reason": reason}


class TestCorrections:
    def test_applied_in_order(self):
        c = small_candidate()
        r, col = 8, 10
        assert c.classes[r, col] == "O"
        classes, lat, lon = document.apply_corrections(c.classes, c.lat, c.lon, c.any_on_globe,
                                                       [_corr(r, col, "land"), _corr(r, col, "margin")])
        assert classes[r, col] == "M" and np.isnan(lat[r, col]) and np.isnan(lon[r, col])
        assert c.classes[r, col] == "O"                      # the candidate is not changed
        assert (classes != c.classes).sum() == 1

    def test_margin_to_ocean_gets_a_location(self):
        c = small_candidate()
        assert c.classes[0, 8] == "M" and c.any_on_globe[0, 8]
        classes, lat, lon = document.apply_corrections(c.classes, c.lat, c.lon, c.any_on_globe,
                                                       [_corr(0, 8, "ocean")])
        assert classes[0, 8] == "O" and lat[0, 8] == c.lat[0, 8] and np.isfinite(lon[0, 8])
        assert np.isnan(lat[classes == "M"]).all() and np.isfinite(lat[classes != "M"]).all()

    @pytest.mark.parametrize("corr, words", [
        (_corr(16, 3, "land"), "outside"),
        (_corr(3, 32, "land"), "outside"),
        (_corr(-1, 3, "land"), "outside"),
        (_corr(8, 10, "ocean"), "stale"),
        (_corr(8, 0, "land"), "no on-globe"),
        (_corr(8, 10, "sea"), "land, ocean or margin"),
        (_corr(8, 10, "land", reason=" "), "reason"),
        ({"row": 8, "col": 10, "class": "land"}, "row, col, class, reason"),
    ])
    def test_errors(self, corr, words):
        c = small_candidate()
        with pytest.raises(document.CorrectionError) as exc:
            document.apply_corrections(c.classes, c.lat, c.lon, c.any_on_globe, [_corr(8, 2, "land"), corr])
        assert words in str(exc.value) and "correction 2" in str(exc.value)

    def test_read_corrections_file(self, tmp_path):
        p = tmp_path / "c.json"
        p.write_text(json.dumps([_corr(1, 2, "land")]), encoding="utf-8")
        assert document.read_corrections(p) == [_corr(1, 2, "land")]
        p.write_text(json.dumps({"corrections": [_corr(1, 2, "land")]}), encoding="utf-8")
        assert document.read_corrections(p) == [_corr(1, 2, "land")]
        p.write_text(json.dumps({"x": 1}), encoding="utf-8")
        with pytest.raises(document.CorrectionError):
            document.read_corrections(p)


# --- the document writer -------------------------------------------------------------------

class TestDocument:
    def test_loads_with_the_package_loader(self):
        doc = synthetic_doc()
        t = parse_template(document.normalise(doc), "winkel-tripel.json")
        assert t.status == "unconfirmed" and t.counts == doc["counts"]
        assert t.dataset.id == "etopo2022-surface-10m"
        assert doc["source"]["generator"] == "cli/tools/maptemplates"
        assert doc["source"]["method"] == {
            "supersample": 4, "on_globe_share": 0.5, "land_share": 0.5, "land_rule": "elevation > 0 m",
            "round_trip_tolerance": 1e-6, "location_rule": generate.LOCATION_RULE}
        assert doc["source"]["software"] == TEST_SOFTWARE
        assert doc["confirmation"] is None and doc["corrections"] == []
        assert doc["disclaimer"] == DISCLAIMER and doc["source"]["disclaimer"] == DISCLAIMER

    def test_field_order_rows_per_line_and_4_decimals(self):
        text = document.to_text(synthetic_doc())
        doc = json.loads(text)
        assert list(doc) == list(document.FIELD_ORDER)
        lines = text.splitlines()
        class_rows = [l for l in lines if re.fullmatch(r'\s*"[LOM]{128}",?', l)]
        assert len(class_rows) == 80
        lat_start = next(i for i, l in enumerate(lines) if l.strip() == '"lat": [')
        lat_rows = lines[lat_start + 1:lat_start + 81]
        assert all(l.strip().startswith("[") and l.strip().rstrip(",").endswith("]") for l in lat_rows)
        numbers = re.findall(r"-?\d+\.\d+", "\n".join(lat_rows))
        assert numbers and all(len(n.split(".")[1]) <= 4 for n in numbers)
        assert text.endswith("\n")

    def test_locations_null_exactly_on_margin(self):
        doc = synthetic_doc()
        classes = np.array([list(r) for r in doc["classes"]])
        lat = np.array([[np.nan if v is None else v for v in row] for row in doc["locations"]["lat"]])
        assert np.isnan(lat[classes == "M"]).all() and np.isfinite(lat[classes != "M"]).all()

    def test_corrections_recorded_and_applied(self):
        c = synthetic_candidate()
        r, col = map(int, np.argwhere(c.classes == "L")[0])
        doc = synthetic_doc(corrections=[_corr(r, col, "ocean", "lake")])
        assert doc["classes"][r][col] == "O" and doc["corrections"] == [_corr(r, col, "ocean", "lake")]
        assert doc["counts"]["ocean"] == int((c.classes == "O").sum()) + 1
        parse_template(document.normalise(doc), "winkel-tripel.json")


class TestConfirmation:
    def test_written_only_with_confirmed_on(self):
        doc = synthetic_doc()
        assert document.resolve_confirmation(doc, None, None) is None
        assert document.resolve_confirmation(doc, None, "2026-11-30") == {"role": "project owner",
                                                                          "date": "2026-11-30"}

    def test_kept_when_classes_and_locations_unchanged(self):
        committed = synthetic_doc(confirmation={"role": "project owner", "date": "2026-11-30"})
        new = synthetic_doc(generated_on="2027-01-01")
        assert document.resolve_confirmation(new, committed, None) == {"role": "project owner",
                                                                       "date": "2026-11-30"}

    def test_cleared_when_classes_or_locations_change(self):
        committed = synthetic_doc(confirmation={"role": "project owner", "date": "2026-11-30"})
        c = synthetic_candidate()
        r, col = map(int, np.argwhere(c.classes == "L")[0])
        new = synthetic_doc(corrections=[_corr(r, col, "ocean")])
        assert document.resolve_confirmation(new, committed, None) is None
        moved = synthetic_doc()
        row = next(i for i, x in enumerate(moved["locations"]["lat"][40]) if x is not None)
        moved["locations"]["lat"][40][row] += 0.0001
        assert document.resolve_confirmation(moved, committed, None) is None

    @pytest.mark.parametrize("date", ["2026-13-01", "yesterday", "", "2026-1-1"])
    def test_bad_date(self, date):
        with pytest.raises(ValueError):
            document.confirmation(date)

    def test_exactly_role_and_date(self):
        assert document.confirmation("2026-11-30") == {"role": "project owner", "date": "2026-11-30"}


# --- differences ---------------------------------------------------------------------------

class TestDifferences:
    def test_none_for_equal_documents_and_generated_on_ignored(self):
        a = document.normalise(synthetic_doc())
        b = document.normalise(synthetic_doc(generated_on="2030-01-01"))
        assert document.differences(a, b) == []

    def test_a_class_change_names_its_stud(self):
        a = document.normalise(synthetic_doc())
        b = json.loads(json.dumps(a))
        row = b["classes"][40]
        col = row.index("O")
        b["classes"][40] = row[:col] + "L" + row[col + 1:]
        diffs = document.differences(b, a)
        assert diffs == [f"classes: row 40, column {col} (section {'ABCDEFGH'[col // 16]}3): committed L, "
                         "regenerated O"]

    @pytest.mark.parametrize("path", [("source", "dataset", "sha256"), ("source", "software", "pyproj"),
                                      ("title",), ("projection", "lat_1"), ("disclaimer",),
                                      ("source", "method", "land_rule")])
    def test_every_other_field_is_compared(self, path):
        a = document.normalise(synthetic_doc())
        b = json.loads(json.dumps(a))
        d = b
        for k in path[:-1]:
            d = d[k]
        d[path[-1]] = "changed" if isinstance(d[path[-1]], str) else d[path[-1]] + 1
        diffs = document.differences(b, a)
        assert diffs and any(".".join(path) in x for x in diffs)

    def test_check_points_and_locations_compared(self):
        a = document.normalise(synthetic_doc())
        b = json.loads(json.dumps(a))
        b["projection"]["check_points"][3][2] += 1e-12
        lat_row = b["locations"]["lat"][40]
        col = next(i for i, x in enumerate(lat_row) if x is not None)
        lat_row[col] += 0.0001
        diffs = document.differences(b, a)
        assert any("projection.check_points" in d for d in diffs)
        assert any(d.startswith("locations.lat") and f"row 40, column {col}" in d for d in diffs)


# --- review sheet --------------------------------------------------------------------------

class TestReviewSheet:
    def test_sheet_shows_classes_ring_modules_sections_flags_and_disclaimer(self, tmp_path):
        doc = synthetic_doc()
        classes = np.array([list(r) for r in doc["classes"]], dtype="U1")
        c = synthetic_candidate()
        flags = generate.review_flags(classes, c.land_share)
        land_flag = next(f for f in flags if f["reason"] == generate.FLAG_LAND_SHARE)
        info = review.render_sheet(tmp_path / "s.png", classes, flags=flags, header=["Test sheet"], px=16)
        im = Image.open(info.path).convert("RGB")
        assert im.size == info.size

        def centre(r, col):
            return im.getpixel(review.stud_centre(info, r, col))

        from lego_image_processor.templates.board import rim_cells
        ring = rim_cells(classes != "M")
        flagged = {(f["row"], f["col"]) for f in flags}
        rows = np.arange(80)[:, None] % 16 != 0      # section names sit in each module's first row
        free = rows & ~np.isin(np.arange(128 * 80).reshape(80, 128), [r * 128 + c for r, c in flagged])

        def pick(mask):
            cells = np.argwhere(mask & free)
            return tuple(map(int, cells[len(cells) // 2]))

        L, O = pick(classes == "L"), pick(classes == "O")
        M, R = pick((classes == "M") & ~ring), pick(ring)
        assert centre(*L) == review.COLORS["land"] and centre(*O) == review.COLORS["ocean"]
        assert centre(*M) == review.COLORS["margin"] and centre(*R) == review.COLORS["ring"]
        x0, y0 = info.origin
        assert im.getpixel((x0 + 16 * 16, y0 + 8 * 16 + 1)) == review.COLORS["module"]  # module line
        # a flagged stud carries its marker at the edge of its box
        bx, by = x0 + land_flag["col"] * 16, y0 + land_flag["row"] * 16
        assert im.getpixel((bx + 8, by)) == review.COLORS["flag_land_share"]
        assert info.section_labels == [f"{c}{r}" for r in range(1, 6) for c in "ABCDEFGH"]
        assert info.text[-1] == DISCLAIMER
        assert "Test sheet" in info.text

    def test_unconnected_water_is_filled_and_marked(self, tmp_path):
        classes = np.full((80, 128), "O", dtype="U1")
        classes[10:13, 10:13] = "L"
        classes[11, 11] = "O"
        flags = generate.review_flags(classes)
        assert [(f["row"], f["col"]) for f in flags] == [(11, 11)]
        info = review.render_sheet(tmp_path / "w.png", classes, flags=flags, px=16)
        im = Image.open(info.path).convert("RGB")
        assert im.getpixel(review.stud_centre(info, 11, 11)) == review.COLORS["inland_water"]
        assert im.getpixel(review.stud_centre(info, 20, 20)) == review.COLORS["ocean"]


# --- the commands --------------------------------------------------------------------------

@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def package_dir(tmp_path, monkeypatch):
    """The package template directory pointed at an empty folder, and regeneration from the
    synthetic layout (no pyproj, no dataset)."""
    d = tmp_path / "package-templates"
    d.mkdir()
    monkeypatch.setattr(generate, "regenerate", lambda spec, dataset_path=None, cache_dir=None:
                        synthetic_regenerated())
    with testing.use_template_dir(d):
        yield d


def _last(output):
    return output.rstrip("\n").splitlines()[-1]


class TestCommands:
    def test_write_then_build_check(self, runner, package_dir):
        r = runner.invoke(main, ["write", "winkel-tripel"])
        assert r.exit_code == 0, r.output
        assert _last(r.output) == DISCLAIMER
        path = package_dir / "winkel-tripel.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        assert doc["confirmation"] is None and doc["corrections"] == []
        assert path.read_text(encoding="utf-8") == document.to_text(doc)
        r = runner.invoke(main, ["build", "winkel-tripel", "--check"])
        assert r.exit_code == 0, r.output
        assert "no differences" in r.output and _last(r.output) == DISCLAIMER

    def test_build_check_names_a_changed_stud(self, runner, package_dir):
        assert runner.invoke(main, ["write", "winkel-tripel"]).exit_code == 0
        path = package_dir / "winkel-tripel.json"
        text = path.read_text(encoding="utf-8")
        doc = json.loads(text)
        row = doc["classes"][33]
        col = row.index("L")
        changed = text.replace(json.dumps(row), json.dumps(row[:col] + "O" + row[col + 1:]), 1)
        assert changed != text
        path.write_text(changed, encoding="utf-8")
        r = runner.invoke(main, ["build", "winkel-tripel", "--check"])
        assert r.exit_code == 1
        assert f"row 33, column {col}" in r.output and _last(r.output) == DISCLAIMER
        path.write_text(text, encoding="utf-8")
        assert runner.invoke(main, ["build", "winkel-tripel", "--check"]).exit_code == 0

    def test_build_check_without_a_committed_file(self, runner, package_dir):
        r = runner.invoke(main, ["build", "winkel-tripel", "--check"])
        assert r.exit_code == 1 and "does not exist" in r.output

    def test_build_needs_check(self, runner, package_dir):
        r = runner.invoke(main, ["build", "winkel-tripel"])
        assert r.exit_code == 2

    def test_unknown_template_id(self, runner, package_dir):
        r = runner.invoke(main, ["write", "mollweide"])
        assert r.exit_code == 2 and "winkel-tripel" in r.output

    def test_confirmation_lifecycle(self, runner, package_dir, tmp_path):
        path = package_dir / "winkel-tripel.json"
        r = runner.invoke(main, ["write", "winkel-tripel", "--confirmed-on", "2026-11-30"])
        assert r.exit_code == 0, r.output
        assert json.loads(path.read_text())["confirmation"] == {"role": "project owner", "date": "2026-11-30"}
        assert runner.invoke(main, ["write", "winkel-tripel"]).exit_code == 0          # kept
        assert json.loads(path.read_text())["confirmation"] == {"role": "project owner", "date": "2026-11-30"}
        c = synthetic_candidate()
        r_, col = map(int, np.argwhere(c.classes == "L")[0])
        corr = tmp_path / "corrections.json"
        corr.write_text(json.dumps([_corr(r_, col, "ocean", "owner: a lake")]), encoding="utf-8")
        r = runner.invoke(main, ["write", "winkel-tripel", "--corrections", str(corr)])
        assert r.exit_code == 0, r.output
        doc = json.loads(path.read_text())
        assert doc["confirmation"] is None and doc["corrections"] == [_corr(r_, col, "ocean", "owner: a lake")]
        assert "confirmation cleared" in r.output
        # later writes keep the committed corrections; build --check applies them
        assert runner.invoke(main, ["write", "winkel-tripel", "--confirmed-on", "2026-12-01"]).exit_code == 0
        doc = json.loads(path.read_text())
        assert doc["corrections"] and doc["confirmation"]["date"] == "2026-12-01"
        assert runner.invoke(main, ["build", "winkel-tripel", "--check"]).exit_code == 0

    def test_write_rejects_a_bad_correction(self, runner, package_dir, tmp_path):
        corr = tmp_path / "corrections.json"
        corr.write_text(json.dumps([_corr(0, 0, "land")]), encoding="utf-8")
        r = runner.invoke(main, ["write", "winkel-tripel", "--corrections", str(corr)])
        assert r.exit_code == 1 and "correction 1" in r.output
        assert not (package_dir / "winkel-tripel.json").exists()

    def test_write_rejects_a_bad_date(self, runner, package_dir):
        r = runner.invoke(main, ["write", "winkel-tripel", "--confirmed-on", "30/11/2026"])
        assert r.exit_code == 2

    def test_generate_writes_candidate_sheet_and_flags(self, runner, package_dir, tmp_path):
        out = tmp_path / "out"
        r = runner.invoke(main, ["generate", "winkel-tripel", "--out", str(out)])
        assert r.exit_code == 0, r.output
        assert _last(r.output) == DISCLAIMER
        cand = out / "winkel-tripel.json"
        sheet = out / "winkel-tripel.review.png"
        flags = out / "winkel-tripel.flags.json"
        assert cand.is_file() and sheet.is_file() and flags.is_file()
        t = parse_template(json.loads(cand.read_text()), cand.name)
        assert t.status == "unconfirmed" and not t.corrections
        fl = json.loads(flags.read_text())
        assert fl["template_id"] == "winkel-tripel" and fl["of"] == "candidate"
        assert fl["counts"][generate.FLAG_LAND_SHARE] > 0
        assert f"{t.counts['land']:,} land" in r.output
        assert not (package_dir / "winkel-tripel.json").exists()     # never the package file

    def test_generate_default_out_is_the_cache(self, runner, package_dir, tmp_path):
        r = runner.invoke(main, ["generate", "winkel-tripel", "--cache-dir", str(tmp_path / "cache")])
        assert r.exit_code == 0, r.output
        assert (tmp_path / "cache" / "templates" / "winkel-tripel.review.png").is_file()

    def test_review_of_the_committed_file(self, runner, package_dir, tmp_path):
        c = synthetic_candidate()
        r_, col = map(int, np.argwhere(c.classes == "L")[0])
        corr = tmp_path / "corrections.json"
        corr.write_text(json.dumps([_corr(r_, col, "ocean", "a lake")]), encoding="utf-8")
        assert runner.invoke(main, ["write", "winkel-tripel", "--corrections", str(corr)]).exit_code == 0
        out = tmp_path / "rev"
        r = runner.invoke(main, ["review", "winkel-tripel", "--out", str(out)])
        assert r.exit_code == 0, r.output
        assert (out / "winkel-tripel.committed-review.png").is_file()
        fl = json.loads((out / "winkel-tripel.committed-flags.json").read_text())
        assert fl["of"] == "committed file" and fl["corrections"] == 1
        assert _last(r.output) == DISCLAIMER


class TestDatasetExitCodes:
    """Exit 4 when the pinned dataset is missing or its checksum differs (needs no pyproj)."""

    @pytest.mark.parametrize("command", ["generate", "write", "build"])
    def test_missing_dataset(self, runner, tmp_path, command):
        args = [command, "winkel-tripel", "--cache-dir", str(tmp_path / "empty")]
        (tmp_path / "winkel-tripel.json").write_text("{}", encoding="utf-8")   # build needs a committed file
        with testing.use_template_dir(tmp_path):
            r = runner.invoke(main, args + (["--check"] if command == "build" else []))
        assert r.exit_code == 4, r.output
        assert "etopo2022-surface-10m" in r.output and _last(r.output) == DISCLAIMER

    def test_checksum_mismatch(self, runner, tmp_path):
        bogus = tmp_path / "etopo.dods"
        bogus.write_bytes(b"not the pinned file")
        r = runner.invoke(main, ["generate", "winkel-tripel", "--dataset", str(bogus), "--out", str(tmp_path)])
        assert r.exit_code == 4, r.output
        assert _last(r.output) == DISCLAIMER


# --- end to end (pyproj and the cached pinned ETOPO 2022 file) -----------------------------

def test_end_to_end_winkel(tmp_path):
    pytest.importorskip("pyproj")
    from lego_image_processor.datasets import cache

    entry = generate.packaged_entry(SPEC.dataset_id)
    if not cache.cached_path(entry).is_file():
        pytest.skip("the pinned ETOPO 2022 file is not cached")
    regen = generate.regenerate(SPEC)
    cand = regen.candidate
    doc = generate.build_document(SPEC, cand, dataset=regen.dataset, software=regen.software,
                                  generated_on="2026-11-23")
    t = parse_template(document.normalise(doc), "winkel-tripel.json")   # loader rules incl. check points
    c = t.counts
    # The outline (margin, ring, modules, corners) depends only on the exact fit (research R2).
    assert (c["margin"], c["ring"]) == (1996, 288)
    assert c["modules"] == {"full": 18, "partial": 22, "empty": 0}
    assert all((b["height"], b["width"]) == (14, 14) for b in c["corners"].values())
    assert abs(c["land"] - 2553) <= 10 and c["land"] + c["ocean"] == 8244
    # Exactly symmetric outline, left-right and top-bottom.
    on = t.on_globe
    assert (on == on[:, ::-1]).all() and (on == on[::-1, :]).all()
    flags = generate.review_flags(cand.classes, cand.land_share)
    water = [f for f in flags if f["reason"] == generate.FLAG_WATER]
    assert max(f["group_size"] for f in water) >= 20                     # the Caspian Sea
    # The committed package file, when present, is reproducible (build --check).
    from lego_image_processor.templates import TEMPLATE_DIR

    package = Path(TEMPLATE_DIR) / "winkel-tripel.json"
    if package.is_file():
        committed = json.loads(package.read_text(encoding="utf-8"))
        again = generate.build_document(SPEC, cand, dataset=regen.dataset, software=regen.software,
                                        generated_on=committed["source"]["generated_on"],
                                        corrections=committed["corrections"],
                                        confirmation=committed["confirmation"])
        assert document.differences(committed, document.normalise(again)) == []
