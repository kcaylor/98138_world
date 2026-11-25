"""Recipe parser (FR-001, FR-002; contracts/recipe-format.md; data-model.md Recipe/Layer)."""

import hashlib

import numpy as np
import pytest

from lego_image_processor.maps.recipe import (
    RecipeError, bundled_recipes, load_recipe, parse_recipe,
)

TILES = ["lego_earth_blue", "lego_medium_azur", "lego_bright_bluish_green"]

BASE = """
format = "1"
id = "demo-map"
title = "Demo"
seed = 7

[land]
role = "background"
colors = ["lego_white"]
weights = [1]

[ocean]
role = "data"
dataset = "etopo2022-surface-10m"
variable = "z"
transform = "negate"
colors = ["lego_earth_blue", "lego_medium_azur", "lego_bright_bluish_green"]

[ocean.classification]
method = "bins"
bounds = [0, 200, 3000, 12000]

[ocean.texture]
kind = "blend"
width = 0.25
"""


def _err(text, **kw):
    with pytest.raises(RecipeError) as e:
        parse_recipe(text, **kw)
    return e.value


class TestValid:
    def test_parse(self):
        r = parse_recipe(BASE)
        assert r.id == "demo-map" and r.format == "1" and r.seed == 7
        assert r.land.role == "background" and r.land.part_id == "6141" and r.land.cls == "land"
        assert r.ocean.role == "data" and r.ocean.part_id == "98138"
        assert r.ocean.dataset.id == "etopo2022-surface-10m"
        assert r.ocean.transform == "negate"
        assert r.ocean.classification.method == "bins"
        assert r.ocean.classification.bounds == (0, 200, 3000, 12000)
        assert r.ocean.texture.kind == "blend" and r.ocean.texture.width == 0.25
        assert r.land.weights == (1.0,)
        assert r.sha256 == hashlib.sha256(BASE.encode("utf-8")).hexdigest()

    def test_default_seed_and_texture(self):
        r = parse_recipe(BASE.replace("seed = 7\n", "").replace('[ocean.texture]\nkind = "blend"\nwidth = 0.25\n', ""))
        assert r.seed == 31203
        assert r.ocean.texture.kind == "none"

    def test_quantile_rank_supply_categorical(self):
        q = parse_recipe(BASE.replace('method = "bins"\nbounds = [0, 200, 3000, 12000]', 'method = "quantile"'))
        assert q.ocean.classification.method == "quantile"
        r = parse_recipe(BASE.replace('method = "bins"\nbounds = [0, 200, 3000, 12000]', 'method = "rank"\nshares = [1, 2, 3]'))
        assert r.ocean.classification.shares == (1.0, 2.0, 3.0)
        s = parse_recipe(BASE.replace('method = "bins"\nbounds = [0, 200, 3000, 12000]', 'method = "rank-to-supply"'))
        assert s.ocean.classification.method == "rank-to-supply"
        c = parse_recipe(BASE.replace('dataset = "etopo2022-surface-10m"\nvariable = "z"\ntransform = "negate"',
                                      'dataset = "kit31203-design"\nvariable = "color"')
                         .replace('method = "bins"\nbounds = [0, 200, 3000, 12000]',
                                  'method = "categorical"\n[ocean.classification.categories]\nlego_earth_blue = "lego_earth_blue"')
                         .replace('[ocean.texture]\nkind = "blend"\nwidth = 0.25\n', ""))
        assert c.ocean.classification.categories == {"lego_earth_blue": "lego_earth_blue"}

    def test_mix_background(self):
        text = BASE.replace('colors = ["lego_white"]\nweights = [1]',
                            'colors = ["lego_white"]\nweights = [1]\n[land.texture]\nkind = "mix"\ncluster = 2.0')
        assert parse_recipe(text).land.texture.cluster == 2.0


