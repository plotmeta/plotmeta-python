"""Extract structured data from matplotlib figures."""

from __future__ import annotations

import io
from pathlib import Path

import numpy as np
from matplotlib.axes import Axes
from matplotlib.container import BarContainer, ErrorbarContainer
from matplotlib.figure import Figure

from ..schema import Annotation, Axis, FigureMeta, PlotMeta, Series

SIGNIFICANT_FIGURES = 6


def extract_axes(
    ax: Axes, subplot_index: int = 0, subplot_grid: list[int] | None = None
) -> PlotMeta:
    """Extract all visible data from a single matplotlib Axes."""
    plot = PlotMeta(
        title=ax.get_title() or None,
        subplot_index=subplot_index,
        subplot_grid=subplot_grid,
        x_axis=_extract_axis(ax, "x"),
        y_axis=_extract_axis(ax, "y"),
    )

    errorbar_children: set[int] = set()
    for container in ax.containers:
        if isinstance(container, ErrorbarContainer):
            for child in container.get_children():
                errorbar_children.add(id(child))

    _extract_lines(ax, plot, errorbar_children)
    _extract_scatter(ax, plot)
    _extract_bars(ax, plot)
    _extract_errorbars(ax, plot)
    _extract_annotations(ax, plot)

    return plot


def extract_figure(fig: Figure) -> FigureMeta:
    """Extract metadata from all axes in a figure."""
    axes = [ax for ax in fig.get_axes() if not _is_colorbar(ax)]
    nrows, ncols = _infer_grid(axes)

    return FigureMeta(
        suptitle=fig._suptitle.get_text() if fig._suptitle else None,
        plots=[extract_axes(ax, i, [nrows, ncols]) for i, ax in enumerate(axes)],
    )


def save(fig: Figure, path: str | Path, **savefig_kwargs) -> Path:
    """Save a matplotlib figure to PNG with embedded plotmeta."""
    from ..transports import png

    path = Path(path)
    meta = extract_figure(fig)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", **savefig_kwargs)
    enriched = png.inject(buf.getvalue(), meta.to_json())
    path.write_bytes(enriched)

    return path


# -- line plots ---------------------------------------------------------------


def _extract_lines(ax: Axes, plot: PlotMeta, skip_ids: set[int]) -> None:
    for line in ax.get_lines():
        if id(line) in skip_ids:
            continue
        xd, yd = line.get_xdata(), line.get_ydata()
        if len(xd) == 0:
            continue
        label = line.get_label()
        plot.series.append(
            Series(
                label=label if not label.startswith("_") else None,
                plot_type="line",
                x=_round_list(xd),
                y=_round_list(yd),
                color=_to_hex(line.get_color()),
                marker=_clean_marker(line.get_marker()),
                linestyle=_clean_linestyle(line.get_linestyle()),
            )
        )


# -- scatter plots -------------------------------------------------------------


def _extract_scatter(ax: Axes, plot: PlotMeta) -> None:
    for coll in ax.collections:
        if type(coll).__name__ != "PathCollection":
            continue
        offsets = coll.get_offsets()
        if offsets is None or len(offsets) == 0:
            continue
        data = np.asarray(offsets)
        label = coll.get_label()
        colors = coll.get_facecolors()
        plot.series.append(
            Series(
                label=label if not label.startswith("_") else None,
                plot_type="scatter",
                x=_round_list(data[:, 0]),
                y=_round_list(data[:, 1]),
                color=_to_hex(colors[0] if len(colors) > 0 else None),
            )
        )


# -- bar plots -----------------------------------------------------------------


def _extract_bars(ax: Axes, plot: PlotMeta) -> None:
    for container in ax.containers:
        if not isinstance(container, BarContainer):
            continue
        xs, heights = [], []
        for rect in container:
            xs.append(float(rect.get_x() + rect.get_width() / 2))
            heights.append(float(rect.get_height()))

        label = container.get_label()
        tick_labels = plot.x_axis.ticks
        if (
            tick_labels
            and isinstance(tick_labels[0], str)
            and len(tick_labels) == len(xs)
        ):
            x_values = tick_labels
        else:
            x_values = _round_floats(xs)

        plot.series.append(
            Series(
                label=label if not label.startswith("_") else None,
                plot_type="bar",
                x=x_values,
                y=_round_floats(heights),
            )
        )


