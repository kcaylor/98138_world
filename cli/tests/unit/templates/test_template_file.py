"""Template file loader rules (feature 016, T026; contracts/template-file.md).

Each broken rule raises ``TemplateError`` (a ``ValueError``) naming the file and the rule. The
documents start from the committed synthetic fixture (tests/fixtures/templates, T025).
"""

import copy
import json
from pathlib import Path

import pytest

from lego_image_processor.templates import (KIT_TEMPLATE_ID, Template, TemplateDataset, TemplateError,
                                            confirmed_templates, list_templates, load_template,
                                            load_template_file)
from lego_image_processor.templates.digest import layout_sha256
from maptemplates.testing import use_template_dir

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "templates" / "winkel-tripel.json"
DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."


@pytest.fixture
def doc():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _write(tmp_path, doc, name="winkel-tripel"):
    p = tmp_path / f"{name}.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    return p


def _broken(tmp_path, doc, rule, name="winkel-tripel"):
    p = _write(tmp_path, doc, name)
    with pytest.raises(TemplateError) as ei:
        load_template_file(p)
    e = ei.value
    assert isinstance(e, ValueError)
    assert e.file == p.name and e.rule == rule, str(e)
    assert str(e).startswith(f"{p.name}: {rule}: "), str(e)
    return e


def _first(doc, cls):
    for r, row in enumerate(doc["classes"]):
        if cls in row:
            return r, row.index(cls)
    raise AssertionError(cls)


# --- the fixture loads ------------------------------------------------------------------------

def test_fixture_loads(tmp_path, doc):
    t = load_template_file(_write(tmp_path, doc))
    assert isinstance(t, Template)
    assert t.id == "winkel-tripel" and not t.is_kit
    assert t.status == "confirmed" and t.buildable
    assert t.width == 128 and t.height == 80
    assert t.parts == {"land": "6141", "ocean": "98138", "margin": "3070b"}
    assert t.arrangements == ("A",)
    assert t.counts == doc["counts"]
    assert t.confirmation.role == "project owner" and t.confirmation.date == "2026-11-23"
    assert len(t.corrections) == 1 and t.corrections[0].class_ == doc["corrections"][0]["class"]
    assert t.corrections[0].to_dict() == doc["corrections"][0]
    assert t.disclaimer == DISCLAIMER
    assert t.path == tmp_path / "winkel-tripel.json"
    assert len(t.file_sha256) == 64


def test_loader_derives_the_layout_digest(tmp_path, doc):
    t = load_template_file(_write(tmp_path, doc))
    assert t.layout_sha256 == layout_sha256(doc)


def test_loader_derives_the_dataset_from_the_registry(tmp_path, doc):
    from lego_image_processor.datasets import get_entry

    t = load_template_file(_write(tmp_path, doc))
    e = get_entry("etopo2022-surface-10m")
    assert isinstance(t.dataset, TemplateDataset)
    assert t.dataset.to_dict() == {"id": e.id, "version": e.version, "title": e.title, "publisher": e.publisher,
                                   "license": e.license, "citation": e.citation, "doi": e.doi}


def test_dataset_check_uses_the_packaged_registry(tmp_path, doc, fixture_registry):
    # The test fixture registry points ETOPO at a small fixture with another SHA-256; the template's
    # provenance is the pinned dataset, so the packaged registry decides.
    from lego_image_processor.datasets import get_entry

    assert get_entry("etopo2022-surface-10m").sha256 != doc["source"]["dataset"]["sha256"]
    t = load_template_file(_write(tmp_path, doc))
    assert t.dataset.version == doc["source"]["dataset"]["version"]


def test_unconfirmed_template_loads_but_is_not_confirmed(tmp_path, doc):
    doc["confirmation"] = None
    _write(tmp_path, doc)
    with use_template_dir(tmp_path):
        t = load_template("winkel-tripel")
        assert t.status == "unconfirmed" and not t.buildable and t.confirmation is None
        assert [x.id for x in list_templates()] == [KIT_TEMPLATE_ID, "winkel-tripel"]
        assert [x.id for x in confirmed_templates()] == [KIT_TEMPLATE_ID]


