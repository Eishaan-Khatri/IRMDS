"""
Unit tests for the AlertManager — the intelligent alert processing pipeline.

Tests cover:
    - Basic alert processing and storage
    - Cooldown filtering (prevents alert spam)
    - Severity escalation (3+ WARNINGs → auto-CRITICAL)
    - Alert stats aggregation
    - Notification callback routing
"""

from __future__ import annotations

from unittest.mock import MagicMock

from core.alert_manager import AlertManager
from core.config import IRMDSConfig
from core.event_bus import Event, EventBus, Severity


def _make_config(**overrides) -> IRMDSConfig:
    """Create a config with test-friendly defaults."""
    defaults = {
        "alert_cooldown_seconds": 1,  # Short cooldown for fast tests
        "alert_max_history": 100,
        "alert_escalation_window": 5,
        "alert_escalation_count": 3,
    }
    defaults.update(overrides)
    return IRMDSConfig(**defaults)


class TestAlertProcessing:
    """Basic alert processing and storage."""

    def test_warning_event_creates_alert(self):
        """WARNING events should be processed and stored."""
        bus = EventBus()
        manager = AlertManager(bus, _make_config())
        manager.start()

        bus.publish(
            Event(
                module="visual",
                type="LOITERING",
                severity=Severity.WARNING,
                data={"zone": "A"},
            )
        )

        alerts = manager.get_alerts()
        assert len(alerts) == 1
        assert alerts[0]["type"] == "LOITERING"
        assert alerts[0]["severity"] == "WARNING"
        manager.stop()

    def test_critical_event_creates_alert(self):
        """CRITICAL events should be processed and stored."""
        bus = EventBus()
        manager = AlertManager(bus, _make_config())
        manager.start()

        bus.publish(
            Event(
                module="network",
                type="NET_ANOMALY",
                severity=Severity.CRITICAL,
                data={"pps": 15000},
            )
        )

        alerts = manager.get_alerts()
        assert len(alerts) == 1
        assert alerts[0]["severity"] == "CRITICAL"
        manager.stop()

    def test_info_events_are_not_processed(self):
        """INFO events should not create alerts (they stay in event history only)."""
        bus = EventBus()
        manager = AlertManager(bus, _make_config())
        manager.start()

        bus.publish(Event(module="visual", type="ZONE_ENTRY", severity=Severity.INFO))

        alerts = manager.get_alerts()
        assert len(alerts) == 0
        manager.stop()


class TestCooldown:
    """Cooldown filtering — prevents alert storms."""

    def test_same_type_within_cooldown_is_suppressed(self):
        """Same alert type fired again within cooldown should be suppressed."""
        bus = EventBus()
        config = _make_config(alert_cooldown_seconds=10)
        manager = AlertManager(bus, config)
        manager.start()

        # First event should pass
        bus.publish(Event(module="visual", type="CROWD_ALERT", severity=Severity.WARNING))
        # Second identical event within cooldown should be suppressed
        bus.publish(Event(module="visual", type="CROWD_ALERT", severity=Severity.WARNING))

        alerts = manager.get_alerts()
        assert len(alerts) == 1
        manager.stop()

    def test_different_types_are_not_affected_by_cooldown(self):
        """Different alert types should not share cooldown timers."""
        bus = EventBus()
        config = _make_config(alert_cooldown_seconds=10)
        manager = AlertManager(bus, config)
        manager.start()

        bus.publish(Event(module="visual", type="CROWD_ALERT", severity=Severity.WARNING))
        bus.publish(Event(module="visual", type="LOITERING", severity=Severity.WARNING))

        alerts = manager.get_alerts()
        assert len(alerts) == 2
        manager.stop()


class TestEscalation:
    """Severity escalation — too many WARNINGs become CRITICAL."""

    def test_multiple_warnings_escalate_to_critical(self):
        """3+ WARNINGs within the escalation window should produce a CRITICAL."""
        bus = EventBus()
        config = _make_config(
            alert_cooldown_seconds=0,  # No cooldown for this test
            alert_escalation_window=60,
            alert_escalation_count=3,
        )
        manager = AlertManager(bus, config)
        manager.start()

        # Fire 3 WARNINGs with different types (so cooldown doesn't block)
        bus.publish(Event(module="visual", type="WARN_A", severity=Severity.WARNING))
        bus.publish(Event(module="visual", type="WARN_B", severity=Severity.WARNING))
        bus.publish(Event(module="visual", type="WARN_C", severity=Severity.WARNING))

        alerts = manager.get_alerts()
        # The 3rd WARNING should be escalated to CRITICAL
        escalated = [a for a in alerts if a["escalated"]]
        assert len(escalated) >= 1
        assert any(a["severity"] == "CRITICAL" for a in escalated)
        manager.stop()


class TestAlertStats:
    """Alert statistics aggregation."""

    def test_stats_count_by_severity(self):
        """Stats should correctly count alerts by severity."""
        bus = EventBus()
        config = _make_config(alert_cooldown_seconds=0)
        manager = AlertManager(bus, config)
        manager.start()

        bus.publish(Event(module="visual", type="A", severity=Severity.WARNING))
        bus.publish(Event(module="network", type="B", severity=Severity.CRITICAL))
        bus.publish(Event(module="network", type="C", severity=Severity.CRITICAL))

        stats = manager.get_stats()
        assert stats["total"] >= 3
        assert stats["by_severity"].get("CRITICAL", 0) >= 2
        manager.stop()

    def test_stats_count_by_module(self):
        """Stats should correctly count alerts by source module."""
        bus = EventBus()
        config = _make_config(alert_cooldown_seconds=0)
        manager = AlertManager(bus, config)
        manager.start()

        bus.publish(Event(module="visual", type="A", severity=Severity.WARNING))
        bus.publish(Event(module="visual", type="B", severity=Severity.WARNING))
        bus.publish(Event(module="network", type="C", severity=Severity.CRITICAL))

        stats = manager.get_stats()
        assert stats["by_module"].get("visual", 0) >= 2
        assert stats["by_module"].get("network", 0) >= 1
        manager.stop()


class TestNotificationCallback:
    """Notification callback routing."""

    def test_callback_receives_processed_alerts(self):
        """Registered notification callback should receive each processed alert."""
        bus = EventBus()
        manager = AlertManager(bus, _make_config())
        callback = MagicMock()
        manager.set_notify_callback(callback)
        manager.start()

        bus.publish(Event(module="test", type="X", severity=Severity.CRITICAL))

        assert callback.called
        alert_arg = callback.call_args[0][0]
        assert alert_arg["type"] == "X"
        assert alert_arg["severity"] == "CRITICAL"
        manager.stop()
