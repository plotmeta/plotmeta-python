"""Sidecar .plotmeta.json file read/write."""

from __future__ import annotations

from pathlib import Path

from ..schema import FigureMeta


def sidecar_path(image_path: str | Path) -> Path:
    """Return the sidecar path for a given image: figure.png -> figure.plotmeta.json."""
    p = Path(image_path)
    return p.parent / f"{p.stem}.plotmeta.json"


def write(image_path: str | Path, meta: FigureMeta) -> Path:
    """Write a sidecar JSON file next to the image."""
    path = sidecar_path(image_path)
    path.write_text(meta.to_json(), encoding="utf-8")
    return path


def read(image_path: str | Path) -> FigureMeta | None:
    """Read the sidecar JSON for an image. Returns None if not found."""
    path = sidecar_path(image_path)
    if not path.exists():
        return None
    return FigureMeta.from_json(path.read_text(encoding="utf-8"))
