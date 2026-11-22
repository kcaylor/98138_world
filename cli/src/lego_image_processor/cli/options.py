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


def arrangement_option(required: bool = False, default="A"):
    kw = {"required": True} if required else {"default": default, "show_default": True}
    return click.option("--arrangement", "-a", type=ArrangementType(), help=ARRANGEMENT_HELP, **kw)
