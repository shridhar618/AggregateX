"""Runtime configuration from environment variables (never from the frontend)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader (KEY=VALUE lines). Existing env vars win."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv(BACKEND_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    cors_origins: list[str]
    hosted_provider: str          # "" (disabled) or "gemini"
    gemini_api_key: str
    gemini_model: str
    hosted_timeout_s: int
    local_model_path: str
    max_upload_bytes: int
    max_upload_pixels: int


def _env(name: str, default: str = "") -> str:
    """Read REVELIO_<name>, falling back to the pre-rename VERISKETCH_<name>."""
    return os.environ.get(f"REVELIO_{name}", os.environ.get(f"VERISKETCH_{name}", default))


def get_settings() -> Settings:
    data_dir = Path(_env("DATA_DIR", BACKEND_DIR / "data")).resolve()
    origins = _env(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173",
    )
    return Settings(
        data_dir=data_dir,
        cors_origins=[o.strip() for o in origins.split(",") if o.strip()],
        hosted_provider=_env("HOSTED_PROVIDER", "").strip().lower(),
        gemini_api_key=os.environ.get("GEMINI_API_KEY", "").strip(),
        gemini_model=os.environ.get("GEMINI_IMAGE_MODEL", "gemini-3-pro-image-preview").strip(),
        hosted_timeout_s=int(_env("HOSTED_TIMEOUT", "90")),
        local_model_path=_env("LOCAL_MODEL_PATH", "").strip(),
        max_upload_bytes=int(_env("MAX_UPLOAD_MB", "5")) * 1024 * 1024,
        max_upload_pixels=4096 * 4096,
    )
