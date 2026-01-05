"""Image loading utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Union

from PIL import Image


SUPPORTED_FORMATS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".gif"}


class ImageLoadError(Exception):
    """Error loading image."""
    pass


def load_image(path: Union[str, Path]) -> Image.Image:
    """Load an image from a file path.

    Args:
        path: Path to the image file

    Returns:
        PIL Image object

    Raises:
        ImageLoadError: If the image cannot be loaded
    """
    path = Path(path)

    if not path.exists():
        raise ImageLoadError(f"File not found: {path}")

    if path.suffix.lower() not in SUPPORTED_FORMATS:
        raise ImageLoadError(
            f"Unsupported format: {path.suffix}. "
            f"Supported: {', '.join(sorted(SUPPORTED_FORMATS))}"
        )

    try:
        image = Image.open(path)
        # Force load to catch any deferred errors
        image.load()
        return image
    except Exception as e:
        raise ImageLoadError(f"Failed to load image: {e}") from e


def is_supported_format(path: Union[str, Path]) -> bool:
    """Check if a file path has a supported image format.

    Args:
        path: Path to check

    Returns:
        True if the format is supported
    """
    return Path(path).suffix.lower() in SUPPORTED_FORMATS


def get_image_info(image: Image.Image) -> dict:
    """Get information about an image.

    Args:
        image: PIL Image object

    Returns:
        Dictionary with image information
    """
    return {
        "width": image.width,
        "height": image.height,
        "mode": image.mode,
        "format": image.format,
        "pixels": image.width * image.height,
    }