class TestErrors:
    def test_format_version(self):
        e = _err(BASE.replace('format = "1"', 'format = "2"'))
        assert e.path == "format" and '"1"' in str(e)

    def test_bad_id(self):
        assert _err(BASE.replace('id = "demo-map"', 'id = "Demo Map"')).path == "id"

    def test_unknown_top_key(self):
        assert _err('colour = "x"\n' + BASE).path == "colour"

    def test_unknown_layer_key(self):
        e = _err(BASE.replace('role = "data"', 'role = "data"\nshade = 3'))
        assert e.path == "ocean.shade"

    def test_missing_layer(self):
        text = BASE[:BASE.index("[land]")] + BASE[BASE.index("[ocean]"):]
        assert _err(text).path == "land"

    def test_bad_role(self):
        assert _err(BASE.replace('role = "data"', 'role = "picture"')).path == "ocean.role"

    def test_background_with_dataset(self):
        e = _err(BASE.replace('weights = [1]', 'weights = [1]\ndataset = "etopo2022-surface-10m"'))
        assert e.path == "land.dataset"

    def test_data_without_classification(self):
        text = BASE.replace('[ocean.classification]\nmethod = "bins"\nbounds = [0, 200, 3000, 12000]\n', "")
        assert _err(text).path == "ocean.classification"

    def test_color_not_for_part(self):
        # Medium Blue is a cited tile color but not a plate color (005 join rule 5)
        e = _err(BASE.replace('colors = ["lego_white"]', 'colors = ["lego_medium_blue"]'))
        assert e.path == "land.colors[0]"
        assert "lego_medium_blue" in str(e) and "6141" in str(e)

    def test_unknown_color(self):
        e = _err(BASE.replace('"lego_medium_azur", "lego_bright', '"lego_plaid", "lego_bright'))
        assert e.path == "ocean.colors[1]"

    def test_bounds_not_increasing(self):
        e = _err(BASE.replace("bounds = [0, 200, 3000, 12000]", "bounds = [0, 3000, 200, 12000]"))
        assert e.path == "ocean.classification.bounds"

    def test_classes_vs_colors(self):
        e = _err(BASE.replace("bounds = [0, 200, 3000, 12000]", "bounds = [0, 200, 12000]"))
        assert e.path == "ocean.classification.bounds"

    def test_shares_length(self):
        e = _err(BASE.replace('method = "bins"\nbounds = [0, 200, 3000, 12000]', 'method = "rank"\nshares = [1, 2]'))
        assert e.path == "ocean.classification.shares"

    def test_unknown_dataset(self):
        assert _err(BASE.replace("etopo2022-surface-10m", "nope")).path == "ocean.dataset"

    def test_unknown_variable(self):
        assert _err(BASE.replace('variable = "z"', 'variable = "sst"')).path == "ocean.variable"

    def test_bad_transform(self):
        assert _err(BASE.replace('"negate"', '"log"')).path == "ocean.transform"

    def test_weights_length(self):
        assert _err(BASE.replace("weights = [1]", "weights = [1, 2]")).path == "land.weights"

    def test_weights_positive(self):
        assert _err(BASE.replace("weights = [1]", "weights = [0]")).path == "land.weights[0]"

    def test_blend_width_range(self):
        assert _err(BASE.replace("width = 0.25", "width = 0.75")).path == "ocean.texture.width"

    def test_mix_on_data_layer(self):
        e = _err(BASE.replace('kind = "blend"\nwidth = 0.25', 'kind = "mix"'))
        assert e.path == "ocean.texture.kind"

    def test_multi_color_background_needs_mix(self):
        text = BASE.replace('colors = ["lego_white"]\nweights = [1]',
                            'colors = ["lego_white", "lego_white"]\nweights = [1, 1]')
        assert _err(text).path in ("land.colors", "land.texture")

    def test_rank_to_supply_needs_kit_colors(self):
        # lego_white is not a kit color of the ocean tile: it fails as unavailable before supply
        e = _err(BASE.replace('"lego_earth_blue", "lego_medium', '"lego_white", "lego_medium')
                     .replace('method = "bins"\nbounds = [0, 200, 3000, 12000]', 'method = "rank-to-supply"'))
        assert e.path.startswith("ocean.colors")

    def test_categorical_value_not_in_colors(self):
        text = (BASE.replace('dataset = "etopo2022-surface-10m"\nvariable = "z"\ntransform = "negate"',
                             'dataset = "kit31203-design"\nvariable = "color"')
                .replace('method = "bins"\nbounds = [0, 200, 3000, 12000]',
                         'method = "categorical"\n[ocean.classification.categories]\nlego_earth_blue = "lego_bright_orange"')
                .replace('[ocean.texture]\nkind = "blend"\nwidth = 0.25\n', ""))
        assert _err(text).path == "ocean.classification.categories.lego_earth_blue"

    def test_not_toml(self):
        assert _err("format = ").path == "(file)"


