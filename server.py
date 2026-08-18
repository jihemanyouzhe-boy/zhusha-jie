#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
朱砂戒后端 — 纯 Python 标准库实现
REST API + SQLite 持久化 + 静态文件服务
启动：python3 server.py   （监听 8000，双栈 IPv4/IPv6）
"""
import http.server
import json
import os
import re
import hashlib
import hmac
import secrets
import socket
import sqlite3
import threading
import posixpath
from contextlib import closing
from datetime import date, timedelta, datetime
from http import HTTPStatus
from urllib.parse import urlparse, parse_qs, unquote

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "data")
DB_PATH = os.path.join(DATA_DIR, "zhuosha.db")
os.makedirs(DATA_DIR, exist_ok=True)

_lock = threading.RLock()

# ---------- 安全/会话常量 ----------
SESSION_TTL_DAYS = 30          # 会话有效期 30 天
MAX_BODY_BYTES = 1_048_576     # 请求体上限 1MB
MAX_QUIZ_SCORE = 8             # 单次答题分数上限
MAX_BREATHS = 500              # 单次冥想呼吸数上限
ALLOWED_STATIC_EXT = {".html", ".htm", ".css", ".js", ".jpg", ".jpeg",
                      ".png", ".gif", ".svg", ".ico", ".webp", ".woff",
                      ".woff2", ".ttf", ".otf", ".map", ".json", ".webmanifest"}

# ---------- 业务常量（与前端镜像） ----------
DEEDS = {
    "help": ("劝善助人", 8), "resist": ("拒一邪念", 6), "filial": ("孝亲尊长", 6),
    "volunteer": ("志愿服务", 8), "exercise": ("健身运动", 3), "early": ("早起早眠", 3),
    "vegetarian": ("清淡饮食", 2), "reflect": ("静坐省过", 4), "kindness": ("与人为善", 4),
    "tidy": ("洒扫居室", 2), "water": ("饮水充足", 1), "noboze": ("亥时前眠", 3),
}
CLASSICS = {
    "shoukang": ("寿康宝鉴", 5), "dizigui": ("弟子规", 5), "ganying": ("太上感应篇", 5),
    "qingjing": ("清静经", 6), "liaofan": ("了凡四训", 6),
}
TASKS = ["s", "j", "e", "n", "z"]  # 今日功课：晨诵/省思/运动/善行/早眠

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  id TEXT PRIMARY KEY, name TEXT UNIQUE, pwd TEXT, salt TEXT,
  region TEXT, goal INTEGER DEFAULT 21, vow TEXT DEFAULT '',
  created_at TEXT, streak INTEGER DEFAULT 0, last_checkin TEXT,
  relapse_count INTEGER DEFAULT 0, merit INTEGER DEFAULT 0, days INTEGER DEFAULT 0,
  pomo_count INTEGER DEFAULT 0, quiz_best INTEGER DEFAULT 0, med_breaths INTEGER DEFAULT 0,
  resist_count INTEGER DEFAULT 0, daily TEXT DEFAULT '{}', demo INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, user_id TEXT, created_at TEXT, expires_at TEXT);
CREATE TABLE IF NOT EXISTS checkins(user_id TEXT, date TEXT, UNIQUE(user_id, date));
CREATE TABLE IF NOT EXISTS challenges(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, days INTEGER,
  start_date TEXT, end_date TEXT, status TEXT);
CREATE TABLE IF NOT EXISTS journal(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, date TEXT, mood TEXT, text TEXT);
CREATE TABLE IF NOT EXISTS health(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, date TEXT,
  sleep TEXT, mood TEXT, sport TEXT, note TEXT, UNIQUE(user_id, date));
CREATE TABLE IF NOT EXISTS treehole(
  id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT, region TEXT, date TEXT,
  hearts INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS encourage(
  id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT, region TEXT, date TEXT,
  hearts INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS reflections(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, date TEXT,
  trigger TEXT, feeling TEXT, lesson TEXT);
CREATE TABLE IF NOT EXISTS likes(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT, target TEXT, item_id INTEGER,
  UNIQUE(user_id, target, item_id));
"""


class ApiError(Exception):
    pass


def db():
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    return con


def tx(fn):
    """写事务（加锁 + 提交）"""
    with _lock, closing(db()) as con:
        with con:
            return fn(con)


def rd(fn):
    """只读查询"""
    with _lock, closing(db()) as con:
        return fn(con)


