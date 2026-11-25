"""Ice regions (feature 015, FR-003): rules, packaged data, arrangement roll."""

import json

import numpy as np
import pytest

from lego_image_processor.datasets.grid import SourceGrid
from lego_image_processor.layout.arrangement import parse_arrangement
from lego_image_processor.maps.build import land_mask_array
from lego_image_processor.maps.ice import (
    ICE_PATH, LAND_ICE_REGIONS, SEA_ICE_RULE, IceRegions, derive_ice_regions, in_region,
    land_ice_mask, load_ice_regions, parse_ice_regions, sea_ice_mask,
)
from lego_image_processor.maps.projection import load_kit_projection

DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."


@pytest.fixture(scope="module")
def proj():
    return load_kit_projection()


@pytest.fixture(scope="module")
def land():
    return land_mask_array()


class TestRegions:
    def test_antarctica(self):
        ant = LAND_ICE_REGIONS[0]
        assert ant["name"] == "Antarctica"
        assert in_region(-75.0, 10.0, ant)
        assert not in_region(-50.0, 10.0, ant)

    def test_greenland_excludes_iceland(self):
        gl = LAND_ICE_REGIONS[1]
        assert gl["name"] == "Greenland"
        assert in_region(72.0, -40.0, gl)
        assert not in_region(65.0, -18.0, gl)      # Iceland
        assert in_region(65.0, -40.0, gl)          # south-east Greenland, west of the exclusion
        assert not in_region(72.0, 20.0, gl)       # Svalbard


