import base64
import io

from PIL import Image

from tests.conftest import SPEC_DESCRIPTION


def _create(client, title="Case test"):
    ex = client.post("/api/traits/extract", json={"description": SPEC_DESCRIPTION}).json()
    r = client.post("/api/sketches/generate", json={"title": title, "description": SPEC_DESCRIPTION, "profile": ex["profile"]})
    assert r.status_code == 201, r.text
    return r.json()


def test_health_and_catalog(client):
    h = client.get("/api/health").json()
    assert h["status"] == "ok"
    ids = {p["id"]: p for p in h["providers"]}
    assert ids["offline"]["available"] is True
    assert ids["hosted"]["available"] is False
    assert ids["local"]["available"] is False
    cat = client.get("/api/catalog").json()
    assert any(t["key"] == "face_shape" for t in cat["traits"])


def test_extract_validation(client):
    assert client.post("/api/traits/extract", json={"description": "tiny"}).status_code == 422


def test_generate_persist_and_reopen(client):
    s = _create(client)
    assert s["id"].startswith("RV-")
    assert s["revision_count"] == 1
    cur = s["current"]
    assert cur["is_ai"] is False and "not AI-generated" in cur["method_label"]
    png = client.get(cur["image_url"])
    assert png.status_code == 200 and png.content.startswith(b"\x89PNG")
    reopened = client.get(f"/api/sketches/{s['id']}").json()
    assert reopened["current"]["profile"]["traits"]["face_shape"]["value"] == "oval"
    assert any(x["id"] == s["id"] for x in client.get("/api/sketches").json()["sketches"])


def test_revisions_history_and_comparison(client):
    s = _create(client)
    profile = s["current"]["profile"]
    profile["traits"]["face_shape"] = {"value": "square", "source": "manual"}
    r = client.post(f"/api/sketches/{s['id']}/revisions", json={"profile": profile, "note": "square face"})
    assert r.status_code == 201
    revs = client.get(f"/api/sketches/{s['id']}/revisions").json()["revisions"]
    assert [x["number"] for x in revs] == [1, 2]
    assert revs[0]["profile"]["traits"]["face_shape"]["value"] == "oval"   # previous revision preserved
    assert revs[1]["profile"]["traits"]["face_shape"]["value"] == "square"
    a = client.get(revs[0]["image_url"]).content
    b = client.get(revs[1]["image_url"]).content
    assert a != b


def test_rename_status_notes_and_delete(client):
    s = _create(client)
    r = client.patch(f"/api/sketches/{s['id']}", json={"title": "Renamed", "status": "final", "notes": "Reviewed"}).json()
    assert r["title"] == "Renamed" and r["status"] == "final" and r["notes"] == "Reviewed"
    assert client.delete(f"/api/sketches/{s['id']}").status_code == 204
    assert client.get(f"/api/sketches/{s['id']}").status_code == 404
    assert client.get(s["current"]["image_url"]).status_code == 404


def test_exports(client):
    s = _create(client)
    data = client.get(f"/api/sketches/{s['id']}/export.json").json()
    assert data["application"] == "Revelio"
    assert "not proof of identity" in data["disclaimer"]
    assert "Eye colour" in data["unknown_traits"]
    html = client.get(f"/api/sketches/{s['id']}/report").text
    assert "not proof of identity" in html and s["id"] in html and "data:image/png;base64," in html
    png = client.post("/api/render.png", json={"profile": s["current"]["profile"]})
    assert png.headers["content-type"] == "image/png" and png.content.startswith(b"\x89PNG")


def test_stats_and_activity_reflect_real_data(client):
    assert client.get("/api/stats").json()["sketches"] == 0
    assert client.get("/api/activity").json()["activity"] == []
    _create(client)
    st = client.get("/api/stats").json()
    assert st["sketches"] == 1 and st["drafts"] == 1 and st["revisions"] == 1
    assert client.get("/api/activity").json()["activity"][0]["kind"] == "created"


def test_delete_all_requires_confirmation(client):
    _create(client)
    assert client.post("/api/data/delete-all", json={"confirm": "yes"}).status_code == 422
    assert client.post("/api/data/delete-all", json={"confirm": "DELETE"}).json()["deleted_sketches"] == 1
    assert client.get("/api/sketches").json()["sketches"] == []


def test_invalid_ids_and_profiles(client):
    assert client.get("/api/sketches/../../etc/passwd").status_code == 404
    assert client.get("/api/sketches/RV-bad").status_code == 404
    bad = {"title": "x", "profile": {"traits": {"face_shape": {"value": "hexagon"}}}}
    assert client.post("/api/sketches/generate", json=bad).status_code == 422
    bad_adj = {"title": "x", "profile": {"adjustments": {"jaw_width": 5}}}
    assert client.post("/api/sketches/generate", json=bad_adj).status_code == 422


def test_refine_endpoints(client):
    ex = client.post("/api/traits/extract", json={"description": SPEC_DESCRIPTION}).json()
    parsed = client.post("/api/refine/parse", json={"instruction": "make the eyebrows thicker", "profile": ex["profile"]}).json()
    applied = client.post("/api/refine/apply", json={"profile": ex["profile"], "changes": parsed["changes"]}).json()
    assert applied["profile"]["traits"]["eyebrow_thickness"]["value"] == "bushy"


def test_offline_mode_rejects_reference_image(client):
    ex = client.post("/api/traits/extract", json={"description": SPEC_DESCRIPTION}).json()
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), "white").save(buf, "PNG")
    data_url = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    r = client.post("/api/sketches/generate", json={"title": "x", "profile": ex["profile"], "reference_image": data_url})
    assert r.status_code == 422 and "does not use reference images" in r.json()["detail"]
