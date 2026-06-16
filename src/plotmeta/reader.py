"""Read plotmeta from image files."""

from __future__ import annotations

from pathlib import Path

from .schema import FigureMeta
from .transports import png


def load(path: str | Path) -> FigureMeta | None:
    """Load plotmeta from an image file. Returns None if no metadata found."""
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix == ".png":
        raw = png.extract(path.read_bytes())
        if raw is None:
            return None
        return FigureMeta.from_json(raw)

    raise ValueError(f"Unsupported format: {suffix}. Currently supported: .png")
