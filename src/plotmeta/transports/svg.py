"""Embed/extract the canonical payload in an SVG file (stdlib only).

SVG is XML we own after matplotlib writes it, so we inject a dedicated
namespaced element holding the payload in a CDATA section (tabs, newlines and
unicode all survive untouched). Placed just before the closing </svg>.
"""

from __future__ import annotations

import re

from ..schema import DATA_KEY

_NS = "https://plotmeta.org/ns"
_OPEN = f'<plotmeta:data xmlns:plotmeta="{_NS}" id="{DATA_KEY}"><![CDATA['
_CLOSE = "]]></plotmeta:data>"
_PATTERN = re.compile(re.escape(_OPEN) + r"(.*?)" + re.escape(_CLOSE), re.DOTALL)


def inject(svg_bytes: bytes, text: str) -> bytes:
    """Insert the payload element before </svg>."""
    svg = svg_bytes.decode("utf-8")
    if "</svg>" not in svg:
        raise ValueError("Not a valid SVG file (no </svg>)")
    if "]]>" in text:
        raise ValueError("Payload cannot contain ']]>' (breaks CDATA)")

    element = _OPEN + text + _CLOSE + "\n"
    svg = svg.replace("</svg>", element + "</svg>", 1)
    return svg.encode("utf-8")


def extract(svg_bytes: bytes) -> str | None:
    """Return the embedded payload, or None if absent."""
    match = _PATTERN.search(svg_bytes.decode("utf-8"))
    return match.group(1) if match else None
