"""Sketch persistence: SQLite metadata + PNG/SVG files on local disk."""

from __future__ import annotations

import json
import secrets
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..catalog import TRAIT_BY_KEY, option_label
from ..database import connect, data_dir, log_activity, now_iso
from ..providers.base import GenerationOutput
from ..providers.registry import get_provider
from ..schemas import SKETCH_ID_RE, GenerateRequest, Profile, RevisionRequest, SketchUpdate, validate_description
from .uploads import validate_reference_image

DISCLAIMER = ("AI-assisted facial composite for investigative assistance only. This image is not proof of "
              "identity and must not be treated as a definitive identification.")


class NotFound(LookupError):
    pass


def _check_id(sketch_id: str) -> str:
    if not SKETCH_ID_RE.match(sketch_id or ""):
        raise NotFound("Sketch not found.")
    return sketch_id


def _new_id(conn) -> str:
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    for _ in range(50):
        sid = f"RV-{day}-{secrets.token_hex(2).upper()}"
        if not conn.execute("SELECT 1 FROM sketches WHERE id = ?", (sid,)).fetchone():
            return sid
    raise RuntimeError("Could not allocate a sketch id")


def _sketch_dir(sketch_id: str) -> Path:
    d = data_dir() / "images" / _check_id(sketch_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def run_generation(mode: str, profile: Profile, caption: str, reference_image: Optional[str]) -> GenerationOutput:
    provider = get_provider(mode)
    reference_png = None
    if reference_image:
        if not provider.supports_reference_image:
            raise ValueError(f"{provider.label} does not use reference images. Remove the image or choose a mode that supports it.")
        reference_png, _ = validate_reference_image(reference_image)
    return provider.generate(profile, caption=caption, reference_png=reference_png)


def _store(sketch_id: str, number: int, out: GenerationOutput) -> tuple[str, Optional[str]]:
    d = _sketch_dir(sketch_id)
    png_name = f"r{number}.png"
    (d / png_name).write_bytes(out.png)
    svg_name = None
    if out.svg:
        svg_name = f"r{number}.svg"
        (d / svg_name).write_text(out.svg, encoding="utf-8")
    return png_name, svg_name


def _insert_revision(conn, sketch_id: str, number: int, profile: Profile, out: GenerationOutput, note: Optional[str]):
    png_name, svg_name = _store(sketch_id, number, out)
    conn.execute(
        """INSERT INTO revisions (sketch_id, number, profile_json, method, method_label, model, is_ai,
                                  image_file, svg_file, notes_json, change_note, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (sketch_id, number, profile.model_dump_json(), out.method, out.method_label, out.model, int(out.is_ai),
         png_name, svg_name, json.dumps(out.notes), (note or "")[:300], now_iso()),
    )


def create_sketch(req: GenerateRequest) -> dict:
    description = req.description.strip()
    if description:
        description = validate_description(description)
    with connect() as conn:
        sid = _new_id(conn)
    out = run_generation(req.mode, req.profile, sid, req.reference_image)  # fails before anything is stored
    ts = now_iso()
    with connect() as conn:
        conn.execute("INSERT INTO sketches (id, title, description, status, notes, created_at, updated_at) VALUES (?, ?, ?, 'draft', '', ?, ?)",
                     (sid, req.title.strip(), description, ts, ts))
        _insert_revision(conn, sid, 1, req.profile, out, req.note or "Initial composite")
        log_activity(conn, "created", f"Created {sid} “{req.title.strip()}” ({out.method_label})", sid)
    return get_sketch(sid)


def add_revision(sketch_id: str, req: RevisionRequest) -> dict:
    _check_id(sketch_id)
    with connect() as conn:
        row = conn.execute("SELECT id FROM sketches WHERE id = ?", (sketch_id,)).fetchone()
        if not row:
            raise NotFound("Sketch not found.")
        number = (conn.execute("SELECT COALESCE(MAX(number), 0) FROM revisions WHERE sketch_id = ?", (sketch_id,)).fetchone()[0]) + 1
    out = run_generation(req.mode, req.profile, sketch_id, req.reference_image)
    with connect() as conn:
        _insert_revision(conn, sketch_id, number, req.profile, out, req.note)
        conn.execute("UPDATE sketches SET updated_at = ? WHERE id = ?", (now_iso(), sketch_id))
        log_activity(conn, "revision", f"Saved revision {number} of {sketch_id} ({out.method_label})", sketch_id)
    return get_sketch(sketch_id)


def _revision_dict(sketch_id: str, r) -> dict:
    return {
        "number": r["number"], "method": r["method"], "method_label": r["method_label"], "model": r["model"],
        "is_ai": bool(r["is_ai"]), "created_at": r["created_at"], "change_note": r["change_note"],
        "notes": json.loads(r["notes_json"] or "[]"), "profile": json.loads(r["profile_json"]),
        "image_url": f"/api/sketches/{sketch_id}/revisions/{r['number']}/image.png",
        "svg_url": f"/api/sketches/{sketch_id}/revisions/{r['number']}/image.svg" if r["svg_file"] else None,
    }


def get_sketch(sketch_id: str) -> dict:
    _check_id(sketch_id)
    with connect() as conn:
        s = conn.execute("SELECT * FROM sketches WHERE id = ?", (sketch_id,)).fetchone()
        if not s:
            raise NotFound("Sketch not found.")
        revs = conn.execute("SELECT * FROM revisions WHERE sketch_id = ? ORDER BY number", (sketch_id,)).fetchall()
    revisions = [_revision_dict(sketch_id, r) for r in revs]
    return {**dict(s), "revisions": revisions, "current": revisions[-1] if revisions else None,
            "revision_count": len(revisions)}


def list_sketches(query: str | None = None) -> list[dict]:
    sql = """SELECT s.*, r.number AS rev_number, r.method_label, r.is_ai, r.method,
                    (SELECT COUNT(*) FROM revisions x WHERE x.sketch_id = s.id) AS revision_count
             FROM sketches s
             LEFT JOIN revisions r ON r.sketch_id = s.id
                  AND r.number = (SELECT MAX(number) FROM revisions y WHERE y.sketch_id = s.id)"""
    params: tuple = ()
    if query:
        sql += " WHERE s.title LIKE ? OR s.id LIKE ? OR s.description LIKE ?"
        q = f"%{query[:80]}%"
        params = (q, q, q)
    sql += " ORDER BY s.updated_at DESC"
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["is_ai"] = bool(d.get("is_ai"))
        d["thumbnail_url"] = f"/api/sketches/{d['id']}/revisions/{d['rev_number']}/image.png" if d.get("rev_number") else None
        out.append(d)
    return out


def update_sketch(sketch_id: str, req: SketchUpdate) -> dict:
    _check_id(sketch_id)
    fields, values, msgs = [], [], []
    if req.title is not None:
        fields.append("title = ?")
        values.append(req.title.strip())
        msgs.append(f"renamed to “{req.title.strip()}”")
    if req.status is not None:
        fields.append("status = ?")
        values.append(req.status)
        msgs.append(f"marked {req.status}")
    if req.notes is not None:
        fields.append("notes = ?")
        values.append(req.notes)
        msgs.append("notes updated")
    if not fields:
        return get_sketch(sketch_id)
    fields.append("updated_at = ?")
    values.append(now_iso())
    with connect() as conn:
        cur = conn.execute(f"UPDATE sketches SET {', '.join(fields)} WHERE id = ?", (*values, sketch_id))
        if cur.rowcount == 0:
            raise NotFound("Sketch not found.")
        log_activity(conn, "updated", f"{sketch_id} " + ", ".join(msgs), sketch_id)
    return get_sketch(sketch_id)


def delete_sketch(sketch_id: str) -> None:
    _check_id(sketch_id)
    with connect() as conn:
        cur = conn.execute("DELETE FROM sketches WHERE id = ?", (sketch_id,))
        if cur.rowcount == 0:
            raise NotFound("Sketch not found.")
        conn.execute("DELETE FROM revisions WHERE sketch_id = ?", (sketch_id,))
        conn.execute("DELETE FROM activity WHERE sketch_id = ?", (sketch_id,))
        log_activity(conn, "deleted", f"Deleted {sketch_id} and its images")
    shutil.rmtree(data_dir() / "images" / sketch_id, ignore_errors=True)


def delete_all_data() -> dict:
    with connect() as conn:
        n = conn.execute("SELECT COUNT(*) FROM sketches").fetchone()[0]
        conn.execute("DELETE FROM revisions")
        conn.execute("DELETE FROM sketches")
        conn.execute("DELETE FROM activity")
    shutil.rmtree(data_dir() / "images", ignore_errors=True)
    (data_dir() / "images").mkdir(parents=True, exist_ok=True)
    return {"deleted_sketches": n}


def image_path(sketch_id: str, number: int, kind: str) -> Path:
    _check_id(sketch_id)
    col = "image_file" if kind == "png" else "svg_file"
    with connect() as conn:
        row = conn.execute(f"SELECT {col} FROM revisions WHERE sketch_id = ? AND number = ?", (sketch_id, int(number))).fetchone()
    if not row or not row[0]:
        raise NotFound("Image not found.")
    path = (data_dir() / "images" / sketch_id / row[0]).resolve()
    if (data_dir() / "images").resolve() not in path.parents or not path.is_file():
        raise NotFound("Image not found.")
    return path


def stats() -> dict:
    with connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM sketches").fetchone()[0]
        drafts = conn.execute("SELECT COUNT(*) FROM sketches WHERE status = 'draft'").fetchone()[0]
        revisions = conn.execute("SELECT COUNT(*) FROM revisions").fetchone()[0]
        last = conn.execute("SELECT method_label, created_at FROM revisions ORDER BY created_at DESC LIMIT 1").fetchone()
    return {"sketches": total, "drafts": drafts, "finals": total - drafts, "revisions": revisions,
            "last_method": last["method_label"] if last else None, "last_generated_at": last["created_at"] if last else None}


def activity(limit: int = 20) -> list[dict]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM activity ORDER BY id DESC LIMIT ?", (max(1, min(limit, 100)),)).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
def _split_traits(profile: dict) -> tuple[list[dict], list[str], list[dict]]:
    confirmed, unknown, conflicts = [], [], []
    for key, spec in TRAIT_BY_KEY.items():
        tv = (profile.get("traits") or {}).get(key) or {}
        if tv.get("value"):
            confirmed.append({"key": key, "label": spec["label"], "value": tv["value"],
                              "value_label": option_label(key, tv["value"]), "source": tv.get("source"),
                              "certainty": tv.get("certainty", "stated"), "rendered": spec["rendered"]})
        elif tv.get("alternatives"):
            conflicts.append({"key": key, "label": spec["label"],
                              "alternatives": [option_label(key, a) for a in tv["alternatives"]]})
        else:
            unknown.append(spec["label"])
    return confirmed, unknown, conflicts


def export_json(sketch_id: str) -> dict:
    s = get_sketch(sketch_id)
    current = s["current"]["profile"] if s["current"] else {}
    confirmed, unknown, conflicts = _split_traits(current)
    with connect() as conn:
        log_activity(conn, "exported", f"Exported {sketch_id} as JSON", sketch_id)
    return {
        "application": "Revelio", "export_version": 1, "exported_at": now_iso(),
        "sketch_id": s["id"], "title": s["title"], "status": s["status"], "description": s["description"],
        "created_at": s["created_at"], "modified_at": s["updated_at"], "operator_notes": s["notes"],
        "current_revision": s["current"]["number"] if s["current"] else None,
        "generation_method": s["current"]["method_label"] if s["current"] else None,
        "confirmed_traits": confirmed, "unknown_traits": unknown, "unresolved_conflicts": conflicts,
        "distinctive_marks": current.get("marks", []), "adjustments": current.get("adjustments", {}),
        "observations": current.get("observations", ""),
        "revisions": [{k: r[k] for k in ("number", "method", "method_label", "model", "is_ai", "created_at", "change_note", "profile", "notes")}
                      for r in s["revisions"]],
        "disclaimer": DISCLAIMER,
    }
