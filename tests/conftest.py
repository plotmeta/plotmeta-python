"""Shared fixtures for plotmeta tests."""

from pathlib import Path

import pytest


@pytest.fixture
def tmp_png(tmp_path: Path) -> Path:
    return tmp_path / "test_figure.png"
