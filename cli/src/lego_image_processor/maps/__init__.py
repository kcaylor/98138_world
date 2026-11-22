"""Map recipes: layers, reprojection, classification, texture, suitability (feature 004).

Not affiliated with or endorsed by The LEGO Group.
"""

from .build import MapResult, agreement_with_official, build_map, check_recipe, missing_datasets
from .classify import ClassResult, MapBuildError, classify
from .preview import write_preview
from .projection import KitProjection, load_kit_projection
from .recipe import (Classification, Layer, Recipe, RecipeError, Texture, bundled_recipes, load_recipe,
                     parse_recipe)
from .reproject import LayerField, reproject_layer
from .suitability import THRESHOLDS, layer_report
from .texture import apply_blend, fill_background

apply_texture = apply_blend  # contracts/library-api.md name for data-layer texture

__all__ = [
    "Recipe", "Layer", "Classification", "Texture", "RecipeError", "load_recipe", "parse_recipe",
    "bundled_recipes", "KitProjection", "load_kit_projection", "LayerField", "reproject_layer",
    "ClassResult", "MapBuildError", "classify", "apply_blend", "apply_texture", "fill_background",
    "THRESHOLDS", "layer_report", "check_recipe", "MapResult", "build_map", "missing_datasets",
    "write_preview", "agreement_with_official",
]
