"""Platform configuration."""
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./auto_research.db"

    # Auth
    secret_key: str = "change-me-in-production"
    magic_link_expiry_minutes: int = 30

    # Claude API (for AI agents)
    anthropic_api_key: str = ""

    # Research engine
    parameter_golf_path: str = str(Path.home() / "parameter-golf")

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Tier limits (runs per month)
    tier_limits: dict = {
        "starter": {"explore": 50, "validate": 0, "full": 0, "concurrent": 1},
        "researcher": {"explore": 200, "validate": 20, "full": 0, "concurrent": 3},
        "pro": {"explore": -1, "validate": 100, "full": 5, "concurrent": 5},  # -1 = unlimited
        "team": {"explore": -1, "validate": 100, "full": 5, "concurrent": 5},
        "admin": {"explore": -1, "validate": -1, "full": -1, "concurrent": -1},
    }

    class Config:
        env_file = ".env"


settings = Settings()
