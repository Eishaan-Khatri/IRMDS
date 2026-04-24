"""
Unit tests for the physics-based speed estimator.

Tests cover:
    - Known displacement → correct m/s calculation
    - Stationary objects → near-zero speed
    - Dynamic calibration via bbox height
    - Insufficient history edge case
    - Speed classification (STATIONARY/WALKING/RUNNING)
    - Anomaly flag behavior
"""

from __future__ import annotations

from core.config import IRMDSConfig
from modules.visual.speed_estimator import (
    SpeedClassification,
    SpeedEstimator,
)


def _make_estimator(**overrides) -> SpeedEstimator:
    """Create an estimator with test-friendly config."""
    defaults = {
        "visual_human_height_m": 1.7,
        "visual_speed_alert_ms": 2.2,
    }
    defaults.update(overrides)
    return SpeedEstimator(IRMDSConfig(**defaults))


class TestSpeedCalculation:
    """Verify the physics math is correct."""

    def test_known_displacement_gives_correct_speed(self):
        """A known pixel displacement over time → expected m/s.

        Setup:
            - bbox height = 170px → ppm = 170/1.7 = 100 px/m
            - Move 100px over 1 second → (100/1.0)/100 = 1.0 m/s
        """
        estimator = _make_estimator()
        bbox = (0, 0, 50, 170)  # height = 170px → 100 px/m

        # Feed 6 frames (need ≥ 5 for reliable estimate)
        for i in range(6):
            centroid = (100 + i * 20, 100)  # 20px per frame
            result = estimator.estimate(
                object_id=0,
                centroid=centroid,
                bbox=bbox,
                timestamp=1000.0 + i * 0.2,  # 0.2s apart
            )

        # Total: 100px over 1.0s with ppm=100 → 1.0 m/s
        assert 0.8 <= result.speed_ms <= 1.2

    def test_stationary_object_has_near_zero_speed(self):
        """An object that doesn't move should have speed ≈ 0."""
        estimator = _make_estimator()
        bbox = (0, 0, 50, 170)

        for i in range(6):
            result = estimator.estimate(
                object_id=0,
                centroid=(100, 100),  # Same position every frame
                bbox=bbox,
                timestamp=1000.0 + i * 0.2,
            )

        assert result.speed_ms < 0.5
        assert result.classification == SpeedClassification.STATIONARY

    def test_insufficient_history_returns_zero(self):
        """With < 5 frames of history, speed should be 0."""
        estimator = _make_estimator()
        result = estimator.estimate(
            object_id=0,
            centroid=(100, 100),
            bbox=(0, 0, 50, 170),
            timestamp=1000.0,
        )
        assert result.speed_ms == 0.0
        assert result.classification == SpeedClassification.STATIONARY


class TestDynamicCalibration:
    """Verify that bbox height calibrates the speed correctly."""

    def test_taller_bbox_gives_lower_speed(self):
        """A taller bbox (closer person) means more px/m → lower speed for same movement."""
        estimator = _make_estimator()

        # Short bbox (far away person): height = 85px → ppm = 50
        for i in range(6):
            result_far = estimator.estimate(
                object_id=0,
                centroid=(100 + i * 20, 100),
                bbox=(0, 0, 50, 85),
                timestamp=1000.0 + i * 0.2,
            )

        estimator_close = _make_estimator()

        # Tall bbox (close person): height = 340px → ppm = 200
        for i in range(6):
            result_close = estimator_close.estimate(
                object_id=1,
                centroid=(100 + i * 20, 100),
                bbox=(0, 0, 50, 340),
                timestamp=1000.0 + i * 0.2,
            )

        # Same pixel displacement, but the close person should have lower speed
        assert result_close.speed_ms < result_far.speed_ms


class TestClassification:
    """Verify speed classification thresholds."""

    def test_walking_classification(self):
        """Speed between 0.5 and 2.2 m/s should be WALKING."""
        estimator = _make_estimator()
        bbox = (0, 0, 50, 170)  # ppm = 100

        # Move at ~1.5 m/s: 150px/s → 1.5 m/s with ppm=100
        for i in range(6):
            result = estimator.estimate(
                object_id=0,
                centroid=(100 + i * 30, 100),
                bbox=bbox,
                timestamp=1000.0 + i * 0.2,
            )

        assert result.classification == SpeedClassification.WALKING
        assert not result.is_anomaly

    def test_running_classification_triggers_anomaly(self):
        """Speed > 2.2 m/s should be RUNNING and flagged as anomaly."""
        estimator = _make_estimator()
        bbox = (0, 0, 50, 170)  # ppm = 100

        # Move at ~4.0 m/s: 400px/s → 4.0 m/s
        for i in range(6):
            result = estimator.estimate(
                object_id=0,
                centroid=(100 + i * 80, 100),
                bbox=bbox,
                timestamp=1000.0 + i * 0.2,
            )

        assert result.classification == SpeedClassification.RUNNING
        assert result.is_anomaly


class TestTrackCleanup:
    """Verify cleanup of deregistered tracks."""

    def test_remove_track_clears_history(self):
        """Removing a track should free its history buffers."""
        estimator = _make_estimator()

        for i in range(6):
            estimator.estimate(0, (100 + i, 100), (0, 0, 50, 170), 1000.0 + i)

        estimator.remove_track(0)
        assert 0 not in estimator._centroids
        assert 0 not in estimator._timestamps
