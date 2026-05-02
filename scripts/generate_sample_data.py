"""
Sample Data Generator for IRMDS.

Produces deterministic datasets for the Finance, Network, and Infrastructure
modules to ensure tests and demos work without live external feeds.
"""

import csv
import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np


def generate_stock_data(path: Path, rows: int = 2000) -> None:
    """Generate OHLCV data with random walk + injected anomalies."""
    print(f"Generating Finance data: {path}")

    # Deterministic seed for repeatable tests
    np.random.seed(42)
    random.seed(42)

    start_price = 150.0
    returns = np.random.normal(0, 0.001, rows)
    prices = start_price * np.exp(np.cumsum(returns))

    # Inject anomalies
    # 1. Flash crash at row 500
    prices[500:510] *= 0.92  # 8% drop

    # 2. Volatility spike at row 1200
    prices[1200:1250] += np.random.normal(0, 5.0, 50)

    # 3. Pump and dump at row 1700
    prices[1700:1720] *= 1.10
    prices[1720:1740] *= 0.85

    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])

        base_time = datetime.now(UTC) - timedelta(days=rows / 1440)
        for i in range(rows):
            ts = (base_time + timedelta(minutes=i)).isoformat()
            p = prices[i]
            # Add some noise for OHLC
            noise = p * 0.002
            o = p + random.uniform(-noise, noise)
            h = max(o, p) + random.uniform(0, noise)
            l = min(o, p) - random.uniform(0, noise)
            c = p
            # Volume spike on anomalies
            vol = random.randint(1000, 5000)
            if 500 <= i <= 510 or 1700 <= i <= 1740:
                vol *= 5

            writer.writerow([ts, round(o, 2), round(h, 2), round(l, 2), round(c, 2), vol])


def generate_syslog_data(path: Path, rows: int = 500) -> None:
    """Generate a log file with various severity patterns."""
    print(f"Generating Infra log data: {path}")

    components = ["AUTH", "KERNEL", "SYSTEMD", "DB", "API", "DISK"]
    events = [
        ("INFO", "User login successful"),
        ("INFO", "Database query optimized"),
        ("WARN", "Disk usage exceeding 80%"),
        ("ERROR", "Connection refused by peer"),
        ("ERROR", "Failed to write to buffer"),
        ("CRITICAL", "Out of memory: Kill process"),
    ]

    with path.open("w") as f:
        base_time = datetime.now(UTC) - timedelta(hours=1)
        for i in range(rows):
            ts = (base_time + timedelta(seconds=i * 7)).strftime("%b %d %H:%M:%S")
            comp = random.choice(components)
            # Higher probability of INFO
            if random.random() < 0.8:
                sev, msg = events[random.randint(0, 1)]
            else:
                sev, msg = random.choice(events[2:])
            
            # Inject a burst of errors near the end
            if 450 < i < 480:
                sev, msg = random.choice(events[3:])

            f.write(f"{ts} {comp}[{random.randint(100, 999)}]: [{sev}] {msg}\n")


def generate_zones_config(path: Path) -> None:
    """Generate a standard zones configuration for the Visual module."""
    print(f"Generating Visual zones config: {path}")

    zones = [
        {
            "name": "Entrance",
            "points": [[100, 100], [300, 100], [300, 400], [100, 400]],
            "loiter_seconds": 5,
            "crowd_threshold": 3,
        },
        {
            "name": "Restricted Area",
            "points": [[400, 50], [600, 50], [600, 300], [400, 300]],
            "loiter_seconds": 2,
            "crowd_threshold": 1,
        },
    ]

    with path.open("w") as f:
        json.dump(zones, f, indent=4)


def main() -> None:
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    generate_stock_data(data_dir / "sample_stock.csv")
    generate_syslog_data(data_dir / "sample_syslog.log")
    generate_zones_config(data_dir / "zones_config.json")

    print("\n[OK] All sample data generated successfully.")


if __name__ == "__main__":
    main()
