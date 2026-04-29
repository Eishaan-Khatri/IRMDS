"""
In-process publish/subscribe event bus for IRMDS.

This is the central nervous system of the architecture. Every domain module
publishes structured events to the bus, and every consumer (API, dashboard,
alert manager, notifications) subscribes to the events it cares about.

Design decisions:
    - In-process (not Kafka/Redis): keeps deployment simple — one process,
      `docker-compose up`, works everywhere. If scaling to multi-process is
      needed later, swap this for a Redis pub/sub backend without changing
      module code (they publish to the same interface).
    - Thread-safe: modules run in background threads, but the bus is shared.
      All mutations are protected by a threading.Lock.
    - Event history: the bus retains the last N events in a deque. The API
      reads from this for the /alerts/latest endpoint + the WebSocket pushes
      events in real-time.

Event schema:
    {
        "id": "evt_a3f8c2d1-...",       # Unique UUID
        "timestamp": "2026-04-23...",    # ISO 8601
        "module": "visual",              # Source module
        "type": "ZONE_ENTRY",            # Event type
        "severity": "INFO",              # INFO | WARNING | CRITICAL
        "data": { ... }                  # Module-specific payload
    }
"""

from __future__ import annotations

import threading
import uuid
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from core.logger import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

log = get_logger("event_bus")


class Severity(StrEnum):
    """Alert severity levels, ordered by escalation priority."""

    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True, slots=True)
class Event:
    """Immutable, structured event emitted by domain modules.

    Frozen dataclass ensures events cannot be accidentally mutated
    after creation — important for thread safety and audit integrity.

    Attributes:
        id:        Unique identifier (UUID4 with 'evt_' prefix).
        timestamp: ISO 8601 creation time in UTC.
        module:    Source module identifier (e.g., "visual", "network").
        type:      Event type string (e.g., "ZONE_ENTRY", "NET_ANOMALY").
        severity:  One of INFO, WARNING, CRITICAL.
        data:      Arbitrary payload dict with module-specific details.
    """

    module: str
    type: str
    severity: Severity
    data: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict for JSON transmission."""
        result = asdict(self)
        result["severity"] = self.severity.value
        return result


@dataclass
class Subscription:
    """A registered callback with optional filters.

    Attributes:
        id:              Unique subscription ID for unsubscribe.
        callback:        Function called with each matching Event.
        filter_module:   Only fire for events from this module (None = all).
        filter_type:     Only fire for this event type (None = all).
        filter_severity: Only fire for this severity or higher (None = all).
    """

    id: str
    callback: Callable[[Event], None]
    filter_module: str | None = None
    filter_type: str | None = None
    filter_severity: Severity | None = None


# Severity ordering for "at least this severe" filtering
_SEVERITY_ORDER = {Severity.INFO: 0, Severity.WARNING: 1, Severity.CRITICAL: 2}


class EventBus:
    """Thread-safe in-process event bus with filtering and history.

    Typical usage:
        bus = EventBus(max_history=500)

        # Subscribe to all CRITICAL events
        bus.subscribe(my_handler, filter_severity=Severity.CRITICAL)

        # Publish from a module
        bus.publish(Event(module="visual", type="SPEED_ANOMALY",
                         severity=Severity.CRITICAL, data={"speed": 3.8}))
    """

    def __init__(self, max_history: int = 1000):
        self._subscribers: dict[str, Subscription] = {}
        self._history: deque[Event] = deque(maxlen=max_history)
        self._lock = threading.Lock()
        self._event_count = 0

    # ─────────────── Publishing ───────────────────────────

    def publish(self, event: Event) -> None:
        """Publish an event to all matching subscribers.

        Thread-safe. The event is appended to history and then
        dispatched to each subscriber whose filters match.

        If a subscriber callback raises an exception, it is logged
        and swallowed — one broken subscriber must never prevent
        other subscribers from receiving the event.
        """
        with self._lock:
            self._history.append(event)
            self._event_count += 1
            # Take a snapshot of subscribers under the lock
            subscribers = list(self._subscribers.values())

        # Dispatch outside the lock to avoid holding it during callbacks
        for sub in subscribers:
            if self._matches(event, sub):
                try:
                    sub.callback(event)
                except Exception:
                    log.error(
                        "subscriber_error",
                        subscription_id=sub.id,
                        event_id=event.id,
                        exc_info=True,
                    )

    # ─────────────── Subscribing ──────────────────────────

    def subscribe(
        self,
        callback: Callable[[Event], None],
        *,
        filter_module: str | None = None,
        filter_type: str | None = None,
        filter_severity: Severity | None = None,
    ) -> str:
        """Register a callback to receive matching events.

        Args:
            callback:        Function to call with each matching Event.
            filter_module:   Only receive events from this module.
            filter_type:     Only receive events of this type.
            filter_severity: Only receive events at this severity or higher.

        Returns:
            Subscription ID string for later unsubscribe.
        """
        sub_id = f"sub_{uuid.uuid4().hex[:8]}"
        subscription = Subscription(
            id=sub_id,
            callback=callback,
            filter_module=filter_module,
            filter_type=filter_type,
            filter_severity=filter_severity,
        )
        with self._lock:
            self._subscribers[sub_id] = subscription

        log.debug(
            "subscriber_added",
            subscription_id=sub_id,
            filter_module=filter_module,
            filter_type=filter_type,
            filter_severity=filter_severity,
        )
        return sub_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Remove a subscription by ID.

        Returns True if the subscription existed and was removed.
        """
        with self._lock:
            removed = self._subscribers.pop(subscription_id, None)
        if removed:
            log.debug("subscriber_removed", subscription_id=subscription_id)
        return removed is not None

    # ─────────────── History & Queries ────────────────────

    def get_history(
        self,
        *,
        limit: int = 50,
        module: str | None = None,
        event_type: str | None = None,
        severity: Severity | None = None,
    ) -> list[Event]:
        """Retrieve recent events from history with optional filters.

        Events are returned in reverse chronological order (newest first).

        Args:
            limit:      Maximum number of events to return.
            module:     Filter by source module.
            event_type: Filter by event type.
            severity:   Filter by exact severity.

        Returns:
            List of matching Event objects, newest first.
        """
        with self._lock:
            events = list(self._history)

        # Apply filters
        if module:
            events = [e for e in events if e.module == module]
        if event_type:
            events = [e for e in events if e.type == event_type]
        if severity:
            events = [e for e in events if e.severity == severity]

        # Return newest first, up to limit
        return list(reversed(events))[:limit]

    @property
    def total_events(self) -> int:
        """Total number of events published since startup."""
        return self._event_count

    @property
    def subscriber_count(self) -> int:
        """Number of active subscriptions."""
        with self._lock:
            return len(self._subscribers)

    # ─────────────── Internal ─────────────────────────────

    @staticmethod
    def _matches(event: Event, sub: Subscription) -> bool:
        """Check if an event passes a subscription's filters."""
        if sub.filter_module and event.module != sub.filter_module:
            return False
        if sub.filter_type and event.type != sub.filter_type:
            return False
        if sub.filter_severity:
            event_level = _SEVERITY_ORDER.get(event.severity, 0)
            filter_level = _SEVERITY_ORDER.get(sub.filter_severity, 0)
            if event_level < filter_level:
                return False
        return True
