"""
Integration test for the visual pipeline.

Unlike unit tests (which test components in isolation), this verifies
that all visual sub-components work together correctly:

    Detector → Tracker → ZoneManager → SpeedEstimator → EventBus → MetricsCollector

Since we can't rely on a real camera or YOLOv8 weights in CI, we mock
the Detector and FrameSource to produce controlled, repeatable inputs.
The test then verifies that the pipeline produces the expected events
and metrics from those inputs.

Test strategy:
    1. Mock FrameSource to yield synthetic black frames
    2. Mock Detector to produce known bounding boxes at controlled positions
    3. Run the pipeline for a short duration
    4. Assert that zone entry events were emitted to the event bus
    5. Assert that metrics were pushed to the metrics collector
    6. Assert that the pipeline can be stopped cleanly
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import numpy as np

from core.config import IRMDSConfig
from core.event_bus import Event, EventBus, Severity
from core.metrics_collector import MetricsCollector
from modules.visual.detector import Detection
from modules.visual.pipeline import VisualPipeline


# ─────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────


def _make_config(**overrides) -> IRMDSConfig:
    """Config with test-friendly defaults."""
    defaults = {
        "visual_source": "0",
        "visual_frame_width": 640,
        "visual_frame_height": 480,
        "visual_frame_skip": 1,
        "visual_confidence": 0.4,
        "visual_iou_threshold": 0.3,
        "visual_max_disappeared": 5,
        "visual_loiter_seconds": 2,
        "visual_crowd_threshold": 3,
        "visual_speed_alert_ms": 2.2,
        "visual_human_height_m": 1.7,
    }
    defaults.update(overrides)
    return IRMDSConfig(**defaults)


def _make_synthetic_frame(width: int = 640, height: int = 480) -> np.ndarray:
    """Create a blank BGR frame for testing."""
    return np.zeros((height, width, 3), dtype=np.uint8)


class MockFrameSource:
    """Produces a fixed number of synthetic frames, then signals exhaustion.

    This simulates a video file that ends after N frames, giving the
    pipeline a natural exit condition without needing `stop()`.
    """

    def __init__(self, max_frames: int = 30, width: int = 640, height: int = 480):
        self._max_frames = max_frames
        self._width = width
        self._height = height
        self._frame_count = 0
        self.source_type = MagicMock()
        self.source_type.value = "test"

    def open(self) -> bool:
        return True

    def read(self) -> tuple[bool, np.ndarray | None]:
        if self._frame_count >= self._max_frames:
            return False, None
        self._frame_count += 1
        return True, _make_synthetic_frame(self._width, self._height)

    def release(self) -> None:
        pass

    @property
    def frame_count(self) -> int:
        return self._frame_count

    @property
    def is_opened(self) -> bool:
        return self._frame_count < self._max_frames


def _make_zone_detector():
    """Detector that places a person squarely in the default zone center.

    The default zone covers x=160..480, y=120..360 (25% margin on 640x480).
    This detector places a person at centroid (320, 240) — dead center.
    It moves slowly (2px per frame) so it stays inside the zone.
    """
    class InZoneDetector:
        def __init__(self):
            self._call_count = 0
            self.last_latency_ms = 3.0

        def detect(self, frame):
            self._call_count += 1
            # Small movement within zone center: x from 295..325
            x = 295 + self._call_count * 2
            return [Detection(
                x1=x, y1=155, x2=x + 50, y2=325,
                confidence=0.9, class_id=0,
            )]

    return InZoneDetector()


def _standard_patches(mock_source, mock_detector):
    """Return the standard set of patches for pipeline integration tests.

    Patches FrameSource.from_config, Detector constructor, and Path
    (to force default zone creation instead of loading from disk).
    """
    return (
        patch("modules.visual.pipeline.FrameSource.from_config", return_value=mock_source),
        patch("modules.visual.pipeline.Detector", return_value=mock_detector),
        patch("modules.visual.pipeline.Path", **{"return_value.exists.return_value": False}),
    )


# ─────────────────────────────────────────────────────────
# Integration Tests
# ─────────────────────────────────────────────────────────


class TestVisualPipelineIntegration:
    """End-to-end integration tests for the visual pipeline.

    These tests verify that all sub-components (detector, tracker,
    zones, speed, heatmap) work together correctly when orchestrated
    by the pipeline.
    """

    def test_pipeline_emits_zone_events(self):
        """Pipeline should emit ZONE_ENTRY events when detections
        fall inside the configured zone.

        The default zone covers the center 50% of the frame (x=160..480,
        y=120..360). The mock detector places detections at (320, 240) —
        squarely inside.
        """
        event_bus = EventBus(max_history=200)
        metrics = MetricsCollector()
        config = _make_config()

        received_events: list[Event] = []
        event_bus.subscribe(received_events.append)

        pipeline = VisualPipeline(event_bus, metrics, config)

        mock_source = MockFrameSource(max_frames=15)
        mock_detector = _make_zone_detector()

        p1, p2, p3 = _standard_patches(mock_source, mock_detector)
        with p1, p2, p3:
            pipeline._running.set()
            pipeline._run()

        # Verify: zone entry events should have been emitted
        zone_events = [e for e in received_events if e.type == "ZONE_ENTRY"]
        assert len(zone_events) > 0, (
            f"Expected ZONE_ENTRY events. Got event types: "
            f"{[e.type for e in received_events]}"
        )
        assert zone_events[0].module == "visual"

    def test_pipeline_pushes_metrics(self):
        """Pipeline should push metrics (fps, latency, active_tracks)
        to the MetricsCollector on every frame.
        """
        event_bus = EventBus(max_history=200)
        metrics = MetricsCollector()
        config = _make_config()

        pipeline = VisualPipeline(event_bus, metrics, config)

        mock_source = MockFrameSource(max_frames=10)
        mock_detector = _make_zone_detector()

        p1, p2, p3 = _standard_patches(mock_source, mock_detector)
        with p1, p2, p3:
            pipeline._running.set()
            pipeline._run()

        # Verify: metrics should have been pushed for the visual module
        latest = metrics.get_latest("visual")
        assert latest != {}, "Expected metrics to be pushed"
        assert "fps" in latest, "fps metric should be present"
        assert "latency_ms" in latest, "latency_ms metric should be present"
        assert "active_tracks" in latest, "active_tracks metric should be present"
        assert latest["active_tracks"] >= 0

    def test_pipeline_handles_source_failure_gracefully(self):
        """If the frame source can't open, the pipeline should emit
        a SOURCE_ERROR event and exit without crashing.
        """
        event_bus = EventBus(max_history=200)
        metrics = MetricsCollector()
        config = _make_config()

        received_events: list[Event] = []
        event_bus.subscribe(received_events.append)

        pipeline = VisualPipeline(event_bus, metrics, config)

        # Create a source that fails to open
        fail_source = MockFrameSource()
        fail_source.open = MagicMock(return_value=False)

        with patch("modules.visual.pipeline.FrameSource.from_config", return_value=fail_source):
            pipeline._running.set()
            pipeline._run()  # Should not raise

        # Verify: a SOURCE_ERROR event was emitted
        error_events = [e for e in received_events if e.type == "SOURCE_ERROR"]
        assert len(error_events) == 1
        assert error_events[0].severity == Severity.CRITICAL

    def test_pipeline_start_stop_lifecycle(self):
        """Pipeline should start in a background thread and stop
        cleanly when stop() is called.
        """
        event_bus = EventBus(max_history=200)
        metrics = MetricsCollector()
        config = _make_config()

        pipeline = VisualPipeline(event_bus, metrics, config)

        # Use a source that produces frames indefinitely
        infinite_source = MockFrameSource(max_frames=999999)
        mock_detector = _make_zone_detector()

        p1, p2, p3 = _standard_patches(infinite_source, mock_detector)
        with p1, p2, p3:
            # Start the pipeline (runs in background thread)
            pipeline.start()
            assert pipeline.status.value in ("starting", "running")

            # Let it process a few frames
            time.sleep(0.3)

            # Stop the pipeline
            pipeline.stop()
            assert pipeline.status.value == "stopped"

        # Metrics should have been pushed during the run
        latest = metrics.get_latest("visual")
        assert latest != {}

    def test_pipeline_speed_anomaly_detection(self):
        """When a tracked object moves fast enough, the pipeline should
        emit a SPEED_ANOMALY event.

        To make speed estimation work in a test (where all frames process
        in microseconds), we mock time.time() across all modules to simulate
        realistic inter-frame timing (200ms per frame).

        The detector controls the clock: it sets a shared timestamp before
        returning detections, and all time.time() calls just read that value.
        """
        event_bus = EventBus(max_history=500)
        metrics = MetricsCollector()
        # Very low speed threshold — 0.8 m/s so moderate movement triggers anomaly
        config = _make_config(visual_speed_alert_ms=0.8)

        received_events: list[Event] = []
        event_bus.subscribe(received_events.append)

        pipeline = VisualPipeline(event_bus, metrics, config)

        # Shared clock — detector controls it, all modules read it
        fake_clock = {"t": 1000.0}

        def fake_time():
            """All modules read the same timestamp for a given frame."""
            return fake_clock["t"]

        # Detector: person walks steadily at 20px/frame within the zone.
        # Moving 20px keeps IoU > 0.3 so the tracker maintains the SAME object ID.
        # Default zone: x=160..480, y=120..360
        # bbox height=170 → ppm=100, 20px/0.2s/100ppm = 1.0 m/s > 0.8 alert threshold
        class FastDetector:
            def __init__(self):
                self._call_count = 0
                self.last_latency_ms = 3.0

            def detect(self, frame):
                self._call_count += 1
                # Set the clock for this frame — 200ms per frame
                fake_clock["t"] = 1000.0 + self._call_count * 0.2
                # Linear walk: x from 200 → 420 (inside zone)
                x = min(200 + self._call_count * 20, 420)
                return [Detection(
                    x1=x, y1=155, x2=x + 50, y2=325,
                    confidence=0.9, class_id=0,
                )]

        mock_source = MockFrameSource(max_frames=12)

        p1, p2, p3 = _standard_patches(mock_source, FastDetector())
        with p1, p2, p3:
            with (
                patch("modules.visual.pipeline.time.time", side_effect=fake_time),
                patch("modules.visual.zone_manager.time.time", side_effect=fake_time),
                patch("modules.visual.speed_estimator.time.time", side_effect=fake_time),
            ):
                pipeline._running.set()
                pipeline._run()

        # With 0.3 m/s threshold and ~1.5 m/s movement, expect SPEED_ANOMALY
        speed_events = [e for e in received_events if e.type == "SPEED_ANOMALY"]
        assert len(speed_events) >= 1, (
            f"Expected SPEED_ANOMALY events. Got types: "
            f"{set(e.type for e in received_events)}"
        )
        assert speed_events[0].severity == Severity.CRITICAL

    def test_pipeline_metrics_contain_zone_stats(self):
        """Pushed metrics should include zone occupancy statistics."""
        event_bus = EventBus(max_history=200)
        metrics = MetricsCollector()
        config = _make_config()

        pipeline = VisualPipeline(event_bus, metrics, config)

        mock_source = MockFrameSource(max_frames=10)
        mock_detector = _make_zone_detector()

        p1, p2, p3 = _standard_patches(mock_source, mock_detector)
        with p1, p2, p3:
            pipeline._running.set()
            pipeline._run()

        latest = metrics.get_latest("visual")
        assert "zone_stats" in latest, "zone_stats should be in metrics"
        assert isinstance(latest["zone_stats"], list)
