"""Data model for plotmeta — describes exactly what a figure shows."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

SCHEMA_VERSION = "0.1.0"
# Key under which the canonical payload is stored in every transport
# (PNG text chunk, SVG element id, matplotlib native metadata).
DATA_KEY = "data"
PNG_CHUNK_KEY = DATA_KEY  # backwards-compatible alias


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

    def to_json(self, indent: int | None = 2) -> str:
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
        """Render as human-readable plain text (see render.to_text)."""
        from . import render

        return render.to_text(self)

    def to_csv(self, separator: str = ",") -> str:
        """Render as one CSV block per series (see render.to_csv)."""
        from . import render

        return render.to_csv(self, separator)


def _strip_none(obj: object) -> object:
    if isinstance(obj, dict):
        return {k: _strip_none(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [_strip_none(item) for item in obj]
    return obj
