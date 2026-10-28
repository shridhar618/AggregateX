"""Local accounts: scrypt password hashes and opaque session tokens (stdlib only).

Only a SHA-256 hash of each session token is stored, so a copy of the database
cannot be used to hijack a live session. Passwords are never logged or returned.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone

from ..database import connect, now_iso

SESSION_COOKIE = "revelio_session"
SESSION_DAYS = 7

_N, _R, _P = 2**14, 8, 1
_DUMMY_HASH: str | None = None  # verified against when an email is unknown, to even out timing

MAX_FAILURES = 5
LOCKOUT_S = 60
_failures: dict[str, tuple[int, float]] = {}
_lock = threading.Lock()


class EmailTaken(Exception):
    pass


class TooManyAttempts(Exception):
    def __init__(self, retry_after: int):
        super().__init__(f"Too many failed attempts. Try again in {retry_after} seconds.")
        self.retry_after = retry_after


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    return f"scrypt${_N}${_R}${_P}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt, digest = stored.split("$")
        if algo != "scrypt":
            return False
        dk = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p),
                            dklen=len(digest) // 2)
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(dk.hex(), digest)


def _public(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "name": row["name"], "email": row["email"], "created_at": row["created_at"]}


def register(name: str, email: str, password: str) -> dict:
    pw_hash = hash_password(password)
    with connect() as conn:
        try:
            cur = conn.execute("INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                               (name, email, pw_hash, now_iso()))
        except sqlite3.IntegrityError:
            raise EmailTaken("An account with this email already exists.") from None
        row = conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _public(row)


def _check_lockout(email: str) -> None:
    with _lock:
        count, until = _failures.get(email, (0, 0.0))
        if count >= MAX_FAILURES and until > time.monotonic():
            raise TooManyAttempts(int(until - time.monotonic()) + 1)


def _record(email: str, ok: bool) -> None:
    with _lock:
        if ok:
            _failures.pop(email, None)
            return
        count, until = _failures.get(email, (0, 0.0))
        if until and until <= time.monotonic():
            count = 0
        count += 1
        _failures[email] = (count, time.monotonic() + LOCKOUT_S if count >= MAX_FAILURES else 0.0)


def authenticate(email: str, password: str) -> dict | None:
    global _DUMMY_HASH
    _check_lockout(email)
    with connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if row is None:
        _DUMMY_HASH = _DUMMY_HASH or hash_password(secrets.token_hex(8))
        verify_password(password, _DUMMY_HASH)
        ok = False
    else:
        ok = verify_password(password, row["password_hash"])
    _record(email, ok)
    return _public(row) if ok else None


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires = (datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    with connect() as conn:
        conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (now_iso(),))
        conn.execute("INSERT INTO sessions (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
                     (_token_hash(token), user_id, now_iso(), expires))
    return token


def user_for_token(token: str | None) -> dict | None:
    if not token or len(token) > 128:
        return None
    with connect() as conn:
        row = conn.execute(
            "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token_hash = ? AND s.expires_at > ?",
            (_token_hash(token), now_iso()),
        ).fetchone()
    return _public(row) if row else None


def delete_session(token: str | None) -> None:
    if token:
        with connect() as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))


def reset_throttle() -> None:
    """Test helper: clear the in-memory failed-login counters."""
    with _lock:
        _failures.clear()