def init_db():
    with closing(db()) as con:
        # 启用 WAL 改善读多写少场景的并发
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA foreign_keys=ON")
        with con:
            con.executescript(SCHEMA)
            # 兼容旧库：为 sessions 补 expires_at 列（IF NOT EXISTS 不会改老表）
            cols = {r[1] for r in con.execute("PRAGMA table_info(sessions)")}
            if "expires_at" not in cols:
                con.execute("ALTER TABLE sessions ADD COLUMN expires_at TEXT")
            # 性能索引（旧库 IF NOT EXISTS 安全幂等）
            con.executescript("""
            CREATE INDEX IF NOT EXISTS idx_journal_user ON journal(user_id);
            CREATE INDEX IF NOT EXISTS idx_health_user ON health(user_id);
            CREATE INDEX IF NOT EXISTS idx_checkins_user_date ON checkins(user_id, date);
            CREATE INDEX IF NOT EXISTS idx_likes_user ON likes(user_id);
            CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
            CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);
            """)
        # 清理已过期会话
        with con:
            con.execute("DELETE FROM sessions WHERE expires_at IS NOT NULL AND expires_at < ?",
                        (today(),))


def hash_pwd(pwd, salt):
    return hashlib.pbkdf2_hmac("sha256", pwd.encode(), bytes.fromhex(salt), 100_000).hex()


def today():
    return date.today().isoformat()

def now_str():
    """完整时间戳：YYYY-MM-DD HH:MM"""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def uid():
    return "u" + secrets.token_hex(8)


def sync_streak_row(con, u):
    """惰性校正：上次打卡距今超过一天，连续日归零"""
    if u["streak"] > 0 and u["last_checkin"]:
        gap = (date.fromisoformat(today()) - date.fromisoformat(u["last_checkin"])).days
        if gap > 1:
            con.execute("UPDATE users SET streak=0 WHERE id=?", (u["id"],))


def user_json(con, u):
    challenges = [dict(r) for r in con.execute(
        "SELECT days, start_date AS start, end_date AS end, status "
        "FROM challenges WHERE user_id=? ORDER BY id", (u["id"],))]
    checkins = [r["date"] for r in con.execute(
        "SELECT date FROM checkins WHERE user_id=? ORDER BY date", (u["id"],))]
    journal_count = con.execute(
        "SELECT COUNT(*) c FROM journal WHERE user_id=?", (u["id"],)).fetchone()["c"]
    health_count = con.execute(
        "SELECT COUNT(*) c FROM health WHERE user_id=?", (u["id"],)).fetchone()["c"]
    done_ch = sum(1 for c in challenges if c["status"] == "done")
    return {
        "id": u["id"], "name": u["name"], "region": u["region"], "goal": u["goal"],
        "vow": u["vow"], "createdAt": u["created_at"], "streak": u["streak"],
        "lastCheckin": u["last_checkin"], "relapseCount": u["relapse_count"],
        "merit": u["merit"], "days": u["days"], "pomoCount": u["pomo_count"],
        "quizBest": u["quiz_best"], "medBreaths": u["med_breaths"],
        "resistCount": u["resist_count"], "daily": json.loads(u["daily"] or "{}"),
        "challenges": challenges, "checkins": checkins,
        "journalCount": journal_count, "healthCount": health_count,
        "doneChallenges": done_ch,
    }


# ============================================================
# 路由注册
# ============================================================
ROUTES = []


def route(method, pattern, auth=True):
    rx = re.compile("^" + pattern + "$")

    def deco(fn):
        ROUTES.append((method, rx, fn, auth))
        return fn
    return deco


# ---------- 认证 ----------
@route("POST", "/auth/register", auth=False)
def register(h, user, body, q, m):
    name = str(body.get("name", "")).strip()
    pwd = str(body.get("pwd", ""))
    region = str(body.get("region", "")).strip()
    try:
        goal = int(body.get("goal", 21))
    except (TypeError, ValueError):
        goal = 21
    vow = str(body.get("vow", "")).strip()
    if not name or len(name) > 12:
        raise ApiError("道号需 1~12 字")
    if not region:
        raise ApiError("请选择所在地区")
    if len(pwd) < 4 or len(pwd) > 1024:
        raise ApiError("口令需 4~1024 字符")

    def op(con):
        if con.execute("SELECT 1 FROM users WHERE name=?", (name,)).fetchone():
            raise ApiError("此道号已被占用")
        salt = secrets.token_hex(16)
        i = uid()
        try:
            con.execute(
                "INSERT INTO users(id,name,pwd,salt,region,goal,vow,created_at) VALUES(?,?,?,?,?,?,?,?)",
                (i, name, hash_pwd(pwd, salt), salt, region, goal, vow, today()))
        except sqlite3.IntegrityError:
            # 并发下 UNIQUE(name) 冲突，返回友好错误而非 500
            raise ApiError("此道号已被占用")
        token = secrets.token_hex(32)
        expires_at = (date.today() + timedelta(days=SESSION_TTL_DAYS)).isoformat()
        con.execute("INSERT INTO sessions(token,user_id,created_at,expires_at) VALUES(?,?,?,?)",
                    (token, i, today(), expires_at))
        u = con.execute("SELECT * FROM users WHERE id=?", (i,)).fetchone()
        return token, user_json(con, u)

    token, uj = tx(op)
    h._json({"ok": True, "token": token, "user": uj})


