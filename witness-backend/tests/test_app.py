"""Offline tests use a fake Codex binary; never contact OpenAI or consume quota."""
import os
import stat
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

import app as dashboard


def _fake_binary(tmp_path: Path, mode: str) -> Path:
    path = tmp_path / "fake-codex"
    path.write_text(f'''#!{sys.executable}
import os, sys, time
from pathlib import Path
from PIL import Image
_ = sys.stdin.read()
time.sleep(0.30)
if "--add-dir" not in sys.argv or sys.argv[sys.argv.index("--add-dir") + 1] != os.environ["CODEX_HOME"]:
    print("Codex home is not writable", file=sys.stderr)
    sys.exit(1)
if {mode!r} == "success":
    p = Path(os.environ["CODEX_HOME"]) / "generated_images" / "fake-thread" / "generated.png"
    p.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (512, 512), (150, 90, 70)).save(p)
    print("Image produced via fake test binary")
elif {mode!r} == "claim-only":
    print("Image generated successfully (but no image exists)")
else:
    print("simulated failure", file=sys.stderr)
    sys.exit(1)
''')
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def _wait(client, job_id):
    for _ in range(75):
        r = client.get(f"/api/jobs/{job_id}")
        assert r.status_code == 200
        if r.json()["status"] in ("complete", "failed"):
            return r.json()
        time.sleep(0.05)
    raise AssertionError("Worker did not finish in test")


def _setup(tmp_path, monkeypatch, mode):
    base = tmp_path / mode
    base.mkdir()
    home = base / ".codex"
    output = base / "outputs"
    work = base / "work"
    output.mkdir()
    work.mkdir()
    binary = _fake_binary(base, mode)
    monkeypatch.setenv("CODEX_HOME", str(home))
    monkeypatch.setattr(dashboard, "CODEX_HOME", home)
    monkeypatch.setattr(dashboard, "GENERATED_IMAGES", home / "generated_images")
    monkeypatch.setattr(dashboard, "CODEX_BIN", str(binary))
    monkeypatch.setattr(dashboard, "OUTPUTS", output)
    monkeypatch.setattr(dashboard, "WORK", work)
    return TestClient(dashboard.app)


def test_success_and_one_job_at_a_time(tmp_path, monkeypatch):
    client = _setup(tmp_path, monkeypatch, "success")
    r = client.post("/api/generate", json={"description": "A fictional person with an oval face and dark hair", "style": "forensic"})
    assert r.status_code == 202
    job_id = r.json()["job_id"]
    busy = client.post("/api/generate", json={"description": "An adult with a round face", "style": "portrait"})
    assert busy.status_code == 409
    finished = _wait(client, job_id)
    assert finished["status"] == "complete", finished
    im = client.get(finished["image_url"])
    assert im.status_code == 200
    assert im.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_no_false_success_from_text_only(tmp_path, monkeypatch):
    client = _setup(tmp_path, monkeypatch, "claim-only")
    r = client.post("/api/generate", json={"description": "A fictional person with an oval face and dark hair"})
    assert r.status_code == 202
    finished = _wait(client, r.json()["job_id"])
    assert finished["status"] == "failed"
    assert finished["image_url"] is None


def test_missing_binary(tmp_path, monkeypatch):
    client = _setup(tmp_path, monkeypatch, "fail")
    monkeypatch.setattr(dashboard, "CODEX_BIN", None)
    r = client.post("/api/generate", json={"description": "A fictional person with an oval face and dark hair"})
    finished = _wait(client, r.json()["job_id"])
    assert finished["status"] == "failed"
    assert "Codex CLI not found" in finished["message"]
