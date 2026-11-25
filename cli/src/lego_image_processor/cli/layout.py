"""Layout CLI commands: a layout from a quantized image (``layout IMAGE``) and re-hanging a layout
in another frame arrangement (``layout arrange``, feature 007)."""

from __future__ import annotations

from pathlib import Path

import click

from ..core.image_loader import load_image, ImageLoadError
from ..palette.loader import LegoPalette
from ..layout.land_sea_mask import load_land_sea_mask
from ..layout.generator import LayoutGenerator
from ..layout.grid import DISCLAIMER, LayoutSchemaError, PositionPlacementGrid
from .options import arrangement_option


class LayoutGroup(click.Group):
    """``layout IMAGE ...`` (the original command) keeps working: a first argument that is not a
    sub-command name runs ``layout image``."""

    def parse_args(self, ctx, args):
        if args and args[0] not in self.commands and args[0] not in ("--help", "-h"):
            args = ["image"] + list(args)
        return super().parse_args(ctx, args)


@click.group(cls=LayoutGroup)
def layout() -> None:
    """Make layouts: from a quantized image, or re-hung in another frame arrangement.

    \b
    Examples:
        lego-image-processor layout quantized.png -o layout.json
        lego-image-processor layout arrange layout.json --arrangement B -o layout-B.json
    """


@layout.command("image")
@click.argument("input_image", type=click.Path(exists=True))
@click.option(
    "--output", "-o",
    required=True,
    type=click.Path(),
    help="Output file path for the layout (JSON or CSV)"
)
@click.option(
    "--format", "-f", "output_format",
    type=click.Choice(["json", "csv"]),
    default="json",
    help="Output format (default: json)"
)
@click.option(
    "--quiet", "-q",
    is_flag=True,
    help="Suppress progress output"
)
def image_layout(input_image: str, output: str, output_format: str, quiet: bool) -> None:
    """Generate LEGO position placement layout from quantized image.

    Takes a color-quantized image (128x80 pixels) and generates a complete
    LEGO World Map building plan with 10,240 positions (3,062 land plates,
    part 6141, + 7,178 ocean tiles, part 98138).

    \b
    Examples:
        # Generate JSON layout
        lego-image-processor layout quantized.png -o layout.json

        # Generate CSV layout
        lego-image-processor layout quantized.png -o layout.csv -f csv

        # Generate layout quietly
        lego-image-processor layout quantized.png -o layout.json -q

    \b
    Input Requirements:
        - Image dimensions: 128x80 pixels (matches LEGO World Map kit 31203)
        - Colors: Only LEGO palette colors (from quantization step)
        - Format: PNG, JPEG, or other supported image formats

    \b
    Output:
        - JSON: Full layout with metadata, positions, and statistics
        - CSV: Tabular format with one row per position
    """
    try:
        # Load image
        if not quiet:
            click.echo(f"Loading quantized image: {input_image}")

        image = load_image(input_image)

        if not quiet:
            click.echo(f"  Image dimensions: {image.width}x{image.height} pixels")
            click.echo(f"  Total pixels: {image.width * image.height:,}")
            click.echo()

        # Load palette
        if not quiet:
            click.echo("Validating image...")

        palette = LegoPalette.load_default()

        # Load land/sea mask
        if not quiet:
            click.echo("Loading land/sea mask...")

        land_sea_mask = load_land_sea_mask()

        if not quiet:
            click.echo(f"  Mask loaded: {land_sea_mask.land_count:,} land positions, "
                      f"{land_sea_mask.ocean_count:,} ocean positions")
            click.echo()

        # Create generator
        generator = LayoutGenerator(palette=palette, land_sea_mask=land_sea_mask)

        # Generate layout with progress
        if not quiet:
            click.echo("Generating position placements...")
            with click.progressbar(
                length=128 * 80,
                label="  Progress",
                show_percent=True
            ) as bar:
                def progress_callback(current: int, total: int) -> None:
                    bar.update(1)

                grid = generator.generate(
                    image,
                    source_filename=Path(input_image).name,
                    progress_callback=progress_callback
                )
        else:
            grid = generator.generate(
                image,
                source_filename=Path(input_image).name
            )

        # Write output
        output_path = Path(output)

        if output_format == "json":
            content = grid.to_json()
        else:
            content = grid.to_csv()

        output_path.write_text(content, encoding="utf-8")

        # Print summary
        if not quiet:
            click.echo()
            click.echo(click.style("Layout generation complete!", fg="green"))
            click.echo(f"  Total positions: {grid.total_positions:,}")
            click.echo(f"  Land plates (6141): {grid.land_positions:,} ({grid.land_positions/grid.total_positions*100:.1f}%)")
            click.echo(f"  Ocean tiles (98138): {grid.ocean_positions:,} ({grid.ocean_positions/grid.total_positions*100:.1f}%)")
            click.echo(f"  Unique colors: {grid.unique_colors}")
            click.echo(f"  Output: {output}")

            # Show build statistics
            stats = grid.compute_statistics()
            click.echo()
            click.echo("Build statistics:")
            if stats.most_common_color:
                click.echo(f"  Most common color: {stats.most_common_color['color_name']} "
                          f"({stats.most_common_color['count']:,} positions, "
                          f"{stats.most_common_color['count']/grid.total_positions*100:.1f}%)")
            click.echo()
            click.echo(DISCLAIMER)

    except ImageLoadError as e:
        raise click.ClickException(f"Failed to load image: {e}")
    except ValueError as e:
        raise click.ClickException(str(e))
    except FileNotFoundError as e:
        raise click.ClickException(f"File not found: {e}")
    except Exception as e:
        raise click.ClickException(f"Unexpected error: {e}")


