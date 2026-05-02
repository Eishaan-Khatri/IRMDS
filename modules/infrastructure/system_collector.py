"""
Infrastructure system collector: uses psutil to gather hardware telemetry.
"""

import psutil


class SystemCollector:
    """Collect CPU, memory, disk, and network metrics."""

    def __init__(self):
        psutil.cpu_percent(interval=None)
        psutil.net_io_counters()

    def collect(self) -> dict[str, float]:
        """Gather the current resource usage snapshot."""
        cpu_usage = psutil.cpu_percent(interval=None)
        cpu_freq_info = psutil.cpu_freq()
        cpu_freq = cpu_freq_info.current if cpu_freq_info else 0.0

        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        net = psutil.net_io_counters()

        return {
            "cpu_usage_pct": float(cpu_usage),
            "cpu_freq_mhz": float(cpu_freq),
            "mem_usage_pct": float(mem.percent),
            "disk_usage_pct": float(disk.percent),
            "net_bytes_sent": float(net.bytes_sent),
            "net_bytes_recv": float(net.bytes_recv),
            "process_count": float(len(psutil.pids())),
        }
