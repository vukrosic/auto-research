"""Auto-Research Platform — API Entry Point"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.database import engine, Base
from api.routers import auth, experiments, competitions, results, chat, webhooks, admin

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Auto-Research", version="0.1.0")

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


@app.get("/health")
def health():
    return {"status": "ok"}
