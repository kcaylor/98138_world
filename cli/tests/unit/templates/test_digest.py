"""Template layout digest (feature 016; contracts/template-file.md "Layout digest";
data-model.md TemplateLayoutDigest.layout_sha256)."""

import copy
import hashlib
import json

import pytest

from lego_image_processor.templates.digest import layout_sha256


def _doc():
    """A small template-shaped document; the digest does not validate it."""
    return {
        "format_version": "1",
        "id": "winkel-tripel",
        "title": "Winkel tripel",
        "description": "A test document.",
        "projection": {
            "name": "winkel-tripel",
            "proj": "+proj=wintri +lat_1=50.4598 +lon_0=11.1 +R=1",
            "lat_1": 50.4598,
            "lon_0": 11.1,
            "citation": "Winkel (1921); Snyder (1993)",
            "fit": {"mode": "contain", "extent": [-2.5, 2.5, -1.5, 1.5], "scale": 24.9, "centre": [0.0, 0.0]},
            "check_points": [[11.1, 0.0, 0.0, 0.0]],
        },
        "board": {"modules": [8, 5], "module": 16, "width": 128, "height": 80, "pitch_mm": 8.0},
        "parts": {"land": "6141", "ocean": "98138", "margin": "3070b"},
        "frame": {"kit": "31203", "arrangements": ["A"], "source": "kit_31203_arrangements.json"},
        "classes": ["MLO", "OOL"],
        "locations": {"lat": [[None, 10.5, -3.25], [1.0, 2.0, 3.0]],
                      "lon": [[None, 20.0, 30.0], [-1.0, -2.0, -3.0]]},
        "counts": {"land": 2, "ocean": 3, "margin": 1},
        "source": {"generator": "cli/tools/maptemplates", "generated_on": "2026-11-23",
                   "disclaimer": "Not affiliated with or endorsed by The LEGO Group."},
        "corrections": [],
        "confirmation": None,
        "disclaimer": "Not affiliated with or endorsed by The LEGO Group.",
    }


def test_digest_is_sha256_of_canonical_layout_json():
    doc = _doc()
    p = doc["projection"]
    layout = {"id": doc["id"], "board": doc["board"], "parts": doc["parts"],
              "projection": {"name": p["name"], "proj": p["proj"], "lat_1": p["lat_1"],
                             "lon_0": p["lon_0"], "fit": p["fit"]},
              "classes": doc["classes"], "locations": doc["locations"]}
    text = json.dumps(layout, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert layout_sha256(doc) == hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_digest_is_hex_and_stable():
    a, b = layout_sha256(_doc()), layout_sha256(_doc())
    assert a == b and len(a) == 64 and int(a, 16) >= 0


@pytest.mark.parametrize("change", [
    lambda d: d.update(confirmation={"role": "project owner", "date": "2026-11-23"}),
    lambda d: d["corrections"].append({"row": 0, "col": 1, "class": "land", "reason": "test"}),
    lambda d: d.update(title="Another title"),
    lambda d: d.update(description="Another description."),
    lambda d: d["source"].update(generated_on="2027-01-01", generator="x"),
    lambda d: d.update(source={}),
    lambda d: d["projection"].update(check_points=[]),
    lambda d: d["projection"].update(citation="another citation"),
    lambda d: d.update(counts={"land": 99}),
    lambda d: d.update(disclaimer="changed"),
    lambda d: d.update(format_version="2"),
    lambda d: d.update(frame={"kit": "31203", "arrangements": ["A", "B"], "source": "x"}),
], ids=["confirmation", "corrections", "title", "description", "source-fields", "source", "check_points",
        "citation", "counts", "disclaimer", "format_version", "frame"])
def test_digest_ignores_fields_outside_the_layout(change):
    doc = _doc()
    before = layout_sha256(doc)
    change(doc)
    assert layout_sha256(doc) == before


@pytest.mark.parametrize("change", [
    lambda d: d.update(classes=["MLL", "OOL"]),
    lambda d: d["locations"]["lat"][0].__setitem__(1, 10.5001),
    lambda d: d["locations"]["lon"][1].__setitem__(2, -3.0001),
    lambda d: d["projection"]["fit"].update(scale=25.0),
    lambda d: d["projection"]["fit"].update(extent=[-2.5, 2.5, -1.5, 1.6]),
    lambda d: d.update(board={"modules": [8, 4], "module": 16, "width": 128, "height": 64, "pitch_mm": 8.0}),
    lambda d: d.update(parts={"land": "6141", "ocean": "98138", "margin": "3070"}),
    lambda d: d.update(id="another-template"),
    lambda d: d["projection"].update(lon_0=-150.0),
    lambda d: d["projection"].update(lat_1=40.0),
    lambda d: d["projection"].update(proj="+proj=wintri +R=1"),
    lambda d: d["projection"].update(name="other"),
], ids=["class", "lat", "lon", "fit-scale", "fit-extent", "board", "parts", "id", "lon_0", "lat_1", "proj",
        "name"])
def test_digest_changes_with_the_layout(change):
    doc = _doc()
    before = layout_sha256(doc)
    change(doc)
    assert layout_sha256(doc) != before


def test_digest_does_not_modify_the_document():
    doc = _doc()
    snapshot = copy.deepcopy(doc)
    layout_sha256(doc)
    assert doc == snapshot


def test_digest_reads_tuples_like_lists():
    doc = _doc()
    tupled = copy.deepcopy(doc)
    tupled["classes"] = tuple(tupled["classes"])
    assert layout_sha256(tupled) == layout_sha256(doc)
