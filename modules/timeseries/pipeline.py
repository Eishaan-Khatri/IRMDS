"""
Finance anomaly detection pipeline.
"""

from __future__ import annotations

from typing import Any

from core.base_module import BaseModule
from core.event_bus import Event, Severity
from modules.timeseries.anomaly_detector import FinanceAnomalyDetector
from modules.timeseries.data_source import FinanceDataSource
from modules.timeseries.feature_extractor import FinanceFeatureExtractor


class FinancePipeline(BaseModule):
    """Financial time-series monitoring pipeline."""

    module_id = "timeseries"
    display_name = "Financial Engine"
    version = "1.0.0"

    def _run(self) -> None:
        """Main replayer loop."""
        source = FinanceDataSource(
            file_path=self.config.finance_data_path,
            replay_speed=self.config.finance_replay_speed,
        )
        extractor = FinanceFeatureExtractor(window_size=50)
        detector = FinanceAnomalyDetector(
            baseline_ticks=self.config.finance_baseline_ticks,
            contamination=0.05,
        )

        self.log.info("finance_pipeline_running", source=self.config.finance_data_path)

        try:
            for tick in source.stream():
                if not self._running.is_set():
                    break

                features = extractor.update(tick.close)
                if not features:
                    continue

                is_anomaly, anomaly_type, score = detector.detect(features)

                # Push Metrics
                metrics = {
                    "price": tick.close,
                    "volume": tick.volume,
                    **features,
                    "anomaly_score": score,
                    "baseline_ready": detector.baseline_ready,
                }
                self.metrics.push(self.module_id, metrics)

                # Emit Metrics Event
                self.event_bus.publish(
                    Event(
                        module=self.module_id,
                        type="FIN_METRICS",
                        severity=Severity.INFO,
                        data=metrics,
                    )
                )

                # Emit Anomaly Event
                if is_anomaly:
                    self.event_bus.publish(
                        Event(
                            module=self.module_id,
                            type="FIN_ANOMALY",
                            severity=Severity.CRITICAL,
                            data={
                                "type": anomaly_type,
                                "price": tick.close,
                                "features": features,
                            },
                        )
                    )

        except Exception as exc:
            self.log.error("finance_pipeline_error", error=str(exc), exc_info=True)
            raise
        finally:
            self.log.info("finance_pipeline_stopped")

    def health_check(self) -> dict[str, Any]:
        return {
            "healthy": self.status.value == "running",
            "status": self.status.value,
            "details": self.get_metrics(),
        }

    def get_metrics(self) -> dict[str, Any]:
        return self.metrics.get_latest(self.module_id)
