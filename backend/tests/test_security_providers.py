import base64
import io
import json
import socket
import urllib.error

import pytest
from PIL import Image

from app.services.uploads import UploadError, validate_reference_image
from tests.conftest import SPEC_DESCRIPTION

FAKE_KEY = "TEST-KEY-should-never-appear-0123456789"


def _png_data_url(size=(16, 16)):
    buf = io.BytesIO()
    Image.new("RGB", size, "gray").save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def test_valid_upload_is_reencoded():
    data, mime = validate_reference_image(_png_data_url())
    assert mime == "image/png" and data.startswith(b"\x89PNG")


@pytest.mark.parametrize("bad", [
    "not a data url",
    "data:image/gif;base64,R0lGODlhAQABAAAAACw=",
    "data:image/png;base64," + base64.b64encode(b"GIF89a not really a png").decode(),
    "data:image/jpeg;base64," + base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 20).decode(),
    "data:image/png;base64,",
])
def test_invalid_uploads_rejected(bad):
    with pytest.raises(UploadError):
        validate_reference_image(bad)


def test_oversized_upload_rejected(monkeypatch):
    monkeypatch.setenv("VERISKETCH_MAX_UPLOAD_MB", "0")
    with pytest.raises(UploadError):
        validate_reference_image(_png_data_url())


def test_truncated_png_rejected():
    raw = base64.b64decode(_png_data_url().split(",")[1])[:30]
    with pytest.raises(UploadError):
        validate_reference_image("data:image/png;base64," + base64.b64encode(raw).decode())


def _profile(client):
    return client.post("/api/traits/extract", json={"description": SPEC_DESCRIPTION}).json()["profile"]


def test_local_provider_unavailable_is_honest(client):
    r = client.post("/api/sketches/generate", json={"title": "x", "profile": _profile(client), "mode": "local"})
    assert r.status_code == 409 and r.json()["offline_available"] is True
    assert client.get("/api/sketches").json()["sketches"] == []   # nothing stored on failure


def test_hosted_failure_is_reported_without_leaking_key(client, monkeypatch):
    monkeypatch.setenv("VERISKETCH_HOSTED_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", FAKE_KEY)

    def boom(req, timeout=0):
        assert FAKE_KEY not in req.full_url                      # key never in the URL
        assert req.get_header("X-goog-api-key") == FAKE_KEY       # sent as a header
        body = json.dumps({"error": {"message": f"API key not valid: {FAKE_KEY}"}}).encode()
        raise urllib.error.HTTPError(req.full_url, 400, "Bad Request", {}, io.BytesIO(body))

    monkeypatch.setattr("urllib.request.urlopen", boom)
    r = client.post("/api/sketches/generate", json={"title": "x", "profile": _profile(client), "mode": "hosted"})
    assert r.status_code == 502
    assert FAKE_KEY not in r.text and "[redacted]" in r.json()["detail"]
    assert r.json()["offline_available"] is True
    assert client.get("/api/sketches").json()["sketches"] == []   # no silent fallback


def test_hosted_success_is_labelled_ai(client, monkeypatch):
    monkeypatch.setenv("VERISKETCH_HOSTED_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", FAKE_KEY)
    buf = io.BytesIO()
    Image.new("RGB", (64, 80), "white").save(buf, "PNG")
    payload = {"candidates": [{"content": {"parts": [{"inlineData": {"mimeType": "image/png",
                                                                     "data": base64.b64encode(buf.getvalue()).decode()}}]}}]}

    class Resp(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout=0: Resp(json.dumps(payload).encode()))
    r = client.post("/api/sketches/generate", json={"title": "x", "profile": _profile(client), "mode": "hosted"})
    assert r.status_code == 201
    cur = r.json()["current"]
    assert cur["is_ai"] is True and cur["method"] == "hosted_gemini" and "AI-generated" in cur["method_label"]
    assert cur["svg_url"] is None


def test_offline_workflow_without_network(client, monkeypatch):
    def no_network(*a, **k):
        raise OSError("network disabled for this test")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)
    profile = _profile(client)
    assert client.post("/api/render", json={"profile": profile}).status_code == 200
    r = client.post("/api/sketches/generate", json={"title": "offline", "profile": profile})
    assert r.status_code == 201
    assert client.get(r.json()["current"]["image_url"]).content.startswith(b"\x89PNG")
