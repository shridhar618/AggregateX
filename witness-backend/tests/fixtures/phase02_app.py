"""Personal, localhost-only Codex image dashboard.

Calls Codex CLI as the logged-in OS user. Requires Codex's built-in image_gen.
No OpenAI API keys and no alternative generator are used by the app.
"""

import os
import shutil
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from PIL import Image, UnidentifiedImageError

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
OUTPUTS = ROOT / "outputs"
WORK = ROOT / "work"
for directory in (OUTPUTS, WORK):
    directory.mkdir(parents=True, exist_ok=True)

CODEX_HOME = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).expanduser()
GENERATED_IMAGES = CODEX_HOME / "generated_images"
CODEX_BIN = os.environ.get("CODEX_BIN") or shutil.which("codex")
MAX_SECONDS = int(os.environ.get("CODEX_GENERATION_TIMEOUT", "600"))

app = FastAPI(title="Revelio Image Dashboard", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=STATIC), name="static")
_guard = threading.Lock()
_jobs_lock = threading.Lock()
_jobs: dict[str, "Job"] = {}


class GenerateRequest(BaseModel):
    description: str = Field(min_length=10, max_length=2500)
    style: Literal["forensic", "portrait", "illustration"] = "forensic"


@dataclass
class Job:
    job_id: str
    description: str
    style: str
    status: str = "working"
    message: str = "Starting Codex..."
    image_url: str | None = None
    created_at: float = field(default_factory=time.time)

    def public(self) -> dict:
        return {"job_id": self.job_id, "status": self.status,
                "message": self.message, "image_url": self.image_url}


def snapshot_generated() -> dict[Path, tuple[int, int]]:
    """Only the built-in Codex output folder counts as proof of image generation."""
    if not GENERATED_IMAGES.exists():
        return {}
    result = {}
    for path in GENERATED_IMAGES.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in (".png", ".webp", ".jpg", ".jpeg"):
            continue
        try:
            s = path.stat()
            result[path] = (s.st_mtime_ns, s.st_size)
        except OSError:
            continue
    return result


def validate_generated_image(path: Path) -> None:
    size = path.stat().st_size
    if not (1000 <= size <= 25 * 1024 * 1024):
        raise ValueError("Invalid generated image file size")
    try:
        with Image.open(path) as im:
            if im.format not in {"PNG", "JPEG", "WEBP"}:
                raise ValueError("Unexpected image format")
            if not (128 <= im.width <= 8192 and 128 <= im.height <= 8192):
                raise ValueError("Invalid image dimensions")
            im.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("Codex output is not a readable image") from exc


def prompt_for(description: str, style: str) -> str:
    styles = {
        "forensic": "black-and-white forensic composite pencil sketch, head-and-shoulders, neutral background, neutral expression",
        "portrait": "realistic head-and-shoulders portrait, neutral background, neutral expression",
        "illustration": "clean illustrated head-and-shoulders portrait, neutral background, neutral expression",
    }
    return f"""Use the installed $imagegen skill and its BUILT-IN image_gen tool to generate ONE raster image.

This task is to create an illustrative composite image for a personal local dashboard.
Description of subject: {description}
Visual style: {styles[style]}.
Preserve only details supplied by the description. Avoid invented identifying markers, words, labels, and watermarks.

MANDATORY: use the actual built-in image_gen tool, not PIL, SVG, screenshots, ASCII art,
local diffusion models, API calls, or a hand-created approximation.
Do not request or use an OPENAI_API_KEY, and do not switch to an API fallback.
The built-in tool normally saves the image below $CODEX_HOME/generated_images/.
If the tool is unavailable, or generation fails, explicitly say so and stop.
Do not claim that an image was generated unless an actual image_gen output exists.
Only generate one image. Report whether the built-in image_gen tool succeeded.
"""


