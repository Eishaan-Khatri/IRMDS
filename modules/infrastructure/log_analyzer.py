"""
Infrastructure log analyzer: tails syslog and detects pattern-based anomalies.
"""

import re
from pathlib import Path


class LogAnalyzer:
    """Monitors log files for critical patterns and error bursts."""

    LOG_PATTERN = re.compile(
        r"(\w{3}\s+\d+\s+[\d:]+)\s+([\w\d.-]+)\[(\d+)\]:\s+\[(\w+)\]\s+(.*)"
    )

    def __init__(self, log_path: str):
        self.log_path = Path(log_path)
        self._last_position = 0

    def analyze_new_lines(self) -> list[dict[str, str]]:
        """Read new lines from the log and parse anomalies."""
        if not self.log_path.exists():
            return []

        results: list[dict[str, str]] = []
        with self.log_path.open() as f:
            f.seek(self._last_position)
            lines = f.readlines()
            self._last_position = f.tell()

            for line in lines:
                match = self.LOG_PATTERN.match(line.strip())
                if not match:
                    continue

                ts, comp, pid, sev, msg = match.groups()
                if sev in {"ERROR", "CRITICAL"}:
                    results.append(
                        {
                            "timestamp": ts,
                            "component": comp,
                            "pid": pid,
                            "severity": sev,
                            "message": msg,
                        }
                    )
        return results