def test_confirmed_template_is_listed_as_confirmed(tmp_path, doc):
    _write(tmp_path, doc)
    with use_template_dir(tmp_path):
        assert [x.id for x in confirmed_templates()] == [KIT_TEMPLATE_ID, "winkel-tripel"]
        assert [x.status for x in list_templates()] == ["reference", "confirmed"]


def test_listing_skips_ice_and_source_files(tmp_path, doc):
    _write(tmp_path, doc)
    (tmp_path / "winkel-tripel-ice.json").write_text("{}", encoding="utf-8")
    (tmp_path / "winkel-tripel.source.json").write_text("{}", encoding="utf-8")
    with use_template_dir(tmp_path):
        assert [x.id for x in list_templates()] == [KIT_TEMPLATE_ID, "winkel-tripel"]


def test_missing_template_dir_lists_the_kit_only(tmp_path):
    with use_template_dir(tmp_path / "none"):
        assert [x.id for x in list_templates()] == [KIT_TEMPLATE_ID]


def test_unknown_template(tmp_path):
    with use_template_dir(tmp_path):
        for bad in ("nope", "../winkel-tripel", "Winkel"):
            with pytest.raises(TemplateError) as ei:
                load_template(bad)
            assert "unknown template" in str(ei.value) and KIT_TEMPLATE_ID in str(ei.value)


def test_cached_load_is_fast(tmp_path, doc):
    import time

    _write(tmp_path, doc)
    with use_template_dir(tmp_path):
        first = load_template("winkel-tripel")
        t0 = time.perf_counter()
        again = load_template("winkel-tripel")
        assert time.perf_counter() - t0 < 0.1
        assert again is first


def test_rewritten_file_is_reloaded(tmp_path, doc):
    p = _write(tmp_path, doc)
    first = load_template_file(p)
    doc["title"] = "Another title"
    p.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    assert load_template_file(p).title == "Another title" != first.title


def test_arrays_are_read_only(tmp_path, doc):
    t = load_template_file(_write(tmp_path, doc))
    with pytest.raises(ValueError):
        t.land[0, 0] = True


# --- one test per rule --------------------------------------------------------------------------

def test_not_json(tmp_path):
    p = tmp_path / "winkel-tripel.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(TemplateError) as ei:
        load_template_file(p)
    assert ei.value.file == "winkel-tripel.json" and ei.value.rule == "json"


def test_format_version(tmp_path, doc):
    doc["format_version"] = "2"
    _broken(tmp_path, doc, "format_version")


@pytest.mark.parametrize("name,ident", [
    ("other-name", "winkel-tripel"),          # id differs from the file stem
    ("Winkel_Tripel", "Winkel_Tripel"),        # pattern
    ("w", "w"),                                # too short
    (KIT_TEMPLATE_ID, KIT_TEMPLATE_ID),        # the kit is built in code
    ("winkel-tripel-ice", "winkel-tripel-ice"),  # reserved for ice files
])
def test_id(tmp_path, doc, name, ident):
    doc["id"] = ident
    _broken(tmp_path, doc, "id", name=name)


@pytest.mark.parametrize("key", ["title", "description"])
def test_title_and_description(tmp_path, doc, key):
    doc[key] = "  "
    _broken(tmp_path, doc, key)


def test_projection_name(tmp_path, doc):
    doc["projection"]["name"] = "robinson"
    _broken(tmp_path, doc, "projection.name")


def test_projection_proj_string(tmp_path, doc):
    doc["projection"]["proj"] = "+proj=wintri +lat_1=50.4598 +lon_0=0 +R=1"
    _broken(tmp_path, doc, "projection.proj")


@pytest.mark.parametrize("key,value", [("lat_1", "50"), ("lon_0", None), ("citation", "")])
def test_projection_parameters(tmp_path, doc, key, value):
    doc["projection"][key] = value
    _broken(tmp_path, doc, f"projection.{key}")


