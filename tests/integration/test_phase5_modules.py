"""
Integration coverage for phase-5 domain modules.
"""

from __future__ import annotations

import csv
import time
from pathlib import Path
from uuid import uuid4

from core.base_module import ModuleStatus
from core.config import IRMDSConfig
from core.event_bus import EventBus, Severity
from core.metrics_collector import MetricsCollector
from core.plugin_registry import PluginRegistry
from modules.infrastructure import system_collector
from modules.infrastructure.pipeline import InfrastructurePipeline


def _wait_for(predicate, timeout: float = 3.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


def _write_stock_fixture(path: Path) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])
        for idx in range(120):
            close = 150.0
            volume = 1000
            if idx == 70:
                close = 138.0
                volume = 6000
            writer.writerow([f"t{idx}", close, close, close, close, volume])


def _test_workdir(name: str) -> Path:
    workdir = Path(".tmp") / "phase5_tests" / f"{name}_{uuid4().hex[:8]}"
    workdir.mkdir(parents=True, exist_ok=True)
    return workdir


def test_finance_pipeline_emits_metrics_and_anomaly():
    """FinancePipeline should run through replay data and emit FIN events."""
    stock_path = _test_workdir("finance") / "sample_stock.csv"
    _write_stock_fixture(stock_path)

    event_bus = EventBus(max_history=200)
    metrics = MetricsCollector()
    config = IRMDSConfig(
        finance_data_path=str(stock_path),
        finance_replay_speed=0,
        finance_baseline_ticks=5,
    )
    registry = PluginRegistry(event_bus=event_bus, metrics=metrics, config=config)
    discovered = registry.discover()
    assert "timeseries" in discovered

    registry.start_module("timeseries")
    pipeline = registry.get_module("timeseries")
    assert _wait_for(lambda: pipeline.status == ModuleStatus.STOPPED)
    registry.stop_all()

    latest = metrics.get_latest("timeseries")
    assert latest["price"] == 150.0

    history = event_bus.get_history(limit=200, module="timeseries")
    assert any(event.type == "FIN_METRICS" for event in history)
    assert any(
        event.type == "FIN_ANOMALY"
        and event.severity == Severity.CRITICAL
        and event.data["type"] == "FLASH_CRASH_SUSPECT"
        for event in history
    )


def test_infrastructure_pipeline_emits_threshold_and_log_events(monkeypatch):
    """InfrastructurePipeline should emit mocked CPU/RAM and log anomaly events."""

    class FakeMetric:
        def __init__(self, **values):
            self.__dict__.update(values)

    class FakePsutil:
        @staticmethod
        def cpu_percent(interval=None):
            return 98.0

        @staticmethod
        def cpu_freq():
            return FakeMetric(current=2400.0)

        @staticmethod
        def virtual_memory():
            return FakeMetric(percent=96.0)

        @staticmethod
        def disk_usage(path):
            return FakeMetric(percent=55.0)

        @staticmethod
        def net_io_counters():
            return FakeMetric(bytes_sent=10.0, bytes_recv=20.0)

        @staticmethod
        def pids():
            return list(range(42))

    log_path = _test_workdir("infra") / "sample_syslog.log"
    log_path.write_text("May 02 10:00:00 API[123]: [ERROR] simulated failure\n")

    monkeypatch.setattr(system_collector, "psutil", FakePsutil)

    event_bus = EventBus(max_history=100)
    metrics = MetricsCollector()
    config = IRMDSConfig(
        infra_log_path=str(log_path),
        infra_poll_interval=0.01,
        infra_cpu_critical=90.0,
        infra_ram_critical=90.0,
    )
    pipeline = InfrastructurePipeline(event_bus=event_bus, metrics=metrics, config=config)

    pipeline.start()
    assert _wait_for(lambda: bool(metrics.get_latest("infrastructure")))
    pipeline.stop()

    latest = metrics.get_latest("infrastructure")
    assert latest["cpu_usage_pct"] == 98.0

    history = event_bus.get_history(limit=100, module="infrastructure")
    event_types = {event.type for event in history}
    assert "INFRA_CPU_HIGH" in event_types
    assert "INFRA_RAM_HIGH" in event_types
    assert "INFRA_LOG_ANOMALY" in event_types
