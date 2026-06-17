"""plotmeta — embed and extract exact plot data from scientific figures."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from .reader import load
from .save import metadata
from .save import save as savefig
from .schema import SCHEMA_VERSION, FigureMeta

if TYPE_CHECKING:
    from matplotlib.figure import Figure

__version__ = "0.1.0"
__all__ = [
    "savefig",
    "metadata",
    "extract",
    "load",
    "to_pandas",
    "FigureMeta",
    "SCHEMA_VERSION",
]


def extract(fig: Figure) -> FigureMeta:
    """Extract plotmeta from a live matplotlib figure as a FigureMeta object.

    No file is written. Use `metadata(fig)` to feed matplotlib's native
    `savefig(metadata=...)`, or `savefig(fig, path)` to write a PNG directly.
    """
    from .writers.matplotlib import extract_figure

    return extract_figure(fig)


def to_pandas(
    source: Figure | str | Path | FigureMeta,
):
    """Extract plot data as DataFrames.

    Returns a single DataFrame for single-panel figures,
    or a list of DataFrames for multi-panel figures.
    Accepts a matplotlib Figure, a file path, or a FigureMeta object.
    Requires pandas to be installed.
    """
    import pandas as pd

    if isinstance(source, FigureMeta):
        meta = source
    elif isinstance(source, (str, Path)):
        meta = load(source)
        if meta is None:
            raise ValueError(f"No plotmeta found in {source}")
    else:
        meta = extract(source)

    dfs = []
    for plot in meta.plots:
        records = []
        for series in plot.series:
            pairs = zip(series.x, series.y) if series.x and series.y else []
            for i, (x, y) in enumerate(pairs):
                record = {
                    "series": series.label or "(unlabeled)",
                    plot.x_axis.label or "x": x,
                    plot.y_axis.label or "y": y,
                }
                if series.y_err_lo and series.y_err_hi:
                    record["y_err_lo"] = series.y_err_lo[i]
                    record["y_err_hi"] = series.y_err_hi[i]
                records.append(record)

        df = pd.DataFrame(records)
        if plot.title:
            df.attrs["title"] = plot.title
        if plot.x_axis.units:
            df.attrs["x_units"] = plot.x_axis.units
        if plot.y_axis.units:
            df.attrs["y_units"] = plot.y_axis.units
        dfs.append(df)

    if len(dfs) == 1:
        return dfs[0]
    return dfs
