"""Human-readable renderings of a FigureMeta (plain text + CSV).

Kept separate from the data model in schema.py: this is presentation, and it
grows independently (the invisible-PDF text-table format builds on it).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .schema import Axis, FigureMeta, PlotMeta


def to_text(meta: FigureMeta) -> str:
    """Render a figure as indented, human-readable plain text."""
    parts: list[str] = []
    if meta.suptitle:
        parts.append(f"Figure: {meta.suptitle}")
    for i, plot in enumerate(meta.plots):
        parts.append(_plot_to_text(plot, i, len(meta.plots)))
    return "\n\n".join(parts)


def to_csv(meta: FigureMeta, separator: str = ",") -> str:
    """Render a figure as one CSV block per series."""
    blocks: list[str] = []
    for pi, plot in enumerate(meta.plots):
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
