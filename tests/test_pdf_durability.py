"""Does the PDF base64 channel survive external PDF re-processing tools?

The lossless payload rides in the page content stream as invisible text, so it
should survive any tool that re-encodes streams while preserving text operators
(compression, linearization, PDF/A conversion, garbage collection). The one
documented exception is a PostScript round-trip, which discards the invisible
text layer entirely.

Each tool test is skip-gated on the binary being present, so CI without the
tool installed simply skips it.
"""

import shutil
import subprocess
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest

import plotmeta


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close("all")


def _make_figure():
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [4, 5, 6], label="line")
    ax.bar(["Control", "Treated"], [12.3, 18.7], label="y")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Resistance (Ω)")  # non-ASCII, to confirm base64 immunity
    ax.set_title("μ test")
    return fig


def _saved(tmp_path: Path):
    fig = _make_figure()
    ref = plotmeta.extract(fig)
    src = plotmeta.savefig(fig, tmp_path / "fig.pdf")
    return src, ref


# name -> (required binary, argv builder (src, out) -> list[str])
PRESERVING_TOOLS = {
    "gs-default": (
        "gs",
        lambda s, o: [
            "gs",
            "-q",
            "-dNOPAUSE",
            "-dBATCH",
            "-sDEVICE=pdfwrite",
            f"-sOutputFile={o}",
            str(s),
        ],
    ),
    "gs-ebook-compress": (
        "gs",
        lambda s, o: [
            "gs",
            "-q",
            "-dNOPAUSE",
            "-dBATCH",
            "-sDEVICE=pdfwrite",
            "-dPDFSETTINGS=/ebook",
            f"-sOutputFile={o}",
            str(s),
        ],
    ),
    "gs-pdfa": (
        "gs",
        lambda s, o: [
            "gs",
            "-q",
            "-dNOPAUSE",
            "-dBATCH",
            "-sDEVICE=pdfwrite",
            "-dPDFA=2",
            "-sColorConversionStrategy=UseDeviceIndependentColor",
            f"-sOutputFile={o}",
            str(s),
        ],
    ),
    "qpdf-linearize": (
        "qpdf",
        lambda s, o: ["qpdf", "--linearize", str(s), str(o)],
    ),
    "qpdf-recompress": (
        "qpdf",
        lambda s, o: [
            "qpdf",
            "--recompress-flate",
            "--object-streams=generate",
            str(s),
            str(o),
        ],
    ),
    "mutool-clean": (
        "mutool",
        lambda s, o: ["mutool", "clean", str(s), str(o)],
    ),
    "mutool-clean-max": (
        "mutool",
        lambda s, o: ["mutool", "clean", "-g", "-g", "-g", "-g", "-z", str(s), str(o)],
    ),
}


@pytest.mark.parametrize("tool", list(PRESERVING_TOOLS))
def test_base64_survives_reencoding(tool: str, tmp_path: Path):
    binary, build = PRESERVING_TOOLS[tool]
    if shutil.which(binary) is None:
        pytest.skip(f"{binary} not installed")

    src, ref = _saved(tmp_path)
    out = tmp_path / f"{tool}.pdf"
    subprocess.run(build(src, out), check=True, capture_output=True)

    assert plotmeta.load(out) == ref


def test_base64_survives_pypdf_roundtrip(tmp_path: Path):
    pypdf = pytest.importorskip("pypdf")

    src, ref = _saved(tmp_path)
    reader = pypdf.PdfReader(str(src))
    writer = pypdf.PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    for page in writer.pages:
        page.compress_content_streams()
    out = tmp_path / "pypdf.pdf"
    with out.open("wb") as fh:
        writer.write(fh)

    assert plotmeta.load(out) == ref


@pytest.mark.skipif(
    shutil.which("pdf2ps") is None or shutil.which("ps2pdf") is None,
    reason="pdf2ps/ps2pdf not installed",
)
def test_postscript_roundtrip_loses_text_layer(tmp_path: Path):
    # Documented limitation: a PDF -> PS -> PDF round-trip discards the invisible
    # text layer wholesale (both the base64 block and the human-readable copy),
    # so nothing is recoverable. This pins that behaviour rather than hiding it.
    src, _ref = _saved(tmp_path)
    ps = tmp_path / "fig.ps"
    out = tmp_path / "roundtrip.pdf"
    subprocess.run(["pdf2ps", str(src), str(ps)], check=True, capture_output=True)
    subprocess.run(["ps2pdf", str(ps), str(out)], check=True, capture_output=True)

    assert plotmeta.load(out) is None
