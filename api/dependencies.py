"""
FastAPI dependency injection module.

These dependencies allow API routes to interact with the core IRMDS
components (EventBus, Registry, Database, etc.) without creating
circular imports or hard-cording global variables into the routing logic.
"""

from collections.abc import Iterator
from typing import cast

from fastapi import Request
from sqlalchemy.orm import Session

from core.alert_manager import AlertManager
from core.config import IRMDSConfig, get_config
from core.database import get_session_factory
from core.event_bus import EventBus
from core.metrics_collector import MetricsCollector
from core.plugin_registry import PluginRegistry

# Core singleton accessors. The FastAPI app state will be initialized
# in main.py lifespan, ensuring we access the active instances.


def get_event_bus(request: Request) -> EventBus:
    """Get the active EventBus instance."""
    return cast("EventBus", request.app.state.event_bus)


def get_metrics_collector(request: Request) -> MetricsCollector:
    """Get the active MetricsCollector instance."""
    return cast("MetricsCollector", request.app.state.metrics)


def get_registry(request: Request) -> PluginRegistry:
    """Get the active PluginRegistry instance."""
    return cast("PluginRegistry", request.app.state.registry)


def get_alert_manager(request: Request) -> AlertManager:
    """Get the active AlertManager instance."""
    return cast("AlertManager", request.app.state.alert_manager)


def get_app_config() -> IRMDSConfig:
    """Get the current application config."""
    return get_config()


def get_db_session() -> Iterator[Session]:
    """Provide a database session per HTTP request.

    Yields a session object that routes can use, and ensures it is
    properly closed after the route handler completes.
    """
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
