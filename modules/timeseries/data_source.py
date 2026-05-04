"""
Finance data source: replays OHLCV data from CSV.
"""

import csv
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path


@dataclass
class StockTick:
    """A single row of OHLCV data."""

    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class FinanceDataSource:
    """Load and yield stock ticks from a CSV file for simulation."""

    def __init__(self, file_path: str, replay_speed: float = 1.0):
        self.file_path = Path(file_path)
        self.replay_speed = replay_speed
        self.ticks_count = 0

    def stream(self) -> Iterator[StockTick]:
        """Yield ticks one by one, simulating a live feed."""
        if not self.file_path.exists():
            raise FileNotFoundError(f"Stock data not found: {self.file_path}")

        with self.file_path.open() as f:
            reader = csv.DictReader(f)
            for row in reader:
                tick = StockTick(
                    timestamp=row["timestamp"],
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=int(row["volume"]),
                )
                self.ticks_count += 1
                yield tick

                if self.replay_speed > 0:
                    time.sleep(1.0 / self.replay_speed)
