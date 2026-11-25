"""Map stickers in the build step (feature 017, US2): one sticker set per map, written with the
CLI library, listed in the manifest (FR-018, SC-008; contracts/web.md; research R12).

Built offline from the CLI's dataset fixtures (the session, living-planet and rainfall sites).
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from conftest import PRICES, TODAY

KIT = "kit-31203"
DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."
STICKER_FILES = {
    "stickers-letter": ("stickers-letter.pdf", "application/pdf",
                        "Sticker print sheet, US Letter: both stickers at true size"),
    "stickers-a4": ("stickers-a4.pdf", "application/pdf",
                    "Sticker print sheet, A4: both stickers at true size"),
    "sticker-small": ("sticker-small.svg", "image/svg+xml", "Small sticker (SVG, 45.8 x 45.8 mm)"),
    "sticker-large": ("sticker-large.svg", "image/svg+xml", "Large sticker (SVG, 125.8 x 61.8 mm)"),
}
NOTES = {"printed": "The sticker is printed, not a LEGO part.",
         "colors": "Printed colors only approximate the LEGO colors."}
SET_LIMIT = 150_000          # bytes per map's four files: 13 sets stay under 2 MB (SC-008)


@pytest.fixture(params=["site_dir", "living_site", "rainfall_site"])
def site(request):
    out = request.getfixturevalue(request.param)
    return out, json.loads((out / "manifest.json").read_text(encoding="utf-8"))


def _library_set(map_id, combination, cache_dir):
    from lego_image_processor.layout.arrangement import parse_arrangement
    from lego_image_processor.maps.build import build_map
    from lego_image_processor.maps.recipe import load_recipe
    from lego_image_processor.stickers import sticker_set

    recipe = load_recipe(map_id)
    result = build_map(recipe, cache_dir=cache_dir, compare_official=False,
                       arrangement=parse_arrangement(combination))
    return recipe, sticker_set(result)


def test_one_sticker_set_per_map(site):
    """US2-1: four files under maps/<map>/stickers/kit-31203/, never per combination."""
    out, manifest = site
    for m in manifest["maps"]:
        assert list(m["stickers"]) == [KIT], m["id"]
        block = m["stickers"][KIT]
        assert list(block["files"]) == list(STICKER_FILES)
        for kind, f in block["files"].items():
            name, media, desc = STICKER_FILES[kind]
            ext = name.rsplit(".", 1)[1]
            assert f["path"] == f"maps/{m['id']}/stickers/{KIT}/{name}"
            data = (out / f["path"]).read_bytes()
            assert f["bytes"] == len(data) and f["sha256"] == hashlib.sha256(data).hexdigest()
            assert f["media_type"] == media and f["description"] == desc
            assert f["filename"] == f"98138-world_{m['id']}_{kind}.{ext}"
            assert set(f) == {"path", "bytes", "sha256", "media_type", "description", "filename"}
        assert sorted(p.name for p in (out / "maps" / m["id"] / "stickers" / KIT).iterdir()) == \
            sorted(n for n, _, _ in STICKER_FILES.values())
        for c, v in m["variants"].items():
            assert "stickers" not in v and not (set(v["files"]) & set(STICKER_FILES)), (m["id"], c)
            assert not (out / "maps" / m["id"] / c / "stickers").exists()


def test_block_matches_the_library_set(site, fixture_datasets):
    """title, line, alt, legend, credit, plaques and notes come from the library's set in the
    recipe's default combination."""
    from lego_image_processor.kit.plaque_parts import load_plaque_parts
    from lego_image_processor.stickers.credits import credit_lines

    plaques = load_plaque_parts().plaques
    _, manifest = site
    for m in manifest["maps"]:
        block = m["stickers"][KIT]
        recipe, s = _library_set(m["id"], m["default_combination"], fixture_datasets)
        t, line = s.text.title, s.text.line
        assert block["title"] == t and block["line"] == line
        assert block["alt"] == {"small": f"Small sticker: {t}. {line}",
                                "large": f"Large sticker: {t}. {line}"}
        assert block["legend"] == [{"label": sw.label, "color": sw.lego_name, "part": sw.part_id}
                                   for sw in s.legend]
        assert block["legend"] and all(row["label"] and row["color"] for row in block["legend"])
        assert block["credit"] == list(credit_lines(recipe, s.credits))
        d = s.to_dict()
        by_size = {p["size"]: p for p in d["plaques"]}
        assert block["plaques"] == [by_size["large"], by_size["small"]]
        assert block["plaques"][0]["sticker_mm"] == [125.8, 61.8]
        for entry, size in zip(block["plaques"], ("large", "small")):
            assert [p["part_id"] for p in entry["parts"]] == [
                plaques[size].tile.part_id, plaques[size].plate.part_id]
        assert block["notes"] == NOTES == d["notes"]
        assert list(block) == ["files", "title", "line", "alt", "legend", "credit", "plaques",
                               "notes"]


def test_files_are_the_library_render(site, fixture_datasets):
    """The files equal render_sticker_pdf / render_sticker_svgs of the default combination's set
    (A, or B for ocean-el-nino)."""
    from pypdf import PdfReader

    from lego_image_processor.stickers import render_sticker_pdf, render_sticker_svgs

    out, manifest = site
    for m in manifest["maps"]:
        files = m["stickers"][KIT]["files"]
        _, s = _library_set(m["id"], m["default_combination"], fixture_datasets)
        assert (out / files["stickers-letter"]["path"]).read_bytes() == render_sticker_pdf(s, "letter")
        assert (out / files["stickers-a4"]["path"]).read_bytes() == render_sticker_pdf(s, "a4")
        svgs = dict(render_sticker_svgs(s))
        for kind in ("sticker-small", "sticker-large"):
            assert (out / files[kind]["path"]).read_text(encoding="utf-8") == svgs[f"{kind}.svg"]
            assert DISCLAIMER in svgs[f"{kind}.svg"]
        pdf = PdfReader(io.BytesIO((out / files["stickers-letter"]["path"]).read_bytes()))
        text = " ".join(pdf.pages[0].extract_text().split())
        assert len(pdf.pages) == 1 and DISCLAIMER in text
        assert f"hung as {m['default_combination']}" in text


