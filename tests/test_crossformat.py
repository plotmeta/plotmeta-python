"""Same metadata in, same metadata out — regardless of PNG / SVG / PDF."""

import shutil
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest

import plotmeta

FORMATS = ["png", "svg", "pdf"]


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close("all")


def _make_figure():
    fig, (ax1, ax2) = plt.subplots(1, 2)
    fig.suptitle("Cross-format")

    ax1.plot([1, 2, 3], [4, 5, 6], label="line", color="tab:blue")
    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel("Voltage (V)")
    ax1.set_title("Panel A")

    ax2.bar(["Control", "Treated"], [12.3, 18.7], label="yields")
    ax2.set_ylabel("Resistance (Ω)")
    ax2.set_title("Panel B")
    return fig


class TestCrossFormatParity:
    def test_all_formats_load_identically(self, tmp_path: Path):
        fig = _make_figure()
        reference = plotmeta.extract(fig)

        loaded = {}
        for fmt in FORMATS:
            out = plotmeta.savefig(fig, tmp_path / f"fig.{fmt}")
            assert out.exists()
            loaded[fmt] = plotmeta.load(out)

        # every format reloads to exactly the live-figure metadata
        for fmt in FORMATS:
            assert loaded[fmt] == reference, f"{fmt} differs from live extract"

        # and therefore to each other
        assert loaded["png"] == loaded["svg"] == loaded["pdf"]

    def test_to_pandas_parity(self, tmp_path: Path):
        fig = _make_figure()
        frames = {}
        for fmt in FORMATS:
            out = plotmeta.savefig(fig, tmp_path / f"fig.{fmt}")
            frames[fmt] = plotmeta.to_pandas(out)

        for fmt in FORMATS:
            # panel A line data identical across formats
            a_png = frames["png"][0]
            a_fmt = frames[fmt][0]
            assert list(a_fmt["Voltage"]) == list(a_png["Voltage"])

    def test_plain_files_return_none(self, tmp_path: Path):
        fig = _make_figure()
        for fmt in FORMATS:
            path = tmp_path / f"plain.{fmt}"
            fig.savefig(path)  # no plotmeta
            assert plotmeta.load(path) is None


class TestPdfChannels:
    def test_lossless_marker_present(self, tmp_path: Path):
        fig = _make_figure()
        out = plotmeta.savefig(fig, tmp_path / "fig.pdf")
        assert b"% plotmeta-data:" in out.read_bytes()

    @pytest.mark.skipif(
        shutil.which("pdftotext") is None, reason="pdftotext not installed"
    )
    def test_invisible_text_is_extractable(self, tmp_path: Path):
        fig = _make_figure()
        out = plotmeta.savefig(fig, tmp_path / "fig.pdf")
        text = subprocess.run(
            ["pdftotext", "-raw", str(out), "-"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        # the data table is readable by a plain PDF text extractor
        assert "plotmeta" in text
        assert "12.3" in text
        assert "Control" in text
