"""Stats command for LEGO Image Processor."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import click
import numpy as np
from PIL import Image

from ..core.image_loader import load_image, ImageLoadError
from ..palette.loader import LegoPalette


@click.command()
@click.argument("input_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output in JSON format"
)
@click.option(
    "-n", "--top",
    type=int,
    default=10,
    help="Number of top colors to show (default: 10)"
)
def stats(
    input_path: Path,
    output_json: bool,
    top: int
) -> None:
    """Show color statistics for an image.

    INPUT_PATH is the path to the image file to analyze.

    Example:

        lego-image-processor stats photo_lego.png
    """
    try:
        # Load image
        image = load_image(input_path)

        if image.mode != "RGB":
            image = image.convert("RGB")

        # Get pixel data
        img_array = np.array(image)
        pixels = img_array.reshape(-1, 3)

        # Count colors
        color_tuples = [tuple(p) for p in pixels]
        color_counts = Counter(color_tuples)

        total_pixels = len(color_tuples)
        unique_colors = len(color_counts)

        # Load palette for color identification
        palette = LegoPalette.load_default()
        palette_rgb_set = {tuple(c.rgb) for c in palette.colors}

        # Check which colors are LEGO colors
        lego_colors_found = sum(1 for c in color_counts if c in palette_rgb_set)
        lego_pixel_count = sum(
            count for c, count in color_counts.items() if c in palette_rgb_set
        )

        if output_json:
            import json
            result = {
                "file": str(input_path),
                "width": image.width,
                "height": image.height,
                "total_pixels": total_pixels,
                "unique_colors": unique_colors,
                "lego_colors_found": lego_colors_found,
                "lego_coverage_percent": round(lego_pixel_count / total_pixels * 100, 2),
                "top_colors": [
                    {
                        "rgb": [int(c) for c in color],
                        "count": count,
                        "percent": round(count / total_pixels * 100, 2),
                        "is_lego": color in palette_rgb_set
                    }
                    for color, count in color_counts.most_common(top)
                ]
            }
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(f"File: {input_path}")
            click.echo(f"Size: {image.width}x{image.height}")
            click.echo(f"Total pixels: {total_pixels:,}")
            click.echo(f"Unique colors: {unique_colors:,}")
            click.echo(f"LEGO colors: {lego_colors_found}")
            click.echo(f"LEGO coverage: {lego_pixel_count / total_pixels * 100:.1f}%")
            click.echo()
            click.echo(f"Top {top} colors:")
            click.echo("-" * 50)

            for color, count in color_counts.most_common(top):
                pct = count / total_pixels * 100
                lego_marker = "*" if color in palette_rgb_set else " "
                rgb_str = f"RGB({color[0]:3}, {color[1]:3}, {color[2]:3})"
                click.echo(f"{lego_marker} {rgb_str}: {count:>8,} ({pct:5.1f}%)")

            click.echo()
            click.echo("* = LEGO palette color")

    except ImageLoadError as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Unexpected error: {e}")
