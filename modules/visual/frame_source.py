"""
Unified frame source abstraction for the visual module.

Provides a consistent interface over multiple video input types:
    - Webcam (source = "0", "1", etc.)
    - Video file (source = "path/to/video.mp4")
    - RTSP stream (source = "rtsp://admin:pass@192.168.1.100/stream")
    - HTTP stream (source = "http://camera.example.com/mjpeg")

The visual pipeline doesn't need to know where frames come from.
It just calls `source.read()` and gets a frame.

Usage:
    source = FrameSource.open("0", width=640, height=480)
    while True:
        success, frame = source.read()
        if not success:
            break
    source.release()
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

import cv2
import numpy as np

from core.logger import get_logger

if TYPE_CHECKING:
    from core.config import IRMDSConfig

log = get_logger("frame_source")


class SourceType(str, enum.Enum):
    """Classification of the input source for logging purposes."""

    WEBCAM = "webcam"
    VIDEO_FILE = "video_file"
    RTSP_STREAM = "rtsp_stream"
    HTTP_STREAM = "http_stream"
    UNKNOWN = "unknown"


class FrameSource:
    """Abstraction over OpenCV VideoCapture with auto-detected source type.

    Handles webcam indices, file paths, RTSP URLs, and HTTP streams
    through a single interface. Supports optional frame resizing and
    frame skipping for performance tuning.
    """

    def __init__(
        self,
        source: str,
        width: int = 640,
        height: int = 480,
        frame_skip: int = 1,
    ):
        """Initialize the frame source.

        Args:
            source:     Webcam index ("0"), file path, or stream URL.
            width:      Desired frame width (resize if different).
            height:     Desired frame height (resize if different).
            frame_skip: Process every Nth frame (1 = all, 2 = every other).
        """
        self._source_str = source
        self._width = width
        self._height = height
        self._frame_skip = max(1, frame_skip)
        self._frame_count = 0
        self._cap: cv2.VideoCapture | None = None
        self.source_type = self._classify_source(source)

    @classmethod
    def from_config(cls, config: IRMDSConfig) -> FrameSource:
        """Create a FrameSource from the global configuration."""
        return cls(
            source=config.visual_source,
            width=config.visual_frame_width,
            height=config.visual_frame_height,
            frame_skip=config.visual_frame_skip,
        )

    def open(self) -> bool:
        """Open the video capture device or file.

        Returns:
            True if the source was successfully opened.
        """
        # Parse webcam index from string if it's a digit
        source = int(self._source_str) if self._source_str.isdigit() else self._source_str

        self._cap = cv2.VideoCapture(source)

        if not self._cap.isOpened():
            log.error("source_open_failed", source=self._source_str, type=self.source_type)
            return False

        log.info(
            "source_opened",
            source=self._source_str,
            type=self.source_type,
            native_width=int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            native_height=int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            target_width=self._width,
            target_height=self._height,
        )
        return True

    def read(self) -> tuple[bool, np.ndarray | None]:
        """Read the next frame, applying skip and resize.

        If frame_skip > 1, intermediate frames are grabbed (fast)
        but not decoded (slow). Only every Nth frame is fully decoded
        and returned. This provides a significant performance boost
        for high-FPS sources where you don't need every frame.

        Returns:
            Tuple of (success, frame). Frame is None if read failed.
        """
        if self._cap is None or not self._cap.isOpened():
            return False, None

        # Skip frames by grabbing without decoding
        for _ in range(self._frame_skip - 1):
            self._cap.grab()

        success, frame = self._cap.read()

        if not success or frame is None:
            return False, None

        self._frame_count += 1

        # Resize if the native resolution doesn't match the target
        h, w = frame.shape[:2]
        if w != self._width or h != self._height:
            frame = cv2.resize(frame, (self._width, self._height))

        return True, frame

    def release(self) -> None:
        """Release the video capture device."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None
            log.info("source_released", total_frames=self._frame_count)

    @property
    def is_opened(self) -> bool:
        """Whether the source is currently open and readable."""
        return self._cap is not None and self._cap.isOpened()

    @property
    def frame_count(self) -> int:
        """Total frames read since opening."""
        return self._frame_count

    @property
    def fps(self) -> float:
        """Native FPS of the source (may differ from actual processing FPS)."""
        if self._cap is None:
            return 0.0
        return self._cap.get(cv2.CAP_PROP_FPS) or 0.0

    @staticmethod
    def _classify_source(source: str) -> SourceType:
        """Classify the source string for logging and error messages."""
        if source.isdigit():
            return SourceType.WEBCAM
        lower = source.lower()
        if lower.startswith("rtsp://"):
            return SourceType.RTSP_STREAM
        if lower.startswith("http://") or lower.startswith("https://"):
            return SourceType.HTTP_STREAM
        if any(lower.endswith(ext) for ext in (".mp4", ".avi", ".mkv", ".mov", ".wmv")):
            return SourceType.VIDEO_FILE
        return SourceType.UNKNOWN
