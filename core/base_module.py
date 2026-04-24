"""
Abstract base class that defines the contract for all IRMDS domain modules.

Every module (visual, network, timeseries, infrastructure) must inherit
from `BaseModule` and implement its abstract methods. This ensures the
plugin registry, API, and dashboard can manage any module uniformly
without knowing its internal implementation.

The lifecycle of a module:
    1. Registry discovers the module via `plugin_registry.py`
    2. API calls `start(config)` → module initializes and begins processing
    3. Module publishes events via `self.event_bus.publish(event)`
    4. Module pushes metrics via `self.metrics.push(self.module_id, {...})`
    5. API calls `stop()` → module gracefully shuts down
    6. API calls `health_check()` periodically for the /health endpoint

Design:
    - Modules run their main processing loop in a background thread.
      The `start()` method spawns the thread; `stop()` signals it to exit.
    - The `_running` threading.Event controls the loop lifecycle.
    - All I/O (frame capture, packet reading, file reading, system polling)
      happens inside the module's thread — never on the main asyncio thread.
"""

from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING, Any

from core.logger import get_logger

if TYPE_CHECKING:
    from core.config import IRMDSConfig
    from core.event_bus import EventBus
    from core.metrics_collector import MetricsCollector


class ModuleStatus(str, Enum):
    """Current operational state of a module."""

    STOPPED = "stopped"      # Not running, no resources allocated
    STARTING = "starting"    # Initializing resources (model loading, etc.)
    RUNNING = "running"      # Actively processing data
    STOPPING = "stopping"    # Graceful shutdown in progress
    ERROR = "error"          # Failed — check logs for details


class BaseModule(ABC):
    """Abstract base class for all IRMDS domain modules.

    Subclasses must implement:
        - _run()         → Main processing loop (called in background thread)
        - health_check() → Report module health for the /health endpoint
        - get_metrics()  → Return current performance metrics

    Subclasses must set as class attributes:
        - module_id:    Unique string identifier (e.g., "visual")
        - display_name: Human-readable name (e.g., "Visual Anomaly Detection")
        - version:      Semantic version string (e.g., "1.0.0")

    Provided by the base class:
        - start() / stop()     → Thread lifecycle management
        - self.event_bus       → Publish events
        - self.metrics         → Push metrics
        - self.config          → Read configuration
        - self.log             → Structured logger
        - self.status          → Current ModuleStatus
    """

    # ── Subclass MUST override these ──────────────────────
    module_id: str = ""
    display_name: str = ""
    version: str = "1.0.0"

    def __init__(
        self,
        event_bus: EventBus,
        metrics: MetricsCollector,
        config: IRMDSConfig,
    ):
        self.event_bus = event_bus
        self.metrics = metrics
        self.config = config
        self.status = ModuleStatus.STOPPED
        self.log = get_logger(self.module_id)

        # Thread lifecycle control
        self._running = threading.Event()
        self._thread: threading.Thread | None = None
        self._error: Exception | None = None

    # ── Public Lifecycle Methods ──────────────────────────

    def start(self) -> None:
        """Initialize resources and begin processing in a background thread.

        Raises:
            ModuleAlreadyRunningError: If the module is already active.
            ModuleStartupError:       If initialization fails.
        """
        if self.status == ModuleStatus.RUNNING:
            from core.exceptions import ModuleAlreadyRunningError
            raise ModuleAlreadyRunningError(self.module_id)

        self.log.info("module_starting")
        self.status = ModuleStatus.STARTING
        self._error = None
        self._running.set()

        # Start the processing loop in a daemon thread.
        # Daemon threads are automatically killed when the main process exits,
        # preventing zombie threads during ungraceful shutdowns.
        self._thread = threading.Thread(
            target=self._safe_run,
            name=f"irmds-{self.module_id}",
            daemon=True,
        )
        self._thread.start()
        self.log.info("module_started", thread=self._thread.name)

    def stop(self) -> None:
        """Signal the module to stop and wait for its thread to exit.

        This is a graceful shutdown: the module's `_run()` loop should
        check `self._running.is_set()` and exit when it becomes False.
        """
        if self.status not in (ModuleStatus.RUNNING, ModuleStatus.STARTING):
            return

        self.log.info("module_stopping")
        self.status = ModuleStatus.STOPPING
        self._running.clear()  # Signal the loop to exit

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10.0)
            if self._thread.is_alive():
                self.log.warning("module_stop_timeout", timeout_seconds=10)

        self.status = ModuleStatus.STOPPED
        self._thread = None
        self.log.info("module_stopped")

    def restart(self) -> None:
        """Stop and restart the module."""
        self.stop()
        self.start()

    # ── Abstract Methods (subclass implements) ────────────

    @abstractmethod
    def _run(self) -> None:
        """Main processing loop — runs in a background thread.

        Implementation contract:
            1. Initialize any resources (model, video capture, etc.)
            2. Loop while `self._running.is_set()`
            3. On each iteration: read → process → publish events → push metrics
            4. When loop exits, release all resources (camera, files, etc.)

        Example:
            def _run(self):
                cap = cv2.VideoCapture(0)
                try:
                    while self._running.is_set():
                        ret, frame = cap.read()
                        # ... process frame ...
                        self.event_bus.publish(event)
                        self.metrics.push(self.module_id, {...})
                finally:
                    cap.release()
        """

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """Report module health for the /health endpoint.

        Returns:
            Dict with at minimum:
                {"healthy": bool, "status": str, "details": {...}}
        """

    @abstractmethod
    def get_metrics(self) -> dict[str, Any]:
        """Return current performance metrics.

        Returns:
            Dict of metric_name → value (e.g., {"fps": 24.5, "latency_ms": 40.8})
        """

    # ── Internal ──────────────────────────────────────────

    def _safe_run(self) -> None:
        """Wrapper around _run() that catches exceptions.

        If the module's processing loop crashes, we capture the error,
        set the status to ERROR, and log it — instead of silently dying.
        """
        try:
            self.status = ModuleStatus.RUNNING
            self._run()
        except Exception as exc:
            self._error = exc
            self.status = ModuleStatus.ERROR
            self.log.error(
                "module_crashed",
                error=str(exc),
                exc_info=True,
            )
        finally:
            # Ensure status is updated even if _run() exits normally
            if self.status == ModuleStatus.RUNNING:
                self.status = ModuleStatus.STOPPED

    def to_dict(self) -> dict[str, Any]:
        """Serialize module state for API responses."""
        return {
            "module_id": self.module_id,
            "display_name": self.display_name,
            "version": self.version,
            "status": self.status.value,
            "error": str(self._error) if self._error else None,
        }
