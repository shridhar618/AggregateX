import sqlite3

import pytest

from app.services.auth_service import MAX_FAILURES, SESSION_COOKIE, hash_password, verify_password

ACCOUNT = {"name": "Ada Officer", "email": "Ada@Example.test", "password": "s3cure-passphrase"}
PROTECTED = [("get", "/api/sketches"), ("get", "/api/stats"), ("get", "/api/activity"), ("get", "/api/storage"),
             ("get", "/api/sketches/RV-20260101-ABCD"), ("post", "/api/data/delete-all")]


def test_password_hash_roundtrip():
    h = hash_password("hunter2hunter2")
    assert h.startswith("scrypt$") and "hunter2" not in h
    assert verify_password("hunter2hunter2", h)
    assert not verify_password("hunter2hunter3", h)
    assert not verify_password("x", "garbage")
    assert hash_password("same") != hash_password("same")  # salted


def test_register_sets_httponly_session_and_me(anon_client):
    r = anon_client.post("/api/auth/register", json=ACCOUNT)
    assert r.status_code == 201
    user = r.json()["user"]
    assert user["email"] == "ada@example.test" and user["name"] == "Ada Officer"
    assert "password" not in str(r.json()) and "hash" not in str(r.json())
    cookie = r.headers["set-cookie"]
    assert SESSION_COOKIE in cookie and "HttpOnly" in cookie and "SameSite=strict" in cookie
    assert anon_client.get("/api/auth/me").json()["user"]["email"] == "ada@example.test"


def test_password_is_not_stored_in_plain_text(anon_client, tmp_path):
    anon_client.post("/api/auth/register", json=ACCOUNT)
    db = sqlite3.connect(tmp_path / "data" / "revelio.db")
    stored, = db.execute("SELECT password_hash FROM users").fetchone()
    tokens = [t for t, in db.execute("SELECT token_hash FROM sessions")]
    assert ACCOUNT["password"] not in stored and stored.startswith("scrypt$")
    assert anon_client.cookies.get(SESSION_COOKIE) not in tokens  # only a hash of the token is stored


def test_duplicate_email_is_rejected_case_insensitively(anon_client):
    assert anon_client.post("/api/auth/register", json=ACCOUNT).status_code == 201
    r = anon_client.post("/api/auth/register", json={**ACCOUNT, "email": "ADA@example.TEST"})
    assert r.status_code == 409 and "already exists" in r.json()["detail"]


@pytest.mark.parametrize("patch, field", [({"email": "not-an-email"}, "email"), ({"password": "short"}, "password"),
                                          ({"name": "   "}, "name")])
def test_register_validation(anon_client, patch, field):
    r = anon_client.post("/api/auth/register", json={**ACCOUNT, **patch})
    assert r.status_code == 422 and r.json()["detail"].startswith(field)


def test_login_logout_cycle(anon_client):
    anon_client.post("/api/auth/register", json=ACCOUNT)
    anon_client.post("/api/auth/logout")
    assert anon_client.get("/api/auth/me").status_code == 401

    bad = anon_client.post("/api/auth/login", json={"email": ACCOUNT["email"], "password": "wrong-password"})
    assert bad.status_code == 401 and bad.json()["detail"] == "Email or password is incorrect."
    unknown = anon_client.post("/api/auth/login", json={"email": "nobody@example.test", "password": "whatever1"})
    assert unknown.json()["detail"] == bad.json()["detail"]  # does not reveal which emails exist

    ok = anon_client.post("/api/auth/login", json={"email": "  ADA@example.test ", "password": ACCOUNT["password"]})
    assert ok.status_code == 200 and anon_client.get("/api/sketches").status_code == 200

    token = anon_client.cookies.get(SESSION_COOKIE)
    assert anon_client.post("/api/auth/logout").status_code == 204
    anon_client.cookies.set(SESSION_COOKIE, token)  # a copied token stops working after logout
    assert anon_client.get("/api/sketches").status_code == 401


def test_repeated_failures_are_throttled(anon_client):
    anon_client.post("/api/auth/register", json=ACCOUNT)
    anon_client.post("/api/auth/logout")
    for _ in range(MAX_FAILURES):
        anon_client.post("/api/auth/login", json={"email": ACCOUNT["email"], "password": "wrong-password"})
    r = anon_client.post("/api/auth/login", json={"email": ACCOUNT["email"], "password": ACCOUNT["password"]})
    assert r.status_code == 429 and "Retry-After" in r.headers


def test_expired_session_is_rejected(anon_client, tmp_path):
    anon_client.post("/api/auth/register", json=ACCOUNT)
    db = sqlite3.connect(tmp_path / "data" / "revelio.db")
    db.execute("UPDATE sessions SET expires_at = '2000-01-01T00:00:00.000000Z'")
    db.commit()
    assert anon_client.get("/api/auth/me").status_code == 401


@pytest.mark.parametrize("method, path", PROTECTED)
def test_saved_data_requires_login(anon_client, method, path):
    kwargs = {"json": {"confirm": "DELETE"}} if method == "post" else {}
    r = getattr(anon_client, method)(path, **kwargs)
    assert r.status_code == 401 and r.json()["detail"] == "Log in to continue."


def test_stateless_demo_routes_stay_public(anon_client):
    """The landing-page demos use these without an account; none of them store anything."""
    assert anon_client.get("/api/health").status_code == 200
    assert anon_client.get("/api/catalog").status_code == 200
    ex = anon_client.post("/api/traits/extract", json={"description": "An adult with an oval face and short dark hair."})
    assert ex.status_code == 200
    assert anon_client.post("/api/render", json={"profile": ex.json()["profile"]}).status_code == 200
