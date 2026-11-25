"""Shared CLI options (feature 007: ``--arrangement``; feature 016: ``--template``, ``--margin-color``,
``--ring-color``; feature 017: ``--plaque``). Not affiliated with or endorsed by The LEGO Group."""

from __future__ import annotations

import click

from ..layout.arrangement import ArrangementError, parse_arrangement, valid_values
from ..maps.margin import NO_PLAQUE, PLAQUE_CORNERS


class ArrangementType(click.ParamType):
    """``A``/``B``/``C`` or ``europe-africa``/``americas``/``asia-australia``, any case."""

    name = "arrangement"

    def get_metavar(self, param, ctx=None):  # noqa: D401 - click API
        return "[A|B|C]"

    def convert(self, value, param, ctx):
        if not isinstance(value, str):
            return value
        try:
            return parse_arrangement(value)
        except ArrangementError:
            self.fail(f"{value!r} is not an arrangement; use one of {', '.join(valid_values())}",
                      param, ctx)


ARRANGEMENT_HELP = ("How the kit's three frames are hung (LEGO 31203 building instructions, pp. 7-8): "
                    "A = 1·2·3, Europe and Africa in the centre (default); B = 3·1·2, America; "
                    "C = 2·3·1, Asia and Australia. Also europe-africa, americas, asia-australia.")


RECIPE_DEFAULT_HELP = (" Default: the recipe's `arrangement`, else A; an explicit --arrangement wins.")


def arrangement_option(required: bool = False, default="A"):
    """``default=None`` (``map build``/``map check``, feature 009) means "not given", so the
    recipe's own ``arrangement`` key can apply."""
    if required:
        kw = {"required": True}
        help_text = ARRANGEMENT_HELP
    elif default is None:
        kw = {"default": None}
        help_text = ARRANGEMENT_HELP.replace(" (default)", "") + RECIPE_DEFAULT_HELP
    else:
        kw = {"default": default, "show_default": True}
        help_text = ARRANGEMENT_HELP
    return click.option("--arrangement", "-a", type=ArrangementType(), help=help_text, **kw)


# --- feature 016: templates and the margin (contracts/cli.md) -----------------------------------

class TemplateType(click.ParamType):
    """A known template id (``kit-31203``, ``winkel-tripel``); unknown ids are a usage error (exit 2)
    naming the confirmed templates. A known but unconfirmed id passes here and is refused by the
    build (exit 1)."""

    name = "template"

    def get_metavar(self, param, ctx=None):  # noqa: D401 - click API
        return "ID"

    def convert(self, value, param, ctx):
        from ..templates import confirmed_text, template_ids

        if not isinstance(value, str):
            return value
        if value not in template_ids():
            self.fail(f"unknown template {value!r}; confirmed templates: {confirmed_text()}", param, ctx)
        return value


TEMPLATE_HELP = ("The template to build on: kit-31203 (the kit grid) or a template the project owner "
                 "confirmed (see `template list`). Default: the recipe's `template`, else kit-31203; an "
                 "explicit --template wins.")
MARGIN_COLOR_HELP = ("Margin color of a non-kit template (a 1x1 square tile color, part 3070b; see `kit "
                     "part-colors --part 3070b`). Default: the recipe's [margin] color, else lego_black.")
RING_COLOR_HELP = ("Color of the outline ring (margin studs touching the globe), or `none`. Default: the "
                   "recipe's [margin] ring, else no ring. Must differ from the margin color.")


# feature 017 (FR-021; contracts/cli.md): the in-margin plaque's corner
PLAQUE_CHOICES = PLAQUE_CORNERS + (NO_PLAQUE,)
PLAQUE_HELP = ("Put the small plaque's Black tile in this margin corner of a non-kit template, one stud in "
               "from both board edges, or `none`. Default: the recipe's [margin] plaque, else none; an "
               "explicit --plaque wins. The kit template has no margin.")


def template_options(f):
    """``--template``, ``--margin-color``, ``--ring-color`` and (feature 017) ``--plaque`` (``map
    build``, ``map check``, ``map cells``)."""
    f = click.option("--plaque", type=click.Choice(PLAQUE_CHOICES), default=None, help=PLAQUE_HELP)(f)
    f = click.option("--ring-color", default=None, metavar="KEY|none", help=RING_COLOR_HELP)(f)
    f = click.option("--margin-color", default=None, metavar="KEY", help=MARGIN_COLOR_HELP)(f)
    f = click.option("--template", "template_id", type=TemplateType(), default=None, help=TEMPLATE_HELP)(f)
    return f
