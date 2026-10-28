from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel

from .. import __version__
from ..catalog import catalog_payload
from ..config import get_settings
from ..providers.registry import all_providers
from ..services import sketch_service
from .auth import AUTH

router = APIRouter(tags=["system"])


@router.get("/health")
def health():
    return {"status": "ok", "app": "Revelio", "version": __version__,
            "renderer": "procedural-v1", "providers": all_providers()}


@router.get("/catalog")
def catalog():
    return catalog_payload()


@router.get("/providers")
def providers():
    return {"providers": all_providers()}


@router.get("/stats", dependencies=AUTH)
def stats():
    return sketch_service.stats()


@router.get("/activity", dependencies=AUTH)
def activity(limit: int = Query(default=20, ge=1, le=100)):
    return {"activity": sketch_service.activity(limit)}


@router.get("/storage", dependencies=AUTH)
def storage():
    s = get_settings()
    return {"data_dir": str(s.data_dir), "database": "SQLite", "images": "PNG/SVG files on local disk",
            "reference_images_stored": False}


class WipeRequest(BaseModel):
    confirm: str


@router.post("/data/delete-all", dependencies=AUTH)
def delete_all(req: WipeRequest):
    if req.confirm != "DELETE":
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="Type DELETE to confirm.")
    return sketch_service.delete_all_data()
