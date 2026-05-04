"""
Manual smoke test for the IRMDS module registry.

This script is intentionally not part of CI because it can start local sources
such as webcam/model-backed visual processing. Use the pytest suite for CI-safe
verification.
"""

import time

from core.alert_manager import AlertManager
from core.config import get_config
from core.event_bus import EventBus
from core.metrics_collector import MetricsCollector
from core.plugin_registry import PluginRegistry


def main() -> None:
    """Discover modules, start them briefly, print metrics, and stop."""
    config = get_config()
    config.finance_replay_speed = 100.0

    event_bus = EventBus()
    metrics = MetricsCollector()
    alert_manager = AlertManager(event_bus, config)
    alert_manager.start()

    registry = PluginRegistry(event_bus, metrics, config)
    modules = registry.discover()
    print(f"Discovered modules: {modules}")

    if "timeseries" not in modules or "infrastructure" not in modules:
        print("[ERROR] Missing expected phase-5 modules.")
        return

    print("Starting modules...")
    registry.start_all()

    print("Waiting 20 seconds for processing...")
    time.sleep(20)

    print("\nLatest metrics:")
    for module_id in modules:
        module_metrics = registry.get_module(module_id).get_metrics()
        print(f"[{module_id}]: {module_metrics}")

    print("\nRecent alerts:")
    for alert in alert_manager.get_alerts():
        print(f"[{alert['module']}] {alert['type']}: {alert['severity']}")

    print("\nStopping modules...")
    registry.stop_all()
    alert_manager.stop()
    print("Done.")


if __name__ == "__main__":
    main()
