"""
Shared test fixtures for the IRMDS test suite.

Provides pre-configured instances of the core components (event bus,
metrics collector, config) that tests can inject via pytest fixtures.
This eliminates boilerplate and ensures consistent test setup.
"""

from __future__ import annotations

import pytest

from core.alert_manager import AlertManager
from core.config import IRMDSConfig, get_config
from core.event_bus import EventBus
from core.metrics_collector import MetricsCollector


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
