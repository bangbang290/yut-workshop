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
import re
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("YUT_DB", os.path.join(BASE, "data", "yut.db"))
_lock = threading.RLock()

# 백업은 게임 상태와 최근 되돌리기 기록만 담습니다. 그림/실행 코드는 읽지 않습니다.
MAX_HISTORY = 80
MAX_LOG_ENTRIES = 18
MAX_PENDING_RESULTS = 128
MAX_BACKUP_BYTES = 2 * 1024 * 1024
BACKUP_FORMAT = "yut-workshop-backup"
BACKUP_SCHEMA_VERSION = 1
_MAX_SAFE_INT = 2**53 - 1
_KST = timezone(timedelta(hours=9))

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


def _clean_text(value: str) -> str:
    """한 줄에 표시되는 이름/기록의 제어 문자를 제거합니다."""
    return " ".join(re.sub(r"[\x00-\x1f\x7f]", " ", value).split())


def norm_cfg(c: dict | None) -> dict:
    d = default_cfg()
    if c is not None and not isinstance(c, dict):
        raise GameError("게임 설정을 확인해 주세요.")
    c = dict(c or {})
    try:
        teams = max(2, min(4, int(c.get("teams", d["teams"]))))
        pieces = max(1, min(6, int(c.get("pieces", d["pieces"]))))
    except (TypeError, ValueError, OverflowError) as exc:
        raise GameError("팀 수와 말 수는 숫자로 입력해 주세요.") from exc
    out = {
        "teams": teams,
        "pieces": pieces,
        "backdo": bool(c.get("backdo", d["backdo"])),
        "strictEnd": bool(c.get("strictEnd", d["strictEnd"])),
        "captureBonus": bool(c.get("captureBonus", d["captureBonus"])),
        "title": (_clean_text(str(c.get("title") or "")) or d["title"])[:20],
        "sub": _clean_text(str(c.get("sub", d["sub"]) or ""))[:12],
    }
    names = c.get("names") or []
    if not isinstance(names, (list, tuple)):
        raise GameError("팀 이름을 확인해 주세요.")
    out["names"] = [(_clean_text(str(names[i])) if i < len(names) else "")[:8] or DEFAULT_NAMES[i] for i in range(4)]
    return out


def fresh(cfg: dict | None = None) -> dict:
    cfg = norm_cfg(cfg)
    n = cfg["teams"]
    return {"cfg": cfg, "groups": [], "home": [cfg["pieces"]] * n, "done": [0] * n, "turn": 0, "phase": "throw",
            "pending": [], "sel": 0, "bonus": 0, "ranks": [], "log": [], "nid": 1, "started": False,
            "preview": None, "last": {"kind": "reset", "at": time.time()}, "ver": 0,
            "game_id": uuid.uuid4().hex}


# ───────────────────────── 규칙 (순수 함수)
def node_of(g) -> str:
    return R[g["route"]][g["idx"]]


def _route_at_position(route: str, idx: int) -> str:
    """빽도로 갈림길 이전까지 돌아왔으면 이전 경로로 되돌립니다.

    예: 모 지름길을 택했다가 빽도로 바깥 윷 칸까지 돌아온 말은,
    다음 개에서 모를 *지나갈* 때 지름길을 탈 수 없습니다.
    각 경로는 갈라지는 지점까지 같은 접두 경로/인덱스를 사용합니다.
    """
    if route == "MC" and idx < R["MC"].index("C"):
        route = "M"
    if route == "M" and idx < R["M"].index("O5"):
        route = "O"
    if route == "D" and idx < R["D"].index("O10"):
        route = "O"
    return route


