"""Bundled Korean display fonts for the folk theme, available without a CDN.

WOFF2 variants retain all source glyphs and use new font names. Source notices
and SIL OFL 1.1 licenses are kept beside the fonts and in the embedded CSS.
"""
from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

_FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"


@lru_cache(maxsize=1)
def css() -> str:
    chunks = []
    for family, source in (("YutBrush", "nanumbrushscript"), ("YutHand", "yeonsung")):
        license_text = (_FONT_DIR / f"{source}-OFL.txt").read_text(encoding="utf-8")
        data = base64.b64encode((_FONT_DIR / f"{family}-Regular.woff2").read_bytes()).decode("ascii")
        chunks.append("/* Bundled font: " + family + "\n" + license_text + "\n*/")
        chunks.append(
            "@font-face{font-family:'" + family + "';"
            "src:url(data:font/woff2;base64," + data + ") format('woff2');"
            "font-weight:400;font-style:normal;font-display:swap;}"
        )
    return "\n".join(chunks)
