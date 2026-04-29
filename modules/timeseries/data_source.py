"""
Finance data source — replays OHLCV data from CSV.
"""

import csv
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


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
    """Loads and yields stock ticks from a CSV file for real-time simulation."""

    def __init__(self, file_path: str, replay_speed: float = 1.0):
        self.file_path = Path(file_path)
        self.replay_speed = replay_speed
        self.ticks_count = 0

    def stream(self) -> Iterator[StockTick]:
        """Generator that yields ticks one by one, simulating a live feed."""
        if not self.file_path.exists():
            raise FileNotFoundError(f"Stock data not found: {self.file_path}")

        with open(self.file_path, "r") as f:
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
                
                # In real use, we might sleep to simulate real-time
                # but for IRMDS v1 simulation we just yield as fast as needed
                # or with a small throttle if requested.
                if self.replay_speed > 0:
                    time.sleep(1.0 / self.replay_speed)
