"""심사2국 워크숍 · 윷놀이 한마당 수정판 2.3.
실제 윷 결과를 진행석에서 입력하고, 팀 대표가 패드에서 말을 옮깁니다.
/?view=screen · /?view=ctrl · /?view=pad — 동일한 SQLite 판을 공유합니다.
"""
from __future__ import annotations

import base64
import html
import json
import time
from datetime import datetime, timezone, timedelta
from functools import lru_cache

import streamlit as st

import board_engine
import font_bundle
import pad_board
import sprites
import yutcore as Y

st.set_page_config(page_title="윷놀이 한마당", page_icon="🎋", layout="wide", initial_sidebar_state="collapsed")
Y.init()
BUILD_LABEL = "수정판 2.3"
DOT = ["🟠", "🟣", "🔵", "🟢"]
NODE_NM = {"END": "참먹이", "C": "방", "A1": "모 지름길 1", "A2": "모 지름길 2", "A3": "방→찌모 1", "A4": "방→찌모 2", "B1": "뒷모 지름길 1", "B2": "뒷모 지름길 2", "B3": "방→참먹이 1", "B4": "방→참먹이 2"}
for _i, _n in enumerate(["도", "개", "걸", "윷", "모"]):
    NODE_NM[f"O{_i + 1}"] = _n
    NODE_NM[f"O{_i + 6}"] = "뒷" + _n
    NODE_NM[f"O{_i + 11}"] = "찌" + _n
    if _i < 4:
        NODE_NM[f"O{_i + 16}"] = "날" + _n

