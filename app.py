"""윷놀이 말판 (Streamlit) — 주소 하나로 세 화면.

  /?view=screen  스크린(프로젝터): 3D 말판. 버튼 없음
  /?view=ctrl    진행석(내무계): 윷 결과 입력 · 되돌리기 · 팀 이름/현수막 · 새 게임
  /?view=pad     말 옮기기(팀 대표, 갤럭시탭): 번호 누르고 → '움직이기'
  /              안내(세 화면으로 가는 버튼)

판은 서버 한 곳(data/yut.db)에 있어서, 어느 기기에서 바꿔도 다른 화면에 1초 안에 반영됩니다.
"""
from __future__ import annotations

import base64
import html
import json

import streamlit as st
import streamlit.components.v1 as components

import board_engine
import yutcore as Y

st.set_page_config(page_title="윷놀이 말판", page_icon="🎲", layout="wide", initial_sidebar_state="collapsed")
Y.init()

DOT = ["🟠", "🟣", "🔵", "🟢"]   # 흥부·놀부·제비·박씨 색
SIDE = {1: "#f3a184", 2: "#f6cd6f", 3: "#8fd0bd", 4: "#9fb9ec"}

BASE_CSS = """<style>
@import url("https://fonts.googleapis.com/css2?family=Gowun+Dodum&family=Yeon+Sung&display=swap");
header[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stDecoration"],[data-testid="stStatusWidget"],#MainMenu,footer{display:none!important}
[data-stale="true"],.stale-element{opacity:1!important;transition:none!important}
.stApp{background:linear-gradient(180deg,#d6ecdf 0%,#f4e7c6 70%)}
.block-container{max-width:760px!important;padding-top:1rem!important;padding-bottom:3rem!important}
.yx{font-family:"Gowun Dodum","Malgun Gothic","Apple SD Gothic Neo",sans-serif;color:#2b2218}
.yx-h{font-family:"Yeon Sung","Malgun Gothic",sans-serif;font-size:1.05rem;color:#6a5a45;margin:.2rem 0 .4rem}
.yx-turn{display:flex;align-items:center;gap:.8rem;padding:.8rem 1rem;border:3px solid #2b2218;border-radius:14px;box-shadow:4px 4px 0 #2b2218;margin-bottom:.8rem}
.yx-turn .dot{width:2.6rem;height:2.6rem;border-radius:50%;border:3px solid #2b2218;flex:none}
.yx-turn b{display:block;font-family:"Yeon Sung","Malgun Gothic",sans-serif;font-weight:400;font-size:2rem;line-height:1.05}
.yx-turn small{font-size:1rem;color:#4a3d2e}
.yx-pend{display:flex;gap:.4rem;flex-wrap:wrap;align-items:center;margin:.2rem 0 .6rem}
.yx-pend span{font-family:"Yeon Sung",sans-serif;font-size:1.5rem;padding:.05rem .9rem;border:3px solid #2b2218;border-radius:999px;background:#fffaf0}
.yx-pend span.on{background:#e8b03f}
.yx-msg{font-size:1.15rem;line-height:1.5;padding:.8rem 1rem;border-radius:12px;background:#fffaf0;border:2px dashed #2b2218;margin:.4rem 0}
.yx-board{display:block;width:100%;max-width:520px;margin:.2rem auto .6rem}
div[data-testid="stButton"] button,div[data-testid="stFormSubmitButton"] button{min-height:3.4rem;border-radius:14px!important;border:3px solid #2b2218!important;box-shadow:0 4px 0 #2b2218;background:#fffaf0;color:#2b2218}
div[data-testid="stButton"] button p,div[data-testid="stFormSubmitButton"] button p{font-family:"Yeon Sung","Malgun Gothic",sans-serif;font-size:1.45rem!important;line-height:1.15}
div[data-testid="stButton"] button:active{transform:translateY(3px);box-shadow:0 1px 0 #2b2218}
div[data-testid="stButton"] button[kind="primary"],div[data-testid="stButton"] button[data-testid="stBaseButton-primary"],div[data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"]{background:#cf4430;color:#fff}
div[data-testid="stButton"] button:disabled{opacity:.35;box-shadow:none}
</style>"""

