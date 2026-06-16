"""Tests for the top-level plotmeta API."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest

import plotmeta


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close("all")


class TestSavefigAndLoad:
    def test_roundtrip(self, tmp_path: Path):
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [4, 5, 6], label="test")
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Voltage (V)")
        ax.set_title("My Plot")

        out = plotmeta.savefig(fig, tmp_path / "fig.png")
        meta = plotmeta.load(out)

        assert meta is not None
        assert meta.plots[0].title == "My Plot"
        assert meta.plots[0].x_axis.label == "Time"
        assert meta.plots[0].x_axis.units == "s"
        assert meta.plots[0].series[0].label == "test"
        assert meta.plots[0].series[0].x == [1.0, 2.0, 3.0]
        assert meta.plots[0].series[0].y == [4.0, 5.0, 6.0]

    def test_no_sidecar_created(self, tmp_path: Path):
        fig, ax = plt.subplots()
        ax.plot([1], [1])

        plotmeta.savefig(fig, tmp_path / "fig.png")
        assert not (tmp_path / "fig.plotmeta.json").exists()

    def test_load_plain_png_returns_none(self, tmp_path: Path):
        fig, ax = plt.subplots()
        ax.plot([1], [1])
        path = tmp_path / "plain.png"
        fig.savefig(path)

        assert plotmeta.load(path) is None

    def test_load_unsupported_format_raises(self, tmp_path: Path):
        path = tmp_path / "fig.bmp"
        path.write_bytes(b"fake")
        with pytest.raises(ValueError, match="Unsupported format"):
            plotmeta.load(path)

    def test_savefig_with_kwargs(self, tmp_path: Path):
        fig, ax = plt.subplots()
        ax.plot([1], [1])

        out = plotmeta.savefig(fig, tmp_path / "fig.png", dpi=72)
        assert out.exists()
        assert plotmeta.load(out) is not None


class TestToPandas:
    def test_from_figure(self):
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [4, 5, 6], label="data")
        ax.set_xlabel("X (m)")
        ax.set_ylabel("Y (m)")

        df = plotmeta.to_pandas(fig)
        assert "X" in df.columns
        assert "Y" in df.columns
        assert "series" in df.columns
        assert list(df["X"]) == [1.0, 2.0, 3.0]
        assert list(df["Y"]) == [4.0, 5.0, 6.0]

    def test_from_file(self, tmp_path: Path):
        fig, ax = plt.subplots()
        ax.plot([1, 2], [3, 4], label="A")
        ax.set_xlabel("Time (s)")
        plotmeta.savefig(fig, tmp_path / "fig.png")

        df = plotmeta.to_pandas(tmp_path / "fig.png")
        assert "Time" in df.columns

    def test_from_meta_object(self):
        from plotmeta.schema import Axis, FigureMeta, PlotMeta, Series

        meta = FigureMeta(
            plots=[
                PlotMeta(
                    title="Test",
                    x_axis=Axis(label="X", units="m"),
                    y_axis=Axis(label="Y"),
                    series=[Series(label="A", x=[1.0, 2.0], y=[3.0, 4.0])],
                )
            ]
        )
        df = plotmeta.to_pandas(meta)
        assert df.attrs["title"] == "Test"
        assert df.attrs["x_units"] == "m"

    def test_multi_panel(self):
        fig, (ax1, ax2) = plt.subplots(1, 2)
        ax1.plot([1, 2], [3, 4], label="left")
        ax2.plot([5, 6], [7, 8], label="right")

        dfs = plotmeta.to_pandas(fig)
        assert isinstance(dfs, list)
        assert len(dfs) == 2

    def test_multi_series_per_panel(self):
        fig, ax = plt.subplots()
        ax.plot([1, 2], [3, 4], label="A")
        ax.plot([1, 2], [5, 6], label="B")

        df = plotmeta.to_pandas(fig)
        assert set(df["series"].unique()) == {"A", "B"}
        assert len(df) == 4

    def test_no_metadata_raises(self, tmp_path: Path):
        fig, ax = plt.subplots()
        ax.plot([1], [1])
        path = tmp_path / "plain.png"
        fig.savefig(path)

        with pytest.raises(ValueError, match="No plotmeta found"):
            plotmeta.to_pandas(path)