# Keep style blocks on separate lines: Markdown ends a raw HTML block at the
# first </style> line, even when another <style> starts on that same line.
BASE_CSS = '<style id="yut-fonts">' + font_bundle.css() + '</style>\n\n<style>' + """
:root{--ink:#453b2c;--muted:#82745d;--paper:#f4edda;--green:#4e5438;--line:#d8c7a6;--coral:#ae4c38}
header[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stDecoration"],#MainMenu,footer{display:none!important}
[data-stale="true"],.stale-element{opacity:1!important;transition:none!important}
.stApp{background-color:var(--paper);background-image:radial-gradient(#8d70320b .7px,transparent .7px);background-size:8px 8px;color:var(--ink)}
.block-container{max-width:1080px!important;padding:1.5rem 2rem 3rem!important}
html,body,[class*="st-"],.yx{font-family:"Malgun Gothic","Apple SD Gothic Neo",sans-serif}
h1,h2,h3,p{word-break:keep-all}
.yx{color:var(--ink)}
.yx-top{display:flex;justify-content:space-between;align-items:center;margin:0 0 1.35rem;padding-bottom:1rem;border-bottom:1.5px solid var(--line);gap:1rem}
.yx-brand{display:flex;align-items:center;gap:.65rem;letter-spacing:-.03em}.yx-brand-sign{position:relative;display:inline-block;font-family:"YutBrush","Malgun Gothic",serif;font-size:1.45rem;font-weight:400;white-space:nowrap;padding:.35rem .8rem;background:linear-gradient(100deg,#eeddb7,#fff4d8 45%,#f3e3bf);border:1.5px solid #ad9263;border-radius:2px 3px 6px 4px;box-shadow:2px 3px 0 #a68b5433}.yx-brand-sign::before,.yx-brand-sign::after{content:"";position:absolute;top:-4px;bottom:-4px;width:3px;background:#79603e;border-radius:2px}.yx-brand-sign::before{left:-4px}.yx-brand-sign::after{right:-4px}.yx-seal{display:grid;place-items:center;width:2rem;height:2.35rem;flex:none;border:1.5px solid #b14c38;color:#b14c38;font-family:"YutBrush","Malgun Gothic",serif;font-size:.8rem;line-height:1.05;transform:rotate(-6deg);border-radius:3px}.yx-brand small{font-size:.75rem;font-weight:500;color:var(--muted);white-space:nowrap}
.yx-nav{display:flex;gap:.35rem;flex-wrap:wrap}.yx-nav a{font-size:.78rem;text-decoration:none!important;color:#71624b!important;padding:.45rem .75rem;border-radius:5px}.yx-nav a.active{background:#ead5ae;color:#6b432a!important;font-weight:800;box-shadow:inset 0 -2px 0 #b89054}
.yx-launch .yx-open{display:flex;align-items:center;justify-content:center;box-sizing:border-box;width:100%;min-height:3rem;padding:.5rem .75rem;border:1.5px solid #c6b087;border-radius:7px;background:#fff8e6;color:#654c31!important;box-shadow:2px 2px 0 #ccb78d;font-family:"Malgun Gothic","Apple SD Gothic Neo",sans-serif;font-size:.95rem;font-weight:700;line-height:1.35;text-decoration:none!important;transition:transform .12s,background .12s}
.yx-launch .yx-open:hover{border-color:#9a7541;background:#f2e3bf;color:#5d3f24!important}.yx-launch .yx-open:active{transform:translateY(1px);box-shadow:none}.yx-launch .yx-open:focus-visible{outline:3px solid #d88d38;outline-offset:3px}
.yx-build{font-family:"Malgun Gothic","Apple SD Gothic Neo",sans-serif;font-size:.65rem;font-weight:500;letter-spacing:0;white-space:nowrap;padding:.2rem .4rem;border:1px solid #d8c7a6;border-radius:4px;color:#8a7557;background:#fff6e2}
.yx-eyebrow{font-size:.7rem;font-weight:800;letter-spacing:.1em;color:#95805f;margin-bottom:.45rem}
.yx-h{font-family:"YutHand","Malgun Gothic",sans-serif;font-size:1.05rem;font-weight:400;letter-spacing:.01em;color:#78613f;margin:.2rem 0 .55rem}
.yx-turn{display:flex;gap:1rem;padding:1.35rem 1.4rem;background:#514a35;border:1.5px solid #393220;border-radius:12px;color:#fff8e8;margin-bottom:.9rem;align-items:center;box-shadow:3px 3px 0 #d5c19a}
.yx-turn .dot{width:3.1rem;height:3.1rem;display:grid;place-items:center;font-family:"YutHand","Malgun Gothic",sans-serif;font-size:1.7rem;font-weight:400;border-radius:9px;border:2px solid #fff6da8c;flex:none;background:var(--tc);color:white}
.yx-turn b{display:block;font-family:"YutHand","Malgun Gothic",sans-serif;font-size:2.15rem;font-weight:400;letter-spacing:-.035em;line-height:1.25}.yx-turn small{display:block;font-size:.9rem;color:#e7dbc0;margin-top:.3rem;line-height:1.45}
.yx-pend{display:flex;gap:.45rem;flex-wrap:wrap;align-items:center;margin:.2rem 0 1rem;min-height:2.7rem}.yx-pend span{font-family:"YutHand","Malgun Gothic",sans-serif;font-size:1.2rem;font-weight:400;padding:.38rem .9rem;border:1.5px solid #c6ae81;border-radius:6px;background:#fff8e5;box-shadow:1px 2px 0 #cfb98e55}.yx-pend span.bonus{background:#edd39a;border-color:#bd9250;color:#6b481d}.yx-pend span em{font-family:"Malgun Gothic","Apple SD Gothic Neo",sans-serif;font-size:.7rem;font-weight:500;font-style:normal;margin-left:.4rem;opacity:.75}.yx-pend .empty{font-size:.85rem;color:#8c7e66}
.yx-msg{font-size:.9rem;line-height:1.65;padding:.85rem 1rem;border-radius:8px;background:#ebe2cb;border-left:3px solid #bda16b;color:#6d6047;margin:.55rem 0}.yx-board{display:block;width:100%;max-width:480px;margin:.5rem auto 1rem}
.yx-teams{display:flex;flex-direction:column;gap:.55rem;margin:.3rem 0 1rem}.yx-team{background:#fff9e9b8;border:1.5px solid var(--line);padding:.8rem .9rem;border-radius:9px;display:grid;grid-template-columns:8px 1fr auto;align-items:center;gap:.75rem}.yx-team.now{background:#fff8e4;border-color:#b59760;box-shadow:2px 2px 0 #c5aa7a44}.yx-team .stripe{height:2.5rem;border-radius:3px;background:var(--tc)}.yx-team b{font-family:"YutHand","Malgun Gothic",sans-serif;font-size:1.18rem;font-weight:400;display:block}.yx-team small{color:#8b7c62;font-size:.73rem;display:block;margin-top:.3rem}.yx-team strong{font-size:1.4rem;color:var(--tc)}.yx-team strong span{font-size:.75rem;color:#9b8b70;font-weight:500}.yx-team .tag{font-family:"Malgun Gothic","Apple SD Gothic Neo",sans-serif;font-size:.65rem;color:#875438;background:#f0dfbd;border-radius:3px;padding:.2rem .35rem;margin-left:.35rem}.yx-progress{height:3px;margin-top:.55rem;background:#e9ddc4;border-radius:3px;overflow:hidden}.yx-progress i{display:block;height:100%;background:var(--tc)}
.yx-log{background:#ede3ca;padding:.9rem 1rem;border-radius:8px;margin:.5rem 0 1rem;border:1px solid #dfcfad}.yx-log div{font-size:.78rem;color:#807051;line-height:1.65;padding:.35rem 0;border-bottom:1px solid #d9c9a8}.yx-log div:first-child{font-weight:700;color:#685034}.yx-log div:last-child{border:0}
.yx-hero{display:grid;grid-template-columns:1.15fr 1fr;align-items:center;gap:2rem;padding:1.8rem 0 2rem}.yx-hero h1{font-family:"YutBrush","Malgun Gothic",serif;font-size:3.65rem;font-weight:400;letter-spacing:-.04em;line-height:1.25;margin:.4rem 0 1rem;color:#4d3d29}.yx-hero p{font-size:.98rem;line-height:1.8;color:#827358}.yx-hero .sub{font-family:"YutHand","Malgun Gothic",sans-serif;font-weight:400;font-size:1.15rem;color:#a35c3c;margin:.6rem 0}.yx-cast{display:grid;grid-template-columns:1fr 1fr;gap:.7rem}.yx-character{display:flex;flex-direction:column;align-items:center;justify-content:flex-end;border:1.5px solid #d5bd91;border-radius:12px 12px 9px 9px;box-shadow:2px 3px 0 #c6ac7440;background:#f1dfbb;padding:1rem .5rem .8rem;min-height:165px}.yx-character:nth-child(2){background:#e3e4cc;border-color:#bfc49c}.yx-character:nth-child(3){background:#dfe6e1;border-color:#b5c2b7}.yx-character:nth-child(4){background:#e9dfb4;border-color:#c9b87f}.yx-character .art{height:125px;width:100%;display:grid;place-items:center}.yx-character svg{height:100%;max-width:95%;width:auto}.yx-character b{font-family:"YutHand","Malgun Gothic",sans-serif;font-size:1rem;font-weight:400;margin-top:.5rem;letter-spacing:.03em}.yx-role{margin-bottom:.4rem;padding:.85rem 0}.yx-role small{color:#9c714a;font-weight:800;letter-spacing:.1em;font-size:.7rem}.yx-role h3{font-family:"YutHand","Malgun Gothic",sans-serif;font-size:1.5rem;font-weight:400;margin:.5rem 0}.yx-role p{font-size:.83rem;line-height:1.65;color:#827358;min-height:3rem}
.yx-footer{margin:2rem 0 .5rem;color:#9a896c;font-size:.73rem;border-top:1px solid var(--line);padding-top:1rem;line-height:1.7}.yx-step{display:flex;gap:.5rem;align-items:center;font-size:.75rem;color:#8b7c60;margin:.1rem 0 1rem}.yx-step b{color:#795539}.yx-step i{font-style:normal;padding:0 .4rem;color:#bbaa87}
div[data-testid="stButton"] button,div[data-testid="stLinkButton"] a,div[data-testid="stDownloadButton"] button,div[data-testid="stFormSubmitButton"] button{min-height:3rem;border-radius:7px!important;border:1.5px solid #c6b087!important;background:#fff8e6;color:#654c31;box-shadow:2px 2px 0 #ccb78d;transition:transform .12s,background .12s}
div[data-testid="stButton"] button p,div[data-testid="stLinkButton"] a p,div[data-testid="stDownloadButton"] button p,div[data-testid="stFormSubmitButton"] button p{font-size:.95rem!important;font-weight:700;line-height:1.35}
div[data-testid="stButton"] button:hover,div[data-testid="stLinkButton"] a:hover{border-color:#9a7541!important;background:#f2e3bf;color:#5d3f24}div[data-testid="stButton"] button:active{transform:translateY(1px);box-shadow:none}
div[data-testid="stButton"] button[kind="primary"],div[data-testid="stButton"] button[data-testid="stBaseButton-primary"],div[data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"]{background:#a34d38;color:#fff8e8;border-color:#843c2c!important;box-shadow:2px 3px 0 #6f3728}
div[data-testid="stButton"] button:disabled{opacity:.32;box-shadow:none}
[data-testid="stExpander"]{background:#fbf4e1;border-radius:9px;border-color:var(--line)}
@media(max-width:850px){.yx-brand small{display:none}}
@media(max-width:700px){.block-container{padding:1rem .9rem 2rem!important}.yx-top{gap:.8rem;align-items:flex-start;flex-direction:column}.yx-brand-sign{font-size:1.35rem}.yx-hero{grid-template-columns:1fr;gap:.5rem;padding-top:.7rem}.yx-hero h1{font-size:2.9rem}.yx-cast{grid-template-columns:repeat(4,1fr);gap:.3rem}.yx-character{min-height:105px;border-radius:8px;padding:.4rem .2rem}.yx-character .art{height:85px}.yx-character b{font-size:.9rem}.yx-turn{padding:1rem}.yx-turn b{font-size:1.9rem}}
@media(prefers-reduced-motion:reduce){*,*::before,*::after{animation:none!important;transition:none!important}}
</style>"""
CTRL_CSS = """<style>div[class*="st-key-throw_"] button{min-height:5.6rem}div[class*="st-key-throw_"] button p{font-family:"YutHand","Malgun Gothic",sans-serif;font-size:2.1rem!important;font-weight:400;letter-spacing:-.03em}div[class*="st-key-throw_yut"] button,div[class*="st-key-throw_mo"] button{background:#edd59a!important;border-color:#bf9550!important;color:#70501f!important;box-shadow:2px 3px 0 #c7a76b}</style>"""
PAD_CSS = """<style>.block-container{max-width:1360px!important;padding-top:1rem!important}.yx-turn b{font-size:1.8rem}.yx-turn{padding:1rem}.yx-team{padding:.65rem .8rem}.yx-team strong{font-size:1.25rem}iframe[title="st.iframe"]{border-radius:14px;overflow:hidden}</style>"""


