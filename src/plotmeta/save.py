"""Saving figures with embedded plotmeta.

The metadata is generated *once* (`extract` -> `table.dumps`) and is identical
regardless of output format. Only the embedding step differs per extension:

    .png  -> compressed text chunk
    .svg  -> namespaced XML element
    .pdf  -> invisible-text base64 block (survives \includegraphics) +
             human-readable copy; optional after-EOF stdlib marker

So the same data is recoverable whether you save (and load) PNG, SVG or PDF.

For PNG you can also use matplotlib's own writer:

    fig.savefig("plot.png", metadata=plotmeta.metadata(fig))

`metadata()` returns ``{"data": <payload>}``; matplotlib stores it as a PNG
text chunk. (This native path is PNG-only — SVG/PDF reject unknown keys.)
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import TYPE_CHECKING

from . import table
from .schema import DATA_KEY

if TYPE_CHECKING:
    from matplotlib.figure import Figure

_RASTER_NATIVE = {".png"}


def metadata(fig: Figure, keyword: str = DATA_KEY) -> dict[str, str]:
    """Build a metadata dict for matplotlib's native ``savefig(metadata=...)``.

    Returns ``{keyword: <payload>}``. PNG only; pass it straight through or
    merge with your own keys::

        fig.savefig("plot.png", metadata=plotmeta.metadata(fig))
    """
    from .writers.matplotlib import extract_figure

    return {keyword: table.dumps(extract_figure(fig))}


def save(
    fig: Figure, path: str | Path, *, stdlib_marker: bool = False, **savefig_kwargs
) -> Path:
    """Save a matplotlib figure with embedded plotmeta, dispatching on format.

    Drop-in replacement for ``fig.savefig()``. Supported: .png, .svg, .pdf.
    Extra keyword arguments are forwarded to ``fig.savefig``.

    ``stdlib_marker`` (PDF only): also append the after-EOF marker so ``load()``
    can read the file with the stdlib alone, without a text extractor. The
    default base64 channel is already lossless and survives ``\\includegraphics``
    but requires pypdf (the ``[pdf]`` extra) or ``pdftotext`` to read back.
    """
    from .transports import pdf, png, svg
    from .writers.matplotlib import extract_figure

    path = Path(path)
    suffix = path.suffix.lower()
    payload = table.dumps(extract_figure(fig))

    if suffix == ".png":
        path.write_bytes(png.inject(_render(fig, "png", **savefig_kwargs), payload))
    elif suffix == ".svg":
        path.write_bytes(svg.inject(_render(fig, "svg", **savefig_kwargs), payload))
    elif suffix == ".pdf":
        pdf.save(fig, path, payload, stdlib_marker=stdlib_marker, **savefig_kwargs)
    else:
        raise ValueError(f"Unsupported format: {suffix}. Supported: .png, .svg, .pdf")

    return path


def _render(fig: Figure, fmt: str, **savefig_kwargs) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format=fmt, **savefig_kwargs)
    return buf.getvalue()
