"""The project was renamed VeriSketch AI → Revelio. Existing data and settings must keep working."""
import sqlite3

from app.schemas import SKETCH_ID_RE


def test_new_and_legacy_sketch_ids_are_valid():
    assert SKETCH_ID_RE.match("RV-20261028-0A1B")
    assert SKETCH_ID_RE.match("VS-20261028-0A1B")
    assert not SKETCH_ID_RE.match("XX-20261028-0A1B")


def test_legacy_env_names_still_work(tmp_path, monkeypatch):
    from app.config import get_settings
    monkeypatch.delenv("REVELIO_DATA_DIR", raising=False)
    monkeypatch.setenv("VERISKETCH_DATA_DIR", str(tmp_path / "legacy"))
    monkeypatch.setenv("VERISKETCH_MAX_UPLOAD_MB", "2")
    s = get_settings()
    assert s.data_dir == (tmp_path / "legacy").resolve()
    assert s.max_upload_bytes == 2 * 1024 * 1024
    monkeypatch.setenv("REVELIO_DATA_DIR", str(tmp_path / "new"))
    assert get_settings().data_dir == (tmp_path / "new").resolve()   # new name wins


def test_legacy_database_is_migrated_with_its_data(tmp_path, monkeypatch, client):
    data = tmp_path / "migrate"
    (data / "images").mkdir(parents=True)
    legacy = sqlite3.connect(data / "verisketch.db")
    legacy.execute("CREATE TABLE sketches (id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', "
                   "status TEXT NOT NULL DEFAULT 'draft', notes TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
    legacy.execute("INSERT INTO sketches VALUES ('VS-20261001-ABCD', 'Old case', '', 'draft', '', '2026-10-01T00:00:00Z', '2026-10-01T00:00:00Z')")
    legacy.commit()
    legacy.close()
    monkeypatch.setenv("REVELIO_DATA_DIR", str(data))
    from app.database import init_db
    init_db()
    assert (data / "revelio.db").exists() and not (data / "verisketch.db").exists()
    titles = [s["title"] for s in client.get("/api/sketches").json()["sketches"]]
    assert titles == ["Old case"]
