"""
Unit tests for the EventBus — the central nervous system of IRMDS.

Tests cover:
    - Publishing and subscribing
    - Filter by module, type, and severity
    - Event history retrieval
    - Unsubscribe behavior
    - Thread safety (concurrent publish)
    - Subscriber error isolation (one bad subscriber doesn't break others)
"""

from __future__ import annotations

import threading

from core.event_bus import Event, EventBus, Severity


class TestEventPublishSubscribe:
    """Basic publish/subscribe functionality."""

    def test_subscriber_receives_published_event(self, event_bus: EventBus):
        """Publishing an event should trigger the subscriber callback."""
        received: list[Event] = []
        event_bus.subscribe(received.append)

        event = Event(module="test", type="TEST_EVENT", severity=Severity.INFO)
        event_bus.publish(event)

        assert len(received) == 1
        assert received[0].module == "test"
        assert received[0].type == "TEST_EVENT"

    def test_multiple_subscribers_all_receive(self, event_bus: EventBus):
        """All subscribers should receive the same event."""
        received_a: list[Event] = []
        received_b: list[Event] = []

        event_bus.subscribe(received_a.append)
        event_bus.subscribe(received_b.append)

        event = Event(module="test", type="MULTI", severity=Severity.INFO)
        event_bus.publish(event)

        assert len(received_a) == 1
        assert len(received_b) == 1

    def test_event_has_unique_id(self, event_bus: EventBus):
        """Each event should have a unique ID."""
        e1 = Event(module="test", type="A", severity=Severity.INFO)
        e2 = Event(module="test", type="B", severity=Severity.INFO)
        assert e1.id != e2.id

    def test_event_has_timestamp(self, event_bus: EventBus):
        """Events should have an ISO 8601 timestamp."""
        event = Event(module="test", type="A", severity=Severity.INFO)
        assert "T" in event.timestamp  # Basic ISO 8601 check


class TestEventFiltering:
    """Filter-based subscription routing."""

    def test_filter_by_module(self, event_bus: EventBus):
        """Subscriber with module filter should only receive matching events."""
        received: list[Event] = []
        event_bus.subscribe(received.append, filter_module="visual")

        event_bus.publish(Event(module="visual", type="A", severity=Severity.INFO))
        event_bus.publish(Event(module="network", type="B", severity=Severity.INFO))

        assert len(received) == 1
        assert received[0].module == "visual"

    def test_filter_by_type(self, event_bus: EventBus):
        """Subscriber with type filter should only receive matching events."""
        received: list[Event] = []
        event_bus.subscribe(received.append, filter_type="ZONE_ENTRY")

        event_bus.publish(Event(module="visual", type="ZONE_ENTRY", severity=Severity.INFO))
        event_bus.publish(Event(module="visual", type="ZONE_EXIT", severity=Severity.INFO))

        assert len(received) == 1
        assert received[0].type == "ZONE_ENTRY"

    def test_filter_by_severity_minimum(self, event_bus: EventBus):
        """Severity filter should pass events at or above the specified level."""
        received: list[Event] = []
        event_bus.subscribe(received.append, filter_severity=Severity.WARNING)

        event_bus.publish(Event(module="test", type="A", severity=Severity.INFO))
        event_bus.publish(Event(module="test", type="B", severity=Severity.WARNING))
        event_bus.publish(Event(module="test", type="C", severity=Severity.CRITICAL))

        # INFO should be filtered out, WARNING and CRITICAL should pass
        assert len(received) == 2
        severities = {e.severity for e in received}
        assert Severity.INFO not in severities
        assert Severity.WARNING in severities
        assert Severity.CRITICAL in severities

    def test_combined_filters(self, event_bus: EventBus):
        """Multiple filters should be AND-ed together."""
        received: list[Event] = []
        event_bus.subscribe(
            received.append,
            filter_module="visual",
            filter_severity=Severity.CRITICAL,
        )

        # Matches module but not severity
        event_bus.publish(Event(module="visual", type="A", severity=Severity.INFO))
        # Matches severity but not module
        event_bus.publish(Event(module="network", type="B", severity=Severity.CRITICAL))
        # Matches both
        event_bus.publish(Event(module="visual", type="C", severity=Severity.CRITICAL))

        assert len(received) == 1
        assert received[0].type == "C"