# -- error bars ----------------------------------------------------------------


def _extract_errorbars(ax: Axes, plot: PlotMeta) -> None:
    for container in ax.containers:
        if not isinstance(container, ErrorbarContainer):
            continue
        data_line = container[0]
        if data_line is None:
            continue
        xd = data_line.get_xdata()
        yd = data_line.get_ydata()
        y_lo, y_hi = _errorbar_bounds(container, yd)
        label = container.get_label()
        plot.series.append(
            Series(
                label=label if not label.startswith("_") else None,
                plot_type="errorbar",
                x=_round_list(xd),
                y=_round_list(yd),
                y_err_lo=y_lo,
                y_err_hi=y_hi,
            )
        )


def _errorbar_bounds(container: ErrorbarContainer, y_data) -> tuple:
    try:
        barlines = container[2]
        if barlines:
            segments = barlines[0].get_segments()
            lo = [_round_float(seg[0, 1]) for seg in segments]
            hi = [_round_float(seg[1, 1]) for seg in segments]
            return lo, hi
    except (IndexError, TypeError):
        pass
    return None, None


# -- annotations ---------------------------------------------------------------


def _extract_annotations(ax: Axes, plot: PlotMeta) -> None:
    for txt in ax.texts:
        content = txt.get_text().strip()
        if content:
            pos = txt.get_position()
            plot.annotations.append(
                Annotation(
                    text=content,
                    x=_round_float(pos[0]),
                    y=_round_float(pos[1]),
                )
            )


# -- axis extraction -----------------------------------------------------------


def _extract_axis(ax: Axes, which: str) -> Axis:
    if which == "x":
        label = ax.get_xlabel() or None
        scale = ax.get_xscale()
        lim = ax.get_xlim()
        ticks = ax.get_xticks()
        tick_labels = [t.get_text() for t in ax.get_xticklabels()]
    else:
        label = ax.get_ylabel() or None
        scale = ax.get_yscale()
        lim = ax.get_ylim()
        ticks = ax.get_yticks()
        tick_labels = [t.get_text() for t in ax.get_yticklabels()]

    units = None
    if label and "(" in label and label.endswith(")"):
        parts = label.rsplit("(", 1)
        label = parts[0].strip()
        units = parts[1][:-1].strip()

    categories = _detect_categories(tick_labels)

    return Axis(
        label=label,
        units=units,
        scale=scale,
        range=[_round_float(lim[0]), _round_float(lim[1])],
        ticks=categories or _round_floats(ticks.tolist()),
    )


def _detect_categories(tick_labels: list[str]) -> list[str] | None:
    non_empty = [t for t in tick_labels if t.strip()]
    if not non_empty:
        return None
    try:
        [float(t.replace("−", "-")) for t in non_empty]
        return None
    except ValueError:
        return non_empty


# -- helpers -------------------------------------------------------------------


def _round_float(v: float) -> float:
    if v == 0:
        return 0.0
    from math import floor, log10

    magnitude = floor(log10(abs(v)))
    factor = 10 ** (SIGNIFICANT_FIGURES - 1 - magnitude)
    return round(v * factor) / factor


def _round_floats(vals: list) -> list[float]:
    return [_round_float(float(v)) for v in vals]


def _round_list(arr) -> list[float]:
    return [_round_float(float(v)) for v in np.asarray(arr)]


def _to_hex(color) -> str | None:
    if color is None:
        return None
    try:
        from matplotlib.colors import to_hex

        return to_hex(color)
    except Exception:
        return None


def _clean_marker(marker: str) -> str | None:
    if marker in ("None", "none", ""):
        return None
    return marker


def _clean_linestyle(ls: str) -> str | None:
    if ls in ("None", "none", ""):
        return None
    return ls


def _infer_grid(axes: list) -> tuple[int, int]:
    if len(axes) <= 1:
        return (1, 1)
    positions = [ax.get_position() for ax in axes]
    nrows = len({round(p.y0, 2) for p in positions})
    ncols = len({round(p.x0, 2) for p in positions})
    return (nrows, ncols)


def _is_colorbar(ax: Axes) -> bool:
    pos = ax.get_position()
    aspect = pos.width / max(pos.height, 1e-6)
    return aspect < 0.15 or aspect > 8
