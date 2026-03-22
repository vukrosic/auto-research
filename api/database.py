"""Database setup."""
import logging
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

from api.config import settings

logger = logging.getLogger(__name__)

engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def run_migrations():
    """Add missing columns to existing tables (SQLite doesn't do this automatically).

    Safe to call on every startup — only adds columns that don't exist yet.
    """
    inspector = inspect(engine)

    migrations = [
        ("experiments", "result_path", "VARCHAR"),
        ("experiments", "spec_id", "INTEGER"),
        ("gpus", "hourly_rate", "FLOAT DEFAULT 0.0"),
    ]

    with engine.connect() as conn:
        for table, column, col_type in migrations:
            if table not in inspector.get_table_names():
                continue
            existing = [c["name"] for c in inspector.get_columns(table)]
            if column not in existing:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
                logger.info(f"Migration: added {table}.{column}")
        conn.commit()