def plan(g, steps, strict_end=False):
    idx = g["idx"]
    route = _route_at_position(g["route"], idx)
    if steps < 0:                                  # 빽도: 왔던 길로 한 칸 뒤로
        if idx <= 0:
            return None
        idx -= 1
        if idx == 0:                               # 도에서 빽도 → 참먹이에 섬(다음에 나감)
            return {"route": route, "idx": len(R[route]) - 1, "finished": False}
        return {"route": _route_at_position(route, idx), "idx": idx, "finished": False}
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
    S["log"] = ([text] + S["log"])[:MAX_LOG_ENTRIES]


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
        S.update(phase="over", pending=[], sel=0, bonus=0, preview=None)
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


def options_for(S, key):
    """말(또는 'new' = 대기 중인 새 말)을 지금 남은 결과 하나하나로 움직이면 어디로 가는지.
    [{'i': 결과 순번, 'r': 결과, 'nodes': 가는 길, 'dest': 도착 칸, 'finished': 나감}]

    같은 칸에 닿아도 서로 다른 결과는 따로 고를 수 있습니다(걸로 나가기/윷으로 나가기).
    중복된 동일 결과만 첫 번째 하나로 줄입니다.
    """
    if S["phase"] != "move" or not S["pending"]:
        return []
    team, strict = S["turn"], S["cfg"]["strictEnd"]
    if key == "new":
        if S["home"][team] <= 0:
            return []
        g, new = {"route": "O", "idx": 0}, True
    else:
        g = next((x for x in S["groups"] if x["id"] == key and x["team"] == team), None)
        if not g:
            return []
        new = False
    out = {}
    for i, r in enumerate(S["pending"]):
        steps = RES[r]["steps"]
        if new and steps < 0:
            continue
        p = plan(g, steps, strict)
        if not p:
            continue
        dest = R[p["route"]][p["idx"]]
        if r in out:
            continue
        out[r] = {"i": i, "r": r, "nodes": path_nodes(g, steps, p, new=new), "dest": dest, "finished": p["finished"]}
    return sorted(out.values(), key=lambda o: o["i"])


def selectable(S):
    """지금 누를 수 있는 말 목록('new' 포함)."""
    if S["phase"] != "move":
        return []
    keys = (["new"] if S["home"][S["turn"]] > 0 else []) + [g["id"] for g in sorted(on_board(S, S["turn"]), key=lambda g: g["id"])]
    return [k for k in keys if options_for(S, k)]


def apply_throw(S, r):
    if not isinstance(r, str) or r not in RES:
        raise GameError("알 수 없는 결과입니다.")
    if S["phase"] != "throw":
        raise GameError("지금은 말을 옮길 차례입니다. 패드에서 말을 옮긴 뒤에 다음 결과를 눌러 주세요."
                        if S["phase"] == "move" else "게임이 끝났습니다.")
    if r == "back" and not S["cfg"]["backdo"]:
        raise GameError("빽도를 쓰지 않는 설정입니다.")
    if len(S["pending"]) >= MAX_PENDING_RESULTS or (RES[r]["again"] and len(S["pending"]) >= MAX_PENDING_RESULTS - 1):
        raise GameError("한 차례에 입력된 결과가 너무 많습니다. 잘못 입력한 결과를 되돌려 주세요.")
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
        S["pending"], S["bonus"], S["sel"] = [], 0, 0
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
def _connect(*, initialize=False):
    """조회 연결에서는 WAL 설정/쓰기 잠금을 반복하지 않습니다."""
    c = None
    try:
        os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
        c = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None, check_same_thread=False)
        if initialize:
            c.execute("PRAGMA journal_mode=WAL")
        return c
    except (OSError, sqlite3.Error) as exc:
        if c is not None:
            c.close()
        raise GameError("게임 저장소에 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.") from exc


@contextmanager
def _tx(*, initialize=False):
    with _lock:
        c = _connect(initialize=initialize)
        try:
            c.execute("BEGIN IMMEDIATE")
            yield c
            c.execute("COMMIT")
        except BaseException as exc:
            if c.in_transaction:
                c.execute("ROLLBACK")
            if isinstance(exc, sqlite3.Error):
                raise GameError("진행 상태를 저장하지 못했습니다. 잠시 후 다시 눌러 주세요.") from exc
            raise
        finally:
            c.close()


