"""
IoU-based centroid tracker for multi-object tracking.

Extracted and refined from the Edge VCA demo pipeline. Associates
detections across frames using Intersection-over-Union (IoU) of
bounding boxes, maintaining persistent integer IDs for each tracked
object.

Algorithm:
    1. For each existing track, find the detection with highest IoU
    2. If IoU ≥ threshold → match (update position, reset disappear counter)
    3. Unmatched detections → register as new tracks
    4. Unmatched tracks → increment disappear counter
    5. Tracks exceeding MAX_DISAPPEARED → deregister (prune)

Why IoU-based instead of centroid-distance?
    IoU considers bounding box overlap, which is more robust to scale
    changes and partial occlusions than simple Euclidean distance between
    centroids. A person walking toward the camera grows in bbox size but
    their centroid might barely move — IoU handles this correctly.

Usage:
    tracker = CentroidTracker(max_disappeared=20, iou_threshold=0.3)
    objects, boxes = tracker.update(detections)
    # objects: {0: (320, 240), 1: (480, 300)}
    # boxes:   {0: (x1, y1, x2, y2), 1: (x1, y1, x2, y2)}
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any


class CentroidTracker:
    """Persistent multi-object tracker using IoU-based association.

    Each tracked object receives a unique integer ID that persists
    across frames as long as the object remains visible. When an
    object disappears for more than `max_disappeared` frames, its
    track is pruned.

    Attributes:
        objects:     Dict mapping track_id → (cx, cy) centroid.
        boxes:       Dict mapping track_id → (x1, y1, x2, y2) bbox.
        metadata:    Dict mapping track_id → arbitrary metadata dict.
        track_ages:  Dict mapping track_id → number of frames since creation.
    """

    def __init__(self, max_disappeared: int = 20, iou_threshold: float = 0.3):
        """Initialize the tracker.

        Args:
            max_disappeared: Number of consecutive frames an object can
                             be unmatched before its track is dropped.
            iou_threshold:   Minimum IoU overlap to consider a detection
                             as matching an existing track.
        """
        self._next_id: int = 0
        self.objects: dict[int, tuple[int, int]] = {}
        self.boxes: dict[int, tuple[int, int, int, int]] = {}
        self.metadata: dict[int, dict[str, Any]] = {}
        self.track_ages: dict[int, int] = {}
        self._disappeared: dict[int, int] = defaultdict(int)
        self._max_disappeared = max_disappeared
        self._iou_threshold = iou_threshold

    def update(
        self, detections: list[tuple[int, int, int, int]]
    ) -> tuple[dict[int, tuple[int, int]], dict[int, tuple[int, int, int, int]]]:
        """Process a new frame's detections and update track state.

        Args:
            detections: List of bounding boxes as (x1, y1, x2, y2) tuples.

        Returns:
            Tuple of (objects, boxes) where:
                objects: {track_id: (cx, cy)} — current centroid positions
                boxes:   {track_id: (x1, y1, x2, y2)} — current bounding boxes
        """
        # Increment age for all existing tracks
        for oid in self.track_ages:
            self.track_ages[oid] += 1

        # If no detections this frame, increment disappear counters
        if not detections:
            self._handle_no_detections()
            return dict(self.objects), dict(self.boxes)

        # Compute centroids for the new detections
        new_centroids = [((x1 + x2) // 2, (y1 + y2) // 2) for x1, y1, x2, y2 in detections]

        # First frame or no existing tracks → register all detections
        if not self.objects:
            for centroid, bbox in zip(new_centroids, detections, strict=False):
                self._register(centroid, bbox)
            return dict(self.objects), dict(self.boxes)

        # Match existing tracks to new detections via IoU
        matched_det_indices: set[int] = set()

        for oid, old_box in list(self.boxes.items()):
            best_iou = -1.0
            best_idx = -1

            for i, det_box in enumerate(detections):
                if i in matched_det_indices:
                    continue  # Already matched to another track
                score = self._compute_iou(old_box, det_box)
                if score > best_iou:
                    best_iou = score
                    best_idx = i

            if best_iou >= self._iou_threshold and best_idx >= 0:
                # Successful match — update track position
                self.objects[oid] = new_centroids[best_idx]
                self.boxes[oid] = detections[best_idx]
                self._disappeared[oid] = 0
                matched_det_indices.add(best_idx)
            else:
                # No match found — object might have left the frame
                self._disappeared[oid] += 1
                if self._disappeared[oid] > self._max_disappeared:
                    self._deregister(oid)

        # Register unmatched detections as new tracks
        for i in range(len(detections)):
            if i not in matched_det_indices:
                self._register(new_centroids[i], detections[i])

        return dict(self.objects), dict(self.boxes)

    # ─────────────── Track Lifecycle ──────────────────────

    def _register(self, centroid: tuple[int, int], bbox: tuple[int, int, int, int]) -> int:
        """Create a new track with a unique ID.

        Returns:
            The assigned track ID.
        """
        oid = self._next_id
        self.objects[oid] = centroid
        self.boxes[oid] = bbox
        self.metadata[oid] = {}
        self.track_ages[oid] = 0
        self._disappeared[oid] = 0
        self._next_id += 1
        return oid

    def _deregister(self, oid: int) -> None:
        """Remove a track and all its associated state."""
        for store in (self.objects, self.boxes, self.metadata, self.track_ages, self._disappeared):
            store.pop(oid, None)

    def _handle_no_detections(self) -> None:
        """Increment disappear counters and prune stale tracks."""
        for oid in list(self._disappeared.keys()):
            self._disappeared[oid] += 1
            if self._disappeared[oid] > self._max_disappeared:
                self._deregister(oid)

    # ─────────────── IoU Computation ──────────────────────

    @staticmethod
    def _compute_iou(
        box_a: tuple[int, int, int, int],
        box_b: tuple[int, int, int, int],
    ) -> float:
        """Compute Intersection-over-Union between two axis-aligned bounding boxes.

        IoU = Area(Intersection) / Area(Union)

        Both boxes are (x1, y1, x2, y2) format where (x1, y1) is top-left
        and (x2, y2) is bottom-right.

        Returns:
            IoU score in [0.0, 1.0]. Returns 0.0 if boxes don't overlap
            or if the union area is zero.
        """
        # Intersection rectangle
        ix1 = max(box_a[0], box_b[0])
        iy1 = max(box_a[1], box_b[1])
        ix2 = min(box_a[2], box_b[2])
        iy2 = min(box_a[3], box_b[3])

        intersection = max(0, ix2 - ix1) * max(0, iy2 - iy1)

        # Union = Area(A) + Area(B) - Intersection
        area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
        area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
        union = area_a + area_b - intersection

        if union <= 0:
            return 0.0

        return intersection / union