CTRL_CSS = """<style>
div[class*="st-key-t_"] button{min-height:5.4rem}
div[class*="st-key-t_"] button p{font-size:2.5rem!important}
</style>"""

PAD_CSS = """<style>
.block-container{max-width:900px!important}
div[data-testid="stButton"] button{min-height:4.2rem}
div[data-testid="stButton"] button p{font-size:1.7rem!important}
</style>"""


def md(h: str):
    st.markdown(h, unsafe_allow_html=True)


def base_url() -> str:
    try:
        h = {k.lower(): v for k, v in st.context.headers.items()}
        host = h.get("x-forwarded-host") or h.get("host") or ""
        if host:
            proto = h.get("x-forwarded-proto") or ("https" if "streamlit.app" in host else "http")
            return f"{proto}://{host}"
    except Exception:
        pass
    return ""


def act(fn, *a) -> bool:
    try:
        fn(*a)
        return True
    except Y.GameError as e:
        st.error(str(e))
        return False


# ───────────────────────── 공통 조각
def turn_card(S):
    over = S["phase"] == "over"
    team = S["ranks"][0] if over and S["ranks"] else S["turn"]
    what = ("모든 말이 먼저 났습니다" if over else "윷을 던지는 중" if S["phase"] == "throw" else "말을 옮길 차례")
    if S["phase"] == "throw" and S["pending"]:
        what = "윷·모가 나와서 한 번 더 던집니다"
    md(f'<div class="yx yx-turn" style="background:color-mix(in srgb,{Y.HEX[team]} 16%,#fffaf0)">'
       f'<span class="dot" style="background:{Y.HEX[team]}"></span><div><b>{html.escape(Y.tname(S, team))} {"승리!" if over else "차례"}</b>'
       f'<small>{what}</small></div></div>')


def pending_html(S, label="이번 결과"):
    chips = "".join(f'<span class="{"on" if S["phase"] == "move" and i == S["sel"] else ""}">{Y.RES[r]["nm"]}</span>'
                    for i, r in enumerate(S["pending"])) or '<small style="color:#8a7a62">아직 없음</small>'
    md(f'<div class="yx yx-h">{label}</div><div class="yx yx-pend">{chips}</div>')