def _get(c, k, default=None):
    r = c.execute("SELECT v FROM kv WHERE k=?", (k,)).fetchone()
    try:
        return json.loads(r[0]) if r else default
    except (TypeError, ValueError, RecursionError) as exc:
        raise GameError("저장된 게임을 읽지 못했습니다. 보관한 백업 파일을 확인해 주세요.") from exc


def _put(c, k, v):
    c.execute("INSERT INTO kv(k, v) VALUES(?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (k, json.dumps(v, ensure_ascii=False)))


def _delete(c, k):
    c.execute("DELETE FROM kv WHERE k=?", (k,))


def init():
    with _tx(initialize=True) as c:
        c.execute("CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT NOT NULL)")
        S = _get(c, "game")
        if S is None:
            _put(c, "game", fresh())
            _put(c, "hist", [])
        elif not S.get("game_id"):
            # 이전 버전의 진행 중인 판도 위치/차례를 유지한 채 사용할 수 있습니다.
            S["game_id"] = uuid.uuid4().hex
            _put(c, "game", S)
        if _get(c, "hist") is None:
            _put(c, "hist", [])


def get() -> dict:
    with _lock:
        c = _connect()
        try:
            S = _get(c, "game")
        finally:
            c.close()
    return S if S else fresh()


def _check_version(S, expected_ver):
    if expected_ver is None:
        return
    if type(expected_ver) is not int or not 0 <= expected_ver <= _MAX_SAFE_INT:
        raise GameError("화면 번호가 올바르지 않습니다. 새로고침한 뒤 다시 눌러 주세요.")
    if expected_ver != S.get("ver", 0):
        raise GameError("다른 기기에서 판이 바뀌었습니다. 최신 화면에서 다시 눌러 주세요.")


def _result_index(value):
    if type(value) is not int or value < 0:
        raise GameError("고를 수 없는 결과입니다. 화면을 다시 확인해 주세요.")
    return value


def _piece_key(value):
    if value is None or value == "new":
        return value
    if isinstance(value, str) and len(value) <= 16 and value.isascii() and value.isdecimal():
        value = int(value)
    if type(value) is not int or not 1 <= value <= _MAX_SAFE_INT:
        raise GameError("고를 수 없는 말입니다. 화면을 다시 확인해 주세요.")
    return value


def _change(fn, keep_history=True, expected_ver=None):
    """상태를 바꾸는 모든 동작은 여기로: 한 번에 하나씩, 되돌리기용 기록을 남기고 판 번호(ver)를 올림."""
    with _tx() as c:
        S = _get(c, "game") or fresh()
        _check_version(S, expected_ver)
        before = copy.deepcopy(S)
        out = fn(S)
        if keep_history:
            hist = _get(c, "hist", [])
            before.pop("preview", None)
            hist.append(before)
            _put(c, "hist", hist[-MAX_HISTORY:])
            # 복원 직후의 '복원 취소'는 첫 실제 진행 뒤부터 보통 되돌리기로 전환합니다.
            _delete(c, "restore_undo")
        S["ver"] = before.get("ver", 0) + 1
        _put(c, "game", S)
        return out


def throw(r, expected_ver=None):
    _change(lambda S: apply_throw(S, r), expected_ver=expected_ver)


def select_result(i, expected_ver=None):
    i = _result_index(i)
    def f(S):
        if S["phase"] != "move" or not (0 <= i < len(S["pending"])):
            raise GameError("고를 수 없는 결과입니다.")
        S["sel"] = i
        S["preview"] = None
    _change(f, keep_history=False, expected_ver=expected_ver)


def preview(key, expected_ver=None):
    """패드에서 말을 한 번 누르면: 갈 길을 스크린에 먼저 보여 줌(아직 안 움직임)."""
    key = _piece_key(key)
    def f(S):
        if key is None:
            S["preview"] = None
        else:
            cand = next((x for x in candidates(S) if x["key"] == key), None)
            if not cand:
                raise GameError("이 말은 지금 움직일 수 없습니다.")
            S["preview"] = {"key": key, "nodes": cand["nodes"], "dest": cand["dest"], "finished": cand["finished"], "team": S["turn"]}
    _change(f, keep_history=False, expected_ver=expected_ver)


def move(key, expected_ver=None):
    key = _piece_key(key)
    _change(lambda S: apply_move(S, key), expected_ver=expected_ver)


def select(key, expected_ver=None):
    """패드에서 말을 누름: 그 말이 갈 수 있는 칸(결과별)을 스크린·패드에 표시. None이면 고르기 취소."""
    key = _piece_key(key)
    def f(S):
        if key is None:
            S["preview"] = None
        else:
            opts = options_for(S, key)
            if not opts:
                raise GameError("이 말은 지금 움직일 수 없습니다.")
            S["preview"] = {"key": key, "team": S["turn"], "options": opts}
    _change(f, keep_history=False, expected_ver=expected_ver)


def move_option(key, i, expected_ver=None):
    """패드에서 도착 칸을 누름: i번째 결과로 그 말을 움직임."""
    key, i = _piece_key(key), _result_index(i)
    def f(S):
        if S["phase"] != "move" or not (0 <= i < len(S["pending"])):
            raise GameError("이미 쓴 결과입니다. 화면을 다시 확인해 주세요.")
        if not any(o["i"] == i for o in options_for(S, key)):
            raise GameError("그 칸으로는 갈 수 없습니다.")
        S["sel"] = i
        apply_move(S, key)
    _change(f, expected_ver=expected_ver)


def undo(expected_ver=None) -> bool:
    with _tx() as c:
        cur = _get(c, "game") or {}
        _check_version(cur, expected_ver)
        restore = _get(c, "restore_undo")
        if restore:
            S, hist = restore["game"], restore["hist"]
            _delete(c, "restore_undo")
        else:
            hist = _get(c, "hist", [])
            if not hist:
                return False
            S = hist.pop()
        S["ver"] = cur.get("ver", 0) + 1
        S.setdefault("game_id", cur.get("game_id") or uuid.uuid4().hex)
        S["preview"] = None
        S["last"] = {"kind": "undo", "at": time.time()}
        _put(c, "game", S)
        _put(c, "hist", hist)
        return True


def can_undo() -> bool:
    with _lock:
        c = _connect()
        try:
            return bool(_get(c, "hist", []) or _get(c, "restore_undo"))
        finally:
            c.close()


def new_game(cfg, expected_ver=None):
    with _tx() as c:
        cur = _get(c, "game") or {}
        _check_version(cur, expected_ver)
        S = fresh(cfg)
        S["ver"] = cur.get("ver", 0) + 1
        _put(c, "game", S)
        _put(c, "hist", [])
        _delete(c, "restore_undo")


def rename(cfg, expected_ver=None):
    """팀 이름·현수막 글씨만 바꿈(판은 그대로)."""
    if not isinstance(cfg, dict):
        raise GameError("팀 이름과 행사 제목을 확인해 주세요.")
    def f(S):
        c = norm_cfg(dict(S["cfg"], **{k: cfg[k] for k in ("names", "title", "sub") if k in cfg}))
        S["cfg"].update(names=c["names"], title=c["title"], sub=c["sub"])
    _change(f, keep_history=False, expected_ver=expected_ver)


# ───────────────────────── 백업/복원 (검증 완료 후 한 번에 저장)
def _backup_int(value, label, low, high):
    if type(value) is not int or not low <= value <= high:
        raise GameError(f"백업의 {label} 값이 올바르지 않습니다.")
    return value


def _backup_text(value, label, limit, *, nonempty=False):
    if not isinstance(value, str) or len(value) > limit:
        raise GameError(f"백업의 {label} 글자 수를 확인해 주세요.")
    value = _clean_text(value)
    if nonempty and not value:
        raise GameError(f"백업의 {label} 값이 비어 있습니다.")
    return value


def _validated_state(raw):
    """실행 코드/그림/임의 필드는 버리고, 복원 가능한 게임 자료만 새 객체로 만듭니다."""
    if not isinstance(raw, dict) or not isinstance(raw.get("cfg"), dict):
        raise GameError("백업에 게임 설정이 없습니다.")
    cfg = raw["cfg"]
    teams = _backup_int(cfg.get("teams"), "팀 수", 2, 4)
    pieces = _backup_int(cfg.get("pieces"), "말 수", 1, 6)
    names = cfg.get("names")
    if not isinstance(names, list) or len(names) != 4:
        raise GameError("백업의 팀 이름 목록이 올바르지 않습니다.")
    clean_cfg = {"teams": teams, "pieces": pieces,
                 "names": [_backup_text(v, "팀 이름", 8, nonempty=True) for v in names],
                 "title": _backup_text(cfg.get("title"), "행사 제목", 20, nonempty=True),
                 "sub": _backup_text(cfg.get("sub", ""), "부제", 12)}
    for name in ("backdo", "strictEnd", "captureBonus"):
        value = cfg.get(name, default_cfg()[name])
        if type(value) is not bool:
            raise GameError("백업의 게임 규칙 설정이 올바르지 않습니다.")
        clean_cfg[name] = value
    S = fresh(clean_cfg)
    for name in ("home", "done"):
        values = raw.get(name)
        if not isinstance(values, list) or len(values) != teams:
            raise GameError("백업의 팀별 말 수가 올바르지 않습니다.")
        S[name] = [_backup_int(v, "팀별 말 수", 0, pieces) for v in values]
    groups = raw.get("groups")
    if not isinstance(groups, list) or len(groups) > teams * pieces:
        raise GameError("백업의 말 목록이 올바르지 않습니다.")
    ids, occupied = set(), set()
    for raw_g in groups:
        if not isinstance(raw_g, dict):
            raise GameError("백업의 말 정보가 올바르지 않습니다.")
        route = raw_g.get("route")
        if not isinstance(route, str) or route not in R:
            raise GameError("백업의 이동 경로가 올바르지 않습니다.")
        idx = _backup_int(raw_g.get("idx"), "말 위치", 1, len(R[route]) - 1)
        g = {"id": _backup_int(raw_g.get("id"), "말 번호", 1, _MAX_SAFE_INT),
             "team": _backup_int(raw_g.get("team"), "말의 팀 번호", 0, teams - 1),
             "n": _backup_int(raw_g.get("n"), "업은 말 수", 1, pieces),
             "route": _route_at_position(route, idx), "idx": idx}
        node = node_of(g)
        if g["id"] in ids or node in occupied:
            raise GameError("백업에 중복된 말 번호 또는 겹친 말 위치가 있습니다.")
        ids.add(g["id"])
        occupied.add(node)
        S["groups"].append(g)
    for team in range(teams):
        on = sum(g["n"] for g in S["groups"] if g["team"] == team)
        if S["home"][team] + S["done"][team] + on != pieces:
            raise GameError("백업의 대기·진행·완주 말 수 합계가 맞지 않습니다.")
    S["nid"] = _backup_int(raw.get("nid"), "다음 말 번호", max(ids, default=0) + 1, _MAX_SAFE_INT)
    S["turn"] = _backup_int(raw.get("turn"), "현재 차례", 0, teams - 1)
    phase = raw.get("phase")
    if phase not in ("throw", "move", "over"):
        raise GameError("백업의 진행 단계가 올바르지 않습니다.")
    S["phase"] = phase
    ranks = raw.get("ranks")
    if not isinstance(ranks, list) or len(ranks) > teams:
        raise GameError("백업의 순위 정보가 올바르지 않습니다.")
    S["ranks"] = [_backup_int(t, "순위의 팀 번호", 0, teams - 1) for t in ranks]
    if len(set(S["ranks"])) != len(S["ranks"]):
        raise GameError("백업의 순위에 같은 팀이 두 번 들어 있습니다.")
    if phase == "over":
        valid_ranks = len(ranks) == teams and all(S["done"][t] == pieces for t in ranks[:-1])
    else:
        valid_ranks = (len(ranks) <= teams - 2 and S["turn"] not in ranks
                       and set(ranks) == {t for t in range(teams) if S["done"][t] == pieces})
    if not valid_ranks:
        raise GameError("백업의 완주 상태와 순위가 맞지 않습니다.")
    pending = raw.get("pending")
    if (not isinstance(pending, list) or len(pending) > MAX_PENDING_RESULTS
            or any(not isinstance(r, str) or r not in RES for r in pending)):
        raise GameError("백업의 남은 윷 결과가 올바르지 않습니다.")
    if not clean_cfg["backdo"] and "back" in pending:
        raise GameError("빽도 미사용 게임의 백업에 빽도가 들어 있습니다.")
    S["pending"] = pending[:]
    S["sel"] = _backup_int(raw.get("sel", 0), "선택한 결과 번호", 0, max(0, len(pending) - 1))
    S["bonus"] = _backup_int(raw.get("bonus", 0), "추가 던지기 수", 0, MAX_PENDING_RESULTS)
    if ((phase == "move" and (not pending or not any(usable(S, r, S["turn"]) for r in pending)))
            or (phase == "throw" and (len(pending) >= MAX_PENDING_RESULTS or any(not RES[r]["again"] for r in pending)))
            or (phase == "over" and (pending or S["bonus"]))):
        raise GameError("백업의 차례와 남은 윷 결과가 맞지 않습니다.")
    logs = raw.get("log", [])
    if not isinstance(logs, list) or len(logs) > MAX_LOG_ENTRIES:
        raise GameError("백업의 최근 기록이 너무 많습니다.")
    S["log"] = [_backup_text(v, "최근 기록", 256) for v in logs]
    if type(raw.get("started", False)) is not bool:
        raise GameError("백업의 시작 상태가 올바르지 않습니다.")
    S["started"] = raw.get("started", False)
    if not S["started"] and (groups or pending or ranks or any(S["done"]) or S["turn"] != 0 or phase != "throw" or S["bonus"]):
        raise GameError("백업의 시작 상태와 말 위치가 맞지 않습니다.")
    S["ver"] = _backup_int(raw.get("ver", 0), "상태 번호", 0, _MAX_SAFE_INT)
    game_id = raw.get("game_id")
    if game_id is not None:
        if not isinstance(game_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", game_id):
            raise GameError("백업의 게임 식별자가 올바르지 않습니다.")
        S["game_id"] = game_id
    # 선택 미리보기와 애니메이션은 복원/되돌리기 때 새 화면에서 다시 계산합니다.
    S["preview"] = None
    S["last"] = {"kind": "restore", "at": time.time()}
    return S


def _reject_duplicate_keys(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise GameError("백업에 중복된 JSON 항목이 있습니다.")
        out[key] = value
    return out


def _reject_nonfinite(value):
    raise GameError("백업에 올바르지 않은 숫자가 있습니다.")


def _decode_backup(data):
    if not isinstance(data, (str, bytes, bytearray)):
        raise GameError("JSON 백업 파일을 선택해 주세요.")
    try:
        if isinstance(data, str):
            data = data.encode("utf-8")
        if not data or len(data) > MAX_BACKUP_BYTES:
            raise GameError("백업 파일은 2MB 이하의 JSON 파일이어야 합니다.")
        obj = json.loads(data.decode("utf-8-sig"), object_pairs_hook=_reject_duplicate_keys,
                         parse_constant=_reject_nonfinite)
    except (UnicodeError, ValueError, RecursionError) as exc:
        if isinstance(exc, GameError):
            raise
        raise GameError("백업 파일을 읽지 못했습니다. 이 앱에서 내려받은 JSON 파일인지 확인해 주세요.") from exc
    if (not isinstance(obj, dict) or obj.get("format") != BACKUP_FORMAT
            or type(obj.get("schema_version")) is not int or obj.get("schema_version") != BACKUP_SCHEMA_VERSION):
        raise GameError("지원하지 않는 백업 형식입니다. 이 앱에서 내려받은 파일을 사용해 주세요.")
    state = _validated_state(obj.get("state"))
    history = obj.get("history", [])
    if not isinstance(history, list) or len(history) > MAX_HISTORY:
        raise GameError("백업의 되돌리기 기록 수가 올바르지 않습니다.")
    history = [_validated_state(item) for item in history]
    saved_at = _backup_text(obj.get("exported_at", ""), "저장 시각", 64)
    return state, history, saved_at


def export_backup() -> bytes:
    """현재 판과 최근 80단계 이내의 되돌리기 기록을 UTF-8 JSON으로 반환합니다."""
    with _lock:
        c = _connect()
        try:
            c.execute("BEGIN")
            S = _get(c, "game") or fresh()
            hist = _get(c, "hist", [])[-MAX_HISTORY:]
            c.execute("COMMIT")
        finally:
            if c.in_transaction:
                c.execute("ROLLBACK")
            c.close()
    S["preview"] = None
    for old in hist:
        old.pop("preview", None)
        old.setdefault("game_id", S["game_id"])
    payload = {"format": BACKUP_FORMAT, "schema_version": BACKUP_SCHEMA_VERSION,
               "exported_at": datetime.now(_KST).isoformat(timespec="seconds"), "state": S, "history": hist}
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(data) > MAX_BACKUP_BYTES:
        raise GameError("게임 기록이 너무 커서 백업을 만들지 못했습니다.")
    return data


def inspect_backup(data) -> dict:
    """파일을 검증하고 요약만 반환합니다. 현재 판은 바꾸지 않습니다."""
    S, history, saved_at = _decode_backup(data)
    return {"title": S["cfg"]["title"], "names": S["cfg"]["names"][:S["cfg"]["teams"]],
            "teams": S["cfg"]["teams"], "pieces": S["cfg"]["pieces"], "turn": S["turn"],
            "turn_name": tname(S, S["turn"]), "phase": S["phase"], "saved_at": saved_at,
            "exported_at": saved_at, "history_count": len(history), "done": S["done"][:], "game_id": S["game_id"]}


def import_backup(data, expected_ver=None):
    """검증된 판/되돌리기 기록을 한 번에 복원합니다.

    파일 속 과거 ver를 쓰지 않고 현재 ver+1을 부여합니다. 복원 직후의 되돌리기는
    복원을 취소합니다. 실제 던지기/이동을 시작하면 파일에 담긴 보통 되돌리기를 사용합니다.
    """
    S, hist, _ = _decode_backup(data)
    with _tx() as c:
        cur = _get(c, "game") or fresh()
        _check_version(cur, expected_ver)
        rollback = {"game": cur, "hist": _get(c, "hist", [])[-MAX_HISTORY:]}
        S["ver"] = cur.get("ver", 0) + 1
        S["preview"] = None
        S["last"] = {"kind": "restore", "at": time.time()}
        _put(c, "game", S)
        _put(c, "hist", hist)
        _put(c, "restore_undo", rollback)


def screen_state() -> dict:
    """스크린 화면에 넘길 내용(판 + 번호 붙은 후보)."""
    S = dict(get())
    S["selectable"] = selectable(S)
    return S
