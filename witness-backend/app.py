"""Personal, localhost-only Codex image dashboard.

Calls Codex CLI as the logged-in OS user. Requires Codex's built-in image_gen.
No OpenAI API keys and no alternative generator are used by the app.
"""

import os
import shutil
import sqlite3
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from PIL import Image, UnidentifiedImageError

import case_store
case_store.initialize()

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
OUTPUTS = Path(os.environ.get("WITNESSTRACE_OUTPUTS_DIR", str(ROOT / "outputs"))).expanduser().resolve()
WORK = Path(os.environ.get("WITNESSTRACE_WORK_DIR", str(ROOT / "work"))).expanduser().resolve()
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
    case_id: str | None = None
    case_revision: int | None = None
    workspace: Literal["text", "lab"] = "text"


@dataclass
class Job:
    job_id: str
    description: str
    style: str
    case_id: str | None = None
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
               "--sandbox", "workspace-write", "--skip-git-repo-check",
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


def durable_run_job(job_id: str) -> None:
    # The proven generation adapter below remains unchanged.
    run_job(job_id)
    job = _jobs[job_id]
    try:
        case_store.finish_job(job, OUTPUTS)
    except Exception:
        job.status = "failed"
        job.image_url = None
        job.message = "Image result could not be recorded. Original output, if any, is retained."
        try:
            case_store.finish_job(job, OUTPUTS)
        except Exception:
            pass  # A DB outage remains visible as an unresolved working record until restart.


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html", media_type="text/html")


@app.post("/api/generate", status_code=202)
def generate(request: GenerateRequest):
    if not _guard.acquire(blocking=False):
        raise HTTPException(409, "A generation is already in progress. Please try again when it finishes.")
    job_id = uuid.uuid4().hex
    job = Job(job_id=job_id, description=request.description.strip(), style=request.style, case_id=request.case_id)
    try:
        case_store.start_job(job, request.case_id, request.case_revision, request.workspace)
    except Exception:
        _guard.release()
        raise
    with _jobs_lock:
        _jobs[job_id] = job
    thread = threading.Thread(target=durable_run_job, args=(job_id,), daemon=True)
    try:
        thread.start()
    except Exception:
        job.status = "failed"
        job.message = "Unable to start generation worker"
        try:
            case_store.finish_job(job, OUTPUTS)
        finally:
            _guard.release()
        raise
    return case_store.job_status(job_id)


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    persisted = case_store.job_status(job_id)
    if persisted:
        return persisted
    raise HTTPException(404, "Unknown job")


@app.get("/images/{job_id}")
def image(job_id: str):
    with _jobs_lock:
        job = _jobs.get(job_id)
    durable_path = case_store.image_path(job_id)
    if durable_path:
        return FileResponse(durable_path)
    if not job or job.status != "complete":
        persisted = case_store.job_status(job_id)
        if persisted and persisted["status"] != "complete":
            raise HTTPException(404, "Image not found")
        # Pre-case outputs have UUID filenames; retain their existing stable links.
        case_store.identifier(job_id)
    for extension in (".png", ".webp", ".jpg"):
        path = OUTPUTS / f"{job_id}{extension}"
        if path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(OUTPUTS.resolve()):
            return FileResponse(path)
    raise HTTPException(404, "Image no longer exists")


@app.get("/api/health")
def health():
    return {"codex_installed": bool(CODEX_BIN),
            "generated_images_directory": str(GENERATED_IMAGES),
            "message": "Codex image tool availability must be checked with a real generation."}


@app.get("/api/cases")
def cases():
    return case_store.list_cases()


@app.post("/api/cases", status_code=201)
def create_case(request: case_store.NewCase):
    return case_store.create(request)


@app.get("/api/cases/{case_id}")
def read_case(case_id: str):
    return case_store.get(case_id)


@app.put("/api/cases/{case_id}")
def save_case(case_id: str, request: case_store.SaveCase):
    return case_store.save(case_id, request)


@app.post("/api/cases/{case_id}/freeze")
def freeze_case(case_id: str, request: case_store.Freeze):
    return case_store.freeze(case_id, request)


