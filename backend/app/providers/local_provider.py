"""Optional local image-generation model — detection only in this build.

A local diffusion model (e.g. Stable Diffusion 1.5 at ~4 GB of weights) needs
roughly 8 GB of free RAM/unified memory and 5–10 GB of disk. That is beyond a
typical student laptop running a browser and dev servers at the same time, and
inference could not be tested reliably while building this project. Rather than
ship untested inference code, this provider reports honestly what it detects.
The procedural generator remains fully functional regardless.
"""

from __future__ import annotations

import importlib.util
import os

from ..config import get_settings
from .base import GenerationProvider, ProviderUnavailable


class LocalModelProvider(GenerationProvider):
    id = "local"
    label = "Local AI Model"
    kind = "ai"
    runs_locally = True
    supports_reference_image = False
    supports_live_edit = False

    def status(self) -> dict:
        settings = get_settings()
        has_diffusers = importlib.util.find_spec("diffusers") is not None
        has_torch = importlib.util.find_spec("torch") is not None
        path = settings.local_model_path
        path_ok = bool(path) and os.path.isdir(path)
        missing = []
        if not has_torch:
            missing.append("PyTorch")
        if not has_diffusers:
            missing.append("diffusers")
        if not path_ok:
            missing.append("a downloaded model (VERISKETCH_LOCAL_MODEL_PATH)")
        reason = ("Not installed: missing " + ", ".join(missing) + "." if missing else
                  "Components detected, but local inference is not enabled in this build.")
        return {
            "available": False,
            "state": "not_installed" if missing else "not_enabled",
            "reason": reason + " See README → Optional local model for hardware requirements.",
            "data_leaves_device": False,
            "detected": {"torch": has_torch, "diffusers": has_diffusers, "model_path": path_ok},
        }

    def generate(self, profile, *, caption=None, reference_png=None):
        raise ProviderUnavailable(self.status()["reason"])