def run_job(job_id: str) -> None:
    # The lock stays held for the entire subprocess, including image attribution.
    with _jobs_lock:
        job = _jobs[job_id]
    try:
        if not CODEX_BIN:
            raise RuntimeError("Codex CLI not found on PATH. Install it and sign in with ChatGPT.")
        starting_images = snapshot_generated()
        started_ns = time.time_ns()
        job_workdir = WORK / job_id
        job_workdir.mkdir(parents=True, exist_ok=False)

        cmd = [CODEX_BIN, "exec", "-C", str(job_workdir),
               "--sandbox", "workspace-write", "--add-dir", str(CODEX_HOME),
               "--skip-git-repo-check",
               "-o", str(job_workdir / "codex-response.txt"), "-"]
        env = os.environ.copy()
        # Never accidentally pay for a different OpenAI API route via inherited env vars.
        env.pop("OPENAI_API_KEY", None)
        env.pop("OPENAI_BASE_URL", None)
        job.message = "Codex is generating an image through its built-in tool..."
        try:
            completed = subprocess.run(cmd, input=prompt_for(job.description, job.style),
                                       text=True, capture_output=True, cwd=job_workdir,
                                       env=env, timeout=MAX_SECONDS, check=False)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"Codex exceeded the {MAX_SECONDS}-second deadline") from exc

        # Don't trust text responses: Codex can claim success without calling image_gen.
        afterward = snapshot_generated()
        candidates = []
        for p, stat in afterward.items():
            if (p not in starting_images or starting_images[p] != stat) and stat[0] >= started_ns - 2_000_000_000:
                try:
                    validate_generated_image(p)
                    candidates.append((stat[0], p))
                except (ValueError, OSError):
                    pass

        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "Codex failed")[-600:]
            raise RuntimeError("Codex exited with an error: " + detail)
        if not candidates:
            detail = (completed.stderr or completed.stdout or "No image file detected")[-450:]
            raise RuntimeError("No new image was saved in Codex's generated_images directory. "
                               "The built-in tool may be unavailable, rate-limited, or unable to save. " + detail)

        candidates.sort(reverse=True)
        selected = candidates[0][1]
        extension = selected.suffix.lower()
        if extension == ".jpeg":
            extension = ".jpg"
        destination = OUTPUTS / f"{job_id}{extension}"
        shutil.copy2(selected, destination)
        validate_generated_image(destination)
        job.image_url = f"/images/{job_id}"
        job.status = "complete"
        job.message = "Image generated and saved successfully."
    except Exception as exc:
        job.status = "failed"
        # Do not expose filesystem details or potentially sensitive prompts in HTTP responses.
        detail = str(exc).replace(str(Path.home()), "~")
        job.message = detail[:1000]
    finally:
        _guard.release()


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html", media_type="text/html")


@app.post("/api/generate", status_code=202)
def generate(request: GenerateRequest):
    if not _guard.acquire(blocking=False):
        raise HTTPException(409, "A generation is already in progress. Please try again when it finishes.")
    job_id = uuid.uuid4().hex
    job = Job(job_id=job_id, description=request.description.strip(), style=request.style)
    with _jobs_lock:
        _jobs[job_id] = job
    thread = threading.Thread(target=run_job, args=(job_id,), daemon=True)
    try:
        thread.start()
    except Exception:
        _guard.release()
        raise
    return job.public()


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Unknown job")
    return job.public()


@app.get("/images/{job_id}")
def image(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job or job.status != "complete":
        raise HTTPException(404, "Image not found")
    for extension in (".png", ".webp", ".jpg"):
        path = OUTPUTS / f"{job_id}{extension}"
        if path.is_file():
            return FileResponse(path)
    raise HTTPException(404, "Image no longer exists")


@app.get("/api/health")
def health():
    return {"codex_installed": bool(CODEX_BIN),
            "generated_images_directory": str(GENERATED_IMAGES),
            "message": "Codex image tool availability must be checked with a real generation."}