def board_img(S, cands=None, preview=None) -> str:
    """패드·진행석용 납작한 말판 그림(번호 붙은 말, 고른 말의 갈 길)."""
    P = Y.P
    o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="-7 -9 114 116" font-family="Malgun Gothic,Apple SD Gothic Neo,sans-serif">',
         '<rect x="-6" y="-8" width="112" height="114" rx="6" fill="#f2e2bb" stroke="#6b4321" stroke-width="1.6"/>',
         '<path d="M90 90 L90 10 L10 10 L10 90 Z M90 10 L10 90 M10 10 L90 90" fill="none" stroke="#7a5532" stroke-width="2.2" stroke-linecap="round"/>']
    for k, (x, y) in P.items():
        big = k in ("END", "C", "O5", "O10", "O15")
        if k[0] == "O" and not big:
            n = int(k[1:])
            fill = SIDE[1 if n < 5 else 2 if n < 10 else 3 if n < 15 else 4]
        else:
            fill = "#cf4430" if k == "END" else "#e8b03f" if k == "C" else "#e8604a" if big else "#fff4dc"
        o.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{4.4 if big else 2.9}" fill="{fill}" stroke="#2b2218" stroke-width=".6"/>')
    o.append('<text x="84.5" y="100.8" font-size="3.6" text-anchor="end" fill="#cf4430">출발</text>')
    if preview and preview.get("nodes"):
        pts = " ".join(f"{P[n][0]:.2f},{P[n][1]:.2f}" for n in preview["nodes"] if n in P)
        o.append(f'<polyline points="{pts}" fill="none" stroke="#cf4430" stroke-width="1.8" stroke-dasharray="2.6 1.6" stroke-linecap="round" stroke-linejoin="round"/>')
        dx, dy = P[preview["dest"]]
        o.append(f'<circle cx="{dx:.2f}" cy="{dy:.2f}" r="6.2" fill="none" stroke="#cf4430" stroke-width="1.1" stroke-dasharray="1.6 1"/>')
    num = {c["key"]: c["num"] for c in (cands or [])}
    sel = preview["key"] if preview else None
    for g in sorted(S["groups"], key=lambda g: g["id"]):
        x, y = P[Y.node_of(g)]
        col = Y.HEX[g["team"]]
        ring = '<circle cx="{0:.2f}" cy="{1:.2f}" r="6.4" fill="none" stroke="#cf4430" stroke-width="1.3"/>'.format(x, y) if g["id"] == sel else ""
        lab = str(num[g["id"]]) if g["id"] in num else ("" if g["n"] == 1 else str(g["n"]))
        o.append(f'{ring}<circle cx="{x:.2f}" cy="{y:.2f}" r="4.6" fill="{col}" stroke="#fff" stroke-width="1"/>')
        if lab:
            o.append(f'<text x="{x:.2f}" y="{y + 1.6:.2f}" font-size="5" font-weight="700" text-anchor="middle" fill="#fff">{lab}</text>')
        if g["id"] in num and g["n"] > 1:
            o.append(f'<text x="{x + 5.4:.2f}" y="{y - 3.6:.2f}" font-size="3.4" fill="#2b2218">×{g["n"]}</text>')
    if "new" in num:
        x, y = P["END"][0] + 8, P["END"][1] + 6
        col = Y.HEX[S["turn"]]
        o.append(f'<circle cx="{x}" cy="{y}" r="4.6" fill="#fffaf0" stroke="{col}" stroke-width="1.4" stroke-dasharray="1.6 1"/>'
                 f'<text x="{x}" y="{y + 1.6}" font-size="5" font-weight="700" text-anchor="middle" fill="{col}">{num["new"]}</text>')
        if sel == "new":
            o.append(f'<circle cx="{x}" cy="{y}" r="6.4" fill="none" stroke="#cf4430" stroke-width="1.3"/>')
    o.append("</svg>")
    b64 = base64.b64encode("".join(o).encode("utf-8")).decode("ascii")
    return f'<img class="yx-board" alt="말판" src="data:image/svg+xml;base64,{b64}">'


def move_panel(S, kp: str):
    """말 옮기기: ① 결과 고르기 ② 말 번호 누르기(스크린에 갈 길 표시) ③ 움직이기."""
    if S["phase"] == "over":
        md('<div class="yx yx-msg">게임이 끝났습니다. 수고하셨습니다!</div>')
        return
    if S["phase"] == "throw":
        md('<div class="yx yx-msg">윷을 던지는 중입니다. 진행석에서 결과를 누르면 여기서 말을 고릅니다.</div>')
        md(board_img(S))
        return
    team = S["turn"]
    if len(S["pending"]) > 1:
        md('<div class="yx yx-h">어떤 결과부터 쓸까요?</div>')
        cols = st.columns(len(S["pending"]))
        for i, (r, col) in enumerate(zip(S["pending"], cols)):
            on = i == S["sel"]
            if col.button(("✔ " if on else "") + Y.RES[r]["nm"], key=f"{kp}_r{i}", use_container_width=True, type="primary" if on else "secondary"):
                if not on and act(Y.select_result, i):
                    st.rerun(scope="fragment")
    r = S["pending"][S["sel"]]
    cands = Y.candidates(S)
    pv = S.get("preview")
    md(board_img(S, cands, pv))
    if pv:
        c = next((x for x in cands if x["key"] == pv["key"]), None)
        what = "새 말" if pv["key"] == "new" else (f"말 {c['n']}개" if c else "말")
        md(f'<div class="yx yx-msg">{DOT[team]} <b>{what}</b>을(를) <b>{Y.RES[r]["nm"]}</b>만큼 — 스크린에 빨간 점선으로 갈 길이 보입니다.'
           f'{" <b>참먹이로 나갑니다!</b>" if pv.get("finished") else ""}</div>')
        if st.button("✔ 이 말로 움직이기", key=f"{kp}_go", type="primary", use_container_width=True):
            if act(Y.move, pv["key"]):
                st.rerun(scope="fragment")
        if st.button("다른 말 고르기", key=f"{kp}_cancel", use_container_width=True):
            if act(Y.preview, None):
                st.rerun(scope="fragment")
        return
    if not cands:
        md('<div class="yx yx-msg">이 결과로 움직일 말이 없습니다.</div>')
        return
    md(f'<div class="yx yx-h">{Y.RES[r]["nm"]}({"뒤로 1칸" if r == "back" else str(Y.RES[r]["steps"]) + "칸"}) — 움직일 말 번호를 누르세요</div>')
    for c in cands:
        label = f"{DOT[team]}  {c['num']}번 · " + ("새 말 놓기" if c["key"] == "new" else (f"말 {c['n']}개 (업힌 말)" if c["n"] > 1 else "판 위의 말"))
        if c["finished"]:
            label += " → 나감!"
        if st.button(label, key=f"{kp}_c{c['key']}", use_container_width=True):
            if act(Y.preview, c["key"]):
                st.rerun(scope="fragment")


