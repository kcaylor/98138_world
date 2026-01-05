"""Main CLI entry point for LEGO Image Processor."""

from __future__ import annotations

import click

from .. import __version__


@click.group()
@click.version_option(version=__version__, prog_name="lego-image-processor")
def cli() -> None:
    """LEGO Image Processor - Convert images to LEGO-compatible color palettes."""
    pass


# Import and register subcommands
from .quantize import quantize
from .stats import stats

cli.add_command(quantize)
cli.add_command(stats)


def main() -> None:
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