@app.post("/api/cases/{case_id}/clarifications", status_code=201)
def append_clarification(case_id: str, request: case_store.Clarification):
    return case_store.append(case_id, request)


@app.get("/api/lab-schema")
def lab_schema():
    from lab_schema import GROUPS
    return {"groups": GROUPS}


@app.post("/api/cases/{case_id}/prompt-preview")
def preview_case_prompt(case_id: str, request: case_store.Draft):
    return case_store.prompt_preview(case_id, request)


@app.post('/api/cases/{case_id}/selection')
def select_case_version(case_id: str, request: case_store.Selection):
    return case_store.select_version(case_id, request)

@app.post('/api/cases/{case_id}/refinement-preview')
def preview_refinement(case_id: str, request: case_store.Refinement):
    return case_store.refinement_preview(case_id, request)

@app.post('/api/cases/{case_id}/refine',status_code=202)
def refine(case_id: str, request: case_store.Refinement):
    existing=case_store.previous_request(case_id,request)
    if existing:
        return case_store.job_status(existing)
    if not _guard.acquire(blocking=False):
        raise HTTPException(409,'A generation is already in progress. Retry when it finishes.')
    job=Job(job_id=uuid.uuid4().hex,description='Refinement request',style=request.draft.style,case_id=case_id)
    try:
        # Recheck after acquiring the process guard for simultaneous identical requests.
        existing=case_store.previous_request(case_id,request)
        if existing:
            _guard.release()
            return case_store.job_status(existing)
        case_store.start_job(job,case_id,request.revision,'refinement',request)
        with _jobs_lock:
            _jobs[job.job_id]=job
        threading.Thread(target=durable_run_job,args=(job.job_id,),daemon=True).start()
    except Exception:
        job.status='failed';job.message='Unable to start generation worker'
        try:
            case_store.finish_job(job,OUTPUTS)
        finally:
            _guard.release()
        raise
    return case_store.job_status(job.job_id)


# Local editing is deliberately independent of the authenticated AI generation adapter.
import sketch_store

@app.get('/api/cases/{case_id}/versions/{version_id}/sketch')
def read_sketch(case_id: str, version_id: str):
    return sketch_store.open_project(case_id,version_id)

@app.post('/api/cases/{case_id}/local-edits',status_code=201)
def save_sketch(case_id: str, request: sketch_store.SaveEdit):
    try:
        return sketch_store.save_edit(case_id,request)
    except (OSError,sqlite3.Error):
        raise HTTPException(503,'Local image could not be saved. Your browser draft is retained; retry Save Edited Version.') from None


import enhance_store

@app.post('/api/cases/{case_id}/imports',status_code=201)
def import_source(case_id: str, request: enhance_store.ImportImage):
    try:
        return enhance_store.import_image(case_id,request)
    except (OSError,sqlite3.Error):
        raise HTTPException(503,'Source image could not be saved. Retry the import.') from None

@app.get('/api/cases/{case_id}/versions/{version_id}/enhance')
def read_enhancement(case_id: str, version_id: str):
    return enhance_store.source(case_id,version_id)

@app.get('/api/cases/{case_id}/versions/{version_id}/pixels')
def read_canonical_pixels(case_id: str, version_id: str):
    return Response(enhance_store.png_bytes(enhance_store.canonical_image(case_id,version_id)),media_type='image/png',headers={'Cache-Control':'no-store'})

@app.post('/api/cases/{case_id}/enhancements',status_code=201)
def save_enhancement(case_id: str, request: enhance_store.SaveEnhancement):
    try:
        return enhance_store.save_enhancement(case_id,request)
    except (OSError,sqlite3.Error):
        raise HTTPException(503,'Enhanced image could not be saved. Preview retained; retry Save Enhanced Version.') from None

@app.get('/api/enhance-schema')
def enhancement_schema():
    return enhance_store.schema()


import multiview_store

@app.post('/api/cases/{case_id}/multiview-preview')
def preview_multiview(case_id: str, request: multiview_store.Request):
    return multiview_store.preview(case_id,request)

@app.get('/api/cases/{case_id}/multiview')
def multiview_history(case_id: str):
    return multiview_store.list_sheets(case_id)

