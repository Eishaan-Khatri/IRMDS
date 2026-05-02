"""
Infrastructure monitoring pipeline.
"""

from __future__ import annotations

import time
from typing import Any

from core.base_module import BaseModule
from core.event_bus import Event, Severity
from modules.infrastructure.log_analyzer import LogAnalyzer
from modules.infrastructure.system_collector import SystemCollector


class InfrastructurePipeline(BaseModule):
    """System-level hardware and log monitoring pipeline."""

    module_id = "infrastructure"
    display_name = "Infrastructure Monitor"
    version = "1.0.0"

    def _run(self) -> None:
        """Main polling loop."""
        collector = SystemCollector()
        log_analyzer = LogAnalyzer(self.config.infra_log_path)
        
        self.log.info("infra_pipeline_running", poll_interval=self.config.infra_poll_interval)

        while self._running.is_set():
            try:
                # 1. Collect System Metrics
                metrics = collector.collect()
                self.metrics.push(self.module_id, metrics)
                
                # 2. Check Static Thresholds
                self._check_thresholds(metrics)

                # 3. Analyze Logs
                log_anomalies = log_analyzer.analyze_new_lines()
                for anomaly in log_anomalies:
                    self.event_bus.publish(
                        Event(
                            module=self.module_id,
                            type="LOG_ANOMALY",
                            severity=Severity.CRITICAL if anomaly["severity"] == "CRITICAL" else Severity.WARNING,
                            data=anomaly
                        )
                    )

                # 4. Sleep until next poll
                time.sleep(self.config.infra_poll_interval)

            except Exception as exc:
                self.log.error("infra_pipeline_error", error=str(exc))
                time.sleep(5)  # Backoff on error

    def _check_thresholds(self, metrics: dict[str, float]) -> None:
        """Check for critical hardware limit breaches."""
        if metrics["cpu_usage_pct"] > self.config.infra_cpu_critical:
            self.event_bus.publish(
                Event(
                    module=self.module_id,
                    type="CPU_CRITICAL",
                    severity=Severity.CRITICAL,
                    data={"usage": metrics["cpu_usage_pct"]}
                )
            )

        if metrics["mem_usage_pct"] > self.config.infra_ram_critical:
            self.event_bus.publish(
                Event(
                    module=self.module_id,
                    type="RAM_CRITICAL",
                    severity=Severity.CRITICAL,
                    data={"usage": metrics["mem_usage_pct"]}
                )
            )

    def health_check(self) -> dict[str, Any]:
        return {
            "healthy": self.status.value == "running",
            "status": self.status.value,
            "details": {}
        }

    def get_metrics(self) -> dict[str, Any]:
        return self.metrics.get_latest(self.module_id)
