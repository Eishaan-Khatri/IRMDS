"""
Physics-based speed estimation for tracked objects.

Calculates real-world velocity (meters per second) from pixel
displacement using dynamic calibration based on bounding box height.

Calibration principle:
    If a person's bounding box is 170 pixels tall and we assume the
    average human height is 1.7 meters, then:
        pixels_per_meter = 170 / 1.7 = 100 px/m

    A centroid displacement of 50 pixels over 0.5 seconds:
        speed = (50 px / 0.5 s) / 100 px/m = 1.0 m/s

    This calibration is *per-object, per-frame*, so it adapts as
    people walk closer to or farther from the camera.

Limitations (documented for engineering maturity):
    - Assumes vertical camera with minimal lens distortion
    - Calibration degrades when person is partially occluded (shorter bbox)
    - Very close/far subjects produce extreme ppm values
    - Does not account for camera pitch angle

Usage:
    estimator = SpeedEstimator(config)
    result = estimator.estimate(object_id=3, centroid=(320, 240),
                                bbox=(300, 200, 340, 370), timestamp=time.time())
    # → SpeedResult(speed_ms=1.2, classification='WALKING', is_anomaly=False)
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from core.config import IRMDSConfig


class SpeedClassification(str, Enum):
    """Human motion classification based on speed thresholds."""

    STATIONARY = "STATIONARY"  # < 0.5 m/s — standing still or minor sway
    WALKING = "WALKING"        # 0.5 – 2.2 m/s — normal walking pace
    RUNNING = "RUNNING"        # > 2.2 m/s — fast movement, potential anomaly


@dataclass(frozen=True, slots=True)
class SpeedResult:
    """Result of a speed estimation for one tracked object.

    Attributes:
        speed_ms:        Estimated speed in meters per second.
        classification:  Human-readable motion category.
        is_anomaly:      True if speed exceeds the configured alert threshold.
    """

    speed_ms: float
    classification: SpeedClassification
    is_anomaly: bool


class SpeedEstimator:
    """Per-object speed estimator using rolling centroid history.

    Maintains a sliding window of centroid positions and timestamps
    for each tracked object. Speed is computed from the displacement
    between the oldest and newest entries in the window, divided by
    the elapsed time, and converted from pixels to meters using
    dynamic bbox-height calibration.

    The rolling window approach smooths out frame-to-frame jitter
    that would make instantaneous per-frame speed noisy and unreliable.
    """

    def __init__(self, config: IRMDSConfig):
        self._human_height_m = config.visual_human_height_m
        self._speed_alert_threshold = config.visual_speed_alert_ms
        self._history_len = 30  # Frames of history to retain

        # Per-object rolling histories
        self._centroids: dict[int, deque[tuple[int, int]]] = defaultdict(
            lambda: deque(maxlen=self._history_len)
        )
        self._timestamps: dict[int, deque[float]] = defaultdict(
            lambda: deque(maxlen=self._history_len)
        )

    def estimate(
        self,
        object_id: int,
        centroid: tuple[int, int],
        bbox: tuple[int, int, int, int],
        timestamp: float | None = None,
    ) -> SpeedResult:
        """Estimate speed for a tracked object.

        Args:
            object_id:  Persistent track ID from the tracker.
            centroid:   Current (cx, cy) centroid position in pixels.
            bbox:       Current (x1, y1, x2, y2) bounding box.
            timestamp:  Current time in seconds (default: time.time()).

        Returns:
            SpeedResult with estimated velocity, classification, and anomaly flag.
        """
        if timestamp is None:
            timestamp = time.time()

        # Append current observation to rolling history
        self._centroids[object_id].append(centroid)
        self._timestamps[object_id].append(timestamp)

        history = self._centroids[object_id]
        times = self._timestamps[object_id]

        # Need at least 5 frames of history for a reliable estimate.
        # Fewer frames = too noisy, especially at high FPS where
        # per-frame displacement is sub-pixel.
        if len(history) < 5:
            return SpeedResult(
                speed_ms=0.0,
                classification=SpeedClassification.STATIONARY,
                is_anomaly=False,
            )

        # Pixel displacement from oldest to newest observation
        dx = history[-1][0] - history[0][0]
        dy = history[-1][1] - history[0][1]
        distance_px = float(np.hypot(dx, dy))

        # Time elapsed across the window
        dt = times[-1] - times[0]

        if dt < 0.1:
            # Less than 100ms of data — unreliable, skip
            return SpeedResult(
                speed_ms=0.0,
                classification=SpeedClassification.STATIONARY,
                is_anomaly=False,
            )

        # Dynamic calibration: pixels-per-meter from bbox height
        # Taller bbox (closer person) = more pixels per meter
        bbox_height = bbox[3] - bbox[1]
        pixels_per_meter = bbox_height / self._human_height_m

        if pixels_per_meter <= 0:
            return SpeedResult(
                speed_ms=0.0,
                classification=SpeedClassification.STATIONARY,
                is_anomaly=False,
            )

        # Convert pixel velocity to real-world velocity
        speed_ms = (distance_px / dt) / pixels_per_meter

        # Classify the motion
        if speed_ms < 0.5:
            classification = SpeedClassification.STATIONARY
        elif speed_ms <= self._speed_alert_threshold:
            classification = SpeedClassification.WALKING
        else:
            classification = SpeedClassification.RUNNING

        return SpeedResult(
            speed_ms=round(speed_ms, 2),
            classification=classification,
            is_anomaly=speed_ms > self._speed_alert_threshold,
        )

    def remove_track(self, object_id: int) -> None:
        """Clean up history for a deregistered track."""
        self._centroids.pop(object_id, None)
        self._timestamps.pop(object_id, None)

    def reset(self) -> None:
        """Clear all tracking history."""
        self._centroids.clear()
        self._timestamps.clear()