def md(value: str):
    st.markdown(value, unsafe_allow_html=True)


@lru_cache(maxsize=2)
def frame_html(document: str, height: int) -> str:
    """Embed the existing renderer without Streamlit's lazy IFrame JS chunk.

    Keep the outer HTML on one Markdown line. Character references restore
    exact srcdoc line endings, including those required by JS line comments.
    The sandbox matches Streamlit 1.41; feature permissions are limited to
    the game's existing audio and fullscreen features.
    """
    source = html.escape(document, quote=True).replace("\r", "&#13;").replace("\n", "&#10;")
    sandbox = ("allow-forms allow-modals allow-popups allow-popups-to-escape-sandbox "
               "allow-same-origin allow-scripts allow-downloads")
    return (
        '<div class="yx-frame"><iframe title="st.iframe" width="100%" '
        f'height="{height}" scrolling="no" '
        'style="display:block;width:100%;border:0;margin:0;padding:0;overflow:hidden;color-scheme:normal" '
        f'sandbox="{sandbox}" allow="autoplay; fullscreen" '
        f'srcdoc="{source}"></iframe></div>'
    )


def base_url() -> str:
    try:
        h = {k.lower(): v for k, v in st.context.headers.items()}
        host = h.get("x-forwarded-host") or h.get("host") or ""
        if host and not any(c in host for c in ('<','>','"',"'",'\\',' ')):
            proto = "https" if h.get("x-forwarded-proto") == "https" or "streamlit.app" in host else "http"
            return f"{proto}://{host}"
    except Exception:
        pass
    return ""


