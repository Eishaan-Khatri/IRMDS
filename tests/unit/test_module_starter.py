"""
Starter-module contract tests.

This test creates a temporary module package under the existing `modules`
namespace and verifies that PluginRegistry can discover and run it. That keeps
the public starter guide honest without shipping the example as a runtime
module.
"""

from __future__ import annotations

import sys
import textwrap
import time

import modules
from core.base_module import ModuleStatus
from core.config import IRMDSConfig
from core.event_bus import EventBus
from core.metrics_collector import MetricsCollector
from core.plugin_registry import PluginRegistry


def test_starter_style_module_can_be_discovered_and_started(tmp_path, monkeypatch):
    """A BaseModule-style plugin under modules/*/pipeline.py should be discoverable."""
    modules_root = tmp_path / "modules"
    starter_pkg = modules_root / "starter_example"
    starter_pkg.mkdir(parents=True)
    (starter_pkg / "__init__.py").write_text("", encoding="utf-8")
    (starter_pkg / "pipeline.py").write_text(
        textwrap.dedent(
            """
            from __future__ import annotations

            import time
            from typing import Any

            from core.base_module import BaseModule, ModuleStatus
            from core.event_bus import Event, Severity


            class StarterExamplePipeline(BaseModule):
                module_id = "starter_example"
                display_name = "Starter Example"
                version = "0.1.0"

                def _run(self) -> None:
                    count = 0
                    while self._running.is_set():
                        count += 1
                        self.metrics.push(self.module_id, {"heartbeat_count": count})
                        self.event_bus.publish(
                            Event(
                                module=self.module_id,
                                type="STARTER_HEARTBEAT",
                                severity=Severity.INFO,
                                data={"heartbeat_count": count},
                            )
                        )
                        time.sleep(0.01)

                def health_check(self) -> dict[str, Any]:
                    return {
                        "healthy": self.status == ModuleStatus.RUNNING,
                        "status": self.status.value,
                        "details": {},
                    }

                def get_metrics(self) -> dict[str, Any]:
                    return self.metrics.get_latest(self.module_id) or {}
            """
        ),
        encoding="utf-8",
    )

    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr(modules, "__path__", [str(modules_root)])
    sys.modules.pop("modules.starter_example", None)
    sys.modules.pop("modules.starter_example.pipeline", None)

    event_bus = EventBus(max_history=20)
    metrics = MetricsCollector()
    registry = PluginRegistry(event_bus=event_bus, metrics=metrics, config=IRMDSConfig())

    discovered = registry.discover()
    assert discovered == ["starter_example"]

    registry.start_module("starter_example")
    module = registry.get_module("starter_example")
    assert module.status == ModuleStatus.RUNNING

    deadline = time.time() + 1.0
    while time.time() < deadline and not metrics.get_latest("starter_example"):
        time.sleep(0.02)

    registry.stop_all()

    assert module.status == ModuleStatus.STOPPED
    assert metrics.get_latest("starter_example")["heartbeat_count"] >= 1
    assert any(
        event.type == "STARTER_HEARTBEAT"
        for event in event_bus.get_history(limit=20, module="starter_example")
    )
