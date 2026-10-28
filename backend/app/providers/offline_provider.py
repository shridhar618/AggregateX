from __future__ import annotations

from ..schemas import Profile
from ..services.procedural_renderer import render_profile
from .base import GenerationOutput, GenerationProvider


class OfflineCompositeProvider(GenerationProvider):
    id = "offline"
    label = "Offline Composite"
    kind = "procedural"
    runs_locally = True
    supports_reference_image = False
    supports_live_edit = True

    def status(self) -> dict:
        return {
            "available": True,
            "state": "ready",
            "reason": "Built-in procedural renderer. Runs on this machine with no network access.",
            "data_leaves_device": False,
        }

    def generate(self, profile: Profile, *, caption=None, reference_png=None) -> GenerationOutput:
        result = render_profile(profile, caption=caption)
        return GenerationOutput(
            png=result.png, svg=result.svg, method="offline_procedural",
            method_label="Procedural composite (offline, not AI-generated)", is_ai=False,
            model="revelio-procedural-v1", notes=result.notes,
        )
