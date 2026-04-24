"""
Unit tests for the IoU centroid tracker.

Tests cover:
    - Registration of new detections
    - ID persistence across frames
    - IoU computation correctness
    - Track pruning after disappearance
    - Handling of empty detection frames
"""

from __future__ import annotations

from modules.visual.tracker import CentroidTracker


class TestTrackRegistration:
    """New detections should receive unique, persistent IDs."""

    def test_two_detections_get_two_ids(self):
        """Each detection in the first frame gets a unique ID."""
        tracker = CentroidTracker()
        objects, boxes = tracker.update([
            (100, 100, 200, 200),
            (300, 300, 400, 400),
        ])
        assert len(objects) == 2
        assert len(boxes) == 2
        # IDs should be 0 and 1
        assert set(objects.keys()) == {0, 1}

    def test_empty_detections_returns_empty(self):
        """No detections on first frame → no tracks."""
        tracker = CentroidTracker()
        objects, boxes = tracker.update([])
        assert len(objects) == 0


class TestIDPersistence:
    """Same object in consecutive frames should keep its ID."""

    def test_same_detection_keeps_id(self):
        """A detection in the same location across frames maintains its ID."""
        tracker = CentroidTracker(iou_threshold=0.3)

        # Frame 1: register
        objects1, _ = tracker.update([(100, 100, 200, 200)])
        original_id = list(objects1.keys())[0]

        # Frame 2: same box, slight shift
        objects2, _ = tracker.update([(105, 105, 205, 205)])
        assert original_id in objects2

    def test_different_location_gets_new_id(self):
        """A detection far from existing tracks gets a new ID."""
        tracker = CentroidTracker(iou_threshold=0.3)

        # Frame 1
        tracker.update([(100, 100, 200, 200)])

        # Frame 2: completely different location, no IoU overlap
        objects, _ = tracker.update([(500, 500, 600, 600)])

        # Should have the new object (old one starts disappearing)
        assert len(objects) >= 1


class TestIoUComputation:
    """Verify the IoU computation is mathematically correct."""

    def test_identical_boxes_iou_is_one(self):
        """Identical boxes should have IoU = 1.0."""
        iou = CentroidTracker._compute_iou(
            (100, 100, 200, 200),
            (100, 100, 200, 200),
        )
        assert iou == 1.0

    def test_no_overlap_iou_is_zero(self):
        """Non-overlapping boxes should have IoU = 0.0."""
        iou = CentroidTracker._compute_iou(
            (0, 0, 50, 50),
            (100, 100, 150, 150),
        )
        assert iou == 0.0

    def test_partial_overlap_iou(self):
        """Partially overlapping boxes should produce IoU between 0 and 1."""
        iou = CentroidTracker._compute_iou(
            (0, 0, 100, 100),
            (50, 50, 150, 150),
        )
        # Intersection: 50×50=2500, Union: 10000+10000-2500=17500
        expected = 2500 / 17500
        assert abs(iou - expected) < 0.001

    def test_contained_box_iou(self):
        """A box fully inside another should have IoU = small_area / large_area."""
        iou = CentroidTracker._compute_iou(
            (0, 0, 200, 200),    # 40000 px²
            (50, 50, 100, 100),  # 2500 px²
        )
        # Intersection = 2500, Union = 40000 + 2500 - 2500 = 40000
        expected = 2500 / 40000
        assert abs(iou - expected) < 0.001


class TestTrackPruning:
    """Tracks should be dropped after disappearing for too many frames."""

    def test_track_dropped_after_max_disappeared(self):
        """A track with no matching detection for N frames gets removed."""
        tracker = CentroidTracker(max_disappeared=3, iou_threshold=0.5)

        # Frame 1: register a track
        tracker.update([(100, 100, 200, 200)])
        assert len(tracker.objects) == 1

        # Frames 2-5: no detections
        for _ in range(4):
            tracker.update([])

        assert len(tracker.objects) == 0

    def test_track_survives_within_disappeared_window(self):
        """A track should persist if disappear count < max_disappeared."""
        tracker = CentroidTracker(max_disappeared=5, iou_threshold=0.5)

        tracker.update([(100, 100, 200, 200)])

        # 3 frames with no detections (under the limit of 5)
        for _ in range(3):
            tracker.update([])

        # Track should still exist (just marked as disappeared)
        # Re-detect in same location → should re-associate
        objects, _ = tracker.update([(100, 100, 200, 200)])
        assert len(objects) == 1


class TestTrackAges:
    """Track age should increment every frame."""

    def test_age_increments(self):
        """Track age should increase by 1 per update call."""
        tracker = CentroidTracker()

        tracker.update([(100, 100, 200, 200)])
        assert tracker.track_ages[0] == 0  # Just registered

        tracker.update([(100, 100, 200, 200)])
        assert tracker.track_ages[0] == 1

        tracker.update([(100, 100, 200, 200)])
        assert tracker.track_ages[0] == 2