def view_url(view: str) -> str:
    return f"?view={view}"


def header(active=""):
    links = [("", "처음"), ("screen", "스크린"), ("ctrl", "진행석"), ("pad", "말 옮기기")]
    nav = "".join(f'<a class="{"active" if v == active else ""}" href="?view={v}" target="_self">{label}</a>' for v,label in links)
    md(f'<div class="yx yx-top"><div class="yx-brand"><span class="yx-brand-sign">윷놀이 한마당</span><span class="yx-seal" aria-hidden="true">한<br>마당</span><small>함께 놀아 더 즐거운 오늘</small><span class="yx-build">{BUILD_LABEL}</span></div><nav class="yx-nav">{nav}</nav></div>')


def act(fn, *args, **kwargs) -> bool:
    try:
        result = fn(*args, **kwargs)
        if result is False:
            st.info("되돌릴 동작이 없습니다.")
        return True
    except Y.GameError as e:
        st.warning(str(e))
        return False


def _state_key(S):
    return (str(Y.DB_PATH), S.get("game_id"), S.get("ver", 0))


def controller_resources(S):
    """Reuse a same-version backup without rereading all undo history each tick.

    The export contains an atomic game/history snapshot. Use its own version,
    not the possibly older UI state, and cache only when the final state read
    still matches. This keeps another device's move from being cached under
    the wrong version. The cache holds only one snapshot per browser session.
    """
    cache_name = "_yut_controller_resources_v22"
    cached = st.session_state.get(cache_name)
    if cached is not None and cached["state_key"] == _state_key(S):
        return cached

    data = Y.export_backup()
    exported = json.loads(data)
    snapshot = exported["state"]
    can_undo = Y.can_undo()
    stamp = datetime.fromisoformat(exported["exported_at"]).strftime("%Y%m%d_%H%M%S")
    resource = {
        "state_key": _state_key(snapshot),
        "data": data,
        "file_name": f'yut_backup_{stamp}_v{snapshot["ver"]}.json',
        "can_undo": can_undo,
    }
    if _state_key(Y.get()) == resource["state_key"]:
        st.session_state[cache_name] = resource
    else:
        st.session_state.pop(cache_name, None)
    return resource


def turn_card(S):
    over = S["phase"] == "over"
    team = S["ranks"][0] if over and S["ranks"] else S["turn"]
    if over:
        what = "모두 함께한 한 판, 수고하셨습니다!"
    elif S["phase"] == "throw":
        reason = Y.throw_reason(S)
        if reason == "capture":
            what = "잡기 성공! 바로 한 번 더 던져 주세요. 남은 결과는 그대로 보관합니다."
        elif reason in ("yut", "mo"):
            what = f"{Y.RES[reason]['nm']}! 한 번 더 던져 주세요."
        else:
            what = "실제 윷을 던지고, 나온 결과를 눌러 주세요."
    else:
        what = "팀 대표가 패드에서 말과 도착 칸을 골라 주세요."
    md(f'<div class="yx yx-turn" style="--tc:{Y.HEX[team]}"><span class="dot">{html.escape(Y.tname(S,team)[:1])}</span><div><div class="yx-eyebrow" style="color:#d9c59c">{"오늘의 우승" if over else "이번 차례"}</div><b>{html.escape(Y.tname(S,team))} {"승리!" if over else "차례"}</b><small>{what}</small></div></div>')


def pending_html(S, label="남은 윷 결과"):
    chips = "".join(f'<span class="{"bonus" if Y.RES[r]["again"] else ""}">{Y.RES[r]["nm"]}<em>{"−1칸" if r=="back" else str(Y.RES[r]["steps"])+"칸"}</em></span>' for r in S["pending"])
    md(f'<div class="yx yx-h">{label}</div><div class="yx yx-pend">{chips or "<div class=empty>윷 결과를 기다리고 있어요.</div>"}</div>')


def _q(p):
    """스크린·패드와 같은 방향(출발이 아래)인 마름모 좌표."""
    return 50 + (p[0] - p[1]) * .46, 50 + (p[0] + p[1] - 100) * .46


