"""
Motion density heatmap accumulator.

Builds a spatial heat map over time by accumulating centroid positions
of tracked objects. Frequently visited areas appear as "hot" regions
when rendered, providing an intuitive visualization of movement patterns.

The heatmap is a float32 accumulator array where each centroid "stamps"
a Gaussian-like circle onto the array. Over time, high-traffic areas
accumulate higher values. The array is normalized and color-mapped
(JET colormap) when exported as an image.

Usage:
    heatmap = Heatmap(width=640, height=480)

    # Every frame:
    heatmap.accumulate(centroids=[(320, 240), (480, 300)])

    # Periodically:
    image = heatmap.export_image()  # → numpy BGR array
    heatmap.save("output/heatmap.png")
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import cv2
import numpy as np


class Heatmap:
    """Float32 motion density accumulator with JET colormap export.

    The accumulator never saturates — it grows unboundedly, which
    means long-running sessions will have more contrast between
    high-traffic and low-traffic areas. Call `reset()` to start
    a fresh accumulation period.
    """

    def __init__(self, width: int, height: int, radius: int = 25):
        """Initialize the heatmap accumulator.

        Args:
            width:  Frame width in pixels.
            height: Frame height in pixels.
            radius: Radius of the circle "stamp" for each centroid.
                    Larger values produce smoother, more diffuse heatmaps.
        """
        self._width = width
        self._height = height
        self._radius = radius
        self._accumulator = np.zeros((height, width), dtype=np.float32)
        self._frame_count = 0

    def accumulate(self, centroids: list[tuple[int, int]]) -> None:
        """Stamp centroid positions onto the accumulator.

        Each centroid adds a filled circle of intensity 1.0 to the
        float32 accumulator. Overlapping circles from the same frame
        or different frames stack additively.

        Args:
            centroids: List of (cx, cy) centroid positions.
        """
        for cx, cy in centroids:
            # Bounds check — centroids near the edge could overflow
            if 0 <= cx < self._width and 0 <= cy < self._height:
                cv2.circle(
                    self._accumulator,
                    (cx, cy),
                    self._radius,
                    1.0,
                    thickness=-1,  # Filled circle
                )
        self._frame_count += 1

    def export_image(self) -> np.ndarray:
        """Render the heatmap as a BGR color image.

        Normalizes the accumulator to 0–255 range and applies the
        JET colormap (blue=cold → red=hot).

        Returns:
            BGR numpy array (H, W, 3) suitable for display or saving.
            Returns a blank JET image if no data has been accumulated.
        """
        if self._accumulator.max() == 0:
            # No data yet — return a uniform blue (cold) image
            blank = np.zeros((self._height, self._width), dtype=np.uint8)
            return cast("np.ndarray", cv2.applyColorMap(blank, cv2.COLORMAP_JET))

        # Normalize to 0–255 for colormap application
        destination = np.zeros((self._height, self._width), dtype=np.uint8)
        normalized = cast(
            "np.ndarray",
            cv2.normalize(
                self._accumulator,
                destination,
                0.0,
                255.0,
                cv2.NORM_MINMAX,
                dtype=cv2.CV_8U,
            ),
        )
        return cast("np.ndarray", cv2.applyColorMap(normalized, cv2.COLORMAP_JET))

    def save(self, path: str | Path) -> None:
        """Save the heatmap image to disk as PNG.

        Creates parent directories if they don't exist.
        """
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(output_path), self.export_image())

    def reset(self) -> None:
        """Clear the accumulator and start fresh."""
        self._accumulator.fill(0)
        self._frame_count = 0

    @property
    def frame_count(self) -> int:
        """Number of frames accumulated since last reset."""
        return self._frame_count

    @property
    def peak_intensity(self) -> float:
        """Maximum accumulated intensity value."""
        return float(self._accumulator.max())
