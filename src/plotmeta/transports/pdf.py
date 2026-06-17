"""Embed/extract the canonical payload in a PDF.

A PDF carries the data in up to three places, by necessity:

1. **base64 block (default lossless channel)** — the exact payload,
   ``zlib``-compressed and base64-encoded, laid into the page as invisible text
   between ``PLOTMETA-B64-BEGIN`` / ``PLOTMETA-B64-END`` sentinels. Because it
   lives in the page *content stream*, it survives LaTeX ``\\includegraphics``
   (which re-wraps the page as a Form XObject), so a figure embedded in a
   compiled paper stays losslessly reloadable. Because base64 is pure ASCII, the
   text-layer mangling that affects the human-readable copy (tabs, non-ASCII
   glyphs) cannot corrupt it. Reading it back needs a text extractor — pypdf
   (the ``[pdf]`` extra) or the ``pdftotext`` binary.

2. **human-readable copy** — the same table laid in as invisible text so
   ``pdftotext`` / ``marker`` / copy-paste recover something a person or an LLM
   can read. This copy is lossy (tabs collapse, some glyphs drop); it is never a
   reload source.

3. **stdlib marker (opt-in)** — ``% plotmeta-data:<base64>`` appended after the
   PDF. Lets ``load()`` read the file with the stdlib alone (no text
   extraction), but it is trailing bytes that do *not* survive
   ``\\includegraphics``. Off by default; enable with ``stdlib_marker=True``.

``extract()`` tries the marker first (fast, stdlib), then the base64 block.
"""

from __future__ import annotations

import base64
import io
import re
import shutil
import subprocess
import zlib
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from matplotlib.figure import Figure

_MARKER = b"% plotmeta-data:"
_B64_BEGIN = "PLOTMETA-B64-BEGIN"
_B64_END = "PLOTMETA-B64-END"
# Match across a whitespace-stripped extraction. The sentinels carry hyphens
# (not in the base64 alphabet), so they can never occur inside the blob.
_B64_RE = re.compile(re.escape(_B64_BEGIN) + r"(.*?)" + re.escape(_B64_END), re.DOTALL)


def save(
    fig: Figure,
    path: str | Path,
    payload: str,
    *,
    stdlib_marker: bool = False,
    **savefig_kwargs,
) -> Path:
    """Render *fig* to PDF with the payload embedded.

    By default the lossless channel is the in-content-stream base64 block (which
    survives ``\\includegraphics``). Set ``stdlib_marker=True`` to additionally
    append the after-EOF marker for dependency-free ``load()`` on the file
    itself.
    """
    path = Path(path)
    pdf_bytes = _render_with_invisible_text(fig, payload, **savefig_kwargs)
    if stdlib_marker:
        pdf_bytes += b"\n" + _MARKER + _encode(payload) + b"\n"
    path.write_bytes(pdf_bytes)
    return path


def extract(pdf_bytes: bytes) -> str | None:
    """Return the embedded payload, or None.

    Marker first (stdlib, fast); then the base64 block via text extraction.
    """
    payload = _extract_marker(pdf_bytes)
    if payload is not None:
        return payload
    return _extract_b64_block(pdf_bytes)


# -- lossless channels ---------------------------------------------------------


def _encode(text: str) -> bytes:
    return base64.b64encode(zlib.compress(text.encode("utf-8")))


def _decode(blob: bytes) -> str:
    return zlib.decompress(base64.b64decode(blob)).decode("utf-8")


def _extract_marker(pdf_bytes: bytes) -> str | None:
    idx = pdf_bytes.rfind(_MARKER)
    if idx == -1:
        return None
    start = idx + len(_MARKER)
    end = pdf_bytes.find(b"\n", start)
    blob = pdf_bytes[start:] if end == -1 else pdf_bytes[start:end]
    try:
        return _decode(blob)
    except Exception:
        return None


def _extract_b64_block(pdf_bytes: bytes) -> str | None:
    text = _extract_text(pdf_bytes)
    if text is None:
        return None
    # Collapse all whitespace so sentinels and the blob are contiguous however
    # the extractor laid them out (line wraps, injected spaces).
    compact = re.sub(r"\s+", "", text)
    match = _B64_RE.search(compact)
    if not match:
        return None
    blob = re.sub(r"[^A-Za-z0-9+/=]", "", match.group(1))
    try:
        return _decode(blob.encode("ascii"))
    except Exception:
        return None


def _extract_text(pdf_bytes: bytes) -> str | None:
    """Extract the text layer via pypdf (preferred) or the pdftotext binary."""
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(pdf_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except ImportError:
        pass
    except Exception:
        pass

    if shutil.which("pdftotext"):
        proc = subprocess.run(
            ["pdftotext", "-raw", "-", "-"],
            input=pdf_bytes,
            capture_output=True,
        )
        if proc.returncode == 0:
            return proc.stdout.decode("utf-8", "replace")
    return None


# -- invisible-text channel ----------------------------------------------------


def _b64_block(payload: str) -> str:
    return _B64_BEGIN + _encode(payload).decode("ascii") + _B64_END


def _invisible_lines(payload: str) -> list[str]:
    """Lines laid into the page: lossless base64 block first (kept near the top
    of the page so it stays on-page), then the human-readable table."""
    return [_b64_block(payload), *payload.replace("\t", "  ").split("\n")]


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
        "\n".join(_invisible_lines(payload)),
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
    for line in _invisible_lines(payload):
        text_obj.textLine(line)
    c.drawText(text_obj)
    c.showPage()
    c.save()
    overlay_buf.seek(0)

    page.merge_page(PdfReader(overlay_buf).pages[0])
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()