def board_img(S) -> str:
    """버튼으로 옮길 때 보는 납작한 말판 그림(팀 색 말, 고른 말이 갈 곳)."""
    P = Y.P
    o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" font-family="Malgun Gothic,Apple SD Gothic Neo,sans-serif">',
         '<polygon points="50,4 96,50 50,96 4,50" fill="#f2e2bb" stroke="#6b4321" stroke-width="1.1" stroke-linejoin="round"/>']
    for a, b2 in (("END", "O5"), ("O5", "O10"), ("O10", "O15"), ("O15", "END"), ("O5", "O15"), ("O10", "END")):
        (x1, y1), (x2, y2) = _q(P[a]), _q(P[b2])
        o.append(f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="#8a6a48" stroke-width="1.2" stroke-linecap="round"/>')
    for k, p in P.items():
        big = k in ("END", "C", "O5", "O10", "O15")
        x, y = _q(p)
        o.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{4.2 if big else 2.7}" fill="{"#ecd8aa" if big else "#fbf2dc"}" stroke="#5a4632" stroke-width=".55"/>')
    x, y = _q(P["END"])
    o.append(f'<text x="{x - 6:.2f}" y="{y + 1.2:.2f}" font-size="3.4" text-anchor="end" fill="#cf4430">출발</text>')
    pv = S.get("preview") or {}
    team = S["turn"]
    for op in pv.get("options") or []:
        x, y = (29, 88) if op["finished"] else _q(P[op["dest"]])
        lab = "나가기" if op["finished"] else Y.RES[op["r"]]["nm"]
        o.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5" fill="{Y.HEX[team]}" fill-opacity=".25" stroke="{Y.HEX[team]}" stroke-width="1" stroke-dasharray="1.6 1"/>'
                 f'<text x="{x:.2f}" y="{y - 6:.2f}" font-size="4" font-weight="700" text-anchor="middle" fill="#2b2218">{lab}</text>')
    for g in S["groups"]:
        x, y = _q(P[Y.node_of(g)])
        col = Y.HEX[g["team"]]
        ring = f'<circle cx="{x:.2f}" cy="{y:.2f}" r="5.6" fill="none" stroke="#cf4430" stroke-width="1.1"/>' if str(pv.get("key")) == str(g["id"]) else ""
        o.append(f'{ring}<circle cx="{x:.2f}" cy="{y:.2f}" r="3.9" fill="{col}" stroke="#fff" stroke-width=".9"/>'
                 f'<text x="{x:.2f}" y="{y + 1.4:.2f}" font-size="3.6" font-weight="700" text-anchor="middle" fill="#fff">{html.escape(Y.tname(S, g["team"])[:1])}</text>')
        if g["n"] > 1:
            o.append(f'<text x="{x + 4.4:.2f}" y="{y - 3:.2f}" font-size="3.2" font-weight="700" fill="#cf4430">×{g["n"]}</text>')
    o.append("</svg>")
    b64 = base64.b64encode("".join(o).encode("utf-8")).decode("ascii")
    return f'<img class="yx-board" alt="말판" src="data:image/svg+xml;base64,{b64}">'


def piece_label(S, key) -> str:
    team = S["turn"]
    if key == "new":
        return f"{DOT[team]} 새 말 놓기 (대기 {S['home'][team]})"
    g = next((x for x in S["groups"] if str(x["id"]) == str(key)), None)
    if not g:
        return f"{DOT[team]} 말"
    return f"{DOT[team]} {NODE_NM.get(Y.node_of(g), '')}에 있는 말" + (f" {g['n']}개" if g["n"] > 1 else "")


def move_panel(S, kp: str):
    """버튼으로 말 옮기기(터치 말판이 안 될 때): ① 말 고르기 ② 갈 곳 고르기 → 바로 이동."""
    if S["phase"] == "over":
        md('<div class="yx yx-msg">게임이 끝났습니다. 수고하셨습니다!</div>')
        return
    if S["phase"] == "throw":
        md('<div class="yx yx-msg">윷을 던지는 중입니다. 진행석에서 결과를 누르면 여기서 말을 고릅니다.</div>')
        md(board_img(S))
        return
    md(board_img(S))
    pv = S.get("preview") or {}
    if pv.get("options"):
        key = pv["key"]
        md(f'<div class="yx yx-h">{html.escape(piece_label(S, key))} — 어디로 갈까요?</div>')
        opts = pv["options"]
        cols = st.columns(min(len(opts), 3))
        for n, op in enumerate(opts):
            label = Y.RES[op["r"]]["nm"] + " → " + ("나가기!" if op["finished"] else NODE_NM.get(op["dest"], op["dest"]))
            if cols[n % len(cols)].button(label, key=f"{kp}_v{S['ver']}_o{op['i']}", type="primary", use_container_width=True):
                if act(Y.move_option, key, op["i"], expected_ver=S["ver"]):
                    st.rerun(scope="fragment")
        if st.button("다른 말 고르기", key=f"{kp}_v{S['ver']}_cancel", use_container_width=True):
            if act(Y.select, None, expected_ver=S["ver"]):
                st.rerun(scope="fragment")
        return
    keys = Y.selectable(S)
    if not keys:
        md('<div class="yx yx-msg">지금 움직일 수 있는 말이 없습니다.</div>')
        return
    md('<div class="yx yx-h">움직일 말을 고르세요</div>')
    for k in keys:
        if st.button(piece_label(S, k), key=f"{kp}_v{S['ver']}_s{k}", use_container_width=True):
            if act(Y.select, k, expected_ver=S["ver"]):
                st.rerun(scope="fragment")