class TestLocal:
    def _local(self, tmp_path, data=b"", **overrides):
        f = tmp_path / "field.npy"
        np.save(f, np.zeros((2, 4)))
        sha = hashlib.sha256(f.read_bytes()).hexdigest()
        fields = dict(path='"field.npy"', format='"npy"', sha256=f'"{sha}"', variable='"v"',
                      citation='"Me, 2026."', license='"CC0-1.0"', lat="[-90, 90]", lon="[-180, 180]")
        fields.update(overrides)
        fields = {k: v for k, v in fields.items() if v is not None}
        table = "\n".join(f"{k} = {v}" for k, v in fields.items())
        text = BASE.replace('dataset = "etopo2022-surface-10m"\nvariable = "z"\n', "") \
            .replace("[ocean.classification]", f"[ocean.local]\n{table}\n\n[ocean.classification]")
        rp = tmp_path / "r.toml"
        rp.write_text(text, encoding="utf-8")
        return rp

    def test_valid_local_resolves_relative_path(self, tmp_path):
        r = load_recipe(self._local(tmp_path))
        e = r.ocean.dataset
        assert e.kind == "local" and e.path == tmp_path / "field.npy"
        assert e.license == "CC0-1.0" and e.citation == "Me, 2026."
        assert r.ocean.variable == "v"

    @pytest.mark.parametrize("field", ["path", "format", "sha256", "variable", "citation", "license"])
    def test_required(self, tmp_path, field):
        with pytest.raises(RecipeError) as e:
            load_recipe(self._local(tmp_path, **{field: None}))
        assert e.value.path == f"ocean.local.{field}"

    def test_npy_needs_extent(self, tmp_path):
        with pytest.raises(RecipeError) as e:
            load_recipe(self._local(tmp_path, lat=None))
        assert e.value.path == "ocean.local.lat"

    def test_wrong_sha_fails_at_build_time_check(self, tmp_path):
        from lego_image_processor.datasets.cache import ChecksumMismatchError, resolve_entry
        r = load_recipe(self._local(tmp_path, sha256='"' + "0" * 64 + '"'))
        with pytest.raises(ChecksumMismatchError):
            resolve_entry(r.ocean.dataset)

    def test_dataset_and_local_conflict(self, tmp_path):
        rp = self._local(tmp_path)
        text = rp.read_text().replace('[ocean]\nrole = "data"', '[ocean]\nrole = "data"\ndataset = "etopo2022-surface-10m"')
        rp.write_text(text)
        with pytest.raises(RecipeError) as e:
            load_recipe(rp)
        assert e.value.path == "ocean.local"


class TestBundled:
    def test_six_bundled(self):
        ids = set(bundled_recipes())
        assert {"official-31203", "official-31203-bathymetry", "ocean-sst", "land-elevation",
                "ocean-el-nino", "ocean-la-nina"} <= ids

    def test_load_by_id(self):
        r = load_recipe("official-31203")
        assert r.id == "official-31203"
        assert r.path.name == "official-31203.toml"

    def test_every_bundled_recipe_has_disclaimer_comment(self):
        for path in bundled_recipes().values():
            assert "Not affiliated with or endorsed by The LEGO Group." in path.read_text(encoding="utf-8")

    def test_duplicate_bundled_ids_rejected(self, tmp_path):
        (tmp_path / "a.toml").write_text(BASE)
        (tmp_path / "b.toml").write_text(BASE)
        with pytest.raises(RecipeError, match="duplicate"):
            bundled_recipes(tmp_path)

    def test_unknown_recipe(self):
        with pytest.raises(RecipeError):
            load_recipe("no-such-recipe")


class TestArrangementKey:
    """Optional top-level ``arrangement`` (feature 009, FR-010; contracts/recipe-arrangement.md)."""

    @staticmethod
    def _with(value_line):
        return BASE.replace('seed = 7\n', f'seed = 7\n{value_line}\n')

    @pytest.mark.parametrize("value", ['"B"', '"b"', '"americas"', '" B "'])
    def test_valid_values_parse_to_b(self, value):
        r = parse_recipe(self._with(f"arrangement = {value}"))
        assert r.arrangement is not None and r.arrangement.id == "B"
        assert r.format == "1"

    def test_absent_is_none(self):
        assert parse_recipe(BASE).arrangement is None

    @pytest.mark.parametrize("value", ['"F"', "2", "true", "{ id = \"B\" }"])
    def test_invalid_values(self, value):
        e = _err(self._with(f"arrangement = {value}"))
        assert e.path == "arrangement"
        for name in ("A", "B", "C", "D", "E", "europe-africa", "americas", "asia-australia",
                     "pacific", "asia-pacific"):
            assert name in e.rule

    def test_unknown_top_level_key_still_rejected(self):
        e = _err(self._with('arrangment = "B"'))
        assert e.path == "arrangment" and "unknown key" in e.rule
