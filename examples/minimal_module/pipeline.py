"""
Minimal example module for IRMDS plugin authors.

This file is intentionally small. Runtime modules belong under modules/<id>/,
but this example shows the shape a plugin should follow before being copied into
the runtime module tree.
"""

from __future__ import annotations

import time
from typing import Any

from core.base_module import BaseModule, ModuleStatus
from core.event_bus import Event, Severity


class MinimalPipeline(BaseModule):
    """Smallest useful module that emits events and metrics."""

    module_id = "minimal"
    display_name = "Minimal Example Module"
    version = "0.1.0"

    def _run(self) -> None:
        heartbeat_count = 0
        while self._running.is_set():
            heartbeat_count += 1
            self.metrics.push(self.module_id, {"heartbeat_count": heartbeat_count})
            self.event_bus.publish(
                Event(
                    module=self.module_id,
                    type="MINIMAL_HEARTBEAT",
                    severity=Severity.INFO,
                    data={"heartbeat_count": heartbeat_count},
                )
            )
            time.sleep(0.1)

    def health_check(self) -> dict[str, Any]:
        return {
            "healthy": self.status == ModuleStatus.RUNNING,
            "status": self.status.value,
            "details": {"thread_alive": bool(self._thread and self._thread.is_alive())},
        }

    def get_metrics(self) -> dict[str, Any]:
        return self.metrics.get_latest(self.module_id) or {}