def teams_html(S) -> str:
    rows = []
    for i in range(S["cfg"]["teams"]):
        on = sum(g["n"] for g in S["groups"] if g["team"] == i)
        rk = S["ranks"].index(i)+1 if i in S["ranks"] else 0
        now = i == S["turn"] and S["phase"] != "over"
        tag = f'<span class="tag">{str(rk)+"등" if rk else "차례"}</span>' if rk or now else ""
        pct = 100*S["done"][i]/S["cfg"]["pieces"]
        rows.append(f'<div class="yx-team {"now" if now else ""}" style="--tc:{Y.HEX[i]}"><span class="stripe"></span><div><b>{html.escape(Y.tname(S,i))}{tag}</b><small>대기 {S["home"][i]} · 이동 중 {on}</small><div class="yx-progress"><i style="width:{pct}%"></i></div></div><strong>{S["done"][i]}<span> / {S["cfg"]["pieces"]}</span></strong></div>')
    return '<div class="yx yx-teams">'+''.join(rows)+'</div>'


def log_html(S):
    rows = ''.join(f'<div>{html.escape(t)}</div>' for t in S.get("log",[])[:4]) or '<div>첫 윷을 던지면 게임이 시작됩니다.</div>'
    md('<div class="yx yx-h">방금 일어난 일</div><div class="yx-log">'+rows+'</div>')


def rules_panel(S):
    with st.expander("이번 판 규칙 보기"):
        st.markdown(f"**이번 판은 팀당 말 {S['cfg']['pieces']}개입니다.** 모든 말을 먼저 내보낸 팀부터 순위를 정합니다.")
        st.markdown("**윷·모는 한 번 더 던집니다.** 추가 던지기를 마친 뒤, 남은 결과를 하나씩 원하는 순서로 사용합니다. 여러 말에 나누어 써도 됩니다.")
        st.markdown("**도·개·걸·빽도로 잡으면 즉시 한 번 더 던집니다.** 아직 쓰지 않은 결과는 보관하며, 새 결과와 함께 원하는 순서로 사용합니다. **윷·모로 잡았을 때는 추가 던지기를 중복 지급하지 않습니다.**" if S["cfg"]["captureBonus"] else "이번 판은 잡기 추가 던지기를 사용하지 않습니다.")
        st.markdown("**잡기·업기는 도착한 칸에서만 적용합니다.** 같은 팀 말은 자동으로 업고 함께 이동합니다. 업힌 말을 잡으면 전부 대기로 돌아갑니다." + (" 여러 개를 잡아도 잡기 추가 던지기는 한 번입니다." if S["cfg"]["captureBonus"] else " 이번 판은 잡아도 추가로 던지지 않습니다."))
        st.markdown("**모·뒷모·방에 멈춘 말**은 다음 전진 때 지름길로 갑니다. 그 칸을 지나가기만 하면 방향을 바꾸지 않습니다.")
        st.markdown("**빽도:** 왔던 길로 한 칸 돌아갑니다. 도에서 빽도가 나오면 참먹이에 서고, 다음 전진 결과로 완주합니다. 판에 말이 없고 쓸 전진 결과도 없으면 빽도를 넘깁니다." if S["cfg"]["backdo"] else "이번 판은 빽도를 사용하지 않습니다.")
        st.markdown("**완주:** 참먹이를 지나야 완주합니다." if S["cfg"]["strictEnd"] else "**완주:** 참먹이에 닿기만 해도 완주합니다.")
        st.markdown("**낙:** 윷이 정한 던지기 구역을 벗어나면 진행석에서 ‘낙’을 누릅니다. 이번 차례의 미사용 결과와 추가 던지기는 사라지고 다음 팀으로 넘어갑니다. 이미 이동한 말은 되돌리지 않습니다.")
        st.caption("널리 쓰는 기본 규칙을 바탕으로 정한 이번 행사 기준입니다. 빽도·낙·완주는 모임마다 다를 수 있으니 시작 전에 함께 확인해 주세요. 마지막 한 팀이 남으면 나머지 순위가 확정됩니다.")


@st.fragment(run_every=1)
def current_rules():
    # This panel must follow a new game/restore in another browser, too.
    rules_panel(Y.get())


def screen_view():
    md('<style>.stApp{background:#f5f2e7}header[data-testid="stHeader"],#MainMenu,footer{display:none!important}</style>')
    md(frame_html(board_engine.component_html(), height=0))
    @st.fragment(run_every=1)
    def live():
        payload = Y.screen_state()
        payload['_server_ts'] = time.time()
        s=json.dumps(payload,ensure_ascii=False)
        md(f'<i class="yut-st" title="{html.escape(s,quote=True)}" style="display:none"></i>')
    live()


