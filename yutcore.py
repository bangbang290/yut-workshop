"""윷놀이 말판 — 규칙과 진행 상태(서버 한 곳에 저장해서 노트북·패드가 같은 판을 봅니다).

말판(HTML) 버전에서 시험을 통과한 규칙을 그대로 옮겼습니다.
  · 모·뒷모·방에 '멈춘' 말만 지름길로 꺾음
  · 업기(같은 팀 말이 같은 칸) · 잡기(상대 말은 대기로, 잡은 팀은 한 번 더)
  · 윷·모는 한 번 더 · 빽도(왔던 길로 한 칸, 도에서 빽도면 참먹이에 섬)
"""
from __future__ import annotations

import copy
import json
import os
import sqlite3
import threading
import time
from contextlib import contextmanager

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("YUT_DB", os.path.join(BASE, "data", "yut.db"))
_lock = threading.RLock()

# ───────────────────────── 판 모양 (0~100). 참먹이(출발)는 오른쪽 아래, 말은 오른쪽 변을 따라 위로.
P: dict[str, tuple[float, float]] = {"END": (90.0, 90.0)}
for _k in range(1, 5):
    P[f"O{_k}"] = (90.0, 90.0 - 16 * _k)
    P[f"O{5 + _k}"] = (90.0 - 16 * _k, 10.0)
    P[f"O{10 + _k}"] = (10.0, 10.0 + 16 * _k)
    P[f"O{15 + _k}"] = (10.0 + 16 * _k, 90.0)
P["O5"], P["O10"], P["O15"] = (90.0, 10.0), (10.0, 10.0), (10.0, 90.0)
_t = 40 / 3
P.update({"A1": (90 - _t, 10 + _t), "A2": (90 - 2 * _t, 10 + 2 * _t), "C": (50.0, 50.0),
          "A3": (10 + 2 * _t, 90 - 2 * _t), "A4": (10 + _t, 90 - _t),
          "B1": (10 + _t, 10 + _t), "B2": (10 + 2 * _t, 10 + 2 * _t),
          "B3": (90 - 2 * _t, 90 - 2 * _t), "B4": (90 - _t, 90 - _t)})


def _seq(a, b):
    return [f"O{i}" for i in range(a, b + 1)]


R = {
    "O": ["S"] + _seq(1, 19) + ["END"],
    "M": ["S"] + _seq(1, 5) + ["A1", "A2", "C", "A3", "A4"] + _seq(15, 19) + ["END"],
    "MC": ["S"] + _seq(1, 5) + ["A1", "A2", "C", "B3", "B4", "END"],
    "D": ["S"] + _seq(1, 10) + ["B1", "B2", "C", "B3", "B4", "END"],
}
RES = {
    "back": {"nm": "빽도", "steps": -1, "again": False},
    "do": {"nm": "도", "steps": 1, "again": False},
    "gae": {"nm": "개", "steps": 2, "again": False},
    "geol": {"nm": "걸", "steps": 3, "again": False},
    "yut": {"nm": "윷", "steps": 4, "again": True},
    "mo": {"nm": "모", "steps": 5, "again": True},
}
RES_ORDER = ["do", "gae", "geol", "yut", "mo", "back"]
DEFAULT_NAMES = ["흥부", "놀부", "제비", "박씨"]
HEX = ["#e07b1f", "#7a3fb0", "#1f3f8f", "#2e8b45"]


class GameError(ValueError):
    """지금 할 수 없는 동작(안내 문구로 보여 줌)."""


def default_cfg() -> dict:
    return {"teams": 4, "names": DEFAULT_NAMES[:], "pieces": 4, "backdo": True, "strictEnd": False,
            "captureBonus": True, "title": "심사2국 워크숍", "sub": "윷놀이 한마당"}


def norm_cfg(c: dict | None) -> dict:
    d = default_cfg()
    c = dict(c or {})
    out = {
        "teams": max(2, min(4, int(c.get("teams", d["teams"])))),
        "pieces": max(1, min(6, int(c.get("pieces", d["pieces"])))),
        "backdo": bool(c.get("backdo", d["backdo"])),
        "strictEnd": bool(c.get("strictEnd", d["strictEnd"])),
        "captureBonus": bool(c.get("captureBonus", d["captureBonus"])),
        "title": (str(c.get("title") or "").strip() or d["title"])[:20],
        "sub": str(c.get("sub", d["sub"]) or "").strip()[:12],
    }
    names = list(c.get("names") or [])
    out["names"] = [(str(names[i]).strip() if i < len(names) and str(names[i]).strip() else DEFAULT_NAMES[i])[:8] for i in range(4)]
    return out