@pytest.mark.parametrize("change", [
    lambda f: f.update(mode="cover"),
    lambda f: f.update(scale=f["scale"] * 1.001),
    lambda f: f.update(extent=[f["extent"][0], f["extent"][1], -1.5, 1.5]),
    lambda f: f.update(centre=[0.01, 0.0]),
    lambda f: f.pop("scale"),
])
def test_projection_fit(tmp_path, doc, change):
    change(doc["projection"]["fit"])
    _broken(tmp_path, doc, "projection.fit")


@pytest.mark.parametrize("change", [
    lambda pts: pts[5].__setitem__(2, pts[5][2] + 2e-9),   # x off by more than 1e-9
    lambda pts: pts[7].__setitem__(3, pts[7][3] - 5e-9),   # y
    lambda pts: pts.pop(),                                   # 23 points
    lambda pts: pts[0].pop(),                                # a point of 3 numbers
])
def test_check_points(tmp_path, doc, change):
    change(doc["projection"]["check_points"])
    _broken(tmp_path, doc, "projection.check_points")


def test_check_points_within_tolerance_pass(tmp_path, doc):
    doc["projection"]["check_points"][3][2] += 5e-10
    load_template_file(_write(tmp_path, doc))


@pytest.mark.parametrize("board", [
    {"modules": [8, 4], "module": 16, "width": 128, "height": 64, "pitch_mm": 8.0},   # 128 x 80 for now
    {"modules": [8, 5], "module": 16, "width": 120, "height": 80, "pitch_mm": 8.0},   # not whole modules
    {"modules": [8, 5], "module": 12, "width": 96, "height": 60, "pitch_mm": 8.0},
    {"modules": [8, 5], "module": 16, "width": 128, "height": 80, "pitch_mm": 7.8},
    {"modules": [8, 5], "module": 16, "width": 128, "height": 80},
])
def test_board(tmp_path, doc, board):
    doc["board"] = board
    _broken(tmp_path, doc, "board")


@pytest.mark.parametrize("parts", [
    {"land": "6141", "ocean": "98138", "margin": "3070"},
    {"land": "6141", "ocean": "98138"},
    {"land": "6141", "ocean": "98138", "margin": "3070b", "label": "3068"},
    {"land": "98138", "ocean": "6141", "margin": "3070b"},
])
def test_parts(tmp_path, doc, parts):
    doc["parts"] = parts
    _broken(tmp_path, doc, "parts")


@pytest.mark.parametrize("frame", [
    {"kit": "31203", "arrangements": ["A", "B", "C"], "source": "kit_31203_arrangements.json"},
    {"kit": "10000", "arrangements": ["A"], "source": "kit_31203_arrangements.json"},
    {"kit": "31203", "arrangements": ["A"]},
])
def test_frame(tmp_path, doc, frame):
    doc["frame"] = frame
    _broken(tmp_path, doc, "frame")


@pytest.mark.parametrize("change", [
    lambda c: c.pop(),                                # 79 rows
    lambda c: c.__setitem__(3, c[3][:-1]),            # a row of 127
    lambda c: c.__setitem__(40, "X" + c[40][1:]),     # a class that is not L, O or M
    lambda c: c.__setitem__(40, list(c[40])),         # not a string
])
def test_classes(tmp_path, doc, change):
    change(doc["classes"])
    _broken(tmp_path, doc, "classes")


def test_location_missing_on_land(tmp_path, doc):
    r, c = _first(doc, "L")
    doc["locations"]["lat"][r][c] = None
    _broken(tmp_path, doc, "locations")


def test_location_on_margin(tmp_path, doc):
    r, c = _first(doc, "M")
    doc["locations"]["lat"][r][c] = 10.0
    doc["locations"]["lon"][r][c] = 10.0
    _broken(tmp_path, doc, "locations")


@pytest.mark.parametrize("axis,value", [("lon", 180.5), ("lon", -181.0), ("lat", 90.01), ("lat", "1")])
def test_location_ranges(tmp_path, doc, axis, value):
    r, c = _first(doc, "O")
    doc["locations"][axis][r][c] = value
    _broken(tmp_path, doc, "locations")


