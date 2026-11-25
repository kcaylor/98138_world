"""Sticker recipes for tests (feature 017, T020; T043).

- ``sticker_recipe(recipe_id)``: the bundled recipe as it is. Since T043 each of the eight bundled
  recipe files ends with its approved ``[sticker]`` table, after one ``# Map stickers (feature
  017):`` comment line (contracts/recipe-sticker.md "Bundled recipes"). Until then this helper
  appended the research R6 draft tables; the drafts went with T043.
- ``fallback_recipe(recipe_id)``: the same recipe without its table (the bytes before the
  comment line, which guard G1 pins to af3ce57), for the fallback to the recipe title and
  description (FR-004).

Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

from lego_image_processor.maps.recipe import Recipe, bundled_recipes, parse_recipe
from tests.integration.stickers_guard import prefix_bytes


def sticker_recipe(recipe_id: str) -> Recipe:
    """The bundled recipe with its approved ``[sticker]`` table, parsed with the bundled path."""
    path = bundled_recipes()[recipe_id]
    return parse_recipe(path.read_bytes(), path=path)


def fallback_recipe(recipe_id: str) -> Recipe:
    """The bundled recipe without its ``[sticker]`` table, parsed with the bundled path."""
    path = bundled_recipes()[recipe_id]
    recipe = parse_recipe(prefix_bytes(path), path=path)
    if recipe.sticker is not None:
        raise ValueError(f"{path.name}: a [sticker] table before the feature 017 comment line")
    return recipe
