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

    # Tier limits (experiments per month)
    tier_limits: dict = {
        "test":    {"experiments": 5},
        "starter": {"experiments": 40},
        "lab":     {"experiments": -1},
        "admin":   {"experiments": -1},
    }

    # Discord bot
    discord_bot_token: str = ""
    discord_api_url: str = "http://localhost:8000/chat/"

    class Config:
        env_file = ".env"


settings = Settings()
