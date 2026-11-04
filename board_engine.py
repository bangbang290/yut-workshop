"""스크린 화면 엔진(static/screen.js)을 Streamlit 화면 본문에 한 번 심는 부품.

components.html 은 같은 주소의 iframe 안에서 돌기 때문에, 바깥 문서(window.parent)에 스크립트를 넣어
Streamlit이 다시 그려도 엔진이 계속 살아 있게 합니다(심사 시스템 효과음과 같은 방식).
"""
from __future__ import annotations

import json
import os

_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


def engine_js() -> str:
    with open(os.path.join(_DIR, "screen.js"), encoding="utf-8") as f:
        js = f.read()
    with open(os.path.join(_DIR, "screen.css"), encoding="utf-8") as f:
        css = f.read()
    return js.replace("__CSS__", json.dumps(css, ensure_ascii=False))


def component_html() -> str:
    code = json.dumps(engine_js(), ensure_ascii=False).replace("</", "<\\/")
    return ("<script>(function(){var code=" + code + ";"
            "try{var P=window.parent;if(P&&P!==window&&P.document){"
            "if(!P.__yutLoaded){P.__yutLoaded=true;var s=P.document.createElement('script');"
            "s.textContent=code;P.document.head.appendChild(s);}return;}}catch(e){}"
            "})();</script>")