def test_el_nino_set_from_its_own_combination(manifest):
    nino = next(m for m in manifest["maps"] if m["id"] == "ocean-el-nino")
    assert nino["default_combination"] == "B" and KIT in nino["stickers"]


def test_total_bytes_counts_the_stickers(site):
    """total_bytes is the site's size, sticker files included; each set is small (SC-008)."""
    _, manifest = site
    variants = sum(f["bytes"] for m in manifest["maps"] for v in m["variants"].values()
                   for f in v["files"].values())
    stickers = sum(f["bytes"] for m in manifest["maps"] for f in m["stickers"][KIT]["files"].values())
    assert manifest["total_bytes"] == variants + stickers
    for m in manifest["maps"]:
        size = sum(f["bytes"] for f in m["stickers"][KIT]["files"].values())
        assert 0 < size <= SET_LIMIT, (m["id"], size)


# --- additions only (FR-018): the sticker step patched out --------------------------------------

class _FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def _tree(root: Path):
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def test_sticker_step_only_adds(tmp_path, fixture_datasets, monkeypatch):
    """A build with the sticker step patched out has identical variant entries and variant files;
    the sticker block, its files and total_bytes are the only differences. Built in B only, so
    both maps need the one extra build in their default combination A."""
    from lego_image_processor.layout import grid
    from lego_image_processor.maps import build

    from web98138 import prebuild

    for mod in (grid, build, prebuild):     # same timestamps in both builds
        monkeypatch.setattr(mod, "datetime", _FrozenDatetime)
    maps = ["official-31203", "ocean-sst"]
    kw = dict(maps=maps, combinations=["B"], cache_dir=fixture_datasets, echo=lambda *a: None,
              prices_path=PRICES, today=TODAY)
    calls = []
    real = prebuild.build_map_stickers

    def counted(*a, **k):
        calls.append(a[0].id)
        return real(*a, **k)

    monkeypatch.setattr(prebuild, "build_map_stickers", counted)
    with_st = prebuild.build_site(tmp_path / "with", **kw)
    assert calls == maps
    monkeypatch.setattr(prebuild, "build_map_stickers", lambda *a, **k: None)
    without = prebuild.build_site(tmp_path / "without", **kw)

    for m in with_st["maps"]:
        assert list(m["variants"]) == ["B"] and KIT in m["stickers"]
    assert all("stickers" not in m for m in without["maps"])
    added = sum(f["bytes"] for m in with_st["maps"] for f in m.pop("stickers")[KIT]["files"].values())
    for key in ("generated_at", "build_seconds"):
        with_st.pop(key), without.pop(key)
    assert with_st.pop("total_bytes") == without.pop("total_bytes") + added
    assert with_st == without
    a, b = _tree(tmp_path / "with"), _tree(tmp_path / "without")
    extra = sorted(set(a) - set(b))
    assert extra == sorted(f"maps/{m}/stickers/{KIT}/{n}" for m in maps
                           for n, _, _ in STICKER_FILES.values())
    assert set(b) <= set(a)
    for path in b:
        if path != "manifest.json":
            assert a[path] == b[path], path
    # the extra build in A is used for the legend values only
    from pypdf import PdfReader

    pdf = PdfReader(io.BytesIO(a[f"maps/ocean-sst/stickers/{KIT}/stickers-letter.pdf"]))
    assert "hung as A" in " ".join(pdf.pages[0].extract_text().split())


def test_sticker_error_is_a_prebuild_error(tmp_path, fixture_datasets, monkeypatch):
    from lego_image_processor import stickers

    from web98138 import prebuild

    def boom(result):
        raise stickers.StickerError("large sticker: legend: ocean does not fit at 5 pt")

    monkeypatch.setattr(stickers, "sticker_set", boom)
    with pytest.raises(prebuild.PrebuildError, match=r"official-31203 stickers: large sticker"):
        prebuild.build_site(tmp_path / "o", maps=["official-31203"], combinations=["A"],
                            cache_dir=fixture_datasets, echo=lambda *a: None,
                            prices_path=PRICES, today=TODAY)


def test_echo_names_the_sticker_set(tmp_path, fixture_datasets):
    from web98138.prebuild import build_site

    lines = []
    build_site(tmp_path / "o", maps=["official-31203"], combinations=["A"],
               cache_dir=fixture_datasets, echo=lines.append, prices_path=PRICES, today=TODAY)
    assert any(line.startswith("official-31203 stickers: 4 files") for line in lines)


def test_kit_template_id_matches_the_library():
    from lego_image_processor.stickers import KIT_TEMPLATE_ID

    from web98138 import prebuild
    from web98138.catalog import STICKER_KINDS, STICKER_TEMPLATES

    assert KIT_TEMPLATE_ID == KIT == prebuild.STICKER_TEMPLATE and STICKER_TEMPLATES == (KIT,)
    assert tuple(prebuild.STICKER_KINDS) == STICKER_KINDS == tuple(STICKER_FILES)
