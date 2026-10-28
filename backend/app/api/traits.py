from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..schemas import ExtractRequest, MergeRequest, Profile, RefineRequest
from ..services.merge_service import merge_descriptions
from ..services.refinement_service import apply_changes, parse_refinement
from ..services.trait_extractor import extract_traits

router = APIRouter(tags=["traits"])


@router.post("/traits/extract")
def extract(req: ExtractRequest):
    return extract_traits(req.description).to_dict()


@router.post("/refine/parse")
def refine_parse(req: RefineRequest):
    return parse_refinement(req.instruction, req.profile)


class ApplyRequest(BaseModel):
    profile: Profile
    changes: list[dict] = Field(min_length=1, max_length=30)


@router.post("/refine/apply")
def refine_apply(req: ApplyRequest):
    return {"profile": apply_changes(req.profile, req.changes).model_dump()}


@router.post("/witnesses/merge")
def merge(req: MergeRequest):
    return merge_descriptions(req.descriptions)
