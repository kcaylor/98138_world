"""Layout CLI command for LEGO Image Processor."""

from __future__ import annotations

from pathlib import Path

import click

from ..core.image_loader import load_image, ImageLoadError
from ..palette.loader import LegoPalette
from ..layout.land_sea_mask import load_land_sea_mask
from ..layout.generator import LayoutGenerator


@click.command()
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
def layout(input_image: str, output: str, output_format: str, quiet: bool) -> None:
    """Generate LEGO position placement layout from quantized image.

    Takes a color-quantized image (128x80 pixels) and generates a complete
    LEGO World Map building plan with 10,240 positions (3,062 land bricks
    + 7,178 ocean tiles).

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
            click.echo(f"  Land bricks (3062b): {grid.land_positions:,} ({grid.land_positions/grid.total_positions*100:.1f}%)")
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

    except ImageLoadError as e:
        raise click.ClickException(f"Failed to load image: {e}")
    except ValueError as e:
        raise click.ClickException(str(e))
    except FileNotFoundError as e:
        raise click.ClickException(f"File not found: {e}")
    except Exception as e:
        raise click.ClickException(f"Unexpected error: {e}")
