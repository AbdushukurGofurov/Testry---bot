"""Oddiy SQLite baza: har bir test urinishi bitta qator."""
import json
import os
import sqlite3
import time

DB_PATH = os.getenv("DB_PATH", "testry.db")


def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init():
    with conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            first_name TEXT,
            ref TEXT,
            started_at INTEGER,
            finished_at INTEGER,
            pos INTEGER DEFAULT 0,
            data TEXT DEFAULT '{}',
            result TEXT,
            rating INTEGER,
            paid_click INTEGER DEFAULT 0,
            receipt INTEGER DEFAULT 0,
            stage TEXT DEFAULT 'test',
            retest_of INTEGER,
            retest_invited INTEGER DEFAULT 0
        )""")


def new_session(user_id, username, first_name, ref=None):
    with conn() as c:
        prev = c.execute("SELECT id FROM sessions WHERE user_id=? AND finished_at IS NOT NULL "
                         "ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()
        cur = c.execute("INSERT INTO sessions(user_id, username, first_name, ref, started_at, retest_of) "
                        "VALUES (?,?,?,?,?,?)",
                        (user_id, username, first_name, ref, int(time.time()), prev["id"] if prev else None))
        return cur.lastrowid


def latest(user_id):
    with conn() as c:
        return c.execute("SELECT * FROM sessions WHERE user_id=? ORDER BY id DESC LIMIT 1", (user_id,)).fetchone()


def get(sid):
    with conn() as c:
        return c.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()


def save(sid, **fields):
    if "data" in fields:
        fields["data"] = json.dumps(fields["data"], ensure_ascii=False)
    if "result" in fields:
        fields["result"] = json.dumps(fields["result"], ensure_ascii=False)
    keys = ", ".join(f"{k}=?" for k in fields)
    with conn() as c:
        c.execute(f"UPDATE sessions SET {keys} WHERE id=?", (*fields.values(), sid))


def data_of(row) -> dict:
    return json.loads(row["data"] or "{}")


def all_rows():
    with conn() as c:
        return c.execute("SELECT * FROM sessions ORDER BY id").fetchall()


def retest_candidates(days=14):
    cutoff = int(time.time()) - days * 86400
    with conn() as c:
        return c.execute("""SELECT s.* FROM sessions s
            WHERE s.finished_at IS NOT NULL AND s.finished_at < ? AND s.retest_invited = 0
            AND NOT EXISTS (SELECT 1 FROM sessions t WHERE t.user_id = s.user_id AND t.id > s.id)""",
                         (cutoff,)).fetchall()