class TestLandIce:
    def test_only_land_cells(self, land, proj):
        m = land_ice_mask(land, proj)
        assert m.shape == land.shape
        assert m.any()
        assert not (m & ~land).any()

    def test_bottom_rows_and_greenland(self, land, proj):
        m = land_ice_mask(land, proj)
        # every land cell of the southernmost row is Antarctica
        assert (m[-1] == land[-1]).all()
        lat, lon = proj.cell_center(8, 0)
        r, c = 8, int(((-40.0 - proj.left_edge_lon) % 360) // proj.deg_per_col)
        if land[r, c]:
            assert m[r, c]


class TestSeaIce:
    def _grid(self, values):
        lat = np.linspace(-89, 89, values.shape[0])
        lon = np.linspace(-179, 179, values.shape[1])
        return SourceGrid(values=values, lat=lat, lon=lon)

    def test_cold_or_unobserved_polar(self, land, proj):
        vals = np.full((90, 180), 10.0)
        vals[-3:, :] = -1.8          # near the north pole: frozen all year
        vals[:6, :] = np.nan         # far south (89-79° S): no value at all
        m = sea_ice_mask(self._grid(vals), land, proj)
        assert not (m & land).any()
        assert m[0][~land[0]].all()                  # row 0 (≈ 90° N) is frozen
        assert m[-1][~land[-1]].all()                # row 79: no value, poleward of 60°
        mid = proj.height // 2
        assert not m[mid].any()

    def test_threshold_is_inclusive(self, land, proj):
        vals = np.full((90, 180), SEA_ICE_RULE["max_value"])
        m = sea_ice_mask(self._grid(vals), land, proj)
        assert (m == ~land).all()

    def test_unobserved_equatorial_is_not_ice(self, land, proj):
        vals = np.full((90, 180), 20.0)
        vals[40:50, :] = np.nan
        m = sea_ice_mask(self._grid(vals), land, proj)
        # only the polar rows the source never reaches (row 0, beyond 89° N) are unobserved ice
        assert not m[1:].any()


class TestPackaged:
    def test_loads_and_agrees_with_mask(self, land):
        ice = load_ice_regions()
        assert isinstance(ice, IceRegions)
        assert ice.land.shape == (80, 128) and ice.sea.shape == (80, 128)
        assert not (ice.land & ~land).any()
        assert not (ice.sea & land).any()
        assert ice.land.sum() > 100 and ice.sea.sum() > 100

    def test_source_block(self):
        data = json.loads(ICE_PATH.read_text(encoding="utf-8"))
        src = data["source"]
        assert src["disclaimer"] == DISCLAIMER
        assert src["sea_ice"]["dataset"]["id"] == "ersst-v5-ltm-1991-2020"
        assert len(src["sea_ice"]["dataset"]["sha256"]) == 64
        assert src["generator"].startswith("cli/tools/kit31203 ice-mask")
        assert data["land_ice"]["count"] == len(data["land_ice"]["cells"])

    def test_land_ice_matches_rule(self, land, proj):
        assert (load_ice_regions().land == land_ice_mask(land, proj)).all()

    def test_rejects_cells_on_wrong_class(self):
        data = json.loads(ICE_PATH.read_text(encoding="utf-8"))
        bad = dict(data, sea_ice=dict(data["sea_ice"], cells=data["sea_ice"]["cells"] + [data["land_ice"]["cells"][0]],
                                      count=data["sea_ice"]["count"] + 1))
        with pytest.raises(ValueError, match="sea_ice"):
            parse_ice_regions(bad)

    def test_rolled(self):
        ice = load_ice_regions()
        b = parse_arrangement("B")
        r = ice.rolled(b)
        assert (r.land == b.roll(ice.land)).all() and (r.sea == b.roll(ice.sea)).all()

    def test_derive_round_trip(self, land, proj):
        # derive_ice_regions with an all-warm field gives the land ice only
        grid = SourceGrid(values=np.full((90, 180), 25.0), lat=np.linspace(-89, 89, 90),
                          lon=np.linspace(-179, 179, 180))
        ice = derive_ice_regions(grid, land=land, projection=proj)
        assert (ice.land == land_ice_mask(land, proj)).all()
        assert not ice.sea[1:].any()     # row 0 (beyond 89° N) has no source value


# --- Feature 016 (T077): a template's ice regions, data/templates/<id>-ice.json -------------

class TestTemplateIce:
    """``load_template_ice(template)`` (FR-020a/b; contracts/template-file.md "Ice file")."""

    def _paths(self, template):
        return template.path, template.path.with_name(f"{template.id}-ice.json")

    def test_reads_the_template_ice_file(self, synthetic_template):
        from lego_image_processor.maps.ice import load_template_ice

        t = synthetic_template
        _, ice_path = self._paths(t)
        data = json.loads(ice_path.read_text(encoding="utf-8"))
        ice = load_template_ice(t)
        assert isinstance(ice, IceRegions)
        assert ice.land.shape == ice.sea.shape == (t.height, t.width)
        assert np.flatnonzero(ice.land.ravel()).tolist() == data["land_ice"]["cells"]
        assert np.flatnonzero(ice.sea.ravel()).tolist() == data["sea_ice"]["cells"]
        assert not (ice.land & ~t.land).any() and not (ice.sea & ~t.ocean).any()
        assert ice.source["template_layout_sha256"] == t.layout_sha256
        assert ice.rolled(parse_arrangement("A")).land.tolist() == ice.land.tolist()

    def test_kit_gets_the_kit_file(self):
        from lego_image_processor.maps.ice import load_template_ice
        from lego_image_processor.templates import kit_template

        assert load_template_ice(kit_template()) is load_ice_regions()

    def test_refuses_another_layout(self, synthetic_template):
        from lego_image_processor.maps.ice import TemplateIceError, load_template_ice

        _, ice_path = self._paths(synthetic_template)
        data = json.loads(ice_path.read_text(encoding="utf-8"))
        data["source"]["template_layout_sha256"] = "f" * 64
        ice_path.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(TemplateIceError, match="template_layout_sha256") as e:
            load_template_ice(synthetic_template)
        assert "ice-mask winkel-tripel" in str(e.value)
        assert isinstance(e.value, ValueError)

    def test_a_copy_that_differs_only_in_confirmation(self, synthetic_template, tmp_path):
        from lego_image_processor.maps.ice import load_template_ice
        from lego_image_processor.templates import load_template_file
        from maptemplates.testing import confirmed_copy

        src = synthetic_template.path.parent
        copy = confirmed_copy(src, tmp_path / "other", "2027-01-31")
        other = load_template_file(copy)
        assert other.file_sha256 != synthetic_template.file_sha256
        assert other.layout_sha256 == synthetic_template.layout_sha256
        a, b = load_template_ice(synthetic_template), load_template_ice(other)
        assert (a.land == b.land).all() and (a.sea == b.sea).all()

    def test_missing_file(self, synthetic_template):
        from lego_image_processor.maps.ice import TemplateIceError, load_template_ice

        _, ice_path = self._paths(synthetic_template)
        ice_path.unlink()
        with pytest.raises(TemplateIceError, match="winkel-tripel-ice.json") as e:
            load_template_ice(synthetic_template)
        assert "ice-mask winkel-tripel" in str(e.value)

    @pytest.mark.parametrize("change, rule", [
        ("template_id", "template_id"),
        ("land_on_ocean", "land_ice"),
        ("sea_on_margin", "sea_ice"),
        ("count", "count"),
        ("disclaimer", "disclaimer"),
        ("format", "format_version"),
    ])
    def test_refuses_a_broken_file(self, synthetic_template, change, rule):
        from lego_image_processor.maps.ice import TemplateIceError, load_template_ice

        t = synthetic_template
        _, ice_path = self._paths(t)
        data = json.loads(ice_path.read_text(encoding="utf-8"))
        if change == "template_id":
            data["template_id"] = "mollweide"
        elif change == "land_on_ocean":
            cell = int(np.flatnonzero(np.asarray(t.ocean).ravel())[0])
            data["land_ice"]["cells"] = sorted(data["land_ice"]["cells"] + [cell])
            data["land_ice"]["count"] += 1
        elif change == "sea_on_margin":
            cell = int(np.flatnonzero(np.asarray(t.margin).ravel())[0])
            data["sea_ice"]["cells"] = sorted(data["sea_ice"]["cells"] + [cell])
            data["sea_ice"]["count"] += 1
        elif change == "count":
            data["land_ice"]["count"] += 1
        elif change == "disclaimer":
            data["source"]["disclaimer"] = ""
        else:
            data["format_version"] = "2"
        ice_path.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(TemplateIceError, match=rule):
            load_template_ice(t)

    def test_reloads_after_the_file_changes(self, synthetic_template):
        from lego_image_processor.maps.ice import load_template_ice

        t = synthetic_template
        _, ice_path = self._paths(t)
        first = load_template_ice(t)
        data = json.loads(ice_path.read_text(encoding="utf-8"))
        data["sea_ice"]["cells"] = data["sea_ice"]["cells"][1:]
        data["sea_ice"]["count"] -= 1
        ice_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        assert load_template_ice(t).sea.sum() == first.sea.sum() - 1

    def test_confirmed_winkel_has_its_ice_file(self, confirmed_winkel):
        """The test confirmation leaves the layout digest unchanged, so the copied ice file loads."""
        from lego_image_processor.maps.ice import load_template_ice, template_ice_path

        t = confirmed_winkel
        assert t.status == "confirmed" and template_ice_path(t).is_file()
        ice = load_template_ice(t)
        assert ice.source["template_layout_sha256"] == t.layout_sha256
        assert ice.land.any() and ice.sea.any()
