"""Data model for plotmeta — describes exactly what a figure shows."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

SCHEMA_VERSION = "0.1.0"
PNG_CHUNK_KEY = "plotmeta"


@dataclass
class Axis:
    label: str | None = None
    units: str | None = None
    scale: str = "linear"
    range: list[float] | None = None
    ticks: list[float | str] | None = None
    inverted: bool = False


@dataclass
class Series:
    label: str | None = None
    plot_type: str = "line"
    x: list[float | str] = field(default_factory=list)
    y: list[float] = field(default_factory=list)

    y_err_lo: list[float] | None = None
    y_err_hi: list[float] | None = None
    x_err_lo: list[float] | None = None
    x_err_hi: list[float] | None = None
    error_type: str | None = None

    bar_edges: list[float] | None = None
    bar_heights: list[float] | None = None

    color: str | None = None
    marker: str | None = None
    linestyle: str | None = None


@dataclass
class Annotation:
    text: str
    x: float | None = None
    y: float | None = None


@dataclass
class PlotMeta:
    """One subplot/axes in a figure."""

    title: str | None = None
    x_axis: Axis = field(default_factory=Axis)
    y_axis: Axis = field(default_factory=Axis)
    series: list[Series] = field(default_factory=list)
    annotations: list[Annotation] = field(default_factory=list)
    subplot_index: int | None = None
    subplot_grid: list[int] | None = None
    colorbar_label: str | None = None


@dataclass
class FigureMeta:
    """Top-level container for an entire figure."""

    schema_version: str = SCHEMA_VERSION
    suptitle: str | None = None
    plots: list[PlotMeta] = field(default_factory=list)

    def to_dict(self) -> dict:
        return _strip_none(asdict(self))

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, d: dict) -> FigureMeta:
        plots = [
            PlotMeta(
                title=p.get("title"),
                x_axis=Axis(**p["x_axis"]) if "x_axis" in p else Axis(),
                y_axis=Axis(**p["y_axis"]) if "y_axis" in p else Axis(),
                series=[Series(**s) for s in p.get("series", [])],
                annotations=[Annotation(**a) for a in p.get("annotations", [])],
                subplot_index=p.get("subplot_index"),
                subplot_grid=p.get("subplot_grid"),
                colorbar_label=p.get("colorbar_label"),
            )
            for p in d.get("plots", [])
        ]
        return cls(
            schema_version=d.get("schema_version", SCHEMA_VERSION),
            suptitle=d.get("suptitle"),
            plots=plots,
        )

    @classmethod
    def from_json(cls, text: str) -> FigureMeta:
        return cls.from_dict(json.loads(text))

    def to_text(self) -> str:
        parts = []
        if self.suptitle:
            parts.append(f"Figure: {self.suptitle}")
        for i, plot in enumerate(self.plots):
            parts.append(_plot_to_text(plot, i, len(self.plots)))
        return "\n\n".join(parts)

    def to_csv(self, separator: str = ",") -> str:
        blocks: list[str] = []
        for pi, plot in enumerate(self.plots):
            plot_label = plot.title or f"Plot {pi}"
            for si, s in enumerate(plot.series):
                series_label = s.label or f"Series {si}"
                blocks.append(f"# {plot_label} / {series_label} ({s.plot_type})")
                if s.x and s.y:
                    x_col = _axis_column_name(plot.x_axis)
                    y_col = _axis_column_name(plot.y_axis)
                    blocks.append(f"{x_col}{separator}{y_col}")
                    for x, y in zip(s.x, s.y):
                        blocks.append(f"{x}{separator}{y}")
                elif s.bar_edges and s.bar_heights:
                    blocks.append(f"bin_lo{separator}bin_hi{separator}count")
                    for j, h in enumerate(s.bar_heights):
                        lo = s.bar_edges[j]
                        hi = s.bar_edges[j + 1] if j + 1 < len(s.bar_edges) else ""
                        blocks.append(f"{lo}{separator}{hi}{separator}{h}")
                blocks.append("")
        return "\n".join(blocks)


def _strip_none(obj: object) -> object:
    if isinstance(obj, dict):
        return {k: _strip_none(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [_strip_none(item) for item in obj]
    return obj


def _axis_column_name(axis: Axis) -> str:
    name = axis.label or "x"
    if axis.units:
        name += f" ({axis.units})"
    return name


def _plot_to_text(plot: PlotMeta, index: int, total: int) -> str:
    lines: list[str] = []

    header = f"Plot {index + 1}/{total}" if total > 1 else "Plot"
    if plot.title:
        header += f": {plot.title}"
    lines.append(header)

    for name, axis in [("X-axis", plot.x_axis), ("Y-axis", plot.y_axis)]:
        desc = name
        if axis.label:
            desc += f": {axis.label}"
        if axis.units:
            desc += f" ({axis.units})"
        desc += f" [{axis.scale}"
        if axis.range:
            desc += f", {axis.range[0]} to {axis.range[1]}"
        desc += "]"
        lines.append(f"  {desc}")

    for s in plot.series:
        tag = s.label or "(unlabeled)"
        n = max(len(s.x), len(s.y), len(s.bar_heights or []))
        lines.append(f"  Series '{tag}' ({s.plot_type}, {n} points):")

        if s.x and s.y:
            pairs = list(zip(s.x, s.y))
            if len(pairs) <= 8:
                for x, y in pairs:
                    lines.append(f"    ({x}, {y})")
            else:
                for x, y in pairs[:3]:
                    lines.append(f"    ({x}, {y})")
                lines.append(f"    ... ({len(pairs) - 6} more) ...")
                for x, y in pairs[-3:]:
                    lines.append(f"    ({x}, {y})")
        elif s.bar_edges and s.bar_heights:
            edge_sfx = "..." if len(s.bar_edges) > 5 else ""
            ht_sfx = "..." if len(s.bar_heights) > 5 else ""
            lines.append(f"    edges: {s.bar_edges[:5]}{edge_sfx}")
            lines.append(f"    heights: {s.bar_heights[:5]}{ht_sfx}")

        if s.error_type:
            lines.append(f"    errors: {s.error_type}")

    for a in plot.annotations:
        lines.append(f'  Annotation: "{a.text}" at ({a.x}, {a.y})')

    if plot.colorbar_label:
        lines.append(f"  Colorbar: {plot.colorbar_label}")

    return "\n".join(lines)
