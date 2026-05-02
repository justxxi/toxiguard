from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from core.database import cleanup_events, init_db
from dashboard.metrics import router as metrics_router
from dashboard.middleware import AuthMiddleware, RateLimitMiddleware
from dashboard.routes import router

STATIC_DIR = Path(__file__).parent / "static"
log = logging.getLogger("toxiguard.dashboard")


async def _cleanup_loop():
    while True:
        await asyncio.sleep(3600)
        try:
            removed = await cleanup_events()
            log.debug("cleanup removed %s events", removed)
        except Exception:
            pass


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    task = asyncio.create_task(_cleanup_loop())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


app = FastAPI(title="toxiguard", docs_url=None, redoc_url=None, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuthMiddleware)
app.add_middleware(RateLimitMiddleware)
app.include_router(router)
app.include_router(metrics_router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("dashboard.app:app", host="127.0.0.1", port=8000, reload=False)