class TestUnsubscribe:
    """Subscription removal."""

    def test_unsubscribe_stops_delivery(self, event_bus: EventBus):
        """After unsubscribe, the callback should not receive events."""
        received: list[Event] = []
        sub_id = event_bus.subscribe(received.append)

        event_bus.publish(Event(module="test", type="A", severity=Severity.INFO))
        assert len(received) == 1

        event_bus.unsubscribe(sub_id)
        event_bus.publish(Event(module="test", type="B", severity=Severity.INFO))
        assert len(received) == 1  # No new events

    def test_unsubscribe_returns_true_for_existing(self, event_bus: EventBus):
        """Unsubscribing an existing subscription should return True."""
        sub_id = event_bus.subscribe(lambda e: None)
        assert event_bus.unsubscribe(sub_id) is True

    def test_unsubscribe_returns_false_for_unknown(self, event_bus: EventBus):
        """Unsubscribing a non-existent ID should return False."""
        assert event_bus.unsubscribe("sub_nonexistent") is False


class TestEventHistory:
    """Event history storage and retrieval."""

    def test_history_stores_events(self, event_bus: EventBus):
        """Published events should be queryable from history."""
        event_bus.publish(Event(module="visual", type="A", severity=Severity.INFO))
        event_bus.publish(Event(module="network", type="B", severity=Severity.WARNING))

        history = event_bus.get_history(limit=10)
        assert len(history) == 2

    def test_history_returns_newest_first(self, event_bus: EventBus):
        """History should be in reverse chronological order."""
        event_bus.publish(Event(module="test", type="FIRST", severity=Severity.INFO))
        event_bus.publish(Event(module="test", type="SECOND", severity=Severity.INFO))

        history = event_bus.get_history(limit=10)
        assert history[0].type == "SECOND"
        assert history[1].type == "FIRST"

    def test_history_filter_by_module(self, event_bus: EventBus):
        """History filter should return only matching module events."""
        event_bus.publish(Event(module="visual", type="A", severity=Severity.INFO))
        event_bus.publish(Event(module="network", type="B", severity=Severity.INFO))

        history = event_bus.get_history(module="visual")
        assert len(history) == 1
        assert history[0].module == "visual"

    def test_history_respects_limit(self, event_bus: EventBus):
        """History should return at most `limit` events."""
        for i in range(10):
            event_bus.publish(Event(module="test", type=f"E{i}", severity=Severity.INFO))

        history = event_bus.get_history(limit=3)
        assert len(history) == 3

    def test_history_max_size(self):
        """History should not exceed max_history size."""
        bus = EventBus(max_history=5)
        for i in range(10):
            bus.publish(Event(module="test", type=f"E{i}", severity=Severity.INFO))

        history = bus.get_history(limit=100)
        assert len(history) == 5

    def test_total_events_counter(self, event_bus: EventBus):
        """Total event counter should track all-time publishes."""
        for _ in range(5):
            event_bus.publish(Event(module="test", type="X", severity=Severity.INFO))

        assert event_bus.total_events == 5


class TestSubscriberErrorIsolation:
    """Fault tolerance — one bad subscriber must not break others."""

    def test_broken_subscriber_doesnt_block_others(self, event_bus: EventBus):
        """If one subscriber raises, other subscribers should still receive."""
        received_good: list[Event] = []

        def bad_subscriber(event: Event):
            raise ValueError("I'm broken!")

        event_bus.subscribe(bad_subscriber)
        event_bus.subscribe(received_good.append)

        event_bus.publish(Event(module="test", type="A", severity=Severity.INFO))

        # Despite the first subscriber crashing, the second should receive
        assert len(received_good) == 1


class TestThreadSafety:
    """Concurrent publish from multiple threads."""

    def test_concurrent_publish(self, event_bus: EventBus):
        """Multiple threads publishing simultaneously should not lose events."""
        received: list[Event] = []
        event_bus.subscribe(received.append)

        def publish_n(n: int):
            for i in range(n):
                event_bus.publish(Event(module="thread", type=f"E{i}", severity=Severity.INFO))

        threads = [threading.Thread(target=publish_n, args=(50,)) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 4 threads × 50 events = 200 events
        assert len(received) == 200
        assert event_bus.total_events == 200
