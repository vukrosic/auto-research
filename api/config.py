"""Platform configuration."""
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./auto_research.db"

    # Auth
    secret_key: str = ""
    magic_link_expiry_minutes: int = 30

    # Novita AI (for chat + AI agents)
    novita_api_key: str = ""
    novita_base_url: str = "https://api.novita.ai/openai"
    chat_model: str = "xiaomimimo/mimo-v2-flash"

    # Research engine
    parameter_golf_path: str = str(Path.home() / "parameter-golf")

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    # Social posts: 1 per N completed experiments
    posts_per_experiments: int = 50

    # Tier limits (runs per month) — solo tiers, no team
    tier_limits: dict = {
        "starter": {"explore": 500, "validate": 0, "full": 0, "concurrent": 1},
        "researcher": {"explore": 2000, "validate": 200, "full": 0, "concurrent": 3},
        "pro": {"explore": 5000, "validate": 1000, "full": 50, "concurrent": 5},
        "admin": {"explore": -1, "validate": -1, "full": -1, "concurrent": -1},
    }

    class Config:
        env_file = ".env"


settings = Settings()
