"""Image writing utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Union

from PIL import Image


class ImageWriteError(Exception):
    """Error writing image."""
    pass


def save_image(
    image: Image.Image,
    path: Union[str, Path],
    format: str | None = None,
    quality: int = 95
) -> None:
    """Save an image to a file.

    Args:
        image: PIL Image to save
        path: Output file path
        format: Image format (inferred from extension if None)
        quality: JPEG quality (1-95, default 95)

    Raises:
        ImageWriteError: If the image cannot be saved
    """
    path = Path(path)

    # Create parent directories if needed
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Determine format from extension if not specified
        if format is None:
            format = path.suffix.lstrip(".").upper()
            if format == "JPG":
                format = "JPEG"
            elif format == "TIF":
                format = "TIFF"

        # Save with appropriate options
        save_kwargs = {}
        if format == "JPEG":
            save_kwargs["quality"] = quality
            # Convert RGBA to RGB for JPEG
            if image.mode == "RGBA":
                image = image.convert("RGB")
        elif format == "PNG":
            save_kwargs["compress_level"] = 6

        image.save(path, format=format, **save_kwargs)

    except Exception as e:
        raise ImageWriteError(f"Failed to save image: {e}") from e


def get_output_path(
    input_path: Union[str, Path],
    output: Union[str, Path] | None = None,
    suffix: str = "_lego"
) -> Path:
    """Get the output path for a processed image.

    Args:
        input_path: Original input file path
        output: Explicit output path (if provided)
        suffix: Suffix to add to filename if output not specified

    Returns:
        Output file path
    """
    input_path = Path(input_path)

    if output:
        return Path(output)

    # Add suffix before extension
    stem = input_path.stem + suffix
    return input_path.parent / f"{stem}{input_path.suffix}"
