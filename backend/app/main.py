"""Revelio — local API server.

Run:  backend/.venv/bin/uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
Binds to localhost by default; it is not exposed to the network.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import __version__
from .api import auth, sketches, speech, system, traits, witness_gateway
from .config import get_settings
from .database import init_db
from .providers.base import ProviderError, ProviderUnavailable
from .services.sketch_service import NotFound
from .services.uploads import UploadError

log = logging.getLogger("revelio")


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Revelio", version=__version__, lifespan=_lifespan,
                  description="From Witness Description to Forensic Sketch — local API")
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["Content-Type"],
    )

    @app.exception_handler(NotFound)
    async def _nf(_: Request, exc: NotFound):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(UploadError)
    async def _upload(_: Request, exc: UploadError):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(ProviderUnavailable)
    async def _unavail(_: Request, exc: ProviderUnavailable):
        return JSONResponse(status_code=409, content={"detail": str(exc), "provider_error": True, "offline_available": True})

    @app.exception_handler(ProviderError)
    async def _perr(_: Request, exc: ProviderError):
        return JSONResponse(status_code=502, content={"detail": str(exc), "provider_error": True, "offline_available": True})

    @app.exception_handler(ValueError)
    async def _value(_: Request, exc: ValueError):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        errors = []
        for e in exc.errors():
            loc = ".".join(str(p) for p in e.get("loc", []) if p != "body")
            msg = str(e.get("msg", "Invalid value")).removeprefix("Value error, ")
            errors.append(f"{loc}: {msg}" if loc else msg)
        return JSONResponse(status_code=422, content={"detail": errors[0] if errors else "Invalid request", "errors": errors})

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):  # never leak internals or secrets
        log.exception("Unhandled error: %s", type(exc).__name__)
        return JSONResponse(status_code=500, content={"detail": "Internal error. See the server log."})

    for r in (auth.router, system.router, traits.router, sketches.router, speech.router):
        app.include_router(r, prefix="/api")
    app.include_router(witness_gateway.router)
    return app


app = create_app()
