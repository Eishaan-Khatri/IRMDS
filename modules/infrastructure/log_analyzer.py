"""
Infrastructure log analyzer — tails syslog and detects pattern-based anomalies.
"""

import re
from pathlib import Path


class LogAnalyzer:
    """Monitors log files for critical patterns and error bursts."""

    # Simplified syslog pattern: Oct 23 10:15:32 component[pid]: [SEV] Message
    LOG_PATTERN = re.compile(r"(\w{3}\s+\d+\s+[\d:]+)\s+([\w\d.-]+)\[(\d+)\]:\s+\[(\w+)\]\s+(.*)")

    def __init__(self, log_path: str):
        self.log_path = Path(log_path)
        self._last_position = 0

    def analyze_new_lines(self) -> list[dict]:
        """Read new lines from the log and parse anomalies."""
        if not self.log_path.exists():
            return []

        results = []
        with open(self.log_path, "r") as f:
            f.seek(self._last_position)
            lines = f.readlines()
            self._last_position = f.tell()

            for line in lines:
                match = self.LOG_PATTERN.match(line.strip())
                if match:
                    ts, comp, pid, sev, msg = match.groups()
                    if sev in ["ERROR", "CRITICAL"]:
                        results.append({
                            "timestamp": ts,
                            "component": comp,
                            "pid": pid,
                            "severity": sev,
                            "message": msg
                        })
        return results
