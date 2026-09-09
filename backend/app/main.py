from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.auth import router as auth_router
from app.api.auth import users_router
from app.api.catalog import router as catalog_router
from app.api.orders import router as orders_router
from app.api.sync_runs import router as sync_runs_router
from app.config import get_settings
from app.logging_config import configure_logging

VERSION = "0.1.1"


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    yield


app = FastAPI(
    title="UniOps API",
    version=VERSION,
    description="Operational system of record for UniGreen. EasyBooks remains accounting SoR.",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    # The session cookie only travels on cross-origin calls when credentials are
    # allowed. It stays paired with an explicit origin list, never a wildcard.
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)
app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(catalog_router, prefix="/api")
app.include_router(orders_router, prefix="/api")
app.include_router(sync_runs_router, prefix="/api")


@app.get("/api/health", tags=["health"])
async def health() -> dict[str, str]:
    """Unauthenticated on purpose, so a monitor can reach it. Reports no data."""
    return {"status": "ok", "version": VERSION}


def _mount_frontend() -> None:
    """Serve the built SPA from this process when asked.

    This is what makes an internal deployment one door instead of two. The
    bundle itself stays readable without a session because the sign-in screen
    has to load before anyone can sign in; it contains no customer data, and
    every API route it calls is guarded.
    """
    dist = Path(settings.frontend_dist_path)
    if not dist.is_dir():
        raise RuntimeError(
            f"UNIOPS_SERVE_FRONTEND is on but {dist} does not exist. "
            "Run `npm run build` in frontend/ first."
        )
    app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")


if settings.serve_frontend:
    _mount_frontend()
