"""
Visual anomaly detection pipeline — orchestrates all visual sub-components.

This is the main entry point for the visual module. It wires together:
    FrameSource → Detector → Tracker → ZoneManager → SpeedEstimator → Heatmap

On each frame cycle:
    1. Read frame from source (webcam, file, RTSP)
    2. Run YOLOv8 detection → filter to persons
    3. Update tracker → persistent IDs
    4. Update zones → entry/exit/loitering/crowd events
    5. Estimate speeds → anomaly classification
    6. Accumulate heatmap
    7. Publish events to EventBus
    8. Push metrics to MetricsCollector

The pipeline runs headless (no cv2.imshow) — it produces data, not UI.
The dashboard and API consume its output via the event bus and metrics.

Inherits from BaseModule, so the PluginRegistry discovers and manages
it automatically. No other code in the system needs to know about this file.
"""

from __future__ import annotations

import time
from collections import deque
from pathlib import Path
from typing import Any

import numpy as np

from core.base_module import BaseModule
from core.event_bus import Event, Severity
from modules.visual.detector import Detector
from modules.visual.frame_source import FrameSource
from modules.visual.heatmap import Heatmap
from modules.visual.speed_estimator import SpeedEstimator
from modules.visual.tracker import CentroidTracker
from modules.visual.zone_manager import ZoneManager


