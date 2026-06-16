"""Round-trip tests for the matplotlib writer."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest

from plotmeta.schema import FigureMeta
from plotmeta.transports import png
from plotmeta.writers.matplotlib import extract_axes, extract_figure, save


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close("all")


class TestLineExtraction:
    def test_basic_line(self):
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [4, 5, 6], label="data")
        ax.set_xlabel("X (m)")
        ax.set_ylabel("Y (m)")
        ax.set_title("Test")

        plot = extract_axes(ax)
        assert plot.title == "Test"
        assert plot.x_axis.label == "X"
        assert plot.x_axis.units == "m"
        assert len(plot.series) == 1
        s = plot.series[0]
        assert s.label == "data"
        assert s.plot_type == "line"
        assert s.x == [1.0, 2.0, 3.0]
        assert s.y == [4.0, 5.0, 6.0]

    def test_unlabeled_line(self):
        fig, ax = plt.subplots()
        ax.plot([1, 2], [3, 4])

        plot = extract_axes(ax)
        assert plot.series[0].label is None

    def test_multi_line(self):
        fig, ax = plt.subplots()
        ax.plot([1, 2], [3, 4], label="A")
        ax.plot([1, 2], [5, 6], label="B")

        plot = extract_axes(ax)
        assert len(plot.series) == 2
        assert plot.series[0].label == "A"
        assert plot.series[1].label == "B"


class TestScatterExtraction:
    def test_basic_scatter(self):
        fig, ax = plt.subplots()
        ax.scatter([1, 2, 3], [4, 5, 6], label="points")

        plot = extract_axes(ax)
        assert len(plot.series) == 1
        s = plot.series[0]
        assert s.label == "points"
        assert s.plot_type == "scatter"
        assert s.x == [1.0, 2.0, 3.0]
        assert s.y == [4.0, 5.0, 6.0]


class TestBarExtraction:
    def test_basic_bar(self):
        fig, ax = plt.subplots()
        ax.bar(["A", "B", "C"], [10, 20, 30])

        plot = extract_axes(ax)
        assert len(plot.series) == 1
        s = plot.series[0]
        assert s.plot_type == "bar"
        assert s.x == ["A", "B", "C"]
        assert s.y == [10.0, 20.0, 30.0]

    def test_numeric_bar(self):
        fig, ax = plt.subplots()
        ax.bar([1, 2, 3], [10, 20, 30], label="vals")

        plot = extract_axes(ax)
        s = plot.series[0]
        assert s.plot_type == "bar"
        assert len(s.x) == 3
        assert s.y == [10.0, 20.0, 30.0]


class TestErrorbarExtraction:
    def test_basic_errorbar(self):
        fig, ax = plt.subplots()
        ax.errorbar([1, 2, 3], [10, 20, 30], yerr=[1, 2, 3], label="measured")

        plot = extract_axes(ax)
        errbar_series = [s for s in plot.series if s.plot_type == "errorbar"]
        assert len(errbar_series) == 1
        s = errbar_series[0]
        assert s.label == "measured"
        assert s.x == [1.0, 2.0, 3.0]
        assert s.y == [10.0, 20.0, 30.0]
        assert s.y_err_lo is not None
        assert s.y_err_hi is not None


class TestAnnotationExtraction:
    def test_text_annotation(self):
        fig, ax = plt.subplots()
        ax.plot([1, 2], [3, 4])
        ax.annotate("Peak", xy=(2, 4))

        plot = extract_axes(ax)
        assert len(plot.annotations) == 1
        assert plot.annotations[0].text == "Peak"


class TestAxisParsing:
    def test_unit_parsing(self):
        fig, ax = plt.subplots()
        ax.plot([1], [1])
        ax.set_xlabel("Pressure (kPa)")
        ax.set_ylabel("Temperature (°C)")

        plot = extract_axes(ax)
        assert plot.x_axis.label == "Pressure"
        assert plot.x_axis.units == "kPa"
        assert plot.y_axis.label == "Temperature"
        assert plot.y_axis.units == "°C"

    def test_no_units(self):
        fig, ax = plt.subplots()
        ax.plot([1], [1])
        ax.set_xlabel("Count")

        plot = extract_axes(ax)
        assert plot.x_axis.label == "Count"
        assert plot.x_axis.units is None

    def test_log_scale(self):
        fig, ax = plt.subplots()
        ax.plot([1, 10, 100], [1, 2, 3])
        ax.set_xscale("log")

        plot = extract_axes(ax)
        assert plot.x_axis.scale == "log"


class TestFigureExtraction:
    def test_suptitle(self):
        fig, ax = plt.subplots()
        fig.suptitle("Big Title")
        ax.plot([1], [1])

        meta = extract_figure(fig)
        assert meta.suptitle == "Big Title"
        assert len(meta.plots) == 1

    def test_multi_panel(self):
        fig, (ax1, ax2) = plt.subplots(1, 2)
        ax1.plot([1, 2], [3, 4], label="left")
        ax2.scatter([5, 6], [7, 8], label="right")

        meta = extract_figure(fig)
        assert len(meta.plots) == 2
        assert meta.plots[0].subplot_grid == [1, 2]


class TestSaveRoundTrip:
    def test_save_and_read_png(self, tmp_path: Path):
        fig, ax = plt.subplots()
        ax.plot([1, 2, 3], [4, 5, 6], label="test")
        ax.set_xlabel("X (m)")

        out = save(fig, tmp_path / "fig.png")
        assert out.exists()

        raw = png.extract(out.read_bytes())
        meta = FigureMeta.from_json(raw)
        assert meta.plots[0].series[0].label == "test"
        assert meta.plots[0].x_axis.units == "m"

    def test_save_with_kwargs(self, tmp_path: Path):
        fig, ax = plt.subplots()
        ax.plot([1], [1])

        out = save(fig, tmp_path / "fig.png", dpi=72)
        assert out.exists()
