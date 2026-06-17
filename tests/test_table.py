"""Round-trip tests for the canonical table serialization (table.py)."""

import pytest

from plotmeta import table
from plotmeta.schema import Annotation, Axis, FigureMeta, PlotMeta, Series


def _roundtrip(meta: FigureMeta) -> FigureMeta:
    return table.loads(table.dumps(meta))


class TestRoundTrip:
    def test_magic_header(self):
        text = table.dumps(FigureMeta())
        assert text.startswith("# plotmeta v0.1")

    def test_line_series(self):
        meta = FigureMeta(
            suptitle="Fig",
            plots=[
                PlotMeta(
                    title="P",
                    x_axis=Axis(
                        label="Time", units="s", scale="linear", range=[0.0, 3.0]
                    ),
                    y_axis=Axis(label="Voltage", units="V"),
                    series=[
                        Series(
                            label="A",
                            plot_type="line",
                            x=[1.0, 2.0, 3.0],
                            y=[4.0, 5.0, 6.0],
                            color="#1f77b4",
                            linestyle="-",
                        )
                    ],
                )
            ],
        )
        assert _roundtrip(meta) == meta

    def test_categorical_bar(self):
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
        assert _roundtrip(meta) == meta

    def test_errorbars(self):
        meta = FigureMeta(
            plots=[
                PlotMeta(
                    series=[
                        Series(
                            label="M",
                            plot_type="errorbar",
                            x=[1.0, 2.0],
                            y=[10.0, 20.0],
                            y_err_lo=[9.0, 18.0],
                            y_err_hi=[11.0, 22.0],
                            error_type="95% CI",
                        )
                    ]
                )
            ]
        )
        assert _roundtrip(meta) == meta

    def test_multi_panel(self):
        meta = FigureMeta(
            suptitle="Multi",
            plots=[
                PlotMeta(
                    title="L",
                    subplot_index=0,
                    subplot_grid=[1, 2],
                    series=[Series(label="l", x=[1.0], y=[2.0])],
                ),
                PlotMeta(
                    title="R",
                    subplot_index=1,
                    subplot_grid=[1, 2],
                    series=[Series(label="r", x=[3.0], y=[4.0])],
                ),
            ],
        )
        assert _roundtrip(meta) == meta

    def test_annotations(self):
        meta = FigureMeta(
            plots=[
                PlotMeta(
                    series=[Series(x=[1.0], y=[2.0])],
                    annotations=[Annotation(text="Peak", x=1.0, y=2.0)],
                )
            ]
        )
        assert _roundtrip(meta) == meta

    def test_unicode_units(self):
        meta = FigureMeta(
            plots=[
                PlotMeta(
                    x_axis=Axis(label="Resistance", units="Ω"),
                    y_axis=Axis(label="Current", units="μA"),
                    series=[Series(label="A", x=[1.0], y=[2.0])],
                )
            ]
        )
        assert _roundtrip(meta) == meta

    def test_empty_figure(self):
        assert _roundtrip(FigureMeta()) == FigureMeta()

    def test_data_rows_are_tsv(self):
        meta = FigureMeta(plots=[PlotMeta(series=[Series(x=[1.0, 2.0], y=[3.0, 4.0])])])
        text = table.dumps(meta)
        assert "1.0\t3.0" in text
        assert "2.0\t4.0" in text

    def test_bad_payload_raises(self):
        with pytest.raises(ValueError, match="missing magic"):
            table.loads("not a plotmeta file")
