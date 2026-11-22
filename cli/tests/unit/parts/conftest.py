"""Fixtures for the parts tests (005 T002): synthetic layouts and owned/missing CSV files."""

import pytest

from .layouts import SMALL, make_grid


@pytest.fixture
def small_grid():
    return make_grid(SMALL)


@pytest.fixture
def write_csv(tmp_path):
    def _write(name: str, text: str, raw: bytes = None):
        p = tmp_path / name
        p.write_bytes(raw if raw is not None else text.encode("utf-8"))
        return p
    return _write