@app.post('/api/cases/{case_id}/multiview',status_code=202)
def generate_multiview(case_id: str, request: multiview_store.Request):
    existing=multiview_store.previous(case_id,request)
    if existing:return case_store.job_status(existing)
    if not _guard.acquire(blocking=False):raise HTTPException(409,'A generation is already in progress. Retry after it finishes.')
    job=Job(job_id=uuid.uuid4().hex,description='Experimental multi-view request',style=request.draft.style,case_id=case_id)
    try:
        existing=multiview_store.previous(case_id,request)
        if existing:
            _guard.release();return case_store.job_status(existing)
        case_store.start_job(job,case_id,request.revision,'multiview',multiview=request)
        with _jobs_lock:_jobs[job.job_id]=job
        threading.Thread(target=durable_run_job,args=(job.job_id,),daemon=True).start()
    except Exception:
        job.status='failed';job.message='Unable to start generation worker'
        try:case_store.finish_job(job,OUTPUTS)
        finally:_guard.release()
        raise
    return case_store.job_status(job.job_id)

@app.post('/api/cases/{case_id}/views/{version_id}/layouts',status_code=201)
def review_multiview_layout(case_id: str, version_id: str, request: multiview_store.Layout):
    return multiview_store.save_layout(case_id,version_id,request)

@app.get('/api/cases/{case_id}/views/{version_id}/layouts/{layout_id}/{angle}.png')
def multiview_panel(case_id: str, version_id: str, layout_id: str, angle: str):
    data=multiview_store.crop_bytes(case_id,version_id,layout_id,angle)
    return Response(data,media_type='image/png',headers={'Content-Disposition':f'attachment; filename="witnesstrace-{case_id}-{version_id}-{angle}.png"'})

import report_store

@app.post('/api/cases/{case_id}/reports',status_code=201)
def create_report(case_id: str, request: report_store.Request):
    try:
        return report_store.create(case_id,request)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503,'Report could not be created. No successful export was recorded; retry or download the selected image.') from None

@app.get('/api/cases/{case_id}/reports')
def report_history(case_id: str):
    return report_store.list_reports(case_id)

@app.get('/api/cases/{case_id}/versions/{version_id}/export.png')
def export_version_png(case_id: str, version_id: str):
    return Response(report_store.png_export(case_id,version_id),media_type='image/png',headers={'Content-Disposition':f'attachment; filename="witnesstrace-{case_id}-{version_id}.png"'})

@app.get('/api/cases/{case_id}/reports/{report_id}/preview')
def report_preview(case_id: str, report_id: str):
    return Response(report_store.preview_html(case_id,report_id),media_type='text/html',headers={'Content-Security-Policy':"default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; frame-ancestors 'self'"})

@app.get('/api/cases/{case_id}/reports/{report_id}/{extension}')
def download_report(case_id: str, report_id: str, extension: str, inline: bool=False):
    path,metadata=report_store.read_file(case_id,report_id,extension)
    return FileResponse(path,media_type={'pdf':'application/pdf','json':'application/json','png':'image/png'}[extension],filename=None if inline else metadata['filename'],headers={'Cache-Control':'no-store'})

@app.get('/api/cases/{case_id}/versions/{version_id}/export.json')
def export_case_metadata(case_id: str, version_id: str):
    import json
    png=report_store.png_export(case_id,version_id)
    data=report_store.snapshot(case_id,version_id,uuid.uuid4().hex,case_store.now(),png)
    return Response(json.dumps(data,ensure_ascii=False,indent=2).encode('utf-8'),media_type='application/json',headers={'Content-Disposition':f'attachment; filename="witnesstrace-{case_id}-{version_id}.json"','Cache-Control':'no-store'})

# Accessible in React only through the authenticated Revelio gateway.
import integrity_store
integrity_store.initialize()

@app.get('/api/cases/{case_id}/versions/{version_id}/integrity')
def image_integrity(case_id: str, version_id: str):
    return integrity_store.verify(case_id, version_id)

@app.post('/api/cases/{case_id}/versions/{version_id}/integrity')
def register_image_integrity(case_id: str, version_id: str, request: integrity_store.Registration):
    return integrity_store.register(case_id, version_id, request)
