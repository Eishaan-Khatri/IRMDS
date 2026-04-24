"""
IRMDS Core — Framework layer providing shared infrastructure.

This package contains the foundational components that all domain modules
depend on: configuration, event routing, alert management, logging,
metrics collection, and the plugin system.

Architecture:
    BaseModule (contract) → PluginRegistry (discovery) → EventBus (routing)
    → AlertManager (classification) → MetricsCollector (observability)
"""

from core.config import get_config
from core.event_bus import EventBus
from core.exceptions import IRMDSError

__all__ = ["EventBus", "IRMDSError", "get_config"]
