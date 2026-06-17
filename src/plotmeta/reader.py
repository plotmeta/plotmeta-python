"""Read plotmeta from image files, dispatching on format."""

from __future__ import annotations

from pathlib import Path

from . import table
from .schema import FigureMeta
from .transports import pdf, png, svg


def load(path: str | Path) -> FigureMeta | None:
    """Load plotmeta from an image file. Returns None if no metadata found.

    Supports .png, .svg and .pdf — all carry the same canonical payload, so the
    result is identical regardless of which format the figure was saved as.
    """
    path = Path(path)
    suffix = path.suffix.lower()
    raw = path.read_bytes()

    if suffix == ".png":
        payload = png.extract(raw)
    elif suffix == ".svg":
        payload = svg.extract(raw)
    elif suffix == ".pdf":
        payload = pdf.extract(raw)
    else:
        raise ValueError(f"Unsupported format: {suffix}. Supported: .png, .svg, .pdf")

    if payload is None:
        return None
    return table.loads(payload)