def fresh(cfg: dict | None = None) -> dict:
    cfg = norm_cfg(cfg)
    n = cfg["teams"]
    return {"cfg": cfg, "groups": [], "home": [cfg["pieces"]] * n, "done": [0] * n, "turn": 0, "phase": "throw",
            "pending": [], "sel": 0, "bonus": 0, "ranks": [], "log": [], "nid": 1, "started": False,
            "preview": None, "last": {"kind": "reset", "at": time.time()}, "ver": 0}


# ───────────────────────── 규칙 (순수 함수)
def node_of(g) -> str:
    return R[g["route"]][g["idx"]]


def plan(g, steps, strict_end=False):
    route, idx = g["route"], g["idx"]
    if steps < 0:                                  # 빽도: 왔던 길로 한 칸 뒤로
        if idx <= 0:
            return None
        idx -= 1
        if idx == 0:                               # 도에서 빽도 → 참먹이에 섬(다음에 나감)
            return {"route": route, "idx": len(R[route]) - 1, "finished": False}
        return {"route": route, "idx": idx, "finished": False}
    node = R[route][idx]
    if route == "O" and node == "O5":
        route = "M"
    elif route == "O" and node == "O10":
        route = "D"
    elif route == "M" and node == "C":
        route = "MC"
    end = len(R[route]) - 1
    started_at_end = idx == end
    idx += steps
    if idx > end or started_at_end:
        return {"route": route, "idx": end, "finished": True}
    if idx == end:
        return {"route": route, "idx": end, "finished": not strict_end}
    return {"route": route, "idx": idx, "finished": False}


def path_nodes(g, steps, p, new=False):
    if steps < 0:
        return [node_of(g), R[p["route"]][p["idx"]]]
    r = R[p["route"]]
    out = [r[i] for i in range(g["idx"], min(p["idx"], len(r) - 1) + 1) if r[i] != "S"]
    return (["END"] + out) if new else out


def on_board(S, team):
    return [g for g in S["groups"] if g["team"] == team]


def usable(S, r, team):
    if r == "back":
        return len(on_board(S, team)) > 0
    return S["home"][team] > 0 or len(on_board(S, team)) > 0


def active_teams(S):
    return [i for i in range(S["cfg"]["teams"]) if i not in S["ranks"]]


def tname(S, i):
    return S["cfg"]["names"][i] if i < len(S["cfg"]["names"]) else DEFAULT_NAMES[i]


def _log(S, text):
    S["log"] = ([text] + S["log"])[:4]


def _pick_sel(S):
    S["sel"] = 0
    for i, r in enumerate(S["pending"]):
        if usable(S, r, S["turn"]):
            S["sel"] = i
            return


def _next_turn(S):
    act = active_teams(S)
    if len(act) <= 1:
        if len(act) == 1 and act[0] not in S["ranks"]:
            S["ranks"].append(act[0])
        S["phase"] = "over"
        return
    t = S["turn"]
    while True:
        t = (t + 1) % S["cfg"]["teams"]
        if t not in S["ranks"]:
            break
    S.update(turn=t, phase="throw", pending=[], sel=0, bonus=0)


def _settle(S):
    """쓸 수 없는 결과(판에 말이 없는데 빽도 등)를 정리하고, 다 쓰면 다음 단계로."""
    if S["phase"] != "move":
        return
    team = S["turn"]
    forward = any(r != "back" and usable(S, r, team) for r in S["pending"])
    kept, removed = [], []
    for r in S["pending"]:
        (kept if (usable(S, r, team) or (r == "back" and forward)) else removed).append(r)
    S["pending"] = kept
    if removed:
        _log(S, f"판에 말이 없어 {', '.join(RES[r]['nm'] for r in removed)}는 넘어갑니다")
    if S["sel"] >= len(S["pending"]):
        S["sel"] = 0
    if S["pending"]:
        return
    if team in S["ranks"]:
        S["bonus"] = 0
        _next_turn(S)
        return
    if S["bonus"] > 0:
        S["bonus"] -= 1
        S["phase"] = "throw"
        return
    _next_turn(S)


