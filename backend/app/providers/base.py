"""Replaceable generation-provider interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..schemas import Profile


class ProviderError(RuntimeError):
    """A provider failed. ``message`` is safe to show to the operator (no secrets)."""


class ProviderUnavailable(ProviderError):
    """The provider is not installed or not configured."""


@dataclass
class GenerationOutput:
    png: bytes
    svg: Optional[str]
    method: str               # e.g. "offline_procedural", "hosted_gemini"
    method_label: str         # human label shown next to every result
    is_ai: bool               # True only for real AI-model output
    model: Optional[str] = None
    notes: list[dict] = field(default_factory=list)


class GenerationProvider:
    id: str = "base"
    label: str = "Base"
    kind: str = "procedural"          # "procedural" | "ai"
    runs_locally: bool = True
    supports_reference_image: bool = False
    supports_live_edit: bool = False  # can re-render instantly from slider changes

    def status(self) -> dict:
        raise NotImplementedError

    def generate(self, profile: Profile, *, caption: str | None = None,
                 reference_png: bytes | None = None) -> GenerationOutput:
        raise NotImplementedError

    def describe(self) -> dict:
        st = self.status()
        return {
            "id": self.id, "label": self.label, "kind": self.kind,
            "runs_locally": self.runs_locally,
            "supports_reference_image": self.supports_reference_image,
            "supports_live_edit": self.supports_live_edit,
            **st,
        }
