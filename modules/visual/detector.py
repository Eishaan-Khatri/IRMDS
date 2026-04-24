"""
YOLOv8 inference wrapper for the visual anomaly detection module.

Encapsulates model loading, prediction, and result parsing into a clean
interface that the pipeline orchestrator calls on every frame:

    detector = Detector(config)
    detections = detector.detect(frame)
    # → [Detection(x1=10, y1=20, x2=100, y2=200, confidence=0.87, class_id=0)]

Design decisions:
    - Lazy model loading: The YOLOv8 model file (~6.5 MB) is only loaded
      on the first call to `detect()`, not at import time. This keeps
      module import fast and allows tests to run without the weights file.
    - Class filtering: Only returns detections for configured class IDs
      (default: person=0). This prevents the tracker from wasting cycles
      on irrelevant objects like chairs or backpacks.
    - Latency tracking: Every inference call records its duration. The
      pipeline reads this to report FPS and latency to the dashboard.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from core.config import IRMDSConfig


@dataclass(frozen=True, slots=True)
class Detection:
    """A single object detection from one frame.

    Coordinates are in pixel space (top-left origin), matching
    the standard OpenCV / YOLO convention.

    Attributes:
        x1, y1: Top-left corner of the bounding box.
        x2, y2: Bottom-right corner of the bounding box.
        confidence: Model's confidence score (0.0–1.0).
        class_id: COCO class index (0=person, 2=car, etc.).
    """

    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float
    class_id: int

    @property
    def centroid(self) -> tuple[int, int]:
        """Center point of the bounding box."""
        return ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)

    @property
    def bbox(self) -> tuple[int, int, int, int]:
        """Bounding box as (x1, y1, x2, y2) tuple."""
        return (self.x1, self.y1, self.x2, self.y2)

    @property
    def height(self) -> int:
        """Height of the bounding box in pixels."""
        return self.y2 - self.y1

    @property
    def width(self) -> int:
        """Width of the bounding box in pixels."""
        return self.x2 - self.x1


class Detector:
    """YOLOv8-based object detector with lazy model loading.

    The detector is stateless between frames — it holds no tracking
    information. Each call to `detect()` is independent.

    Attributes:
        last_latency_ms: Inference latency of the most recent frame.
    """

    def __init__(self, config: IRMDSConfig):
        self._model_path = config.visual_model_path
        self._confidence = config.visual_confidence
        self._classes = [0]  # Person class by default
        self._model = None   # Loaded lazily on first detect()
        self.last_latency_ms: float = 0.0

    def detect(self, frame: np.ndarray) -> list[Detection]:
        """Run YOLOv8 inference on a single frame.

        Args:
            frame: BGR image as a numpy array (H, W, 3).

        Returns:
            List of Detection objects passing the confidence threshold,
            filtered to only the configured class IDs.
        """
        if self._model is None:
            self._load_model()

        t_start = time.perf_counter()

        # Run inference with verbose=False to suppress Ultralytics' per-frame logs
        results = self._model(
            frame,
            classes=self._classes,
            conf=self._confidence,
            verbose=False,
        )[0]

        self.last_latency_ms = (time.perf_counter() - t_start) * 1000.0

        return self._parse_results(results)

    def _load_model(self) -> None:
        """Load the YOLOv8 model from disk.

        Deferred to first use so that:
        1. Import of this module is instant (no 2-second model load)
        2. Unit tests can mock the detector without needing weights
        """
        from ultralytics import YOLO

        self._model = YOLO(self._model_path)

    @staticmethod
    def _parse_results(results) -> list[Detection]:
        """Convert Ultralytics Results object into our Detection dataclass.

        This isolates the Ultralytics API surface to a single method.
        If Ultralytics changes their results format in a future version,
        only this method needs updating.
        """
        detections: list[Detection] = []

        if results.boxes is None or len(results.boxes) == 0:
            return detections

        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            confidence = float(box.conf[0])
            class_id = int(box.cls[0])

            detections.append(Detection(
                x1=x1, y1=y1, x2=x2, y2=y2,
                confidence=confidence,
                class_id=class_id,
            ))

        return detections