def candidates(S):
    """지금 고른 결과로 움직일 수 있는 것들: [{'key': 'new'|그룹id, 'num': 1.., 'nodes', 'dest', 'finished'}]"""
    if S["phase"] != "move" or not S["pending"]:
        return []
    r = S["pending"][S["sel"]]
    steps, team, strict = RES[r]["steps"], S["turn"], S["cfg"]["strictEnd"]
    out = []
    if steps > 0 and S["home"][team] > 0:
        g0 = {"route": "O", "idx": 0}
        p = plan(g0, steps, strict)
        out.append({"key": "new", "nodes": path_nodes(g0, steps, p, new=True), "dest": R[p["route"]][p["idx"]],
                    "finished": p["finished"], "n": 1})
    groups = sorted(on_board(S, team), key=lambda g: g["id"])
    for g in groups:
        p = plan(g, steps, strict)
        if p:
            out.append({"key": g["id"], "nodes": path_nodes(g, steps, p), "dest": R[p["route"]][p["idx"]],
                        "finished": p["finished"], "n": g["n"], "at": node_of(g)})
    for i, c in enumerate(out):
        c["num"] = i + 1
    return out


def apply_throw(S, r):
    if r not in RES:
        raise GameError("알 수 없는 결과입니다.")
    if S["phase"] != "throw":
        raise GameError("지금은 말을 옮길 차례입니다. 패드에서 말을 옮긴 뒤에 다음 결과를 눌러 주세요."
                        if S["phase"] == "move" else "게임이 끝났습니다.")
    if r == "back" and not S["cfg"]["backdo"]:
        raise GameError("빽도를 쓰지 않는 설정입니다.")
    thrower = S["turn"]
    S["started"] = True
    S["pending"].append(r)
    S["preview"] = None
    if RES[r]["again"]:
        _log(S, f"{tname(S, S['turn'])} {RES[r]['nm']} — 한 번 더 던집니다")
    else:
        S["phase"] = "move"
        _pick_sel(S)
        _settle(S)
    S["last"] = {"kind": "throw", "r": r, "team": thrower, "at": time.time()}


def apply_move(S, key):
    if S["phase"] != "move" or not S["pending"]:
        raise GameError("지금은 말을 옮길 때가 아닙니다.")
    r = S["pending"][S["sel"]]
    steps, team, strict = RES[r]["steps"], S["turn"], S["cfg"]["strictEnd"]
    new = key == "new"
    if new:
        if steps < 0 or S["home"][team] <= 0:
            raise GameError("새 말을 놓을 수 없습니다.")
        g = {"id": S["nid"], "team": team, "n": 1, "route": "O", "idx": 0}
    else:
        g = next((x for x in S["groups"] if x["id"] == key), None)
        if not g or g["team"] != team:
            raise GameError("이 팀의 말이 아닙니다.")
    p = plan(g, steps, strict)
    if not p:
        raise GameError("이 말은 움직일 수 없습니다.")
    nodes = path_nodes(g, steps, p, new=new)
    start_n = g["n"]
    if new:
        S["nid"] += 1
        S["home"][team] -= 1
        S["groups"].append(g)
    g["route"], g["idx"] = p["route"], p["idx"]
    msg = f"{tname(S, team)} {RES[r]['nm']}"
    caught_at, caught_n, stacked = None, 0, False
    if p["finished"]:
        S["done"][team] += g["n"]
        S["groups"] = [x for x in S["groups"] if x is not g]
        msg += f" — 말 {g['n']}개가 났습니다"
    else:
        key_node = node_of(g)
        names = []
        keep = []
        for o in S["groups"]:
            if o is not g and o["team"] != team and node_of(o) == key_node:
                S["home"][o["team"]] += o["n"]
                caught_n += o["n"]
                names.append(tname(S, o["team"]))
            else:
                keep.append(o)
        S["groups"] = keep
        mine = next((o for o in S["groups"] if o is not g and o["team"] == team and node_of(o) == key_node), None)
        if mine:
            g["n"] += mine["n"]
            S["groups"] = [o for o in S["groups"] if o is not mine]
            stacked = True
            msg += f" — 업었습니다(말 {g['n']}개)"
        if not caught_n and not mine:
            msg += " — 새 말이 나왔습니다" if new else (" — 한 칸 물러났습니다" if steps < 0 else " — 말을 옮겼습니다")
        if caught_n:
            caught_at = key_node
            msg += f" — {', '.join(names)} 말 {caught_n}개를 잡았습니다"
            if S["cfg"]["captureBonus"]:
                S["bonus"] += 1
                msg += " · 한 번 더"
    _log(S, msg)
    S["pending"].pop(S["sel"])
    S["preview"] = None
    S["last"] = {"kind": "move", "team": team, "n": start_n, "id": g["id"], "nodes": nodes, "finished": p["finished"],
                 "caught": caught_at, "caughtN": caught_n, "stacked": stacked, "new": new, "at": time.time()}
    if S["done"][team] >= S["cfg"]["pieces"] and team not in S["ranks"]:
        S["ranks"].append(team)
        S["pending"], S["bonus"] = [], 0
        _log(S, f"{tname(S, team)} 말이 모두 났습니다! {len(S['ranks'])}등")
        S["last"]["rank"] = len(S["ranks"])
        if len(active_teams(S)) <= 1:
            rest = active_teams(S)
            if rest:
                S["ranks"].append(rest[0])
            S["phase"] = "over"
            return
    if S["pending"]:
        _pick_sel(S)
    _settle(S)