def test_location_shape(tmp_path, doc):
    doc["locations"]["lon"][10] = doc["locations"]["lon"][10][:-1]
    _broken(tmp_path, doc, "locations")


def test_class_change_without_location_change_breaks_the_location_rule(tmp_path, doc):
    r, c = _first(doc, "O")
    doc["classes"][r] = doc["classes"][r][:c] + "M" + doc["classes"][r][c + 1:]
    _broken(tmp_path, doc, "locations")


@pytest.mark.parametrize("change", [
    lambda n: n.update(land=n["land"] + 1),
    lambda n: n.update(ring=n["ring"] - 1),
    lambda n: n["modules"].update(full=19),
    lambda n: n["corners"]["top-left"].update(width=13),
    lambda n: n.pop("margin"),
])
def test_counts(tmp_path, doc, change):
    change(doc["counts"])
    _broken(tmp_path, doc, "counts")


@pytest.mark.parametrize("change,rule", [
    (lambda d: d.update(generator="someone else"), "source.generator"),
    (lambda d: d.update(generated_on="23 Nov 2026"), "source.generated_on"),
    (lambda d: d.pop("method"), "source.method"),
    (lambda d: d["method"].pop("land_rule"), "source.method"),
    (lambda d: d.pop("software"), "source.software"),
    (lambda d: d["software"].update(proj=3), "source.software"),
])
def test_source_fields(tmp_path, doc, change, rule):
    change(doc["source"])
    _broken(tmp_path, doc, rule)


@pytest.mark.parametrize("key,value", [
    ("version", "2022-v2"), ("sha256", "0" * 64), ("citation", "another citation"), ("license", "CC-BY"),
    ("id", "etopo-unknown"),
])
def test_source_dataset_must_match_the_registry(tmp_path, doc, key, value):
    doc["source"]["dataset"][key] = value
    _broken(tmp_path, doc, "source.dataset")


def test_source_dataset_missing(tmp_path, doc):
    del doc["source"]["dataset"]
    _broken(tmp_path, doc, "source.dataset")


def test_source_disclaimer(tmp_path, doc):
    doc["source"]["disclaimer"] = ""
    _broken(tmp_path, doc, "source.disclaimer")


def test_disclaimer(tmp_path, doc):
    del doc["disclaimer"]
    _broken(tmp_path, doc, "disclaimer")


@pytest.mark.parametrize("change", [
    lambda c: c[0].pop("reason"),
    lambda c: c[0].update(reason=" "),
    lambda c: c[0].update(**{"class": "sea"}),
    lambda c: c[0].update(row=80),
    lambda c: c[0].update(col=-1),
    lambda c: c[0].update(extra=1),
    lambda c: c.append("land at 3, 4"),
])
def test_correction_shapes(tmp_path, doc, change):
    change(doc["corrections"])
    _broken(tmp_path, doc, "corrections")


def test_correction_must_match_the_classes(tmp_path, doc):
    corr = doc["corrections"][0]
    corr["class"] = "land" if corr["class"] != "land" else "ocean"
    _broken(tmp_path, doc, "corrections")


def test_corrections_must_be_a_list(tmp_path, doc):
    doc["corrections"] = None
    _broken(tmp_path, doc, "corrections")


@pytest.mark.parametrize("confirmation", [
    {"role": "owner", "date": "2026-11-23"},
    {"role": "project owner", "date": "2026-11-23", "name": "someone"},
    {"role": "project owner", "date": "Nov 23"},
    {"role": "project owner"},
    "yes",
])
def test_confirmation_shapes(tmp_path, doc, confirmation):
    doc["confirmation"] = confirmation
    _broken(tmp_path, doc, "confirmation")


def test_confirmation_key_required(tmp_path, doc):
    del doc["confirmation"]
    _broken(tmp_path, doc, "confirmation")


def test_documents_are_not_changed_by_loading(tmp_path, doc):
    before = copy.deepcopy(doc)
    load_template_file(_write(tmp_path, doc))
    assert doc == before
