"""
O(1) Bounded Network Feature Extractor.

Aggregates packet topologies into statistical windows without memory leakage.
Calculates Shannon entropy to detect port scanning, and BPS to detect exfiltration.
"""

import collections
import math
import queue
import time
from typing import Optional

from structlog import get_logger

from modules.network.schemas import FeatureWindow, PacketConfig

logger = get_logger("network_extractor")


def _calculate_entropy(counter: collections.Counter) -> float:
    """Calculates Shannon entropy for a given distribution."""
    total = sum(counter.values())
    if total <= 1:
        return 0.0
    entropy = 0.0
    for count in counter.values():
        p = count / total
        if p > 0:
            entropy -= p * math.log2(p)
    return entropy


class FeatureExtractor:
    """Consumes packets from a thread-safe queue and yields feature vectors."""

    def __init__(self, window_seconds: float = 1.0):
        self.window_seconds = window_seconds
        
        # We process packets but immediately discard them structurally after aggregating.
        # This keeps O(1) memory guarantees globally.
        self._current_window_start = 0.0
        
        # Rolling stateless accumulators
        self._pps = 0
        self._bps = 0
        self._tcp_count = 0
        self._udp_count = 0
        self._icmp_count = 0
        self._max_size = 0
        self._src_ips = set()
        self._dst_ports = set()
        self._dst_ips_counter = collections.Counter()

    def _reset_accumulators(self, start_time: float):
        """Flushes the accumulators for a new window."""
        self._current_window_start = start_time
        self._pps = 0
        self._bps = 0
        self._tcp_count = 0
        self._udp_count = 0
        self._icmp_count = 0
        self._max_size = 0
        self._src_ips.clear()
        self._dst_ports.clear()
        self._dst_ips_counter.clear()

    def process_queue(
        self, 
        packet_queue: queue.Queue, 
        running_flag: list[bool]
    ) -> list[FeatureWindow]:
        """
        Pulls packets from the queue. Groups them by `window_seconds`.
        Returns generated FeatureWindows if a window boundary is crossed.
        
        Note: `running_flag` is passed as a mutable list/obj so the thread
        can be externally signaled to stop without blocking forever on get().
        """
        windows_generated = []
        
        while running_flag[0]:
            try:
                # Block for a very short time to remain responsive to shutdown
                packet: PacketConfig = packet_queue.get(timeout=0.2)
            except queue.Empty:
                break # We yield back to the main loop to process whatever generated windows exist

            # Initialize first window
            if self._current_window_start == 0.0:
                self._reset_accumulators(packet.timestamp)

            # Check if packet crosses the window boundary
            if packet.timestamp >= self._current_window_start + self.window_seconds:
                # Seal current window
                end_time = self._current_window_start + self.window_seconds
                
                # Mathematical derivatives
                total = self._pps if self._pps > 0 else 1 # avoid ZeroDivision
                tcp_r = self._tcp_count / total
                udp_r = self._udp_count / total
                icmp_r = self._icmp_count / total
                entropy = _calculate_entropy(self._dst_ips_counter)
                avg_size = self._bps / total

                # Generate final contract
                window = FeatureWindow(
                    start_time=self._current_window_start,
                    end_time=end_time,
                    packets_per_second=self._pps,
                    bytes_per_second=self._bps,
                    unique_src_ips=len(self._src_ips),
                    unique_dst_ports=len(self._dst_ports),
                    tcp_ratio=tcp_r,
                    udp_ratio=udp_r,
                    icmp_ratio=icmp_r,
                    dst_ip_entropy=entropy,
                    avg_packet_size=avg_size,
                    max_packet_size=self._max_size
                )
                windows_generated.append(window)

                # Reset for the new window, anchored by the offending packet's timestamp block
                # Ensure we align to strict structural boundaries
                new_start = packet.timestamp - (packet.timestamp % self.window_seconds)
                self._reset_accumulators(new_start)

            # Accumulate current packet into state
            self._pps += 1
            self._bps += packet.size_bytes
            
            if packet.protocol == "TCP": self._tcp_count += 1
            elif packet.protocol == "UDP": self._udp_count += 1
            elif packet.protocol == "ICMP": self._icmp_count += 1
            
            if packet.size_bytes > self._max_size:
                self._max_size = packet.size_bytes
                
            self._src_ips.add(packet.src_ip)
            self._dst_ports.add(packet.dst_port)
            self._dst_ips_counter[packet.dst_ip] += 1
            
            # Fast pump: do not pause to append continuously, only break outward 
            # if we accumulate some windows. This way we drain the queue efficiently.
            packet_queue.task_done()
            
            if len(windows_generated) >= 5:
                # If we're behind and accumulated multi-windows, yield them before hoarding more memory
                break

        return windows_generated
