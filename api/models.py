"""Database models."""
import secrets
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship

from api.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, default="")
    tier = Column(String, default="starter")  # starter, researcher, pro, team, admin
    api_key = Column(String, unique=True, default=lambda: f"ar_{secrets.token_hex(24)}")
    skool_id = Column(String, nullable=True)  # Link to Skool membership

    # Usage tracking (reset monthly)
    explore_runs_used = Column(Integer, default=0)
    validate_runs_used = Column(Integer, default=0)
    full_runs_used = Column(Integer, default=0)
    usage_reset_at = Column(DateTime, default=utcnow)

    # BYOG credentials (encrypted in production)
    gpu_credentials = Column(Text, nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utcnow)
    last_login = Column(DateTime, nullable=True)

    experiments = relationship("Experiment", back_populates="user")


class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    template = Column(String, default="parameter_golf")
    stage = Column(String, default="explore")  # explore, validate, full

    # Config overrides (JSON string)
    config_overrides = Column(Text, default="{}")
    steps = Column(Integer, default=500)

    # Status
    status = Column(String, default="queued")  # queued, running, completed, failed, cancelled
    gpu_name = Column(String, nullable=True)
    current_step = Column(Integer, default=0)
    current_loss = Column(Float, nullable=True)
    val_bpb = Column(Float, nullable=True)

    # Competition link
    competition_id = Column(Integer, ForeignKey("competitions.id"), nullable=True)

    # Timestamps
    queued_at = Column(DateTime, default=utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="experiments")
    competition = relationship("Competition", back_populates="experiments")


class Competition(Base):
    __tablename__ = "competitions"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    template = Column(String, default="parameter_golf")
    rules = Column(Text, default="")

    # Scoring
    metric = Column(String, default="val_bpb")  # lower = better
    max_steps = Column(Integer, default=13780)
    max_params = Column(Integer, default=16_000_000)  # 16MB

    # Prizes
    prize_description = Column(Text, default="")
    sponsor = Column(String, nullable=True)

    # Lifecycle
    status = Column(String, default="upcoming")  # upcoming, active, scoring, completed
    starts_at = Column(DateTime, nullable=True)
    ends_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    experiments = relationship("Experiment", back_populates="competition")


class GPU(Base):
    __tablename__ = "gpus"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    host = Column(String, nullable=False)  # e.g. proxy.us-ca-6.gpu-instance.novita.ai
    port = Column(Integer, default=22)
    user = Column(String, default="root")
    password = Column(String, nullable=True)  # TODO: encrypt in production
    ssh_key = Column(Text, nullable=True)

    # Status
    status = Column(String, default="unknown")  # online, offline, training, idle, unknown
    current_experiment = Column(String, nullable=True)
    current_step = Column(Integer, nullable=True)
    gpu_utilization = Column(Float, nullable=True)
    gpu_temp = Column(Float, nullable=True)

    # Config
    repo_path = Column(String, default="/root/parameter-golf")
    added_at = Column(DateTime, default=utcnow)
    last_seen = Column(DateTime, nullable=True)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String, nullable=False)  # user / assistant
    content = Column(Text, nullable=False)

    # Token usage (assistant messages only)
    input_tokens = Column(Integer, default=0)
    cache_read_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    latency_ms = Column(Integer, default=0)

    created_at = Column(DateTime, default=utcnow)


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=True)
    resolved_by_ai = Column(Boolean, default=False)
    needs_human = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)
    resolved_at = Column(DateTime, nullable=True)