# ───────────────────────── 화면들
def screen_view():
    md("""<style>header[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stDecoration"],[data-testid="stStatusWidget"],#MainMenu,footer{display:none!important}
.stApp{background:#d6ecdf}</style>""")
    components.html(board_engine.component_html(), height=0)

    @st.fragment(run_every=1)
    def live():
        s = json.dumps(Y.screen_state(), ensure_ascii=False)
        md(f'<i class="yut-st" title="{html.escape(s, quote=True)}" style="display:none"></i>')

    live()


def ctrl_view():
    md(BASE_CSS + CTRL_CSS)
    md('<div class="yx yx-h" style="font-size:1.3rem">진행석 · 윷 결과 입력</div>')

    @st.fragment(run_every=1.5)
    def live():
        S = Y.get()
        turn_card(S)
        pending_html(S)
        can = S["phase"] == "throw"
        rows = [Y.RES_ORDER[:3], Y.RES_ORDER[3:]]
        for row in rows:
            cols = st.columns(3)
            for r, col in zip(row, cols):
                dis = not can or (r == "back" and not S["cfg"]["backdo"])
                label = Y.RES[r]["nm"] + (" ↺" if Y.RES[r]["again"] else "")
                if col.button(label, key=f"t_{r}", use_container_width=True, disabled=dis, type="primary" if Y.RES[r]["again"] else "secondary"):
                    if act(Y.throw, r):
                        st.rerun(scope="fragment")
        if S["phase"] == "move":
            md('<div class="yx yx-msg">팀 대표가 패드에서 말을 옮기는 중입니다. 다 옮기면 다음 결과를 누를 수 있습니다.</div>')
        elif S["phase"] == "over":
            md('<div class="yx yx-msg">게임이 끝났습니다. 아래 [새 게임]으로 다시 시작할 수 있습니다.</div>')
        if S["log"]:
            md('<div class="yx" style="font-size:.95rem;color:#5b4c39;line-height:1.6;margin:.3rem 0 .6rem">' +
               "".join(f"<div>{html.escape(x)}</div>" for x in S["log"][:3]) + "</div>")
        c1, c2 = st.columns(2)
        if st.session_state.get("cf_undo"):
            c1.warning("방금 한 동작을 되돌립니다.")
            if c1.button("되돌리기 실행", key="undo_ok", type="primary", use_container_width=True):
                st.session_state.pop("cf_undo", None)
                if not Y.undo():
                    st.info("되돌릴 것이 없습니다.")
                st.rerun(scope="fragment")
            if c2.button("취소", key="undo_no", use_container_width=True):
                st.session_state.pop("cf_undo", None)
                st.rerun(scope="fragment")
        elif c1.button("↶ 되돌리기", key="undo", use_container_width=True, disabled=not Y.can_undo()):
            st.session_state["cf_undo"] = True
            st.rerun(scope="fragment")
        with st.expander("패드가 안 될 때 — 여기서 말 옮기기"):
            move_panel(S, "cm")

    live()
    S = Y.get()
    with st.expander("팀 이름 · 현수막 글씨 (판은 그대로)"):
        with st.form("names"):
            cols = st.columns(2)
            names = [cols[i % 2].text_input(f"{DOT[i]} {i + 1}번 팀", S["cfg"]["names"][i], max_chars=8, key=f"nm{i}") for i in range(4)]
            title = st.text_input("현수막 글씨", S["cfg"]["title"], max_chars=20)
            sub = st.text_input("현수막 옆 작은 글씨 (비우면 숨김)", S["cfg"]["sub"], max_chars=12)
            if st.form_submit_button("저장", type="primary"):
                Y.rename({"names": names, "title": title, "sub": sub})
                st.success("바꿨습니다. 스크린에 바로 반영됩니다.")
    with st.expander("새 게임 (팀 수 · 말 수 · 규칙)"):
        with st.form("newgame"):
            teams = st.radio("팀 수", [2, 3, 4], index=[2, 3, 4].index(S["cfg"]["teams"]), horizontal=True, format_func=lambda n: f"{n}팀")
            pieces = st.radio("팀마다 말 수", [2, 3, 4, 5], index=[2, 3, 4, 5].index(S["cfg"]["pieces"]) if S["cfg"]["pieces"] in (2, 3, 4, 5) else 2,
                              horizontal=True, format_func=lambda n: f"{n}개")
            backdo = st.checkbox("빽도 쓰기", S["cfg"]["backdo"])
            cap = st.checkbox("상대 말을 잡으면 한 번 더 던지기", S["cfg"]["captureBonus"])
            strict = st.checkbox("참먹이를 지나야 나가기 (정식 규칙, 끄면 참먹이에 닿기만 해도 남)", S["cfg"]["strictEnd"])
            sure = st.checkbox("지금 판을 지우고 새로 시작합니다")
            if st.form_submit_button("새 게임 시작", type="primary"):
                if not sure:
                    st.warning("'지금 판을 지우고 새로 시작합니다'에 체크해 주세요.")
                else:
                    Y.new_game(dict(S["cfg"], teams=teams, pieces=pieces, backdo=backdo, captureBonus=cap, strictEnd=strict))
                    st.success("새 게임을 시작했습니다.")
    url = base_url()
    if url:
        st.caption(f"스크린: {url}/?view=screen · 패드: {url}/?view=pad")