@route("POST", "/auth/login", auth=False)
def login(h, user, body, q, m):
    name = str(body.get("name", "")).strip()
    pwd = str(body.get("pwd", ""))

    def op(con):
        u = con.execute("SELECT * FROM users WHERE name=?", (name,)).fetchone()
        # 常量时间密码比较，规避理论侧信道
        if not u or not hmac.compare_digest(hash_pwd(pwd, u["salt"]), u["pwd"]):
            raise ApiError("道号或口令有误")
        sync_streak_row(con, u)
        token = secrets.token_hex(32)
        expires_at = (date.today() + timedelta(days=SESSION_TTL_DAYS)).isoformat()
        con.execute("INSERT INTO sessions(token,user_id,created_at,expires_at) VALUES(?,?,?,?)",
                    (token, u["id"], today(), expires_at))
        u = con.execute("SELECT * FROM users WHERE id=?", (u["id"],)).fetchone()
        return token, user_json(con, u)

    token, uj = tx(op)
    h._json({"ok": True, "token": token, "user": uj})


@route("POST", "/auth/logout")
def logout(h, user, body, q, m):
    token = h.headers.get("X-Token", "")
    tx(lambda con: con.execute("DELETE FROM sessions WHERE token=?", (token,)))
    h._json({"ok": True})


@route("GET", "/me")
def me(h, user, body, q, m):
    def op(con):
        sync_streak_row(con, user)
        u = con.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        return user_json(con, u)
    h._json({"ok": True, "user": tx(op)})


# ---------- 打卡 / 破戒 ----------
@route("POST", "/checkin")
def checkin(h, user, body, q, m):
    t = today()

    def op(con):
        u = con.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        sync_streak_row(con, u)
        u = con.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        if u["last_checkin"] == t:
            return user_json(con, u), False
        if u["last_checkin"]:
            diff = (date.fromisoformat(t) - date.fromisoformat(u["last_checkin"])).days
            streak = u["streak"] + 1 if diff == 1 else 1
        else:
            streak = 1
        con.execute(
            "UPDATE users SET streak=?, last_checkin=?, merit=merit+5, days=days+1 WHERE id=?",
            (streak, t, u["id"]))
        con.execute("INSERT OR IGNORE INTO checkins(user_id,date) VALUES(?,?)", (u["id"], t))
        u2 = con.execute("SELECT * FROM users WHERE id=?", (u["id"],)).fetchone()
        return user_json(con, u2), True

    uj, changed = tx(op)
    h._json({"ok": True, "user": uj, "changed": changed, "streak": uj["streak"]})


@route("POST", "/relapse")
def relapse(h, user, body, q, m):
    def op(con):
        con.execute(
            "UPDATE users SET streak=0, last_checkin=NULL, relapse_count=relapse_count+1 WHERE id=?",
            (user["id"],))
        u = con.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        return user_json(con, u)
    h._json({"ok": True, "user": tx(op)})


# ---------- 今日功课 ----------
@route("POST", "/daily")
def daily_toggle(h, user, body, q, m):
    task = str(body.get("task", ""))
    if task not in TASKS:
        raise ApiError("未知功课")

    def op(con):
        u = con.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        daily = json.loads(u["daily"] or "{}")
        day = daily.setdefault(today(), {})
        bonus = False
        if task in day:
            del day[task]  # 取消勾选
        else:
            day[task] = True
            if all(k in day for k in TASKS) and "_bonus" not in day:
                day["_bonus"] = True
                bonus = True
                con.execute("UPDATE users SET merit=merit+8 WHERE id=?", (u["id"],))
        daily[today()] = day
        con.execute("UPDATE users SET daily=? WHERE id=?", (json.dumps(daily), u["id"]))
        u = con.execute("SELECT * FROM users WHERE id=?", (u["id"],)).fetchone()
        return user_json(con, u), bonus

    uj, bonus = tx(op)
    h._json({"ok": True, "user": uj, "bonus": bonus})


