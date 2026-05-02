"""
Quick sanity check for the newly implemented modules.
"""

import time
from core.config import get_config
from core.event_bus import EventBus
from core.metrics_collector import MetricsCollector
from core.plugin_registry import PluginRegistry
from core.alert_manager import AlertManager

def main():
    config = get_config()
    event_bus = EventBus()
    metrics = MetricsCollector()
    alert_manager = AlertManager(event_bus, config)
    alert_manager.start()
    
    registry = PluginRegistry(event_bus, metrics, config)
    modules = registry.discover()
    print(f"Discovered modules: {modules}")
    
    if "timeseries" in modules and "infrastructure" in modules:
        print("[OK] New modules discovered.")
    else:
        print("❌ Missing modules.")
        return

    print("Starting modules...")
    config.finance_replay_speed = 100.0
    registry.start_all()
    
    print("Waiting 20 seconds for processing...")
    time.sleep(20)  # Wait for some processing
    
    print("\nLatest Metrics:")
    for mid in modules:
        m = registry.get_module(mid).get_metrics()
        print(f"[{mid}]: {m}")

    print("\nRecent Alerts:")
    alerts = alert_manager.get_alerts()
    for a in alerts:
        print(f"[{a['module']}] {a['type']}: {a['severity']}")

    print("\nStopping modules...")
    registry.stop_all()
    alert_manager.stop()
    print("Done.")

if __name__ == "__main__":
    main()
