"""Seamless integration with matplotlib's native savefig(metadata=...)."""

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


class TestMetadataDict:
    def test_returns_data_keyword(self):
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [4, 5, 6])

        md = plotmeta.metadata(fig)
        assert set(md) == {"data"}

    def test_value_is_table_payload(self):
        fig, ax = plt.subplots()
        ax.plot([1, 2], [3, 4])

        value = plotmeta.metadata(fig)["data"]
        # canonical table format: magic header + TSV data rows
        assert value.startswith("# plotmeta")
        assert "\t" in value


class TestNativeSavefigRoundtrip:
    def test_fig_savefig_metadata(self, tmp_path: Path):
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [4, 5, 6], label="native")
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Voltage (V)")
        ax.set_title("Native")

        path = tmp_path / "native.png"
        fig.savefig(path, metadata=plotmeta.metadata(fig))

        meta = plotmeta.load(path)
        assert meta is not None
        assert meta.plots[0].title == "Native"
        assert meta.plots[0].x_axis.label == "Time"
        assert meta.plots[0].x_axis.units == "s"
        s = meta.plots[0].series[0]
        assert s.label == "native"
        assert s.x == [1.0, 2.0, 3.0]
        assert s.y == [4.0, 5.0, 6.0]

    def test_merge_with_user_keys(self, tmp_path: Path):
        fig, ax = plt.subplots()
        ax.plot([1, 2], [3, 4])

        path = tmp_path / "merged.png"
        fig.savefig(path, metadata={**plotmeta.metadata(fig), "Author": "Jane"})

        # plotmeta still readable alongside the user's own PNG metadata
        assert plotmeta.load(path) is not None

    def test_matches_savefig_wrapper(self, tmp_path: Path):
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [10, 20, 30], label="A")
        ax.set_xlabel("X (m)")

        native = tmp_path / "native.png"
        wrapped = tmp_path / "wrapped.png"
        fig.savefig(native, metadata=plotmeta.metadata(fig))
        plotmeta.savefig(fig, wrapped)

        assert plotmeta.load(native).to_dict() == plotmeta.load(wrapped).to_dict()


class TestExtract:
    def test_extract_returns_figuremeta(self):
        fig, ax = plt.subplots()
        ax.plot([1, 2], [3, 4], label="A")

        meta = plotmeta.extract(fig)
        assert isinstance(meta, plotmeta.FigureMeta)
        assert meta.plots[0].series[0].label == "A"
