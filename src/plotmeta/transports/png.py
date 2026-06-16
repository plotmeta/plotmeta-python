"""PNG zTXt chunk injection and extraction (stdlib only)."""

from __future__ import annotations

import struct
import zlib

from ..schema import PNG_CHUNK_KEY


def inject(png_bytes: bytes, text: str, keyword: str = PNG_CHUNK_KEY) -> bytes:
    """Insert a zTXt chunk into PNG bytes, just before IEND."""
    if png_bytes[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Not a valid PNG file")

    compressed = zlib.compress(text.encode("utf-8"))
    chunk_data = keyword.encode("latin-1") + b"\x00\x00" + compressed

    chunk_type = b"zTXt"
    chunk = (
        struct.pack(">I", len(chunk_data))
        + chunk_type
        + chunk_data
        + struct.pack(">I", zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF)
    )

    iend_pos = png_bytes.rfind(b"IEND") - 4
    if iend_pos < 8:
        raise ValueError("PNG file has no IEND chunk")
    return png_bytes[:iend_pos] + chunk + png_bytes[iend_pos:]


def extract(png_bytes: bytes, keyword: str = PNG_CHUNK_KEY) -> str | None:
    """Extract text from a tEXt, zTXt, or iTXt chunk with the given keyword."""
    if png_bytes[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Not a valid PNG file")

    pos = 8
    while pos < len(png_bytes):
        length = struct.unpack(">I", png_bytes[pos : pos + 4])[0]
        chunk_type = png_bytes[pos + 4 : pos + 8]
        chunk_data = png_bytes[pos + 8 : pos + 8 + length]

        if chunk_type == b"tEXt":
            null = chunk_data.index(b"\x00")
            if chunk_data[:null].decode("latin-1") == keyword:
                return chunk_data[null + 1 :].decode("latin-1")

        elif chunk_type == b"zTXt":
            null = chunk_data.index(b"\x00")
            if chunk_data[:null].decode("latin-1") == keyword:
                return zlib.decompress(chunk_data[null + 2 :]).decode("utf-8")

        elif chunk_type == b"iTXt":
            null = chunk_data.index(b"\x00")
            if chunk_data[:null].decode("latin-1") == keyword:
                rest = chunk_data[null + 1 :]
                comp_flag = rest[0]
                rest = rest[2:]
                lang_end = rest.index(b"\x00")
                rest = rest[lang_end + 1 :]
                trans_end = rest.index(b"\x00")
                text_data = rest[trans_end + 1 :]
                if comp_flag:
                    return zlib.decompress(text_data).decode("utf-8")
                return text_data.decode("utf-8")

        elif chunk_type == b"IEND":
            break

        pos += 12 + length

    return None
