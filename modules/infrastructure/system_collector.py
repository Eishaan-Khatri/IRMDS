"""
Infrastructure system collector — uses psutil to gather hardware telemetry.
"""

import psutil


class SystemCollector:
    """Collects CPU, Memory, Disk, and Network metrics."""

    def __init__(self):
        # Initialize some counters to get accurate deltas on first poll
        psutil.cpu_percent(interval=None)
        psutil.net_io_counters()

    def collect(self) -> dict[str, float]:
        """Gathers current resource usage snapshot."""
        # CPU
        cpu_usage = psutil.cpu_percent(interval=None)
        cpu_freq = psutil.cpu_freq().current if psutil.cpu_freq() else 0.0
        
        # Memory
        mem = psutil.virtual_memory()
        mem_usage = mem.percent
        
        # Disk
        disk = psutil.disk_usage('/')
        disk_usage = disk.percent
        
        # Network
        net = psutil.net_io_counters()
        
        # Process Count
        proc_count = len(psutil.pids())

        return {
            "cpu_usage_pct": float(cpu_usage),
            "cpu_freq_mhz": float(cpu_freq),
            "mem_usage_pct": float(mem_usage),
            "disk_usage_pct": float(disk_usage),
            "net_bytes_sent": float(net.bytes_sent),
            "net_bytes_recv": float(net.bytes_recv),
            "process_count": float(proc_count)
        }