def pad_view():
    md(BASE_CSS + PAD_CSS)

    @st.fragment(run_every=1)
    def live():
        S = Y.get()
        turn_card(S)
        if S["phase"] == "move":
            pending_html(S, "쓸 결과")
        move_panel(S, "p")

    live()


def home_view():
    md(BASE_CSS)
    S = Y.get()
    md(f'<div class="yx" style="text-align:center;margin:1.5rem 0 1rem"><div class="yx-h">{html.escape(S["cfg"]["sub"])}</div>'
       f'<div style="font-family:Yeon Sung,sans-serif;font-size:2.6rem">{html.escape(S["cfg"]["title"])} · 윷놀이</div></div>')
    url = base_url()
    for label, v, desc in (("📺 스크린 (프로젝터)", "screen", "노트북을 프로젝터에 연결하고 이 화면을 F11 전체 화면으로"),
                           ("🎯 진행석 (윷 결과 입력)", "ctrl", "내무계 직원 — 윷 결과를 누르는 화면"),
                           ("✋ 말 옮기기 (팀 대표 · 패드)", "pad", "갤럭시탭 — 말 번호를 누르고 '움직이기'")):
        st.link_button(label, f"{url}/?view={v}" if url else f"?view={v}", use_container_width=True)
        st.caption(desc)


view = st.query_params.get("view", "")
if view == "screen":
    screen_view()
elif view == "ctrl":
    ctrl_view()
elif view == "pad":
    pad_view()
else:
    home_view()