# ───────────────────────── 저장 (SQLite 한 파일)
def _connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    c = sqlite3.connect(DB_PATH, timeout=20, isolation_level=None, check_same_thread=False)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=20000")
    return c


@contextmanager
def _tx():
    with _lock:
        c = _connect()
        try:
            c.execute("BEGIN IMMEDIATE")
            yield c
            c.execute("COMMIT")
        except BaseException:
            c.execute("ROLLBACK")
            raise
        finally:
            c.close()


def _get(c, k, default=None):
    r = c.execute("SELECT v FROM kv WHERE k=?", (k,)).fetchone()
    return json.loads(r[0]) if r else default


def _put(c, k, v):
    c.execute("INSERT INTO kv(k, v) VALUES(?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, json.dumps(v, ensure_ascii=False)))


def init():
    with _tx() as c:
        c.execute("CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT NOT NULL)")
        if _get(c, "game") is None:
            _put(c, "game", fresh())
            _put(c, "hist", [])


def get() -> dict:
    with _lock:
        c = _connect()
        try:
            S = _get(c, "game")
        finally:
            c.close()
    return S if S else fresh()


def _change(fn, keep_history=True):
    """상태를 바꾸는 모든 동작은 여기로: 한 번에 하나씩, 되돌리기용 기록을 남기고 판 번호(ver)를 올림."""
    with _tx() as c:
        S = _get(c, "game") or fresh()
        before = copy.deepcopy(S)
        out = fn(S)
        if keep_history:
            hist = _get(c, "hist", [])
            before.pop("preview", None)
            hist.append(before)
            _put(c, "hist", hist[-80:])
        S["ver"] = before.get("ver", 0) + 1
        _put(c, "game", S)
        return out


def throw(r):
    _change(lambda S: apply_throw(S, r))


def select_result(i):
    def f(S):
        if S["phase"] != "move" or not (0 <= int(i) < len(S["pending"])):
            raise GameError("고를 수 없는 결과입니다.")
        S["sel"] = int(i)
        S["preview"] = None
        S["last"] = {"kind": "select", "at": time.time()}
    _change(f, keep_history=False)


def preview(key):
    """패드에서 말을 한 번 누르면: 갈 길을 스크린에 먼저 보여 줌(아직 안 움직임)."""
    def f(S):
        if key is None:
            S["preview"] = None
        else:
            cand = next((x for x in candidates(S) if x["key"] == key), None)
            if not cand:
                raise GameError("이 말은 지금 움직일 수 없습니다.")
            S["preview"] = {"key": key, "nodes": cand["nodes"], "dest": cand["dest"], "finished": cand["finished"], "team": S["turn"]}
        S["last"] = {"kind": "preview", "at": time.time()}
    _change(f, keep_history=False)


def move(key):
    _change(lambda S: apply_move(S, key))


def undo() -> bool:
    with _tx() as c:
        hist = _get(c, "hist", [])
        if not hist:
            return False
        S = hist.pop()
        cur = _get(c, "game") or {}
        S["ver"] = cur.get("ver", 0) + 1
        S["preview"] = None
        S["last"] = {"kind": "undo", "at": time.time()}
        _put(c, "game", S)
        _put(c, "hist", hist)
        return True


def can_undo() -> bool:
    with _lock:
        c = _connect()
        try:
            return bool(_get(c, "hist", []))
        finally:
            c.close()


def new_game(cfg):
    with _tx() as c:
        cur = _get(c, "game") or {}
        S = fresh(cfg)
        S["ver"] = cur.get("ver", 0) + 1
        _put(c, "game", S)
        _put(c, "hist", [])


def rename(cfg):
    """팀 이름·현수막 글씨만 바꿈(판은 그대로)."""
    def f(S):
        c = norm_cfg(dict(S["cfg"], **{k: cfg[k] for k in ("names", "title", "sub") if k in cfg}))
        S["cfg"].update(names=c["names"], title=c["title"], sub=c["sub"])
        S["last"] = {"kind": "rename", "at": time.time()}
    _change(f, keep_history=False)


def screen_state() -> dict:
    """스크린 화면에 넘길 내용(판 + 번호 붙은 후보)."""
    S = get()
    S = dict(S)
    S["cands"] = [{"key": x["key"], "num": x["num"], "at": x.get("at")} for x in candidates(S)]
    return S
