from __future__ import annotations

import re
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from .catalog import ADJUSTMENT_KEYS, MARK_LOCATIONS, MARK_SIZES, MARK_TYPES, TRAIT_BY_KEY

Source = Literal["described", "extracted", "manual", "unknown"]
Certainty = Literal["stated", "uncertain"]

DESCRIPTION_MIN = 10
DESCRIPTION_MAX = 2000
SKETCH_ID_RE = re.compile(r"^VS-\d{8}-[0-9A-F]{4}$")


class TraitValue(BaseModel):
    value: Optional[str] = None
    source: Source = "unknown"
    evidence: Optional[str] = Field(default=None, max_length=300)
    certainty: Certainty = "stated"
    # Non-empty when the description contained conflicting statements.
    # A conflicting trait keeps value=None until an operator resolves it.
    alternatives: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _consistent(self):
        if self.value is None and self.source != "unknown" and not self.alternatives:
            self.source = "unknown"
        return self


class Mark(BaseModel):
    id: str = Field(min_length=1, max_length=40)
    type: str
    location: str
    size: str = "small"
    dx: float = Field(default=0.0, ge=-1.0, le=1.0)
    dy: float = Field(default=0.0, ge=-1.0, le=1.0)
    # False when the witness did not say which side (left/right) the mark is on.
    side_specified: bool = True
    source: Source = "extracted"
    evidence: Optional[str] = Field(default=None, max_length=300)

    @field_validator("type")
    @classmethod
    def _type(cls, v):
        if v not in MARK_TYPES:
            raise ValueError(f"unsupported mark type '{v}'")
        return v

    @field_validator("location")
    @classmethod
    def _loc(cls, v):
        if v not in MARK_LOCATIONS:
            raise ValueError(f"unsupported mark location '{v}'")
        return v

    @field_validator("size")
    @classmethod
    def _size(cls, v):
        if v not in MARK_SIZES:
            raise ValueError(f"unsupported mark size '{v}'")
        return v


class Profile(BaseModel):
    traits: dict[str, TraitValue] = Field(default_factory=dict)
    marks: list[Mark] = Field(default_factory=list, max_length=20)
    adjustments: dict[str, float] = Field(default_factory=dict)
    observations: str = Field(default="", max_length=1000)

    @field_validator("traits")
    @classmethod
    def _traits(cls, v: dict[str, TraitValue]):
        for key, tv in v.items():
            spec = TRAIT_BY_KEY.get(key)
            if spec is None:
                raise ValueError(f"unknown trait '{key}'")
            if tv.value is not None and tv.value not in spec["options"]:
                raise ValueError(f"'{tv.value}' is not a valid option for {key}")
            for alt in tv.alternatives:
                if alt not in spec["options"]:
                    raise ValueError(f"'{alt}' is not a valid option for {key}")
        return v

    @field_validator("adjustments")
    @classmethod
    def _adjustments(cls, v: dict[str, float]):
        out = {}
        for key, val in v.items():
            if key not in ADJUSTMENT_KEYS:
                raise ValueError(f"unknown adjustment '{key}'")
            if not isinstance(val, (int, float)) or val != val:  # NaN check
                raise ValueError(f"adjustment '{key}' must be a number")
            if val < -1 or val > 1:
                raise ValueError(f"adjustment '{key}' must be between -1 and 1")
            out[key] = float(val)
        return out

    def trait(self, key: str) -> Optional[str]:
        tv = self.traits.get(key)
        return tv.value if tv else None


def validate_description(text: str) -> str:
    cleaned = (text or "").strip()
    if len(cleaned) < DESCRIPTION_MIN:
        raise ValueError(f"Description must be at least {DESCRIPTION_MIN} characters.")
    if len(cleaned) > DESCRIPTION_MAX:
        raise ValueError(f"Description must be at most {DESCRIPTION_MAX} characters.")
    if not re.search(r"[A-Za-z]{3,}", cleaned):
        raise ValueError("Description must contain words describing the person.")
    return cleaned


class ExtractRequest(BaseModel):
    description: str = Field(max_length=DESCRIPTION_MAX + 200)

    @field_validator("description")
    @classmethod
    def _desc(cls, v):
        return validate_description(v)


class RenderRequest(BaseModel):
    profile: Profile
    caption: Optional[str] = Field(default=None, max_length=60)


class GenerateRequest(BaseModel):
    title: str = Field(default="Untitled composite", min_length=1, max_length=120)
    description: str = Field(default="", max_length=DESCRIPTION_MAX + 200)
    profile: Profile
    mode: Literal["offline", "local", "hosted"] = "offline"
    reference_image: Optional[str] = Field(default=None, max_length=8_000_000)
    note: Optional[str] = Field(default=None, max_length=300)


class RevisionRequest(BaseModel):
    profile: Profile
    mode: Literal["offline", "local", "hosted"] = "offline"
    reference_image: Optional[str] = Field(default=None, max_length=8_000_000)
    note: Optional[str] = Field(default=None, max_length=300)


class SketchUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=120)
    status: Optional[Literal["draft", "final"]] = None
    notes: Optional[str] = Field(default=None, max_length=2000)


class RefineRequest(BaseModel):
    instruction: str = Field(min_length=3, max_length=500)
    profile: Profile


class MergeRequest(BaseModel):
    descriptions: list[str] = Field(min_length=2, max_length=6)

    @field_validator("descriptions")
    @classmethod
    def _descs(cls, v):
        return [validate_description(d) for d in v]
