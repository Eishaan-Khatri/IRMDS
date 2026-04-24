"""
Unit tests for the polygon zone manager.

Tests cover:
    - Point-in-polygon containment
    - Zone entry and exit events
    - Loitering detection with threshold
    - Crowd alert triggering
    - Zone stats aggregation
"""

from __future__ import annotations

import time
from unittest.mock import patch

from modules.visual.zone_manager import Zone, ZoneManager


def _square_zone(
    name: str = "Test Zone",
    crowd_threshold: int = 3,
    loiter_seconds: int = 2,
) -> Zone:
    """Create a 100×100 square zone at origin for testing."""
    return Zone(
        name=name,
        points=[(0, 0), (100, 0), (100, 100), (0, 100)],
        crowd_threshold=crowd_threshold,
        loiter_seconds=loiter_seconds,
    )


class TestPointInPolygon:
    """Geometric containment tests."""

    def test_point_inside_zone(self):
        """A point clearly inside the polygon should return True."""
        zone = _square_zone()
        assert zone.point_inside((50, 50)) is True

    def test_point_outside_zone(self):
        """A point clearly outside the polygon should return False."""
        zone = _square_zone()
        assert zone.point_inside((200, 200)) is False

    def test_point_on_boundary(self):
        """A point on the polygon boundary should return True (≥ 0 check)."""
        zone = _square_zone()
        assert zone.point_inside((0, 0)) is True


class TestZoneEntryExit:
    """Entry and exit event generation."""

    def test_entry_event_on_first_detection(self):
        """First time an object appears inside a zone → ZONE_ENTRY event."""
        zone = _square_zone()

        events = zone.update({0: (50, 50)})

        entry_events = [e for e in events if e.type == "ZONE_ENTRY"]
        assert len(entry_events) == 1
        assert entry_events[0].object_id == 0
        assert entry_events[0].zone_name == "Test Zone"

    def test_no_event_when_staying_inside(self):
        """An object remaining inside should not generate new entry events."""
        zone = _square_zone()

        zone.update({0: (50, 50)})  # Enter
        events = zone.update({0: (55, 55)})  # Still inside

        entry_events = [e for e in events if e.type == "ZONE_ENTRY"]
        assert len(entry_events) == 0

    def test_exit_event_when_leaving(self):
        """An object leaving the zone → ZONE_EXIT event with dwell time."""
        zone = _square_zone()

        zone.update({0: (50, 50)})  # Enter
        events = zone.update({})     # Object disappeared (left frame)

        exit_events = [e for e in events if e.type == "ZONE_EXIT"]
        assert len(exit_events) == 1
        assert exit_events[0].object_id == 0

    def test_enter_count_increments(self):
        """Zone enter_count should increment for each unique entry."""
        zone = _square_zone()

        zone.update({0: (50, 50)})
        zone.update({0: (50, 50), 1: (60, 60)})  # Second person enters

        assert zone.enter_count == 2


class TestLoitering:
    """Loitering detection with dwell time threshold."""

    def test_loitering_after_threshold(self):
        """Object dwelling longer than threshold → LOITERING event."""
        zone = _square_zone(loiter_seconds=1)

        # Simulate time passing by mocking time.time()
        base_time = 1000.0

        with patch("modules.visual.zone_manager.time.time", return_value=base_time):
            zone.update({0: (50, 50)})

        # 2 seconds later (exceeds 1-second threshold)
        with patch("modules.visual.zone_manager.time.time", return_value=base_time + 2.0):
            events = zone.update({0: (50, 50)})

        loiter_events = [e for e in events if e.type == "LOITERING"]
        assert len(loiter_events) == 1
        assert loiter_events[0].dwell_seconds >= 1.0

    def test_no_duplicate_loiter_alerts(self):
        """Same object should only trigger loitering alert once per visit."""
        zone = _square_zone(loiter_seconds=1)
        base_time = 1000.0

        with patch("modules.visual.zone_manager.time.time", return_value=base_time):
            zone.update({0: (50, 50)})

        # First check after threshold
        with patch("modules.visual.zone_manager.time.time", return_value=base_time + 2.0):
            events1 = zone.update({0: (50, 50)})

        # Second check — should NOT re-alert
        with patch("modules.visual.zone_manager.time.time", return_value=base_time + 5.0):
            events2 = zone.update({0: (50, 50)})

        assert len([e for e in events1 if e.type == "LOITERING"]) == 1
        assert len([e for e in events2 if e.type == "LOITERING"]) == 0


class TestCrowdAlert:
    """Crowd density alerting."""

    def test_crowd_alert_when_threshold_reached(self):
        """Reaching crowd_threshold people → CROWD_ALERT event."""
        zone = _square_zone(crowd_threshold=2)

        events = zone.update({0: (50, 50), 1: (60, 60)})

        crowd_events = [e for e in events if e.type == "CROWD_ALERT"]
        assert len(crowd_events) == 1
        assert crowd_events[0].occupancy == 2

    def test_no_crowd_alert_below_threshold(self):
        """Below crowd_threshold → no CROWD_ALERT."""
        zone = _square_zone(crowd_threshold=3)

        events = zone.update({0: (50, 50), 1: (60, 60)})

        crowd_events = [e for e in events if e.type == "CROWD_ALERT"]
        assert len(crowd_events) == 0

    def test_crowd_alert_resets_when_dispersed(self):
        """After crowd disperses and reforms, alert should fire again."""
        zone = _square_zone(crowd_threshold=2)

        # Crowd forms
        zone.update({0: (50, 50), 1: (60, 60)})

        # Crowd disperses
        zone.update({0: (50, 50)})

        # Crowd reforms
        events = zone.update({0: (50, 50), 1: (60, 60)})

        crowd_events = [e for e in events if e.type == "CROWD_ALERT"]
        assert len(crowd_events) == 1


class TestZoneManager:
    """Multi-zone management."""

    def test_manager_combines_events(self):
        """ZoneManager.update() should return events from all zones."""
        z1 = _square_zone("Zone 1")
        z2 = Zone("Zone 2", [(200, 0), (300, 0), (300, 100), (200, 100)])

        manager = ZoneManager([z1, z2])

        events = manager.update({0: (50, 50), 1: (250, 50)})

        # One entry in Zone 1, one entry in Zone 2
        entry_events = [e for e in events if e.type == "ZONE_ENTRY"]
        assert len(entry_events) == 2

    def test_default_zone_creation(self):
        """create_default() should produce one zone."""
        manager = ZoneManager.create_default(640, 480)
        assert len(manager.zones) == 1
        assert manager.zones[0].name == "Zone A"

    def test_stats_aggregation(self):
        """get_stats() should return per-zone summary."""
        zone = _square_zone()
        manager = ZoneManager([zone])
        manager.update({0: (50, 50)})

        stats = manager.get_stats()
        assert len(stats) == 1
        assert stats[0]["occupancy"] == 1
        assert stats[0]["enter_count"] == 1
