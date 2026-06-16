"""Tests for PNG and sidecar transports."""

import struct
import zlib
from pathlib import Path

import pytest

from plotmeta.schema import Axis, FigureMeta, PlotMeta, Series
from plotmeta.transports import png, sidecar


def _make_png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    body = chunk_type + data
    return (
        struct.pack(">I", len(data))
        + body
        + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
    )


def _make_minimal_png() -> bytes:
    """Create a valid 1x1 white RGB PNG."""
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    raw_pixel = b"\x00\xff\xff\xff"  # filter=none, white
    return (
        b"\x89PNG\r\n\x1a\n"
        + _make_png_chunk(b"IHDR", ihdr_data)
        + _make_png_chunk(b"IDAT", zlib.compress(raw_pixel))
        + _make_png_chunk(b"IEND", b"")
    )


_MINIMAL_PNG = _make_minimal_png()


def _sample_meta() -> FigureMeta:
    return FigureMeta(
        plots=[
            PlotMeta(
                title="Test",
                x_axis=Axis(label="X", units="m"),
                series=[Series(label="A", x=[1.0, 2.0], y=[3.0, 4.0])],
            )
        ]
    )


class TestPngTransport:
    def test_inject_and_extract(self):
        meta = _sample_meta()
        enriched = png.inject(_MINIMAL_PNG, meta.to_json())
        extracted = png.extract(enriched)
        assert extracted is not None
        restored = FigureMeta.from_json(extracted)
        assert restored.plots[0].title == "Test"
        assert restored.plots[0].series[0].x == [1.0, 2.0]

    def test_extract_returns_none_when_missing(self):
        assert png.extract(_MINIMAL_PNG) is None

    def test_inject_invalid_png_raises(self):
        with pytest.raises(ValueError, match="Not a valid PNG"):
            png.inject(b"not a png", "hello")

    def test_extract_invalid_png_raises(self):
        with pytest.raises(ValueError, match="Not a valid PNG"):
            png.extract(b"not a png")

    def test_roundtrip_preserves_image(self):
        enriched = png.inject(_MINIMAL_PNG, "test data")
        assert enriched[:8] == b"\x89PNG\r\n\x1a\n"
        assert enriched.endswith(b"IEND\xaeB`\x82")

    def test_large_payload(self):
        big_meta = FigureMeta(
            plots=[
                PlotMeta(
                    series=[
                        Series(
                            x=[float(i) for i in range(1000)],
                            y=[float(i * 2) for i in range(1000)],
                        )
                    ]
                )
            ]
        )
        enriched = png.inject(_MINIMAL_PNG, big_meta.to_json())
        extracted = png.extract(enriched)
        restored = FigureMeta.from_json(extracted)
        assert len(restored.plots[0].series[0].x) == 1000


class TestSidecarTransport:
    def test_write_and_read(self, tmp_path: Path):
        img = tmp_path / "figure.png"
        img.write_bytes(_MINIMAL_PNG)

        meta = _sample_meta()
        written = sidecar.write(img, meta)
        assert written == tmp_path / "figure.plotmeta.json"
        assert written.exists()

        restored = sidecar.read(img)
        assert restored is not None
        assert restored.plots[0].title == "Test"
        assert restored.plots[0].series[0].y == [3.0, 4.0]

    def test_read_returns_none_when_missing(self, tmp_path: Path):
        img = tmp_path / "nosidecar.png"
        assert sidecar.read(img) is None

    def test_sidecar_path(self):
        expected = Path("/some/dir/plot.plotmeta.json")
        assert sidecar.sidecar_path("/some/dir/plot.png") == expected
        assert sidecar.sidecar_path("fig.jpg") == Path("fig.plotmeta.json")