@layout.command("arrange")
@click.argument("layout_file", type=click.Path(dir_okay=False))
@arrangement_option(required=True)
@click.option("--output", "-o", required=True, type=click.Path(dir_okay=False), help="Layout JSON to write")
@click.option("--quiet", "-q", is_flag=True, help="Suppress output")
def arrange(layout_file: str, arrangement, output: str, quiet: bool) -> None:
    """Re-hang LAYOUT in another arrangement of the kit's frames (A-E; D and E split frame 2).

    A pure frame move, as when moving the physical frames: every position moves by whole frames
    (32 or 64 columns, cyclically); colors and parts never change, and arranging back to A
    restores the original positions. A layout without ``metadata.arrangement`` is in A.

    \b
    Examples:
        lego-image-processor layout arrange official.json --arrangement B -o official-B.json
        lego-image-processor layout arrange official-B.json --arrangement asia-australia -o official-C.json
    """
    from ..layout.arrangement import ArrangementError, arrange_grid, arrangement_of
    from .map import CommandError

    try:
        text = Path(layout_file).read_text(encoding="utf-8")
    except OSError as exc:
        raise CommandError(f"Cannot read layout {layout_file}: {exc.strerror or exc}", 1)
    try:
        grid = PositionPlacementGrid.from_json(text)
    except LayoutSchemaError as exc:
        raise CommandError(str(exc), 1)
    except (ValueError, KeyError, TypeError) as exc:
        raise CommandError(f"{layout_file}: not a valid layout ({exc.__class__.__name__}: {exc})", 1)
    try:
        current = arrangement_of(grid)
        out = arrange_grid(grid, arrangement)
    except ArrangementError as exc:
        raise CommandError(f"{layout_file}: {exc}", 1)
    try:
        Path(output).write_text(out.to_json(), encoding="utf-8")
    except OSError as exc:
        raise CommandError(f"Cannot write output: {exc}", 1)
    if not quiet:
        delta = (arrangement.column_shift - current.column_shift) % out.width
        click.echo(f"Arranged {layout_file} from {current.id} to {arrangement.id} "
                   f"(column shift +{delta}): {output} ({len(out.positions):,} positions)")
        click.echo(f"  {arrangement.describe()}; frames left to right: "
                   + ", ".join(f"{g.label} {g.frame.name}" for g in arrangement.group_spans()))
        click.echo("  Colors and parts unchanged; every arrangement uses the same pieces.")
        click.echo(DISCLAIMER)
