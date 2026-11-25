"""Web kit golden (feature 016, T009; SC-001, SC-006, research R9).

The session's sites (the small site: official-31203, ocean-sst and ocean-el-nino; the
living-planet site; the rainfall site) are digested with ``kit_golden.site_digests`` and compared
with tests/fixtures/kit_variants_golden.json, written from an unmodified checkout of main (commit
6038d9c; re-based once from af3ce57 on 2026-11-23, when main drew previews as round studs on
black: only the 15 previews and their manifest entries changed). Every kit variant's
timestamp-free files are compared byte for byte; layout and parts lists, manifest entries and the
rendered map pages after normalisation (kit_golden.py).

Feature 016 (T089): the session builds on a confirmed Winkel tripel template (conftest), so the
eligible maps (ocean-sst, living-planet, rainfall) also have a template variant. The comparison
allows exactly what that adds to kit outputs: one "Winkel tripel" nav item on each of their kit
pages (removed before digesting, and required to be there once) and the square tile in the site's
``part_labels``. Kit pages of official-31203 and ocean-el-nino are compared as they are. The golden
file itself is not re-written for this.

To write the golden file, run in a checkout of main with this file and kit_golden.py copied in
(never from feature 016 code): ``KIT_GOLDEN_WRITE=1 .venv/bin/pytest tests/test_kit_golden.py``.
"""

from __future__ import annotations

import json
import os

import pytest

import kit_golden


@pytest.fixture(scope="module")
def sites(site_dir, living_site, rainfall_site):
    return {"small": site_dir, "living-planet": living_site, "rainfall": rainfall_site}


def test_kit_variants_unchanged(sites):
    actual = kit_golden.golden_document(sites)
    if os.environ.get("KIT_GOLDEN_WRITE"):
        kit_golden.GOLDEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        kit_golden.GOLDEN_PATH.write_text(kit_golden.to_text(actual), encoding="utf-8")
        pytest.skip(f"wrote {kit_golden.GOLDEN_PATH}")
    expected = json.loads(kit_golden.GOLDEN_PATH.read_text(encoding="utf-8"))
    diffs = kit_golden.compare(expected, actual)
    assert not diffs, f"{len(diffs)} kit web output(s) differ from the golden:\n" + "\n".join(diffs)


def test_golden_covers_every_kit_variant_and_page():
    doc = json.loads(kit_golden.GOLDEN_PATH.read_text(encoding="utf-8"))
    by_site = {s["site"]: s for s in doc["sites"]}
    assert set(by_site) == {"small", "living-planet", "rainfall"}
    small = by_site["small"]
    assert small["maps"] == ["official-31203", "ocean-sst", "ocean-el-nino"]
    assert small["part_labels"] == {"6141": "plate 1x1 round", "98138": "tile 1x1 round"}
    for s in doc["sites"]:
        assert len(s["variants"]) == 3 * len(s["maps"])
        for v in s["variants"]:
            d = v["digests"]
            assert {"preview.png", "thumb.png", "cells.json", "layout.json (normalised)",
                    "parts.json (normalised)", "parts-1kit.json (normalised)",
                    "manifest entry (normalised)", f"page /maps/{v['map']}/{v['combination']}"} <= set(d)
            assert not any(k.endswith(".pdf") for k in d)   # the CLI golden covers the PDFs
    assert doc["disclaimer"] == "Not affiliated with or endorsed by The LEGO Group."


