from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .api import api_router
from .config import Settings, load_settings, validate_environment
from .linker import Linker, LinkError
from .path_mapper import PathMapper
from .qbit_client import QbitClient
from .refresh import RefreshManager

STATIC_DIR = Path(__file__).resolve().parents[2] / "frontend" / "dist"


def create_app(settings: Settings, refresh: RefreshManager, linker: Linker,
               lifespan=None) -> FastAPI:
    app = FastAPI(title="qbit-unlinked-finder", lifespan=lifespan)
    app.state.settings = settings
    app.state.refresh = refresh
    app.state.linker = linker

    allowed = set(settings.server.allowed_hosts)

    @app.middleware("http")
    async def host_origin_check(request: Request, call_next):
        # Guards against CSRF and DNS rebinding from the user's own browser
        host = (request.headers.get("host") or "").split(":")[0]
        if host not in allowed:
            return JSONResponse(status_code=403, content={"error": {
                "code": "FORBIDDEN_HOST", "message": f"host {host} not allowed"}})
        origin = request.headers.get("origin")
        if origin and request.method not in ("GET", "HEAD", "OPTIONS"):
            if urlsplit(origin).hostname not in allowed:
                return JSONResponse(status_code=403, content={"error": {
                    "code": "FORBIDDEN_ORIGIN",
                    "message": f"origin {origin} not allowed"}})
        return await call_next(request)

    @app.exception_handler(LinkError)
    async def link_error_handler(request: Request, exc: LinkError):
        body = {"error": {"code": exc.code, "message": exc.message}}
        if exc.rolled_back is not None:
            body["rolled_back"] = exc.rolled_back
        return JSONResponse(status_code=400, content=body)

    app.include_router(api_router)

    if STATIC_DIR.is_dir():
        app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"),
                  name="assets")

        @app.get("/{path:path}")
        def spa(path: str):
            candidate = STATIC_DIR / path
            if path and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(STATIC_DIR / "index.html")

    return app


def build() -> FastAPI:
    settings = load_settings(Path(os.environ.get("QUF_CONFIG", "config.toml")))
    validate_environment(settings)
    mapper = PathMapper(
        [(m.from_, m.to) for m in settings.qbittorrent.path_mappings])
    qbit = QbitClient(settings.qbittorrent, mapper)
    refresh = RefreshManager(settings, qbit)
    linker = Linker(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        tasks = [
            asyncio.ensure_future(refresh.run_scan()),
            asyncio.ensure_future(refresh.periodic()),
            asyncio.ensure_future(refresh.poll_qbit()),
        ]
        yield
        for t in tasks:
            t.cancel()

    return create_app(settings, refresh, linker, lifespan=lifespan)
