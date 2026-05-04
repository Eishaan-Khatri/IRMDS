"""
Network traffic analysis pipeline.

The API and plugin registry manage modules through the synchronous
BaseModule contract. This pipeline keeps that contract and runs packet
generation plus feature extraction in background threads.
"""

from __future__ import annotations

import threading
import time
from typing import Any

from core.base_module import BaseModule
from core.event_bus import Event, Severity
from modules.network.anomaly_detector import NetworkAnomalyDetector
from modules.network.feature_extractor import FeatureExtractor
from modules.network.traffic_generator import TrafficGenerator


class NetworkPipeline(BaseModule):
    """Synthetic network telemetry pipeline with hybrid anomaly detection."""

    module_id = "network"
    display_name = "Network Security Analytics"
    version = "0.1.0"

    def __init__(self, event_bus, metrics, config):
        super().__init__(event_bus=event_bus, metrics=metrics, config=config)
        self.generator = TrafficGenerator()
        self.extractor = FeatureExtractor(
            window_seconds=config.network_window_seconds,
        )
        self.detector = NetworkAnomalyDetector(
            baseline_windows=config.network_baseline_windows,
            contamination=config.network_anomaly_contamination,
        )
        self.detector.ema_detector.threshold = config.network_zscore_threshold
        self.detector.DDOS_PPS_THRESHOLD = config.network_ddos_pps
        self.detector.PORT_SCAN_THRESHOLD = config.network_scan_ports

        self._worker_running = [False]
        self._generator_thread: threading.Thread | None = None
        self._windows_processed = 0
        self._last_window_at = 0.0
        self._last_anomaly_type: str | None = None

    def stop(self) -> None:
        """Stop the generator promptly before waiting for BaseModule shutdown."""
        self._worker_running[0] = False
        self.generator.stop()
        super().stop()

    def _run(self) -> None:
        """Run packet generation and feature extraction until stopped."""
        self._worker_running[0] = True
        self._generator_thread = threading.Thread(
            target=self.generator.start,
            args=(800,),
            daemon=True,
            name="irmds-network-generator",
        )
        self._generator_thread.start()
        self.log.info("network_generator_thread_started")

        try:
            while self._running.is_set():
                self._worker_running[0] = True
                windows = self.extractor.process_queue(
                    self.generator.packet_queue,
                    self._worker_running,
                )

                if not windows:
                    time.sleep(0.05)
                    continue

                for window in windows:
                    if not self._running.is_set():
                        break
                    self._process_window(window)
        finally:
            self._worker_running[0] = False
            self.generator.stop()
            if self._generator_thread and self._generator_thread.is_alive():
                self._generator_thread.join(timeout=2.0)
            self._generator_thread = None
            self.log.info("network_pipeline_stopped")

    def _process_window(self, window) -> None:
        """Run detection for one feature window and publish metrics/events."""
        result = self.detector.process(window)
        self._windows_processed += 1
        self._last_window_at = time.time()

        metrics = {
            "packets_per_second": window.packets_per_second,
            "bytes_per_second": window.bytes_per_second,
            "unique_src_ips": window.unique_src_ips,
            "unique_dst_ports": window.unique_dst_ports,
            "tcp_ratio": window.tcp_ratio,
            "dst_ip_entropy": window.dst_ip_entropy,
            "anomaly_score": result.isolation_forest_score,
            "baseline_ready": self.detector.baseline_ready,
            "windows_processed": self._windows_processed,
        }
        self.metrics.push(self.module_id, metrics)

        self.event_bus.publish(
            Event(
                module=self.module_id,
                type="NET_METRICS",
                severity=Severity.INFO,
                data=metrics,
            )
        )

        if result.is_anomaly:
            self._last_anomaly_type = result.anomaly_type
            self.event_bus.publish(
                Event(
                    module=self.module_id,
                    type="NET_ANOMALY",
                    severity=Severity.CRITICAL,
                    data={
                        "alert_type": result.anomaly_type,
                        "triggers": result.triggers,
                        "pps": window.packets_per_second,
                        "bps": window.bytes_per_second,
                        "unique_src_ips": window.unique_src_ips,
                        "unique_dst_ports": window.unique_dst_ports,
                    },
                )
            )

    def health_check(self) -> dict[str, Any]:
        """Return lightweight health details without doing expensive work."""
        generator_alive = self._generator_thread is not None and self._generator_thread.is_alive()
        return {
            "healthy": self.status.value == "running" and generator_alive,
            "status": self.status.value,
            "details": {
                "queue_size": self.generator.packet_queue.qsize(),
                "baseline_ready": self.detector.baseline_ready,
                "windows_processed": self._windows_processed,
                "last_window_at": self._last_window_at,
                "last_anomaly_type": self._last_anomaly_type,
            },
        }

    def get_metrics(self) -> dict[str, Any]:
        """Return latest network metrics from the shared collector."""
        return self.metrics.get_latest(self.module_id)
