"""Optional hosted AI provider (Google Gemini image generation).

* Disabled unless VERISKETCH_HOSTED_PROVIDER=gemini AND GEMINI_API_KEY are set
  in the backend environment. The key never reaches the browser.
* The key is sent in the ``x-goog-api-key`` header, never in the URL, so it
  cannot appear in URL logs.
* Usage may be billed by Google. VeriSketch does not claim this is free; check
  your own quota and pricing before enabling it.
* Never silently replaced: if this provider fails, the API returns an error and
  the operator chooses whether to use the offline composite instead.
"""

from __future__ import annotations

import base64
import io
import json
import urllib.error
import urllib.request

from PIL import Image, UnidentifiedImageError

from ..catalog import TRAIT_BY_KEY, option_label
from ..config import get_settings
from ..schemas import Profile
from .base import GenerationOutput, GenerationProvider, ProviderError, ProviderUnavailable

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def build_prompt(profile: Profile) -> str:
    """Prompt from described traits only. Unknown traits are explicitly unspecified."""
    known, unknown = [], []
    for key, spec in TRAIT_BY_KEY.items():
        tv = profile.traits.get(key)
        if tv and tv.value:
            known.append(f"{spec['label'].lower()}: {option_label(key, tv.value).lower()}")
        else:
            unknown.append(spec["label"].lower())
    for m in profile.marks:
        known.append(f"{m.size} {m.type} on the subject's {m.location.replace('_', ' ')}")
    lines = [
        "Create a single front-facing forensic facial composite sketch.",
        "Style: monochrome graphite pencil drawing on a plain light background, head and shoulders, neutral expression.",
        "This is an investigative aid, not a portrait of a specific real person.",
        "Described characteristics: " + ("; ".join(known) if known else "none") + ".",
    ]
    if unknown:
        lines.append("Not described (keep neutral, do not add distinctive details): " + ", ".join(unknown) + ".")
    if profile.observations.strip():
        lines.append("Additional notes: " + profile.observations.strip()[:300])
    lines.append("No text, no watermark, no frame, no colour.")
    return "\n".join(lines)


class HostedGeminiProvider(GenerationProvider):
    id = "hosted"
    label = "Hosted AI (Gemini)"
    kind = "ai"
    runs_locally = False
    supports_reference_image = True
    supports_live_edit = False

    def status(self) -> dict:
        s = get_settings()
        if s.hosted_provider != "gemini":
            return {"available": False, "state": "disabled",
                    "reason": "Disabled. Set VERISKETCH_HOSTED_PROVIDER=gemini and GEMINI_API_KEY in backend/.env to enable.",
                    "data_leaves_device": True, "model": s.gemini_model}
        if not s.gemini_api_key:
            return {"available": False, "state": "missing_key",
                    "reason": "GEMINI_API_KEY is not set in the backend environment.",
                    "data_leaves_device": True, "model": s.gemini_model}
        return {"available": True, "state": "configured",
                "reason": "Configured. Not verified until a generation succeeds; usage may be billed by Google.",
                "data_leaves_device": True, "model": s.gemini_model}

    def _sanitize(self, text: str) -> str:
        key = get_settings().gemini_api_key
        if key:
            text = text.replace(key, "[redacted]")
        return text[:300]

    def generate(self, profile: Profile, *, caption=None, reference_png: bytes | None = None) -> GenerationOutput:
        st = self.status()
        if not st["available"]:
            raise ProviderUnavailable(st["reason"])
        s = get_settings()
        parts: list[dict] = [{"text": build_prompt(profile)}]
        if reference_png:
            parts.append({"inlineData": {"mimeType": "image/png", "data": base64.b64encode(reference_png).decode()}})
        body = json.dumps({"contents": [{"parts": parts}],
                           "generationConfig": {"responseModalities": ["IMAGE"]}}).encode()
        req = urllib.request.Request(
            ENDPOINT.format(model=s.gemini_model), data=body, method="POST",
            headers={"Content-Type": "application/json", "x-goog-api-key": s.gemini_api_key},
        )
        try:
            with urllib.request.urlopen(req, timeout=s.hosted_timeout_s) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = json.loads(e.read().decode("utf-8")).get("error", {}).get("message", "")
            except Exception:
                pass
            raise ProviderError(self._sanitize(f"Hosted provider returned HTTP {e.code}. {detail}".strip())) from None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            reason = getattr(e, "reason", e)
            raise ProviderError(self._sanitize(f"Could not reach the hosted provider ({reason}).")) from None
        except json.JSONDecodeError:
            raise ProviderError("Hosted provider returned an unreadable response.") from None

        inline = None
        for cand in payload.get("candidates", []) or []:
            for part in (cand.get("content", {}) or {}).get("parts", []) or []:
                if "inlineData" in part:
                    inline = part["inlineData"]
                    break
            if inline:
                break
        if not inline:
            raise ProviderError("Hosted provider returned no image (it may have declined the request).")
        try:
            raw = base64.b64decode(inline.get("data", ""))
            with Image.open(io.BytesIO(raw)) as img:
                img = img.convert("RGB")
                img.thumbnail((1024, 1280))
                buf = io.BytesIO()
                img.save(buf, format="PNG")
        except (UnidentifiedImageError, OSError, ValueError):
            raise ProviderError("Hosted provider returned an image that could not be decoded.") from None
        return GenerationOutput(
            png=buf.getvalue(), svg=None, method="hosted_gemini",
            method_label=f"AI-generated (hosted: Google {s.gemini_model})", is_ai=True, model=s.gemini_model,
            notes=[{"trait": "generation", "kind": "ai",
                    "message": "AI-generated image. The model may add details that were never described; review carefully."}],
        )
