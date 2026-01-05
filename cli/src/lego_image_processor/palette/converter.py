"""Color space conversion utilities."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def rgb_to_xyz(rgb: NDArray[np.float64]) -> NDArray[np.float64]:
    """Convert RGB to XYZ color space.

    Args:
        rgb: RGB values in range [0, 255] with shape (..., 3)

    Returns:
        XYZ values with shape (..., 3)
    """
    # Normalize RGB to [0, 1]
    rgb_normalized = rgb / 255.0

    # Apply gamma correction (sRGB to linear)
    mask = rgb_normalized > 0.04045
    rgb_linear = np.where(
        mask,
        ((rgb_normalized + 0.055) / 1.055) ** 2.4,
        rgb_normalized / 12.92
    )

    # RGB to XYZ transformation matrix (sRGB D65)
    transform_matrix = np.array([
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041]
    ])

    # Apply transformation
    xyz = np.dot(rgb_linear, transform_matrix.T) * 100

    return xyz


def xyz_to_lab(xyz: NDArray[np.float64]) -> NDArray[np.float64]:
    """Convert XYZ to LAB color space.

    Args:
        xyz: XYZ values with shape (..., 3)

    Returns:
        LAB values with shape (..., 3)
    """
    # D65 reference white
    ref_white = np.array([95.047, 100.000, 108.883])

    # Normalize by reference white
    xyz_normalized = xyz / ref_white

    # Apply f function
    epsilon = 0.008856
    kappa = 903.3

    mask = xyz_normalized > epsilon
    f_xyz = np.where(
        mask,
        np.cbrt(xyz_normalized),
        (kappa * xyz_normalized + 16) / 116
    )

    # Calculate LAB
    L = 116 * f_xyz[..., 1] - 16
    a = 500 * (f_xyz[..., 0] - f_xyz[..., 1])
    b = 200 * (f_xyz[..., 1] - f_xyz[..., 2])

    return np.stack([L, a, b], axis=-1)


def rgb_to_lab(rgb: NDArray[np.float64]) -> NDArray[np.float64]:
    """Convert RGB to LAB color space.

    Args:
        rgb: RGB values in range [0, 255] with shape (..., 3)

    Returns:
        LAB values with shape (..., 3)
    """
    xyz = rgb_to_xyz(rgb)
    return xyz_to_lab(xyz)


def lab_to_xyz(lab: NDArray[np.float64]) -> NDArray[np.float64]:
    """Convert LAB to XYZ color space.

    Args:
        lab: LAB values with shape (..., 3)

    Returns:
        XYZ values with shape (..., 3)
    """
    # D65 reference white
    ref_white = np.array([95.047, 100.000, 108.883])

    # Calculate f values
    fy = (lab[..., 0] + 16) / 116
    fx = lab[..., 1] / 500 + fy
    fz = fy - lab[..., 2] / 200

    # Apply inverse f function
    epsilon = 0.008856
    kappa = 903.3

    xr = np.where(fx ** 3 > epsilon, fx ** 3, (116 * fx - 16) / kappa)
    yr = np.where(lab[..., 0] > kappa * epsilon, fy ** 3, lab[..., 0] / kappa)
    zr = np.where(fz ** 3 > epsilon, fz ** 3, (116 * fz - 16) / kappa)

    xyz = np.stack([xr, yr, zr], axis=-1) * ref_white

    return xyz


def xyz_to_rgb(xyz: NDArray[np.float64]) -> NDArray[np.float64]:
    """Convert XYZ to RGB color space.

    Args:
        xyz: XYZ values with shape (..., 3)

    Returns:
        RGB values in range [0, 255] with shape (..., 3)
    """
    # XYZ to RGB transformation matrix (sRGB D65)
    transform_matrix = np.array([
        [ 3.2404542, -1.5371385, -0.4985314],
        [-0.9692660,  1.8760108,  0.0415560],
        [ 0.0556434, -0.2040259,  1.0572252]
    ])

    # Apply transformation
    rgb_linear = np.dot(xyz / 100, transform_matrix.T)

    # Apply gamma correction (linear to sRGB)
    mask = rgb_linear > 0.0031308
    rgb_normalized = np.where(
        mask,
        1.055 * np.power(np.maximum(rgb_linear, 0), 1/2.4) - 0.055,
        12.92 * rgb_linear
    )

    # Clamp and scale to [0, 255]
    rgb = np.clip(rgb_normalized * 255, 0, 255)

    return rgb


def lab_to_rgb(lab: NDArray[np.float64]) -> NDArray[np.float64]:
    """Convert LAB to RGB color space.

    Args:
        lab: LAB values with shape (..., 3)

    Returns:
        RGB values in range [0, 255] with shape (..., 3)
    """
    xyz = lab_to_xyz(lab)
    return xyz_to_rgb(xyz)
