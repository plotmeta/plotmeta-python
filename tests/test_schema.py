"""Tests for the plotmeta data model and serialization."""

from plotmeta.schema import (
    SCHEMA_VERSION,
    Annotation,
    Axis,
    FigureMeta,
    PlotMeta,
    Series,
)


def _make_line_plot() -> FigureMeta:
    return FigureMeta(
        suptitle="Test Figure",
        plots=[
            PlotMeta(
                title="Test Plot",
                x_axis=Axis(label="Time", units="s", scale="linear", range=[0.0, 10.0]),
                y_axis=Axis(
                    label="Voltage", units="V", scale="linear", range=[-1.0, 1.0]
                ),
                series=[
                    Series(
                        label="Signal",
                        plot_type="line",
                        x=[0.0, 1.0, 2.0, 3.0],
                        y=[0.0, 0.5, 0.8, 0.3],
                        color="#1f77b4",
                    ),
                ],
                annotations=[Annotation(text="Peak", x=2.0, y=0.8)],
            )
        ],
    )


class TestJsonRoundTrip:
    def test_to_json_and_back(self):
        original = _make_line_plot()
        json_str = original.to_json()
        restored = FigureMeta.from_json(json_str)

        assert restored.schema_version == SCHEMA_VERSION
        assert restored.suptitle == "Test Figure"
        assert len(restored.plots) == 1
        assert restored.plots[0].title == "Test Plot"

    def test_series_data_preserved(self):
        original = _make_line_plot()
        restored = FigureMeta.from_json(original.to_json())

        s = restored.plots[0].series[0]
        assert s.label == "Signal"
        assert s.plot_type == "line"
        assert s.x == [0.0, 1.0, 2.0, 3.0]
        assert s.y == [0.0, 0.5, 0.8, 0.3]
        assert s.color == "#1f77b4"

    def test_axis_preserved(self):
        original = _make_line_plot()
        restored = FigureMeta.from_json(original.to_json())

        x = restored.plots[0].x_axis
        assert x.label == "Time"
        assert x.units == "s"
        assert x.scale == "linear"
        assert x.range == [0.0, 10.0]

    def test_annotations_preserved(self):
        original = _make_line_plot()
        restored = FigureMeta.from_json(original.to_json())

        a = restored.plots[0].annotations[0]
        assert a.text == "Peak"
        assert a.x == 2.0
        assert a.y == 0.8

    def test_none_fields_stripped_from_json(self):
        meta = FigureMeta(plots=[PlotMeta(series=[Series(x=[1.0], y=[2.0])])])
        d = meta.to_dict()
        series_dict = d["plots"][0]["series"][0]
        assert "y_err_lo" not in series_dict
        assert "marker" not in series_dict

    def test_empty_figure(self):
        meta = FigureMeta()
        restored = FigureMeta.from_json(meta.to_json())
        assert restored.plots == []
        assert restored.suptitle is None


class TestCategoricalSeries:
    def test_string_x_values(self):
        meta = FigureMeta(
            plots=[
                PlotMeta(
                    series=[
                        Series(
                            label="Yields",
                            plot_type="bar",
                            x=["Control", "Treatment A", "Treatment B"],
                            y=[12.3, 18.7, 15.2],
                        )
                    ]
                )
            ]
        )
        restored = FigureMeta.from_json(meta.to_json())
        expected = ["Control", "Treatment A", "Treatment B"]
        assert restored.plots[0].series[0].x == expected


class TestErrorBars:
    def test_error_bar_series(self):
        meta = FigureMeta(
            plots=[
                PlotMeta(
                    series=[
                        Series(
                            label="Measured",
                            plot_type="errorbar",
                            x=[1.0, 2.0, 3.0],
                            y=[10.0, 20.0, 30.0],
                            y_err_lo=[9.0, 18.0, 27.0],
                            y_err_hi=[11.0, 22.0, 33.0],
                            error_type="95% CI",
                        )
                    ]
                )
            ]
        )
        restored = FigureMeta.from_json(meta.to_json())
        s = restored.plots[0].series[0]
        assert s.y_err_lo == [9.0, 18.0, 27.0]
        assert s.y_err_hi == [11.0, 22.0, 33.0]
        assert s.error_type == "95% CI"


class TestMultiPanel:
    def test_subplot_metadata(self):
        meta = FigureMeta(
            suptitle="Multi-panel",
            plots=[
                PlotMeta(title="Left", subplot_index=0, subplot_grid=[1, 2]),
                PlotMeta(title="Right", subplot_index=1, subplot_grid=[1, 2]),
            ],
        )
        restored = FigureMeta.from_json(meta.to_json())
        assert len(restored.plots) == 2
        assert restored.plots[0].subplot_grid == [1, 2]
        assert restored.plots[1].subplot_index == 1


class TestToText:
    def test_basic_output(self):
        meta = _make_line_plot()
        text = meta.to_text()
        assert "Test Figure" in text
        assert "Test Plot" in text
        assert "Time" in text
        assert "Signal" in text
        assert "(0.0, 0.0)" in text

    def test_multiplot_numbering(self):
        meta = FigureMeta(
            plots=[PlotMeta(title="A"), PlotMeta(title="B")],
        )
        text = meta.to_text()
        assert "Plot 1/2: A" in text
        assert "Plot 2/2: B" in text

    def test_long_series_truncated(self):
        meta = FigureMeta(
            plots=[
                PlotMeta(
                    series=[
                        Series(x=list(range(20)), y=list(range(20))),
                    ]
                )
            ]
        )
        text = meta.to_text()
        assert "... (14 more) ..." in text


class TestToCsv:
    def test_basic_csv(self):
        meta = _make_line_plot()
        csv = meta.to_csv()
        assert "Time (s),Voltage (V)" in csv
        assert "0.0,0.0" in csv
        assert "3.0,0.3" in csv

    def test_tsv(self):
        meta = _make_line_plot()
        tsv = meta.to_csv(separator="\t")
        assert "Time (s)\tVoltage (V)" in tsv
