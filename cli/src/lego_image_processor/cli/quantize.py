"""Quantize command for LEGO Image Processor."""

from __future__ import annotations

from pathlib import Path

import click
from tqdm import tqdm

from ..core.color_quantizer import ColorQuantizer
from ..core.image_loader import load_image, ImageLoadError
from ..core.image_writer import save_image, get_output_path, ImageWriteError
from ..palette.loader import LegoPalette


@click.command()
@click.argument("input_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o", "--output",
    type=click.Path(path_type=Path),
    help="Output file path (default: input_lego.ext)"
)
@click.option(
    "-q", "--quality",
    type=int,
    default=95,
    help="JPEG quality (1-95, default: 95)"
)
@click.option(
    "-v", "--verbose",
    is_flag=True,
    help="Show detailed processing information"
)
def quantize(
    input_path: Path,
    output: Path | None,
    quality: int,
    verbose: bool
) -> None:
    """Quantize an image to use only LEGO colors.

    INPUT_PATH is the path to the image file to process.

    Example:

        lego-image-processor quantize photo.jpg -o photo_lego.png
    """
    try:
        # Load image
        if verbose:
            click.echo(f"Loading image: {input_path}")

        image = load_image(input_path)

        if verbose:
            click.echo(f"Image size: {image.width}x{image.height}")
            click.echo(f"Image mode: {image.mode}")

        # Initialize quantizer
        palette = LegoPalette.load_default()
        quantizer = ColorQuantizer(palette)

        if verbose:
            click.echo(f"Using palette with {len(palette)} colors")

        # Quantize
        if verbose:
            click.echo("Quantizing image...")

        result = quantizer.quantize(image)

        if verbose:
            click.echo(f"Original colors: {result.original_colors}")
            click.echo(f"Mapped to: {result.mapped_colors} LEGO colors")

        # Save output
        output_path = get_output_path(input_path, output)

        if verbose:
            click.echo(f"Saving to: {output_path}")

        save_image(result.image, output_path, quality=quality)

        click.echo(f"Saved: {output_path}")

    except ImageLoadError as e:
        raise click.ClickException(str(e))
    except ImageWriteError as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Unexpected error: {e}")