def ctrl_view():
    md("\n\n".join((BASE_CSS, CTRL_CSS)))
    header("ctrl")
    @st.fragment(run_every=1)
    def live():
        S=Y.get()
        resources=controller_resources(S)
        main,side=st.columns([1.5,1],gap="large")
        with main:
            md('<div class="yx-eyebrow">진행자 전용 · 윷 결과 입력</div>')
            turn_card(S)
            pending_html(S)
            md('<div class="yx yx-h">던진 윷 결과를 눌러 주세요</div>')
            can=S['phase']=='throw'
            for row in [Y.RES_ORDER[:3],Y.RES_ORDER[3:]]:
                cols=st.columns(3)
                for r,col in zip(row,cols):
                    disabled=not can or (r=='back' and not S['cfg']['backdo'])
                    label=Y.RES[r]['nm']+(' ↻' if Y.RES[r]['again'] else '')
                    if col.button(label,key=f'throw_{r}_v{S["ver"]}',disabled=disabled,use_container_width=True,help=('한 번 더 던지기' if Y.RES[r]['again'] else f'{Y.RES[r]["steps"]}칸 이동')):
                        if act(Y.throw,r,expected_ver=S['ver']): st.rerun(scope='fragment')
            if st.button('낙 · 이번 차례 넘기기',key=f'nak_v{S["ver"]}',disabled=not can,use_container_width=True,
                         help='던지기 구역을 벗어난 경우에만 누르세요. 이번 차례의 남은 결과를 버리고 다음 팀으로 넘깁니다. 잘못 눌렀다면 되돌릴 수 있습니다.'):
                if act(Y.nak,expected_ver=S['ver']): st.rerun(scope='fragment')
            if S['phase']=='move':
                capture_hint = '도·개·걸·빽도로 잡으면 즉시 추가 던지기로 바뀝니다.' if S['cfg']['captureBonus'] else '이번 판은 잡기 추가 던지기를 사용하지 않습니다.'
                md('<div class="yx-msg">결과 입력 완료 · 팀 대표가 말을 옮기는 중입니다.<br>남은 결과는 원하는 순서로 사용하세요. '+capture_hint+'</div>')
            elif S['phase']=='over':
                md('<div class="yx-msg">한 판이 끝났습니다. 아래 ‘새 게임’에서 다시 시작할 수 있어요.</div>')
            else:
                md('<div class="yx-msg">추가 던지기 중에도 남은 결과는 보관합니다. 던지기를 마치면 새 결과와 함께 골라 쓰세요.<br>결과를 잘못 눌렀다면 되돌리기를 사용하세요.</div>')
            left,right=st.columns(2)
            if left.button('↶ 한 수 되돌리기',key=f'undo_v{S["ver"]}',disabled=not resources['can_undo'],use_container_width=True):
                if act(Y.undo,expected_ver=S['ver']): st.rerun(scope='fragment')
            right.download_button('↓ 현재 판 백업',data=resources['data'],file_name=resources['file_name'],mime='application/json',key='backup_download',use_container_width=True)
            with st.expander('진행석에서 직접 말 옮기기'):
                move_panel(S,'ctrl_move')
        with side:
            md('<div class="yx yx-h">팀별 완주 현황</div>')
            md(teams_html(S))
            log_html(S)
            st.caption(f'최근 수신 {datetime.now(timezone(timedelta(hours=9))).strftime("%H:%M:%S")} · 판 번호 {S["ver"]}')
    live()
    md('<div class="yx-footer">행사 설정 · 이름과 현수막, 게임 규칙, 백업 복원을 관리합니다.</div>')
    S=Y.get()
    with st.expander('팀 이름 · 현수막 바꾸기'):
        with st.form('names'):
            cols=st.columns(2)
            names=[cols[i%2].text_input(f'{DOT[i]} {i+1}번 팀',S['cfg']['names'][i],max_chars=8,key=f'name_{i}') for i in range(4)]
            title=st.text_input('현수막 제목',S['cfg']['title'],max_chars=20)
            sub=st.text_input('작은 제목',S['cfg']['sub'],max_chars=12)
            if st.form_submit_button('이름 · 현수막 적용',type='primary'):
                if act(Y.rename,{'names':names,'title':title,'sub':sub}):
                    st.success('적용했습니다. 모든 화면에 반영됩니다.')
    with st.expander('백업 파일로 이어 하기'):
        st.caption('내려받은 JSON 백업 파일로 말 위치·순서·남은 결과를 복원합니다. 복원 직후 되돌리기를 누르면 복원 전 판으로 돌아갑니다.')
        f=st.file_uploader('윷놀이 백업 파일',type=['json'],key='backup_upload')
        if f is not None:
            try:
                raw=f.getvalue()
                info=Y.inspect_backup(raw)
                st.info(f'{info["title"]} · {info["teams"]}팀 · 팀당 {info["pieces"]}개 · {info["turn_name"]} 차례')
                st.caption('저장 시각: '+str(info.get('saved_at','')))
                sure=st.checkbox('현재 판 대신 이 백업을 불러옵니다',key='restore_sure')
                if st.button('백업 복원',disabled=not sure,key='restore',type='primary'):
                    if act(Y.import_backup,raw,expected_ver=Y.get()['ver']):
                        st.success('복원했습니다. 스크린과 패드에서 이어서 진행하세요.')
            except Y.GameError as e:
                st.error(str(e))
    with st.expander('새 게임 · 팀 수와 규칙 설정'):
        mode=st.radio('새 판 규칙',['행사 기본 규칙','직접 설정'],horizontal=True,key='new_rule_mode')
        custom=mode=='직접 설정'
        defaults=S['cfg'] if custom else Y.default_cfg()
        st.caption('행사 기본: 팀당 말 4개 · 빽도 사용 · 잡으면 즉시 추가 던지기 · 윷·모 잡기 중복 없음 · 참먹이를 지나면 완주 · 낙이면 차례 종료')
        with st.form('newgame'):
            teams=st.radio('참가 팀 수',[2,3,4],index=[2,3,4].index(S['cfg']['teams']),horizontal=True,format_func=lambda n:f'{n}팀')
            pieces=st.radio('팀마다 말 수',[1,2,3,4,5,6],index=defaults['pieces']-1,horizontal=True,format_func=lambda n:f'{n}개',disabled=not custom,key=f'new_pieces_{custom}')
            backdo=st.checkbox('빽도 사용',defaults['backdo'],disabled=not custom,key=f'new_backdo_{custom}')
            cap=st.checkbox('상대 말을 잡으면 한 번 더 던지기',defaults['captureBonus'],disabled=not custom,key=f'new_capture_{custom}')
            strict=st.checkbox('참먹이를 지나야 완주 (끄면 닿기만 해도 완주)',defaults['strictEnd'],disabled=not custom,key=f'new_end_{custom}')
            sure=st.checkbox('현재 판을 끝내고 새로 시작합니다')
            if st.form_submit_button('새 게임 시작',type='primary'):
                if not sure: st.warning('‘현재 판을 끝내고 새로 시작합니다’를 먼저 선택해 주세요.')
                elif act(Y.new_game,dict(S['cfg'],teams=teams,pieces=pieces,backdo=backdo,captureBonus=cap,strictEnd=strict)):
                    st.success('새 게임을 시작했습니다.')
    current_rules()


