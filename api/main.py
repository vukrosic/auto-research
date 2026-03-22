"""Auto-Research Platform — API Entry Point"""
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.config import settings
from api.database import engine, Base
from api.routers import auth, experiments, competitions, results, chat, webhooks, admin, fleet, terminal
from engine.scheduler import scheduler_loop
from engine.collector import collector_loop

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create tables
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start background tasks on startup, cancel on shutdown."""
    scheduler_task = asyncio.create_task(scheduler_loop())
    collector_task = asyncio.create_task(collector_loop())
    logger.info("Background tasks started: scheduler, collector")
    yield
    scheduler_task.cancel()
    collector_task.cancel()
    logger.info("Background tasks stopped")


app = FastAPI(title="Auto-Research", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(experiments.router, prefix="/experiments", tags=["experiments"])
app.include_router(competitions.router, prefix="/competitions", tags=["competitions"])
app.include_router(results.router, prefix="/results", tags=["results"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(fleet.router, prefix="/fleet", tags=["fleet"])
app.include_router(terminal.router, prefix="/terminal", tags=["terminal"])


@app.get("/health")
def health():
    return {"status": "ok"}


# Serve frontend
STATIC_DIR = Path(__file__).parent.parent / "web" / "static"


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")
