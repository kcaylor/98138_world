"""Fixtures for the build-sheet tests (006): the official layout and full synthetic layouts."""

import pytest

from lego_image_processor.kit import load_official_design

from .layouts import FEW, WITH_UNCITED, full_grid


@pytest.fixture(scope="session")
def official_grid():
    return load_official_design().to_layout()


@pytest.fixture(scope="session")
def few_grid():
    return full_grid(FEW)


@pytest.fixture(scope="session")
def uncited_grid():
    return full_grid(WITH_UNCITED)
