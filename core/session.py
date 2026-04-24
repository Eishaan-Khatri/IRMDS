"""
Session management for IRMDS monitoring sessions.

A "session" represents a bounded period of active monitoring. It tracks
which modules were running, how many alerts fired, and produces a
summary when stopped.

Sessions are useful for:
    - Benchmarking: "Run for 60 seconds, then show results"
    - Shift tracking: "Monitor from 09:00 to 17:00"
    - Demo recordings: "Start session → run demo → stop → show report"

Usage:
    session_mgr = SessionManager()
    session_id = session_mgr.start()
    # ... monitoring happens ...
    summary = session_mgr.stop(alert_manager)
    # → {"duration_seconds": 300, "alerts": {"CRITICAL": 2, "WARNING": 8}, ...}
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from core.logger import get_logger

if TYPE_CHECKING:
    from core.alert_manager import AlertManager

log = get_logger("session")


class SessionStatus(str, Enum):
    """Current state of a monitoring session."""

    ACTIVE = "active"
    COMPLETED = "completed"


@dataclass
class Session:
    """A single monitoring session with timing and summary data."""

    id: str = field(default_factory=lambda: f"sess_{uuid.uuid4().hex[:10]}")
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    status: SessionStatus = SessionStatus.ACTIVE
    summary: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float:
        """Elapsed time in seconds (ongoing or completed)."""
        end = self.end_time or time.time()
        return round(end - self.start_time, 2)

    def to_dict(self) -> dict[str, Any]:
        """Serialize for API responses."""
        return {
            "id": self.id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": self.duration_seconds,
            "status": self.status.value,
            "summary": self.summary,
        }


class SessionManager:
    """Manages monitoring session lifecycle.

    Only one session can be active at a time. Starting a new session
    while one is active will stop the current session first.
    """

    def __init__(self):
        self._current: Session | None = None
        self._history: list[Session] = []

    def start(self) -> str:
        """Start a new monitoring session.

        If a session is already active, it will be stopped automatically
        before starting the new one.

        Returns:
            The new session's ID.
        """
        if self._current and self._current.status == SessionStatus.ACTIVE:
            log.info("auto_stopping_previous_session", session_id=self._current.id)
            self._finalize_current()

        self._current = Session()
        log.info("session_started", session_id=self._current.id)
        return self._current.id

    def stop(self, alert_manager: AlertManager | None = None) -> dict[str, Any]:
        """Stop the current session and generate a summary.

        Args:
            alert_manager: If provided, the summary includes alert statistics.

        Returns:
            Session summary dict. Returns empty dict if no active session.
        """
        if not self._current or self._current.status != SessionStatus.ACTIVE:
            return {}

        if alert_manager:
            self._current.summary = {
                "alert_stats": alert_manager.get_stats(),
                "total_alerts": alert_manager.total_alerts,
            }

        self._finalize_current()
        return self._current.to_dict()

    def get_current(self) -> dict[str, Any] | None:
        """Get the current active session, if any."""
        if self._current and self._current.status == SessionStatus.ACTIVE:
            return self._current.to_dict()
        return None

    def get_history(self) -> list[dict[str, Any]]:
        """Get all completed sessions."""
        return [s.to_dict() for s in self._history]

    def _finalize_current(self) -> None:
        """Mark the current session as completed and archive it."""
        if self._current:
            self._current.end_time = time.time()
            self._current.status = SessionStatus.COMPLETED
            self._history.append(self._current)
            log.info(
                "session_completed",
                session_id=self._current.id,
                duration_seconds=self._current.duration_seconds,
            )