# ---------- 挑战 ----------
@route("POST", "/challenge/start")
def challenge_start(h, user, body, q, m):
    days = int(body.get("days", 0))
    if days not in (7, 21, 30, 100, 365):
        raise ApiError("无效挑战天数")

    def op(con):
        if con.execute(
                "SELECT 1 FROM challenges WHERE user_id=? AND status='active'",
                (user["id"],)).fetchone():
            raise ApiError("已有进行中的挑战")
        end = (date.today() + timedelta(days=days - 1)).isoformat()
        con.execute(
            "INSERT INTO challenges(user_id,days,start_date,end_date,status) VALUES(?,?,?,?, 'active')",
            (user["id"], days, today(), end))
        u = con.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        return user_json(con, u)
    h._json({"ok": True, "user": tx(op)})


@route("POST", "/challenge/finish")
def challenge_finish(h, user, body, q, m):
    def op(con):
        c = con.execute(
            "SELECT * FROM challenges WHERE user_id=? AND status='active'",
            (user["id"],)).fetchone()
        if not c:
            raise ApiError("没有进行中的挑战")
        passed = (date.fromisoformat(today()) - date.fromisoformat(c["start_date"])).days + 1
        if passed < c["days"]:
            raise ApiError("戒期未满，不可结修")
        con.execute("UPDATE challenges SET status='done', end_date=? WHERE id=?",
                    (today(), c["id"]))
        con.execute("UPDATE users SET merit=merit+20 WHERE id=?", (user["id"],))
        u = con.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        return user_json(con, u)
    h._json({"ok": True, "user": tx(op)})


@route("POST", "/challenge/abandon")
def challenge_abandon(h, user, body, q, m):
    def op(con):
        c = con.execute(
            "SELECT * FROM challenges WHERE user_id=? AND status='active'",
            (user["id"],)).fetchone()
        if c:
            con.execute("UPDATE challenges SET status='abandoned', end_date=? WHERE id=?",
                        (today(), c["id"]))
        u = con.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        return user_json(con, u)
    h._json({"ok": True, "user": tx(op)})


# ---------- 功德 / 诵读 / 冥想 / 番茄 / 答题 / 拒念 ----------
@route("POST", "/merit")
def merit_add(h, user, body, q, m):
    did = str(body.get("id", ""))
    if did not in DEEDS:
        raise ApiError("未知善行")
    name, m_ = DEEDS[did]

    def op(con):
        con.execute("UPDATE users SET merit=merit+? WHERE id=?", (m_, user["id"]))
        u = con.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        return user_json(con, u), name
    uj, name = tx(op)
    h._json({"ok": True, "user": uj, "name": name, "merit": m_})


@route("POST", "/classic")
def classic_recite(h, user, body, q, m):
    book = str(body.get("book", ""))
    if book not in CLASSICS:
        raise ApiError("未知经典")
    title, m_ = CLASSICS[book]

    def op(con):
        con.execute("UPDATE users SET merit=merit+? WHERE id=?", (m_, user["id"]))
        u = con.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        return user_json(con, u), title
    uj, title = tx(op)
    h._json({"ok": True, "user": uj, "title": title, "merit": m_})