class TestNormalisation:
    def test_layout_and_parts_lists(self):
        layout = {"metadata": {"generated_at": "2026-11-23T10:00:00Z", "width": 128}, "positions": []}
        other = json.loads(json.dumps(layout))
        other["metadata"]["generated_at"] = "2027-01-01T00:00:00Z"
        a = kit_golden.normalise_file("layout", json.dumps(layout).encode())
        assert a == kit_golden.normalise_file("layout", json.dumps(other, indent=2).encode())
        parts = {"layout": {"path": "layout.json", "sha256": "a" * 64}, "lots": [1]}
        p2 = {"layout": {"path": "layout.json", "sha256": "b" * 64}, "lots": [1]}
        assert kit_golden.normalise_file("parts", json.dumps(parts).encode()) == \
            kit_golden.normalise_file("parts-1kit", json.dumps(p2).encode())
        assert kit_golden.normalise_file("preview", b"\x89PNG") == b"\x89PNG"

    def test_manifest_entry_drops_layout_derived_checksums_only(self):
        entry = {"summary": {"lots": 10},
                 "files": {k: {"path": f"x/{k}", "bytes": 1, "sha256": "s"}
                           for k in ("layout", "parts", "parts-1kit", "sheets-letter", "sheets-a4", "preview")}}
        n = kit_golden.normalise_entry(entry)
        for k in ("layout", "parts", "parts-1kit", "sheets-letter", "sheets-a4"):
            assert n["files"][k] == {"path": f"x/{k}"}
        assert n["files"]["preview"] == {"path": "x/preview", "bytes": 1, "sha256": "s"}
        assert entry["files"]["layout"]["sha256"] == "s"   # the input is not changed

    def test_page_asset_tokens_and_build_line(self):
        html = ('<link href="/static/style.css?v=0.1.0-881ead4ed3"><script src="/static/palette.js?v=0.1.0-881ead4ed3">'
                "Built 2026-11-23 with lego-image-processor 0.1.0 (commit abc1234); <a>")
        other = html.replace("881ead4ed3", "fca1963cfb").replace("2026-11-23", "2027-02-01").replace(
            " (commit abc1234)", "")
        assert kit_golden.normalise_page(html) == kit_golden.normalise_page(other)
        assert "?v=" + kit_golden.ASSET_TOKEN in kit_golden.normalise_page(html)


class TestTemplateAllowance:
    """Feature 016: exactly the Winkel nav item and the square tile label, nothing else."""

    ITEM = ('\n      <li class="combo-template"><a href="/maps/ocean-sst/winkel-tripel"><span class="combo-id">'
            'Winkel tripel</span> <span class="combo-name">curved map</span></a></li>')
    PAGE = '<ul>\n      <li><a href="/maps/ocean-sst/C">C</a></li>\n    {}\n    </ul>'

    def test_strip_removes_exactly_the_item(self):
        page = self.PAGE.format(self.ITEM)
        assert kit_golden.strip_template_nav(page, "ocean-sst", ["winkel-tripel"]) == self.PAGE.format("")
        assert kit_golden.strip_template_nav(self.PAGE.format(""), "ocean-sst", []) == self.PAGE.format("")

    @pytest.mark.parametrize("page, tids", [
        (PAGE.format(""), ["winkel-tripel"]),                       # missing
        (PAGE.format(ITEM + ITEM), ["winkel-tripel"]),              # doubled
        (PAGE.format(ITEM), []),                                    # on a map without the variant
        (PAGE.format(ITEM.replace("ocean-sst", "rainfall")), ["winkel-tripel"]),   # another map's
        (PAGE.format(ITEM.replace("\n      ", "\n")), ["winkel-tripel"]),          # other spacing
    ])
    def test_strip_refuses_anything_else(self, page, tids):
        with pytest.raises(AssertionError):
            kit_golden.strip_template_nav(page, "ocean-sst", tids)

    def test_part_labels_allow_only_the_square_tile_with_template_variants(self):
        kit = {"6141": "plate 1x1 round", "98138": "tile 1x1 round"}

        def doc(labels, templates=None):
            s = {"site": "s", "maps": [], "part_labels": labels, "map_rows": {}, "variants": []}
            if templates:
                s["template_variants"] = templates
            return {"sites": [s]}
        both = {**kit, "3070b": "tile 1x1 square"}
        assert kit_golden.compare(doc(kit), doc(both, {"ocean-sst": ["winkel-tripel"]})) == []
        assert kit_golden.compare(doc(kit), doc(kit)) == []
        assert kit_golden.compare(doc(kit), doc(both))                       # no template variant
        assert kit_golden.compare(doc(kit), doc(kit, {"ocean-sst": ["winkel-tripel"]}))
        assert kit_golden.compare(doc(kit), doc({**both, "x": "y"}, {"ocean-sst": ["winkel-tripel"]}))
