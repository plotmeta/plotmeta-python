"""Durability of a plotmeta PDF through LaTeX ``\\includegraphics``.

A plotmeta PDF carries data in two channels (see ``transports/pdf.py``):

* the **base64 block** (default lossless channel) — real text operators inside
  the page content stream;
* the optional **stdlib marker** — ``% plotmeta-data:`` appended *after*
  ``%%EOF``, i.e. trailing bytes that are not part of any PDF object.

When ``\\includegraphics`` embeds a figure, LaTeX parses its objects and
re-wraps the page as a Form XObject. The content stream (hence the base64 block
and the human-readable copy) is copied through; bytes after ``%%EOF`` are not.
These tests pin that down empirically: a figure included in a compiled paper is
still losslessly reloadable via the base64 block, while the opt-in marker is
dropped.
"""

import shutil
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest

import plotmeta

requires_latex = pytest.mark.skipif(
    shutil.which("pdflatex") is None or shutil.which("pdftotext") is None,
    reason="pdflatex and/or pdftotext not installed",
)


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close("all")


def _make_figure():
    fig, ax = plt.subplots()
    ax.bar(["Control", "Treated"], [12.3, 18.7], label="yields")
    ax.set_xlabel("Group")
    ax.set_ylabel("Resistance (Ω)")
    ax.set_title("Panel B")
    return fig


def _compile(tmp_path: Path, figure_name: str = "fig") -> Path:
    """Compile a one-figure document and return the output PDF path."""
    (tmp_path / "doc.tex").write_text(
        r"\documentclass{article}"
        r"\usepackage{graphicx}"
        r"\begin{document}"
        rf"\includegraphics{{{figure_name}}}"
        r"\end{document}"
    )
    subprocess.run(
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "doc.tex"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    return tmp_path / "doc.pdf"


def _pdftotext(pdf: Path) -> str:
    return subprocess.run(
        ["pdftotext", "-raw", str(pdf), "-"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


@requires_latex
class TestIncludegraphicsDurability:
    def test_lossless_reload_survives_compilation(self, tmp_path: Path):
        # the headline guarantee: a figure dropped into a paper with
        # \includegraphics is still losslessly reloadable from the compiled PDF
        fig = _make_figure()
        plotmeta.savefig(fig, tmp_path / "fig.pdf")
        reference = plotmeta.extract(fig)

        out = _compile(tmp_path)

        assert plotmeta.load(out) == reference

    def test_human_readable_survives_compilation(self, tmp_path: Path):
        fig = _make_figure()
        plotmeta.savefig(fig, tmp_path / "fig.pdf")

        out = _compile(tmp_path)
        text = _pdftotext(out)

        # the human/LLM-readable copy is carried into the host document too
        assert "plotmeta" in text
        assert "Control" in text
        assert "12.3" in text

    def test_opt_in_marker_is_dropped(self, tmp_path: Path):
        # the after-EOF marker, even when requested, does not survive embedding;
        # reload then falls back to the base64 block, so load() still works
        fig = _make_figure()
        src = plotmeta.savefig(fig, tmp_path / "fig.pdf", stdlib_marker=True)
        assert b"% plotmeta-data:" in src.read_bytes()

        out = _compile(tmp_path)

        assert b"% plotmeta-data:" not in out.read_bytes()
        assert plotmeta.load(out) == plotmeta.extract(fig)