def pad_view():
    md("\n\n".join((BASE_CSS, PAD_CSS, pad_board.HIDDEN_CSS)))
    header('pad')
    left,right=st.columns([2,1],gap='large')
    # iframe은 라이브 조각 밖에 둡니다. 매초 재생성하면 진행 중인 터치가 끊깁니다.
    with left:
        md(frame_html(pad_board.pad_html(shared_fonts=True), height=720))
    with right:
        @st.fragment(run_every=1)
        def live():
            S=Y.get()
            with st.container(key='yx_hidden'):
                for key,what,arg in pad_board.hidden_keys(S):
                    if st.button('.',key=key):
                        if what=='select':
                            act(Y.select,arg['key'],expected_ver=arg['expected_ver'])
                        else:
                            act(Y.move_option,arg['key'],arg['i'],expected_ver=arg['expected_ver'])
                        st.rerun(scope='fragment')
            md(pad_board.marker(S))
            turn_card(S)
            pending_html(S)
            md('<div class="yx yx-h">완주한 말</div>')
            md(teams_html(S))
            log_html(S)
            with st.expander('버튼으로 말 옮기기'):
                move_panel(S,'pad_move')
        live()
    current_rules()


def home_view():
    md(BASE_CSS)
    header('')
    S=Y.get()
    md(sprites.DEFS)
    art=''.join(f'<div class="yx-character"><div class="art">{sprites.SPRITES[i]}</div><b>{html.escape(Y.tname(S,i))}</b></div>' for i in range(4))
    md(f'<section class="yx yx-hero"><div><div class="yx-eyebrow">함께 웃고, 함께 달리는</div><div class="sub">{html.escape(S["cfg"]["title"])}</div><h1>한 수에 웃고,<br>한 판에 가까이.</h1><p>흥부도 놀부도, 오늘은 한 팀.<br>윷은 직접 던지고, 말판은 화면에서 함께 즐겨요.</p></div><div class="yx-cast">{art}</div></section>')
    cols=st.columns(3,gap='large')
    roles=[('01 · 함께 보는 말판','함께 보는 스크린','프로젝터에 크게 띄워 주세요.<br>움직이는 말과 순위를 모두 함께 봅니다.','스크린 열기','screen'),('02 · 진행자','한눈에, 진행석','던진 윷 결과를 입력해 주세요.<br>되돌리기와 백업도 이곳에서 합니다.','진행석 열기','ctrl'),('03 · 팀 대표','톡톡, 말 옮기기','팀 대표가 태블릿으로 조작해요.<br>말을 고르고, 갈 칸을 누르면 끝!','말판 열기','pad')]
    for col,(n,title,desc,label,v) in zip(cols,roles):
        with col:
            md(f'<div class="yx yx-role"><small>{n}</small><h3>{title}</h3><p>{desc}</p></div>')
            # Plain links use the already-loaded Markdown renderer. They avoid
            # LinkButton's extra JS chunk, which failed to load on Community Cloud.
            md('<div class="yx-launch">'
               f'<a class="yx-open" href="{html.escape(view_url(v), quote=True)}" '
               f'target="_blank" rel="noopener noreferrer">{html.escape(label)}</a></div>')
    with st.expander('처음 준비한다면 · 3분 안내'):
        st.markdown('1. **진행석**에서 팀 이름·현수막과 팀 수·말 수를 설정합니다.\n2. 노트북을 프로젝터에 연결하고 **스크린**을 엽니다. `F11` 또는 화면의 전체 화면 버튼을 사용합니다.\n3. 태블릿에서 같은 앱 주소의 **말 옮기기** 화면을 엽니다.\n4. 팀원이 윷을 던지면 진행자가 결과를 누르고, 팀 대표가 말을 옮깁니다.\n5. 쉬는 시간에는 진행석의 **현재 판 백업**을 내려받아 두세요.')
        st.caption('세 화면은 같은 앱 주소를 사용해야 합니다. 스크린을 한 번 클릭하면 효과음을 켤 수 있습니다. M 키로 음소거합니다.')
    md('<div class="yx yx-footer">워크숍 윷놀이 · 실제 윷과 함께 사용하는 공유 말판입니다.<br>자동 저장은 실행 중인 서버에 보관됩니다. 서버 교체 등에 대비하려면 JSON 백업도 내려받아 주세요.</div>')


view=st.query_params.get('view','')
if view=='screen': screen_view()
elif view=='ctrl': ctrl_view()
elif view=='pad': pad_view()
else: home_view()
