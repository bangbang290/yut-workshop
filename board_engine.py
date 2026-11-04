"""Shared projector renderer and a self-contained preview builder.

The Streamlit bridge installs the visual renderer once in its parent document.
Subsequent fragment refreshes update only the tiny state marker, so animations,
fullscreen mode, and the local audio preference survive normal updates.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

_DIR = Path(__file__).resolve().parent


def engine_js() -> str:
    """Return the renderer with local CSS and character assets embedded."""
    import sprites

    js = (_DIR / "screen.js").read_text(encoding="utf-8")
    css = (_DIR / "screen.css").read_text(encoding="utf-8")
    return js.replace("__CSS__", json.dumps(css, ensure_ascii=False)).replace(
        "__SPRITES__", sprites.js_bundle()
    )


def component_html() -> str:
    """A zero-height Streamlit component that installs the live presentation."""
    code = json.dumps(engine_js(), ensure_ascii=False).replace("</", "<\\/")
    return (
        "<script>(function(){var code=" + code + ";"
        "try{var P=window.parent;if(P&&P!==window&&P.document){"
        "if(!P.__yutLoaded){var s=P.document.createElement('script');"
        "s.id='yut-live-renderer';s.textContent=code;"
        "P.document.head.appendChild(s);P.__yutLoaded=true;}return;}}"
        "catch(e){console.warn('Yut presentation bridge unavailable.');}"
        "})();</script>"
    )


def preview_html(state: dict | None = None, title: str = "윷놀이 한마당 · 스크린 미리보기") -> str:
    """Build an offline visual preview with no external asset requests.

    This is a viewer, not a second game database. QA may drive transitions via
    ``window.__yutScreenTest.take(next_state)``. Actual play uses Streamlit's
    controller and tablet views against the shared game state.
    """
    if state is None:
        import yutcore as Y

        state = Y.fresh()
        state["selectable"] = Y.selectable(state)
    marker = html.escape(json.dumps(state, ensure_ascii=False), quote=True)
    code = engine_js().replace("</", "<\\/")
    return (
        '<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{html.escape(title)}</title>"
        '<style>html,body{margin:0;min-height:100%;background:#faf7ef}</style>'
        '</head><body><i class="yut-st" style="display:none" '
        f'title="{marker}"></i><script>window.__YUT_PREVIEW__=true;</script>'
        f"<script>{code}</script></body></html>"
    )
