"""Canonical plotmeta serialization: structured header + TSV data blocks.

This is the single text format embedded in *every* transport (PNG chunk, SVG
element, PDF marker). It is the lossless source of truth for `load()`.

Layout::

    # plotmeta v0.1
    # figure {"schema_version": "0.1.0"}
    # plot {"title": "...", "x_axis": {...}, "y_axis": {...}}
    # series {"label": "A", "plot_type": "line", "columns": ["x", "y"]}
    Time (s)\tVoltage (V)
    1.0\t4.0
    2.0\t5.0

Design:
- Metadata lives in ``# <kind> <json>`` header lines (structured, safe to
  parse). Lines beginning with ``#`` are skipped by numpy.loadtxt / pandas.
- The bulk numeric data is plain TSV, one block per series, blocks separated
  by blank lines (gnuplot convention). The first row of each block is a
  human-readable column header; the machine-readable column *roles* are in
  the series JSON, so the header text is cosmetic.
"""

from __future__ import annotations

import json

from .schema import (
    SCHEMA_VERSION,
    Annotation,
    Axis,
    FigureMeta,
    PlotMeta,
    Series,
    _strip_none,
)

MAGIC = "# plotmeta v0.1"

# series.<attr> reachable as a TSV column, in stable order
_ERROR_COLS = ("y_err_lo", "y_err_hi", "x_err_lo", "x_err_hi")


def dumps(meta: FigureMeta) -> str:
    """Serialize a FigureMeta to the canonical text format."""
    lines: list[str] = [MAGIC]

    fig_header = {"schema_version": meta.schema_version}
    if meta.suptitle is not None:
        fig_header["suptitle"] = meta.suptitle
    lines.append("# figure " + json.dumps(fig_header))

    for plot in meta.plots:
        lines.append("")
        lines.append("# plot " + json.dumps(_plot_header(plot)))
        for series in plot.series:
            _dump_series(lines, plot, series)

    return "\n".join(lines) + "\n"


def loads(text: str) -> FigureMeta:
    """Parse the canonical text format back into a FigureMeta."""
    lines = text.split("\n")
    if not lines or not lines[0].startswith("# plotmeta"):
        raise ValueError("Not a plotmeta payload (missing magic header)")

    meta = FigureMeta()
    plot: PlotMeta | None = None
    series: Series | None = None
    cols: list[str] = []
    expect_header = False

    for line in lines[1:]:
        if line.strip() == "":
            series = None
            continue

        if line.startswith("# "):
            kind, _, rest = line[2:].partition(" ")
            if kind == "figure":
                obj = json.loads(rest)
                meta.schema_version = obj.get("schema_version", SCHEMA_VERSION)
                meta.suptitle = obj.get("suptitle")
            elif kind == "plot":
                plot = _build_plot(json.loads(rest))
                meta.plots.append(plot)
                series = None
            elif kind == "series":
                obj = json.loads(rest)
                cols = obj["columns"]
                series = _build_series(obj)
                if plot is None:  # defensive: series before any plot
                    plot = PlotMeta()
                    meta.plots.append(plot)
                plot.series.append(series)
                expect_header = True
            # any other "# ..." line is a comment; ignore
            continue

        # data row
        if series is None:
            continue
        if expect_header:
            expect_header = False
            continue
        _read_row(series, cols, line.split("\t"))

    return meta


# -- dump helpers --------------------------------------------------------------


def _plot_header(plot: PlotMeta) -> dict:
    header = {
        "title": plot.title,
        "subplot_index": plot.subplot_index,
        "subplot_grid": plot.subplot_grid,
        "x_axis": _axis_dict(plot.x_axis),
        "y_axis": _axis_dict(plot.y_axis),
        "annotations": [_strip_none(vars(a)) for a in plot.annotations] or None,
        "colorbar_label": plot.colorbar_label,
    }
    return _strip_none(header)


def _axis_dict(axis: Axis) -> dict:
    return _strip_none(vars(axis))


def _dump_series(lines: list[str], plot: PlotMeta, series: Series) -> None:
    cols = _series_columns(series)
    header = {"label": series.label, "plot_type": series.plot_type, "columns": cols}
    for attr in ("color", "marker", "linestyle", "error_type"):
        value = getattr(series, attr)
        if value is not None:
            header[attr] = value

    lines.append("")
    lines.append("# series " + json.dumps(_strip_none(header)))
    if not cols:
        return

    lines.append("\t".join(_column_name(plot, col) for col in cols))
    col_values = [getattr(series, col) for col in cols]
    n = max((len(v) for v in col_values), default=0)
    for i in range(n):
        row = [_fmt(v[i]) if i < len(v) else "" for v in col_values]
        lines.append("\t".join(row))


def _series_columns(series: Series) -> list[str]:
    cols: list[str] = []
    if series.x:
        cols.append("x")
    if series.y:
        cols.append("y")
    cols += [c for c in _ERROR_COLS if getattr(series, c)]
    return cols


def _column_name(plot: PlotMeta, col: str) -> str:
    if col in ("x", "y"):
        axis = plot.x_axis if col == "x" else plot.y_axis
        name = axis.label or col
        return f"{name} ({axis.units})" if axis.units else name
    return col


def _fmt(value: float | str) -> str:
    return value if isinstance(value, str) else repr(value)


# -- load helpers --------------------------------------------------------------


def _build_plot(obj: dict) -> PlotMeta:
    return PlotMeta(
        title=obj.get("title"),
        subplot_index=obj.get("subplot_index"),
        subplot_grid=obj.get("subplot_grid"),
        x_axis=Axis(**obj["x_axis"]) if "x_axis" in obj else Axis(),
        y_axis=Axis(**obj["y_axis"]) if "y_axis" in obj else Axis(),
        annotations=[Annotation(**a) for a in obj.get("annotations", [])],
        colorbar_label=obj.get("colorbar_label"),
    )


def _build_series(obj: dict) -> Series:
    return Series(
        label=obj.get("label"),
        plot_type=obj.get("plot_type", "line"),
        color=obj.get("color"),
        marker=obj.get("marker"),
        linestyle=obj.get("linestyle"),
        error_type=obj.get("error_type"),
    )


def _read_row(series: Series, cols: list[str], cells: list[str]) -> None:
    for col, cell in zip(cols, cells):
        target = getattr(series, col)
        if target is None:
            target = []
            setattr(series, col, target)
        target.append(_parse_cell(col, cell))


def _parse_cell(col: str, cell: str) -> float | str:
    if col == "x":
        try:
            return float(cell)
        except ValueError:
            return cell
    return float(cell)
