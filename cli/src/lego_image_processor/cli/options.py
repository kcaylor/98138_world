"""Shared CLI options (feature 007: ``--arrangement``). Not affiliated with or endorsed by The LEGO Group."""

from __future__ import annotations

import click

from ..layout.arrangement import ArrangementError, parse_arrangement, valid_values


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
