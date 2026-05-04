"""
Shared test fixtures for the IRMDS test suite.

Provides pre-configured instances of the core components (event bus,
metrics collector, config) that tests can inject via pytest fixtures.
This eliminates boilerplate and ensures consistent test setup.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import suppress
from pathlib import Path

import pytest

from core.alert_manager import AlertManager
from core.command_bus import CommandBus
from core.config import IRMDSConfig, get_config
from core.event_bus import EventBus
from core.metrics_collector import MetricsCollector

TEST_RUNTIME_DIR = Path(".tmp/test_runtime")
TEST_RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("IRMDS_DATABASE_URL", f"sqlite:///{TEST_RUNTIME_DIR / 'irmds_test.db'}")


@pytest.fixture
def event_bus() -> EventBus:
    """Fresh event bus with small history for fast test iterations."""
    return EventBus(max_history=100)


@pytest.fixture
def metrics_collector() -> MetricsCollector:
    """Fresh metrics collector with small history."""
    return MetricsCollector(history_size=50)


@pytest.fixture
def config() -> IRMDSConfig:
    """Default config instance for testing.

    Uses all default values from IRMDSConfig — no .env file loaded.
    Override specific values in individual tests via monkeypatch.
    """
    # Clear the lru_cache to ensure a fresh config per test
    get_config.cache_clear()
    return IRMDSConfig()


@pytest.fixture
def alert_manager(event_bus: EventBus, config: IRMDSConfig) -> AlertManager:
    """Alert manager connected to a test event bus."""
    manager = AlertManager(event_bus, config)
    manager.start()
    yield manager
    manager.stop()


@pytest.fixture(autouse=True)
def clean_command_ledger() -> None:
    """Keep the dry-run command ledger isolated between tests."""
    get_config.cache_clear()
    db_path = CommandBus._path_from_database_url(get_config().database_url)
    if db_path.exists():
        with sqlite3.connect(db_path) as conn, suppress(sqlite3.OperationalError):
            conn.execute("DELETE FROM commands")
