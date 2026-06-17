"""Embed/extract the canonical payload in a PDF.

Two channels, by necessity:

1. **Lossless reload channel** — the exact payload, zlib+base64, appended after
   the PDF as a ``% plotmeta-data:`` comment line. Found and decoded with the
   stdlib alone, so `load()` stays dependency-free and byte-exact. This is what
   guarantees cross-format parity. (The PDF text layer mangles tabs and drops
   non-ASCII glyphs, so it cannot serve as the lossless source.)

2. **Invisible-text channel** — a human/LLM-readable copy laid into the page so
   ``pdftotext`` / ``marker`` / copy-paste recover the data with no special
   tooling. Produced render-mode-3 via reportlab+pypdf when available, else via
   a dependency-free matplotlib ``alpha=0`` text artist.
"""

from __future__ import annotations

import base64
import io
import zlib
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from matplotlib.figure import Figure

_MARKER = b"% plotmeta-data:"


def save(fig: Figure, path: str | Path, payload: str, **savefig_kwargs) -> Path:
    """Render *fig* to PDF with embedded payload (both channels)."""
    path = Path(path)
    pdf_bytes = _render_with_invisible_text(fig, payload, **savefig_kwargs)
    pdf_bytes += b"\n" + _MARKER + _encode(payload) + b"\n"
    path.write_bytes(pdf_bytes)
    return path


def extract(pdf_bytes: bytes) -> str | None:
    """Return the embedded payload from the lossless channel, or None."""
    idx = pdf_bytes.rfind(_MARKER)
    if idx == -1:
        return None
    start = idx + len(_MARKER)
    end = pdf_bytes.find(b"\n", start)
    blob = pdf_bytes[start:] if end == -1 else pdf_bytes[start:end]
    return _decode(blob)


# -- lossless channel ----------------------------------------------------------


def _encode(text: str) -> bytes:
    return base64.b64encode(zlib.compress(text.encode("utf-8")))


def _decode(blob: bytes) -> str:
    return zlib.decompress(base64.b64decode(blob)).decode("utf-8")


# -- invisible-text channel ----------------------------------------------------


def _render_with_invisible_text(fig: Figure, payload: str, **kw) -> bytes:
    try:
        return _render_reportlab(fig, payload, **kw)
    except ImportError:
        return _render_alpha(fig, payload, **kw)


def _render_alpha(fig: Figure, payload: str, **kw) -> bytes:
    """Dependency-free: an alpha=0 text artist still emits real text operators."""
    artist = fig.text(
        0.005,
        0.005,
        payload.replace("\t", "  "),
        alpha=0,
        fontsize=1,
        family="monospace",
        va="bottom",
    )
    try:
        buf = io.BytesIO()
        fig.savefig(buf, format="pdf", **kw)
        return buf.getvalue()
    finally:
        artist.remove()


def _render_reportlab(fig: Figure, payload: str, **kw) -> bytes:
    """High-fidelity: render-mode-3 (truly invisible) text via reportlab+pypdf."""
    from pypdf import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas

    base_buf = io.BytesIO()
    fig.savefig(base_buf, format="pdf", **kw)
    base_buf.seek(0)

    writer = PdfWriter(clone_from=base_buf)
    page = writer.pages[0]
    width = float(page.mediabox.width)
    height = float(page.mediabox.height)

    overlay_buf = io.BytesIO()
    c = canvas.Canvas(overlay_buf, pagesize=(width, height))
    text_obj = c.beginText(2, height - 2)
    text_obj.setTextRenderMode(3)  # neither fill nor stroke = invisible
    text_obj.setFont("Courier", 1)
    for line in payload.split("\n"):
        text_obj.textLine(line.replace("\t", "  "))
    c.drawText(text_obj)
    c.showPage()
    c.save()
    overlay_buf.seek(0)

    page.merge_page(PdfReader(overlay_buf).pages[0])
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()
