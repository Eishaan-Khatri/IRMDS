"""
Real-time metrics collector for IRMDS.

Each domain module pushes its current metrics (FPS, latency, anomaly scores,
counts) into this collector every processing cycle. The API and dashboard
read from it to power live gauges and charts.

Design:
    - Thread-safe: modules push from background threads, API reads from
      the main asyncio thread.
    - Rolling history: keeps the last N snapshots per module for sparkline
      charts and rolling statistics (mean, min, max).
    - Lightweight: no database writes — purely in-memory. The collector
      is ephemeral by design; historical metrics go into SQLite via
      the alert manager if they represent anomalies.

Usage:
    from core.metrics_collector import MetricsCollector

    collector = MetricsCollector(history_size=300)

    # Module pushes metrics every frame
    collector.push("visual", {"fps": 24.5, "latency_ms": 40.8, "active_tracks": 3})

    # API reads latest metrics
    latest = collector.get_latest("visual")
    # → {"fps": 24.5, "latency_ms": 40.8, "active_tracks": 3}

    # Dashboard reads rolling stats
    stats = collector.get_rolling_stats("visual")
    # → {"fps": {"current": 24.5, "mean": 23.8, "min": 20.1, "max": 26.2}, ...}
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModuleMetrics:
    """Metrics state for a single module.

    Stores the latest snapshot plus a rolling history for computing
    time-windowed statistics.
    """

    latest: dict[str, Any] = field(default_factory=dict)
    history: deque[dict[str, Any]] = field(default_factory=lambda: deque(maxlen=300))
    last_updated: float = 0.0  # Unix timestamp of last push
    push_count: int = 0


class MetricsCollector:
    """Thread-safe, in-memory metrics store with rolling statistics.

    Each module is identified by a string key (e.g., "visual", "network").
    Metrics are arbitrary string→number dicts — the collector doesn't
    enforce a schema, so modules can evolve their metrics independently.
    """

    def __init__(self, history_size: int = 300):
        """Initialize the collector.

        Args:
            history_size: Number of snapshots to retain per module.
                          At 30 FPS, 300 snapshots ≈ 10 seconds of history.
        """
        self._modules: dict[str, ModuleMetrics] = {}
        self._history_size = history_size
        self._lock = threading.Lock()

    def push(self, module_id: str, metrics: dict[str, Any]) -> None:
        """Record a new metrics snapshot for a module.

        Called by modules on every processing cycle (every frame, every
        tick, every poll). The snapshot replaces `latest` and is also
        appended to the rolling history.

        Args:
            module_id: Module identifier (e.g., "visual").
            metrics:   Dict of metric_name → numeric value.
        """
        with self._lock:
            if module_id not in self._modules:
                self._modules[module_id] = ModuleMetrics(
                    history=deque(maxlen=self._history_size)
                )
            state = self._modules[module_id]
            state.latest = metrics.copy()
            state.history.append(metrics.copy())
            state.last_updated = time.time()
            state.push_count += 1

    def get_latest(self, module_id: str) -> dict[str, Any]:
        """Get the most recent metrics snapshot for a module.

        Returns an empty dict if the module hasn't pushed any metrics yet.
        """
        with self._lock:
            state = self._modules.get(module_id)
            if not state:
                return {}
            return {
                **state.latest,
                "_last_updated": state.last_updated,
                "_push_count": state.push_count,
            }

    def get_all_latest(self) -> dict[str, dict[str, Any]]:
        """Get latest metrics from all modules.

        Returns:
            Dict of module_id → latest metrics dict.
        """
        with self._lock:
            return {
                module_id: {
                    **state.latest,
                    "_last_updated": state.last_updated,
                    "_push_count": state.push_count,
                }
                for module_id, state in self._modules.items()
            }

    def get_rolling_stats(self, module_id: str) -> dict[str, dict[str, float]]:
        """Compute rolling statistics from the metrics history.

        For each numeric metric, returns current value, mean, min, and max
        over the retained history window.

        Returns:
            Dict of metric_name → {"current": ..., "mean": ..., "min": ..., "max": ...}
            Returns empty dict if no history exists.
        """
        with self._lock:
            state = self._modules.get(module_id)
            if not state or not state.history:
                return {}
            history = list(state.history)

        # Collect all numeric keys from history
        stats: dict[str, dict[str, float]] = {}
        if not history:
            return stats

        # Use the latest snapshot's keys as the reference set
        for key in history[-1]:
            values = []
            for snapshot in history:
                val = snapshot.get(key)
                if isinstance(val, (int, float)):
                    values.append(val)
            if values:
                stats[key] = {
                    "current": values[-1],
                    "mean": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                }

        return stats

    def get_history(self, module_id: str, limit: int = 60) -> list[dict[str, Any]]:
        """Get raw metrics history for a module (for sparkline charts).

        Args:
            module_id: Module identifier.
            limit:     Max number of snapshots to return (most recent).

        Returns:
            List of metrics dicts, oldest first.
        """
        with self._lock:
            state = self._modules.get(module_id)
            if not state:
                return []
            return list(state.history)[-limit:]

    def clear(self, module_id: str | None = None) -> None:
        """Clear metrics for a specific module or all modules.

        Called when a module is stopped to reset its metrics state.
        """
        with self._lock:
            if module_id:
                self._modules.pop(module_id, None)
            else:
                self._modules.clear()
