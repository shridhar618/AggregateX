from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from ..services import speech
from .auth import AUTH

router = APIRouter(tags=["speech"])


@router.get("/speech")
def speech_status():
    return speech.status()


@router.post("/speech/transcribe", dependencies=AUTH)
async def transcribe(request: Request):
    if not speech.status()["available"]:
        raise HTTPException(503, "Local speech recognition is not installed on this server.")
    kind = request.headers.get("content-type", "").split(";")[0].strip()
    if not (kind.startswith("audio/") or kind in ("video/webm", "application/octet-stream")):
        raise HTTPException(415, "Send the recording as audio.")
    audio = await request.body()
    if not audio:
        raise HTTPException(422, "The recording is empty.")
    if len(audio) > speech.MAX_AUDIO_BYTES:
        raise HTTPException(413, "The recording is too long. Dictate in shorter parts.")
    lang = request.query_params.get("lang", "").split("-")[0].lower() or None
    if speech.MODEL.endswith(".en"):
        lang = None  # English-only models take no language hint
    return {"text": await run_in_threadpool(speech.transcribe, audio, lang)}
