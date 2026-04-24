"""
Database configuration and SQLAlchemy ORM models.

IRMDS uses SQLAlchemy 2.0 to support both SQLite (default/development)
and PostgreSQL (production) with zero code changes.

The ORM models represent:
    1. Alert: A processed, deduplicated event that passed the AlertManager.
    2. Session: A bounded monitoring period with its summary statistics.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import JSON, Float, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from core.config import get_config
from core.logger import get_logger

log = get_logger("database")


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    # Use a custom JSON serializer for the JSON columns to ensure
    # Pydantic models / non-standard types don't break serialization
    type_annotation_map = {dict[str, Any]: JSON}


# ─────────────────────────────────────────────────────────────
# ORM Models
# ─────────────────────────────────────────────────────────────


class SessionRecord(Base):
    """Database representation of a monitoring session."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class AlertRecord(Base):
    """Database representation of a processed alert."""

    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    timestamp: Mapped[str] = mapped_column(String, nullable=False, index=True)
    module: Mapped[str] = mapped_column(String, nullable=False, index=True)
    type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String, nullable=False, index=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    escalated: Mapped[bool] = mapped_column(default=False)
    session_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)


# ─────────────────────────────────────────────────────────────
# Engine & Session Configuration
# ─────────────────────────────────────────────────────────────

# We lazily initialize these so that if config changes during tests,
# they aren't prematurely bound.
_engine = None
_SessionFactory = None


def get_engine():
    """Get or create the SQLAlchemy engine."""
    global _engine
    if _engine is None:
        config = get_config()
        # Ensure SQLite works in a multi-threaded FastAPI / Background thread environment
        connect_args = {"check_same_thread": False} if "sqlite" in config.database_url else {}
        
        _engine = create_engine(
            config.database_url,
            connect_args=connect_args,
            # Uncomment for SQL query logging during debug:
            # echo=True, 
        )
    return _engine


def get_session_factory() -> sessionmaker:
    """Get the session factory for creating database sessions."""
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
        )
    return _SessionFactory


def init_db() -> None:
    """Create all tables in the database if they don't exist.

    This is called automatically during API startup.
    """
    engine = get_engine()
    try:
        Base.metadata.create_all(bind=engine)
        log.info("database_initialized", url=get_config().database_url)
    except Exception as exc:
        log.critical("database_initialization_failed", error=str(exc))
        raise
