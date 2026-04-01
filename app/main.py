import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.storage import ensure_storage_initialized
from app.api.auth_routes import router as auth_router
from app.api.campaign_routes import router as campaign_router
from app.api.dashboard_routes import router as dashboard_router
from app.jobs.scheduler import start_scheduler, shutdown_scheduler

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle events."""
    settings = get_settings()
    logger.info("Starting %s (debug=%s)", settings.APP_NAME, settings.DEBUG)

    # Prepare local file storage with seed data.
    ensure_storage_initialized()
    logger.info("File storage initialized")

    # Start background scheduler
    start_scheduler()

    yield

    # Shutdown
    shutdown_scheduler()
    logger.info("Application shutdown complete")


# ── App ──────────────────────────────────────────────────────────────────────
settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description="Campaign Live Simulation Dashboard — File Storage Backend",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all origins during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(campaign_router)
app.include_router(dashboard_router)


# ── Health Check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy", "app": settings.APP_NAME}
