"""
Alert manager — intelligent alert processing pipeline.

Sits between the event bus and the notification system. Raw events from
modules flow in; processed, deduplicated, severity-classified alerts flow
out. This prevents alert storms and ensures operators see only actionable
information.

Processing pipeline:
    Event → Severity Check → Cooldown Filter → Dedup → Escalation → Store → Notify

Features:
    - Per-type cooldown:     Same alert type won't fire again within N seconds
    - Deduplication:         Same module + type + object_id within window = one alert
    - Severity escalation:   3+ WARNINGs in 60 seconds auto-escalates to CRITICAL
    - Persistent storage:    Alerts written to SQLite for historical queries
    - Notification routing:  CRITICAL → Slack/Discord/Email, WARNING → console

Usage:
    manager = AlertManager(event_bus, config)
    manager.start()  # Subscribes to event bus and begins processing
"""

from __future__ import annotations

import time
import threading
from collections import defaultdict, deque
from typing import TYPE_CHECKING, Any, Callable

from core.event_bus import Event, Severity
from core.logger import get_logger

if TYPE_CHECKING:
    from core.config import IRMDSConfig
    from core.event_bus import EventBus

log = get_logger("alerts")


class AlertManager:
    """Processes raw events into actionable, deduplicated alerts.

    The alert manager subscribes to ALL events on the event bus and
    applies its filtering pipeline before storing and forwarding.
    """

    def __init__(self, event_bus: EventBus, config: IRMDSConfig):
        self._event_bus = event_bus
        self._config = config

        # Cooldown tracking: (module, type) → last fire timestamp
        self._cooldowns: dict[tuple[str, str], float] = {}

        # Dedup tracking: (module, type, object_id) → last fire timestamp
        self._dedup_cache: dict[tuple[str, str, str], float] = {}

        # Escalation tracking: sliding window of WARNING events
        self._warning_window: deque[float] = deque()

        # Alert storage (in-memory + optional DB callback)
        self._alerts: deque[dict[str, Any]] = deque(
            maxlen=config.alert_max_history
        )
        self._alert_count = 0
        self._lock = threading.Lock()

        # External notification callback (set by notification manager)
        self._notify_callback: Callable[[dict], None] | None = None

        # Subscription ID for cleanup
        self._subscription_id: str | None = None

    def start(self) -> None:
        """Subscribe to the event bus and begin processing.

        Listens to WARNING and CRITICAL events only — INFO events
        are stored in the event bus history but don't need alert
        processing (no cooldown, no escalation, no notifications).
        """
        self._subscription_id = self._event_bus.subscribe(
            self._process_event,
            filter_severity=Severity.WARNING,
        )
        log.info("alert_manager_started")

    def stop(self) -> None:
        """Unsubscribe from the event bus."""
        if self._subscription_id:
            self._event_bus.unsubscribe(self._subscription_id)
            self._subscription_id = None
        log.info("alert_manager_stopped")

    def set_notify_callback(self, callback: Callable[[dict], None]) -> None:
        """Register a callback for alert notifications.

        The notification manager sets this during startup so it
        receives processed alerts without circular imports.
        """
        self._notify_callback = callback

    # ─────────────── Alert Queries ────────────────────────

    def get_alerts(
        self,
        *,
        limit: int = 50,
        module: str | None = None,
        alert_type: str | None = None,
        severity: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve processed alerts with optional filtering.

        Returns alerts in reverse chronological order (newest first).
        """
        with self._lock:
            alerts = list(self._alerts)

        if module:
            alerts = [a for a in alerts if a["module"] == module]
        if alert_type:
            alerts = [a for a in alerts if a["type"] == alert_type]
        if severity:
            alerts = [a for a in alerts if a["severity"] == severity]

        return list(reversed(alerts))[:limit]

    def get_stats(self) -> dict[str, Any]:
        """Aggregate alert statistics for the /alerts/stats endpoint.

        Returns counts grouped by severity, module, and type.
        """
        with self._lock:
            alerts = list(self._alerts)

        by_severity: dict[str, int] = defaultdict(int)
        by_module: dict[str, int] = defaultdict(int)
        by_type: dict[str, int] = defaultdict(int)

        for alert in alerts:
            by_severity[alert["severity"]] += 1
            by_module[alert["module"]] += 1
            by_type[alert["type"]] += 1

        return {
            "total": len(alerts),
            "by_severity": dict(by_severity),
            "by_module": dict(by_module),
            "by_type": dict(by_type),
        }

    @property
    def total_alerts(self) -> int:
        """Total number of processed alerts since startup."""
        return self._alert_count

    # ─────────────── Processing Pipeline ──────────────────

    def _process_event(self, event: Event) -> None:
        """Main processing pipeline for incoming events.

        Steps:
            1. Check cooldown — skip if same type fired too recently
            2. Check dedup — skip if same object+type is duplicate
            3. Check escalation — upgrade severity if too many WARNINGs
            4. Store the alert
            5. Fire notification callback
        """
        now = time.time()
        cooldown_key = (event.module, event.type)
        object_id = str(event.data.get("object_id", ""))
        dedup_key = (event.module, event.type, object_id)

        # Step 1: Cooldown — prevent same alert type from spamming
        last_fire = self._cooldowns.get(cooldown_key, 0)
        if now - last_fire < self._config.alert_cooldown_seconds:
            return  # Too soon, skip

        # Step 2: Dedup — same object + same type within cooldown = duplicate
        if object_id:
            last_dedup = self._dedup_cache.get(dedup_key, 0)
            if now - last_dedup < self._config.alert_cooldown_seconds:
                return  # Duplicate, skip

        # Step 3: Escalation — check if we should upgrade to CRITICAL
        severity = event.severity
        if severity == Severity.WARNING:
            self._warning_window.append(now)
            # Prune old entries outside the escalation window
            cutoff = now - self._config.alert_escalation_window
            while self._warning_window and self._warning_window[0] < cutoff:
                self._warning_window.popleft()
            # Escalate if too many WARNINGs in the window
            if len(self._warning_window) >= self._config.alert_escalation_count:
                severity = Severity.CRITICAL
                log.warning(
                    "severity_escalated",
                    original="WARNING",
                    escalated_to="CRITICAL",
                    warnings_in_window=len(self._warning_window),
                )

        # Step 4: Store the processed alert
        alert = {
            "id": event.id,
            "timestamp": event.timestamp,
            "module": event.module,
            "type": event.type,
            "severity": severity.value,
            "data": event.data,
            "escalated": severity != event.severity,
        }

        with self._lock:
            self._alerts.append(alert)
            self._alert_count += 1

        # Update cooldown and dedup caches
        self._cooldowns[cooldown_key] = now
        if object_id:
            self._dedup_cache[dedup_key] = now

        log.info(
            "alert_processed",
            alert_id=event.id,
            module=event.module,
            type=event.type,
            severity=severity.value,
        )

        # Step 5: Fire notification callback (if registered)
        if self._notify_callback:
            try:
                self._notify_callback(alert)
            except Exception:
                log.error("notification_callback_failed", exc_info=True)