class VisualPipeline(BaseModule):
    """Real-time visual anomaly detection via YOLOv8 + IoU tracking.

    This module processes video frames in a background thread,
    detecting persons, tracking them across frames, analyzing their
    behavior (speed, zone interactions, dwell time), and emitting
    structured events for the rest of the system to consume.

    Module identity:
        module_id:    "visual"
        display_name: "Visual Anomaly Detection"
        version:      "1.0.0"
    """

    module_id = "visual"
    display_name = "Visual Anomaly Detection"
    version = "1.0.0"

    def _run(self) -> None:
        """Main processing loop — runs in a background thread.

        Initializes all sub-components, then enters a frame-by-frame
        processing loop that continues until `self._running` is cleared
        by the `stop()` method.
        """
        # ── Initialize Sub-Components ────────────────────
        self.log.info("initializing_components")

        source = FrameSource.from_config(self.config)
        if not source.open():
            self.log.error("frame_source_unavailable", source=self.config.visual_source)
            # Emit an error event so the dashboard shows it
            self.event_bus.publish(
                Event(
                    module=self.module_id,
                    type="SOURCE_ERROR",
                    severity=Severity.CRITICAL,
                    data={"source": self.config.visual_source, "error": "Cannot open video source"},
                )
            )
            return

        detector = Detector(self.config)
        tracker = CentroidTracker(
            max_disappeared=self.config.visual_max_disappeared,
            iou_threshold=self.config.visual_iou_threshold,
        )
        speed_estimator = SpeedEstimator(self.config)

        # Load zones from config file, or create a default zone
        zones_config_path = Path("data/zones_config.json")
        if zones_config_path.exists():
            zone_manager = ZoneManager.from_config(zones_config_path)
            self.log.info("zones_loaded_from_config", count=len(zone_manager.zones))
        else:
            # Use first frame to determine dimensions for the default zone
            success, first_frame = source.read()
            if not success or first_frame is None:
                self.log.error("cannot_read_first_frame")
                source.release()
                return
            h, w = first_frame.shape[:2]
            zone_manager = ZoneManager.create_default(w, h)
            self.log.info("default_zone_created", width=w, height=h)

        # Initialize heatmap with frame dimensions
        heatmap = Heatmap(
            width=self.config.visual_frame_width,
            height=self.config.visual_frame_height,
        )

        # FPS tracking with a rolling window
        fps_window: deque[float] = deque(maxlen=30)

        # Alert deduplication — prevent repeated speed alerts for the same track
        speed_alerted: set[int] = set()

        self.log.info("pipeline_running", source_type=source.source_type.value)

        # ── Main Processing Loop ─────────────────────────
        try:
            while self._running.is_set():
                t_frame_start = time.perf_counter()

                # 1. Read frame
                success, frame = source.read()
                if not success or frame is None:
                    self.log.info("source_exhausted_or_disconnected")
                    break

                # 2. Detect objects
                detections = detector.detect(frame)
                detection_boxes = [d.bbox for d in detections]

                # 3. Track objects
                tracked_objects, tracked_boxes = tracker.update(detection_boxes)

                # 4. Update zones → emit zone events
                zone_events = zone_manager.update(tracked_objects)
                for ze in zone_events:
                    severity = Severity.INFO
                    if ze.type == "LOITERING" or ze.type == "CROWD_ALERT":
                        severity = Severity.WARNING

                    self.event_bus.publish(
                        Event(
                            module=self.module_id,
                            type=ze.type,
                            severity=severity,
                            data={
                                "zone": ze.zone_name,
                                "object_id": ze.object_id,
                                "dwell_seconds": ze.dwell_seconds,
                                "occupancy": ze.occupancy,
                            },
                        )
                    )

                # 5. Estimate speeds → emit speed anomalies
                active_speeds: list[float] = []
                now = time.time()

                for oid, centroid in tracked_objects.items():
                    bbox = tracked_boxes.get(oid)
                    if bbox is None:
                        continue

                    result = speed_estimator.estimate(oid, centroid, bbox, now)
                    if result.speed_ms > 0:
                        active_speeds.append(result.speed_ms)

                    # Emit CRITICAL event for running/abnormal speed (once per track)
                    if result.is_anomaly and oid not in speed_alerted:
                        speed_alerted.add(oid)
                        self.event_bus.publish(
                            Event(
                                module=self.module_id,
                                type="SPEED_ANOMALY",
                                severity=Severity.CRITICAL,
                                data={
                                    "object_id": oid,
                                    "speed_ms": result.speed_ms,
                                    "classification": result.classification.value,
                                },
                            )
                        )

                # Clean up speed estimator for deregistered tracks
                active_ids = set(tracked_objects.keys())
                stale_ids = speed_alerted - active_ids
                for oid in stale_ids:
                    speed_alerted.discard(oid)
                    speed_estimator.remove_track(oid)

                # 6. Accumulate heatmap
                centroids = list(tracked_objects.values())
                heatmap.accumulate(centroids)

                # 7. Compute FPS
                frame_time = time.perf_counter() - t_frame_start
                fps_window.append(1.0 / max(frame_time, 1e-6))
                current_fps = float(np.mean(fps_window))

                # 8. Push metrics to the collector
                avg_speed = float(np.mean(active_speeds)) if active_speeds else 0.0
                max_speed = float(np.max(active_speeds)) if active_speeds else 0.0

                self.metrics.push(
                    self.module_id,
                    {
                        "fps": round(current_fps, 1),
                        "latency_ms": round(detector.last_latency_ms, 1),
                        "active_tracks": len(tracked_objects),
                        "avg_speed_ms": round(avg_speed, 2),
                        "max_speed_ms": round(max_speed, 2),
                        "detections": len(detections),
                        "heatmap_frames": heatmap.frame_count,
                        "zone_stats": zone_manager.get_stats(),
                    },
                )

        finally:
            # Always release resources, even if the loop crashes
            source.release()
            # Save heatmap snapshot on shutdown
            try:
                heatmap.save("logs/heatmap_latest.png")
                self.log.info("heatmap_saved", path="logs/heatmap_latest.png")
            except Exception:
                self.log.warning("heatmap_save_failed", exc_info=True)

            self.log.info(
                "pipeline_stopped",
                total_frames=source.frame_count,
                heatmap_frames=heatmap.frame_count,
            )

    def health_check(self) -> dict[str, Any]:
        """Report module health for the /health endpoint."""
        metrics = self.metrics.get_latest(self.module_id)
        fps = metrics.get("fps", 0)

        return {
            "healthy": self.status.value == "running" and fps > 0,
            "status": self.status.value,
            "details": {
                "fps": fps,
                "latency_ms": metrics.get("latency_ms", 0),
                "active_tracks": metrics.get("active_tracks", 0),
            },
        }

    def get_metrics(self) -> dict[str, Any]:
        """Return current performance metrics."""
        return self.metrics.get_latest(self.module_id)