@route("POST", "/meditation")
def meditation_log(h, user, body, q, m):
    breaths = max(0, min(MAX_BREATHS, int(body.get("breaths", 0))))
    gain = 3 * (breaths // 10)

    def op(con):
        con.execute(
            "UPDATE users SET med_breaths=med_breaths+?, merit=merit+? WHERE id=?",
            (breaths, gain, user["id"]))
        u = con.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        return user_json(con, u)
    h._json({"ok": True, "user": tx(op), "gain": gain})


@route("POST", "/pomodoro")
def pomodoro_log(h, user, body, q, m):
    mode = str(body.get("mode", ""))
    if mode != "focus":
        h._json({"ok": True, "user": None})
        return

    def op(con):
        con.execute(
            "UPDATE users SET pomo_count=pomo_count+1, merit=merit+4 WHERE id=?",
            (user["id"],))
        u = con.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        return user_json(con, u)
    h._json({"ok": True, "user": tx(op)})


@route("POST", "/quiz")
def quiz_submit(h, user, body, q, m):
    # 钳制分数到 [0, MAX_QUIZ_SCORE]，防止前端伪造高分刷功德
    score = max(0, min(MAX_QUIZ_SCORE, int(body.get("score", 0))))
    total = max(1, int(body.get("total", MAX_QUIZ_SCORE)))

    def op(con):
        u = con.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        best = max(u["quiz_best"], score)
        # 仅奖励超越历史最佳的部分，避免重复答题刷分
        gain = max(0, score - u["quiz_best"]) * 2
        con.execute("UPDATE users SET quiz_best=?, merit=merit+? WHERE id=?",
                    (best, gain, user["id"]))
        u = con.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        return user_json(con, u), best
    uj, best = tx(op)
    h._json({"ok": True, "user": uj, "best": best, "gain": 0, "total": total})


@route("POST", "/resist")
def resist(h, user, body, q, m):
    def op(con):
        con.execute(
            "UPDATE users SET resist_count=resist_count+1, merit=merit+6 WHERE id=?",
            (user["id"],))
        u = con.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        return user_json(con, u)
    h._json({"ok": True, "user": tx(op)})


# ---------- 日记 ----------
@route("GET", "/journal")
def journal_list(h, user, body, q, m):
    rows = rd(lambda con: [dict(r) for r in con.execute(
        "SELECT id,date,mood,text FROM journal WHERE user_id=? ORDER BY id DESC LIMIT 100",
        (user["id"],))])
    h._json({"ok": True, "list": rows})


@route("POST", "/journal")
def journal_add(h, user, body, q, m):
    text = str(body.get("text", "")).strip()
    mood = str(body.get("mood", "平淡"))
    if not text:
        raise ApiError("请先写下心念")
    if len(text) > 2000:
        raise ApiError("日记过长")

    def op(con):
        con.execute("INSERT INTO journal(user_id,date,mood,text) VALUES(?,?,?,?)",
                    (user["id"], now_str(), mood, text))
        con.execute("UPDATE users SET merit=merit+3 WHERE id=?", (user["id"],))
        u = con.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        return user_json(con, u)
    h._json({"ok": True, "user": tx(op)})


@route("POST", "/journal/delete")
def journal_del(h, user, body, q, m):
    jid = int(body.get("id", 0))
    tx(lambda con: con.execute(
        "DELETE FROM journal WHERE id=? AND user_id=?", (jid, user["id"])))
    h._json({"ok": True})


# ---------- 健康 ----------
@route("GET", "/health")
def health_list(h, user, body, q, m):
    rows = rd(lambda con: [dict(r) for r in con.execute(
        "SELECT date,sleep,mood,sport,note FROM health WHERE user_id=? "
        "ORDER BY date DESC LIMIT 30", (user["id"],))])
    h._json({"ok": True, "list": rows})


@route("POST", "/health")
def health_save(h, user, body, q, m):
    rec = {
        "sleep": str(body.get("sleep", ""))[:8],
        "mood": str(body.get("mood", ""))[:8],
        "sport": str(body.get("sport", ""))[:8],
        "note": str(body.get("note", ""))[:500],
    }

    def op(con):
        exists = con.execute(
            "SELECT 1 FROM health WHERE user_id=? AND date=?", (user["id"], today())).fetchone()
        if exists:
            con.execute("UPDATE health SET sleep=?,mood=?,sport=?,note=? WHERE user_id=? AND date=?",
                        (rec["sleep"], rec["mood"], rec["sport"], rec["note"], user["id"], today()))
        else:
            con.execute("INSERT INTO health(user_id,date,sleep,mood,sport,note) VALUES(?,?,?,?,?,?)",
                        (user["id"], today(), rec["sleep"], rec["mood"], rec["sport"], rec["note"]))
            con.execute("UPDATE users SET merit=merit+2 WHERE id=?", (user["id"],))
        u = con.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        return user_json(con, u), not exists
    uj, is_new = tx(op)
    h._json({"ok": True, "user": uj, "new": is_new})


# ---------- 树洞 ----------
@route("GET", "/treehole")
def treehole_list(h, user, body, q, m):
    def op(con):
        rows = [dict(r) for r in con.execute(
            "SELECT id,text,region,date,hearts FROM treehole ORDER BY id DESC LIMIT 50")]
        liked = {r["item_id"] for r in con.execute(
            "SELECT item_id FROM likes WHERE user_id=? AND target='treehole'",
            (user["id"],))}
        for r in rows:
            r["liked"] = r["id"] in liked
        return rows
    h._json({"ok": True, "list": rd(op)})


@route("POST", "/treehole")
def treehole_add(h, user, body, q, m):
    text = str(body.get("text", "")).strip()
    if not text:
        raise ApiError("请先写下心声")
    if len(text) > 500:
        raise ApiError("心声过长")

    def op(con):
        region = user["region"] or "远方"
        con.execute("INSERT INTO treehole(text,region,date,hearts) VALUES(?,?,?,0)",
                    (text, region, now_str()))
        con.execute("UPDATE users SET merit=merit+2 WHERE id=?", (user["id"],))
        u = con.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        return user_json(con, u)
    h._json({"ok": True, "user": tx(op)})


@route("POST", "/treehole/heart")
def treehole_heart(h, user, body, q, m):
    hid = int(body.get("id", 0))

    def op(con):
        cur = con.execute("SELECT hearts FROM treehole WHERE id=?", (hid,)).fetchone()
        if not cur:
            raise ApiError("心声不存在")
        try:
            con.execute(
                "INSERT INTO likes(user_id,target,item_id) VALUES(?,?,?)",
                (user["id"], "treehole", hid))
        except sqlite3.IntegrityError:
            raise ApiError("已点过赞")
        con.execute("UPDATE treehole SET hearts=hearts+1 WHERE id=?", (hid,))
        return cur["hearts"] + 1
    h._json({"ok": True, "hearts": tx(op)})


# ---------- 同修共勉墙 ----------
@route("GET", "/encourage")
def encourage_list(h, user, body, q, m):
    def op(con):
        rows = [dict(r) for r in con.execute(
            "SELECT id,text,region,date,hearts FROM encourage ORDER BY id DESC LIMIT 60")]
        liked = {r["item_id"] for r in con.execute(
            "SELECT item_id FROM likes WHERE user_id=? AND target='encourage'",
            (user["id"],))}
        for r in rows:
            r["liked"] = r["id"] in liked
        return rows
    h._json({"ok": True, "list": rd(op)})


@route("POST", "/encourage")
def encourage_add(h, user, body, q, m):
    text = str(body.get("text", "")).strip()
    if not text:
        raise ApiError("请先写下勉语")
    if len(text) > 200:
        raise ApiError("勉语宜简，勿过两百字")

    def op(con):
        region = user["region"] or "远方"
        con.execute("INSERT INTO encourage(text,region,date,hearts) VALUES(?,?,?,0)",
                    (text, region, now_str()))
        con.execute("UPDATE users SET merit=merit+4 WHERE id=?", (user["id"],))
        u = con.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        return user_json(con, u)
    h._json({"ok": True, "user": tx(op)})


@route("POST", "/encourage/heart")
def encourage_heart(h, user, body, q, m):
    eid = int(body.get("id", 0))

    def op(con):
        cur = con.execute("SELECT hearts FROM encourage WHERE id=?", (eid,)).fetchone()
        if not cur:
            raise ApiError("勉语不存在")
        try:
            con.execute(
                "INSERT INTO likes(user_id,target,item_id) VALUES(?,?,?)",
                (user["id"], "encourage", eid))
        except sqlite3.IntegrityError:
            raise ApiError("已点过赞")
        con.execute("UPDATE encourage SET hearts=hearts+1 WHERE id=?", (eid,))
        return cur["hearts"] + 1
    h._json({"ok": True, "hearts": tx(op)})


# ---------- 破戒复盘 ----------
@route("GET", "/reflections")
def reflections_list(h, user, body, q, m):
    rows = rd(lambda con: [dict(r) for r in con.execute(
        "SELECT id,date,trigger,feeling,lesson FROM reflections "
        "WHERE user_id=? ORDER BY id DESC LIMIT 30", (user["id"],))])
    h._json({"ok": True, "list": rows})


@route("POST", "/reflections")
def reflections_add(h, user, body, q, m):
    trigger = str(body.get("trigger", "")).strip()[:200]
    feeling = str(body.get("feeling", "")).strip()[:200]
    lesson = str(body.get("lesson", "")).strip()[:500]
    if not trigger and not lesson:
        raise ApiError("请填写诱因或教训")

    def op(con):
        con.execute(
            "INSERT INTO reflections(user_id,date,trigger,feeling,lesson) VALUES(?,?,?,?,?)",
            (user["id"], now_str(), trigger, feeling, lesson))
        u = con.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        return user_json(con, u)
    h._json({"ok": True, "user": tx(op)})


@route("POST", "/reflections/delete")
def reflections_del(h, user, body, q, m):
    rid = int(body.get("id", 0))
    tx(lambda con: con.execute(
        "DELETE FROM reflections WHERE id=? AND user_id=?", (rid, user["id"])))
    h._json({"ok": True})


# ---------- 红黑榜（服务端地区聚合） ----------
@route("GET", "/leaderboard")
def leaderboard(h, user, body, q, m):
    def op(con):
        con.execute(
            "UPDATE users SET streak=0 WHERE streak>0 AND last_checkin IS NOT NULL AND last_checkin<?",
            ((date.today() - timedelta(days=1)).isoformat(),))
        rows = con.execute(
            "SELECT region,streak,days,merit,relapse_count FROM users").fetchall()
        agg = {}
        for r in rows:
            rg = r["region"] or "未知"
            a = agg.setdefault(rg, {"region": rg, "count": 0, "streak": 0,
                                    "max": 0, "days": 0, "merit": 0, "relapse": 0})
            a["count"] += 1
            a["streak"] += r["streak"]
            a["max"] = max(a["max"], r["streak"])
            a["days"] += r["days"]
            a["merit"] += r["merit"]
            a["relapse"] += r["relapse_count"]
        red = sorted((a for a in agg.values() if a["streak"] > 0 or a["days"] > 0),
                     key=lambda x: (-x["streak"], -x["days"], -x["merit"]))
        black = sorted((a for a in agg.values() if a["relapse"] > 0),
                       key=lambda x: (-x["relapse"], -x["days"]))
        return red, black
    red, black = tx(op)
    h._json({"ok": True, "red": red, "black": black, "myRegion": user["region"] or "未知"})


# ---------- 演示数据 ----------
DEMO_NAMES = ["清心子", "守拙生", "明尘", "静远", "素行", "砺志", "澄怀", "抱朴",
              "观澜", "慎独", "弘毅", "知非", "省身", "克己", "笃行", "安素"]
DEMO_REGIONS = ["广东", "江苏", "浙江", "山东", "河南", "四川", "湖北", "湖南",
                "福建", "安徽", "河北", "北京", "上海", "陕西", "江西", "辽宁",
                "云南", "重庆", "黑龙江", "山西"]


@route("POST", "/demo/seed")
def demo_seed(h, user, body, q, m):
    import random

    def op(con):
        added = 0
        for i, rg in enumerate(DEMO_REGIONS):
            n = random.randint(1, 3)
            for k in range(n):
                nm = "演示" + DEMO_NAMES[(i + k) % len(DEMO_NAMES)] + (str(k) if k else "")
                if con.execute("SELECT 1 FROM users WHERE name=?", (nm,)).fetchone():
                    continue
                streak = random.randint(0, 400)
                days = streak + random.randint(0, 120)
                uid_ = "demo_" + secrets.token_hex(4)
                salt = secrets.token_hex(16)
                con.execute(
                    "INSERT INTO users(id,name,pwd,salt,region,goal,vow,created_at,streak,"
                    "last_checkin,relapse_count,merit,days,pomo_count,quiz_best,med_breaths,"
                    "resist_count,daily,demo) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)",
                    (uid_, nm, hash_pwd(secrets.token_hex(8), salt), salt, rg,
                     random.choice([7, 21, 100, 365]), "", today(), streak,
                     today() if streak > 0 else None, random.randint(0, 9),
                     days * 5 + random.randint(0, 120), days,
                     random.randint(0, 30), random.randint(0, 8), random.randint(0, 400),
                     random.randint(0, 10), "{}"))
                if days > 0:
                    dates = []
                    d0 = date.today()
                    step = max(1, days // 60)  # 抽样生成，避免过多行
                    for d in range(0, min(days, 400), step):
                        dates.append(((d0 - timedelta(days=d)).isoformat(), uid_))
                    con.executemany("INSERT OR IGNORE INTO checkins(user_id,date) VALUES(?,?)", dates)
                added += 1
        return added
    added = tx(op)
    h._json({"ok": True, "added": added})


@route("POST", "/demo/clear")
def demo_clear(h, user, body, q, m):
    def op(con):
        ids = [r["id"] for r in con.execute("SELECT id FROM users WHERE demo=1")]
        for i in ids:
            con.execute("DELETE FROM checkins WHERE user_id=?", (i,))
            con.execute("DELETE FROM challenges WHERE user_id=?", (i,))
            con.execute("DELETE FROM journal WHERE user_id=?", (i,))
            con.execute("DELETE FROM health WHERE user_id=?", (i,))
            con.execute("DELETE FROM likes WHERE user_id=?", (i,))
            con.execute("DELETE FROM reflections WHERE user_id=?", (i,))
            con.execute("DELETE FROM sessions WHERE user_id=?", (i,))
        con.execute("DELETE FROM users WHERE demo=1")
        return len(ids)
    n = tx(op)
    h._json({"ok": True, "removed": n})


# ---------- 设置 / 账号 ----------
@route("POST", "/settings")
def settings_update(h, user, body, q, m):
    vow = str(body.get("vow", "")).strip()[:200]
    try:
        goal = int(body.get("goal", 21))
    except (TypeError, ValueError):
        goal = 21
    if goal not in (7, 21, 100, 365):
        goal = 21
    region = str(body.get("region", "")).strip() or user["region"]

    def op(con):
        con.execute("UPDATE users SET vow=?, goal=?, region=? WHERE id=?",
                    (vow, goal, region, user["id"]))
        u = con.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        return user_json(con, u)
    h._json({"ok": True, "user": tx(op)})


@route("GET", "/export")
def export_data(h, user, body, q, m):
    def op(con):
        u = con.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        return {
            "profile": user_json(con, u),
            "journal": [dict(r) for r in con.execute(
                "SELECT date,mood,text FROM journal WHERE user_id=? ORDER BY id", (user["id"],))],
            "health": [dict(r) for r in con.execute(
                "SELECT date,sleep,mood,sport,note FROM health WHERE user_id=? ORDER BY date",
                (user["id"],))],
        }
    h._json({"ok": True, "data": rd(op)})


@route("POST", "/account/delete")
def account_delete(h, user, body, q, m):
    token = h.headers.get("X-Token", "")

    def op(con):
        i = user["id"]
        con.execute("DELETE FROM checkins WHERE user_id=?", (i,))
        con.execute("DELETE FROM challenges WHERE user_id=?", (i,))
        con.execute("DELETE FROM journal WHERE user_id=?", (i,))
        con.execute("DELETE FROM health WHERE user_id=?", (i,))
        con.execute("DELETE FROM likes WHERE user_id=?", (i,))
        con.execute("DELETE FROM reflections WHERE user_id=?", (i,))
        con.execute("DELETE FROM sessions WHERE user_id=?", (i,))
        con.execute("DELETE FROM users WHERE id=?", (i,))
    tx(op)
    h._json({"ok": True})


# ============================================================
# HTTP 服务（静态 + API，双栈）
# ============================================================
class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def log_message(self, fmt, *args):
        pass  # 静默访问日志

    # ---- 基础工具 ----
    def _set_cors_headers(self):
        """CORS 跨域 + 安全响应头（基于 X-Token 而非 Cookie，可用 *）"""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Token")
        self.send_header("Access-Control-Max-Age", "86400")
        # 安全头
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")

    def _json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        """处理 CORS 预检请求"""
        self.send_response(HTTPStatus.NO_CONTENT)
        self._set_cors_headers()
        self.end_headers()

    def _body(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0:
            return {}
        if length > MAX_BODY_BYTES:
            raise ApiError("请求体过大（上限 1MB）")
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            return {}

    def _user(self):
        tok = self.headers.get("X-Token")
        if not tok:
            return None
        today_str = today()
        return rd(lambda con: con.execute(
            "SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id "
            "WHERE s.token=? AND (s.expires_at IS NULL OR s.expires_at >= ?)",
            (tok, today_str)).fetchone())

    # ---- 分发 ----
    def _dispatch(self, method):
        parsed = urlparse(self.path)
        path = parsed.path
        if not path.startswith("/api/"):
            if method == "GET":
                # 路径规范化（防止 ../、//、./ 绕过访问 data 目录）
                norm = posixpath.normpath(unquote(path))
                # 二次检查：规范化后再判 data 目录
                if norm == "/data" or norm.startswith("/data/"):
                    return self.send_error(HTTPStatus.FORBIDDEN)
                # 静态文件后缀白名单（防止数据库 .db 等被直接访问）
                _, ext = posixpath.splitext(norm.lower())
                if norm != "/" and ext not in ALLOWED_STATIC_EXT:
                    return self.send_error(HTTPStatus.FORBIDDEN)
                return super().do_GET()
            return self.send_error(HTTPStatus.METHOD_NOT_ALLOWED)

        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        try:
            body = self._body() if method in ("POST", "DELETE") else {}
        except ApiError as e:
            return self._json({"ok": False, "error": str(e)}, 400)
        except Exception as e:
            return self._json({"ok": False, "error": "请求体解析失败: " + str(e)}, 400)
        api_path = path[len("/api"):]  # 去掉 /api 前缀再匹配路由
        for m, rx, fn, auth in ROUTES:
            if m != method:
                continue
            match = rx.match(api_path)
            if not match:
                continue
            try:
                user = self._user() if auth else None
                if auth and user is None:
                    return self._json({"ok": False, "error": "请先登录"}, 401)
                return fn(self, user, body, query, match)
            except ApiError as e:
                return self._json({"ok": False, "error": str(e)}, 400)
            except Exception as e:  # 兜底：不让线程崩掉
                return self._json({"ok": False, "error": "服务器内部错误: " + str(e)}, 500)
        return self._json({"ok": False, "error": "接口不存在"}, 404)

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_DELETE(self):
        self._dispatch("DELETE")


class DualStackServer(http.server.ThreadingHTTPServer):
    address_family = socket.AF_INET6
    allow_reuse_address = True
    daemon_threads = True


def main():
    init_db()
    with DualStackServer(("::", 8000), Handler) as httpd:
        print("朱砂戒后端已启动: http://localhost:8000/  (双栈 IPv4+IPv6, SQLite 持久化)")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
