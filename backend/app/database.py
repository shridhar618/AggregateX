"""SQLite persistence (standard library only). One short-lived connection per call."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .config import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS sketches (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'draft',
    notes       TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS revisions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    sketch_id    TEXT NOT NULL REFERENCES sketches(id) ON DELETE CASCADE,
    number       INTEGER NOT NULL,
    profile_json TEXT NOT NULL,
    method       TEXT NOT NULL,
    method_label TEXT NOT NULL,
    model        TEXT,
    is_ai        INTEGER NOT NULL DEFAULT 0,
    image_file   TEXT NOT NULL,
    svg_file     TEXT,
    notes_json   TEXT NOT NULL DEFAULT '[]',
    change_note  TEXT,
    created_at   TEXT NOT NULL,
    UNIQUE (sketch_id, number)
);
CREATE TABLE IF NOT EXISTS activity (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    sketch_id  TEXT,
    kind       TEXT NOT NULL,
    message    TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_revisions_sketch ON revisions(sketch_id);
CREATE INDEX IF NOT EXISTS idx_activity_created ON activity(created_at);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def data_dir() -> Path:
    d = get_settings().data_dir
    (d / "images").mkdir(parents=True, exist_ok=True)
    return d


def db_path() -> Path:
    return data_dir() / "verisketch.db"


@contextmanager
def connect():
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


def log_activity(conn: sqlite3.Connection, kind: str, message: str, sketch_id: str | None = None) -> None:
    conn.execute(
        "INSERT INTO activity (sketch_id, kind, message, created_at) VALUES (?, ?, ?, ?)",
        (sketch_id, kind, message[:300], now_iso()),
    )
