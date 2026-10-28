from __future__ import annotations

from fastapi import APIRouter, Query, Response
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from ..schemas import GenerateRequest, RenderRequest, RevisionRequest, SketchUpdate
from ..services import sketch_service
from ..services.procedural_renderer import render_profile
from ..services.report import build_report
from .auth import AUTH

router = APIRouter(tags=["sketches"])
NO_STORE = {"Cache-Control": "no-store"}


@router.post("/render")
def render_preview(req: RenderRequest):
    """Live preview: offline procedural SVG only. Nothing is stored."""
    result = render_profile(req.profile, caption=req.caption)
    return {"svg": result.svg, "notes": result.notes, "method": "offline_procedural",
            "method_label": "Procedural composite (offline, not AI-generated)", "is_ai": False}


@router.post("/render.png")
def render_preview_png(req: RenderRequest):
    result = render_profile(req.profile, caption=req.caption)
    return Response(content=result.png, media_type="image/png",
                    headers={"Content-Disposition": 'attachment; filename="revelio-preview.png"', **NO_STORE})


@router.get("/sketches", dependencies=AUTH)
def list_sketches(q: str | None = Query(default=None, max_length=80)):
    return {"sketches": sketch_service.list_sketches(q)}


@router.post("/sketches/generate", status_code=201, dependencies=AUTH)
def generate(req: GenerateRequest):
    return sketch_service.create_sketch(req)


@router.get("/sketches/{sketch_id}", dependencies=AUTH)
def get_sketch(sketch_id: str):
    return sketch_service.get_sketch(sketch_id)


@router.patch("/sketches/{sketch_id}", dependencies=AUTH)
def update_sketch(sketch_id: str, req: SketchUpdate):
    return sketch_service.update_sketch(sketch_id, req)


@router.delete("/sketches/{sketch_id}", status_code=204, dependencies=AUTH)
def delete_sketch(sketch_id: str):
    sketch_service.delete_sketch(sketch_id)
    return Response(status_code=204)


@router.get("/sketches/{sketch_id}/revisions", dependencies=AUTH)
def revisions(sketch_id: str):
    return {"revisions": sketch_service.get_sketch(sketch_id)["revisions"]}


@router.post("/sketches/{sketch_id}/revisions", status_code=201, dependencies=AUTH)
def add_revision(sketch_id: str, req: RevisionRequest):
    return sketch_service.add_revision(sketch_id, req)


@router.get("/sketches/{sketch_id}/revisions/{number}/image.png", dependencies=AUTH)
def revision_png(sketch_id: str, number: int, download: bool = False):
    path = sketch_service.image_path(sketch_id, number, "png")
    headers = {"Content-Disposition": f'attachment; filename="{sketch_id}-r{number}.png"'} if download else {}
    return FileResponse(path, media_type="image/png", headers=headers)


@router.get("/sketches/{sketch_id}/revisions/{number}/image.svg", dependencies=AUTH)
def revision_svg(sketch_id: str, number: int):
    path = sketch_service.image_path(sketch_id, number, "svg")
    return FileResponse(path, media_type="image/svg+xml",
                        headers={"Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'"})


@router.get("/sketches/{sketch_id}/export.json", dependencies=AUTH)
def export_json(sketch_id: str, download: bool = False):
    data = sketch_service.export_json(sketch_id)
    headers = {"Content-Disposition": f'attachment; filename="{sketch_id}.json"'} if download else {}
    return JSONResponse(data, headers=headers)


@router.get("/sketches/{sketch_id}/report", response_class=HTMLResponse, dependencies=AUTH)
def report(sketch_id: str):
    return HTMLResponse(build_report(sketch_id), headers={
        "Content-Security-Policy": "default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'",
        **NO_STORE,
    })
