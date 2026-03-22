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
from api.database import engine, SessionLocal, Base, run_migrations
from api.routers import auth, experiments, results, chat, admin, fleet, terminal, research, queues, specs
from engine.scheduler import scheduler_loop
from engine.collector import collector_loop

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create tables + add any new columns to existing tables
Base.metadata.create_all(bind=engine)
run_migrations()


async def result_sync_loop():
    """Periodically sync parameter-golf result files into DB index."""
    from engine.sync import sync_results_to_db, sync_specs_to_db
    while True:
        try:
            db = SessionLocal()
            try:
                spec_stats = sync_specs_to_db(db)
                stats = sync_results_to_db(db)
                if any(spec_stats.get(k, 0) > 0 for k in ("indexed", "updated")):
                    logger.info(f"Spec sync: {spec_stats}")
                if stats.get("indexed", 0) > 0 or stats.get("updated", 0) > 0:
                    logger.info(f"Result sync: {stats}")
            finally:
                db.close()
        except Exception:
            logger.exception("Result sync error")
        await asyncio.sleep(300)  # every 5 minutes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start background tasks on startup, cancel on shutdown."""
    scheduler_task = asyncio.create_task(scheduler_loop())
    collector_task = asyncio.create_task(collector_loop())
    sync_task = asyncio.create_task(result_sync_loop())
    logger.info("Background tasks started: scheduler, collector, result_sync")
    yield
    scheduler_task.cancel()
    collector_task.cancel()
    sync_task.cancel()
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
app.include_router(results.router, prefix="/results", tags=["results"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(fleet.router, prefix="/fleet", tags=["fleet"])
app.include_router(terminal.router, prefix="/terminal", tags=["terminal"])
app.include_router(research.router, prefix="/research", tags=["research"])
app.include_router(specs.router, prefix="/specs", tags=["specs"])
app.include_router(queues.router, prefix="/queues", tags=["queues"])


@app.get("/health")
def health():
    return {"status": "ok"}


# Serve frontend
STATIC_DIR = Path(__file__).parent.parent / "web" / "static"


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")
