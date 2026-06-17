"""Smoke test: every script in examples/ runs end-to-end without error.

Keeps the documentation examples from rotting as the API evolves. Each script
is self-contained and writes only to a temp dir, so running them here is
side-effect-free.
"""

import runpy
from pathlib import Path

import matplotlib
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"
EXAMPLE_SCRIPTS = sorted(EXAMPLES_DIR.glob("*.py"))


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close("all")


@pytest.mark.skipif(not EXAMPLE_SCRIPTS, reason="no example scripts found")
@pytest.mark.parametrize("script", EXAMPLE_SCRIPTS, ids=lambda p: p.name)
def test_example_runs(script: Path):
    runpy.run_path(str(script), run_name="__main__")
