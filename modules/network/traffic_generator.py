"""
Deterministic Synthetic Traffic Generator.

Produces high-speed synthetic `PacketConfig` instances and pushes them into
a `queue.Queue` bound by memory. Simulates organic traffic mixed with structured
attacks natively so we can validate without heavy reliance on .pcap data.
"""

import queue
import time
from typing import Literal

import numpy as np
from structlog import get_logger

from modules.network.schemas import PacketConfig

logger = get_logger("network_generator")


class TrafficGenerator:
    """Enterprise synthetic network generator driving realistic traffic topologies."""

    def __init__(self, seed: int = 42, queue_maxsize: int = 50000):
        self.rng = np.random.RandomState(seed)
        self.packet_queue: queue.Queue[PacketConfig] = queue.Queue(maxsize=queue_maxsize)
        self._running = False
        self._base_ip = "192.168.1."
        self._external_ips = [f"203.0.113.{i}" for i in range(1, 100)]
        self._internal_ips = [f"{self._base_ip}{i}" for i in range(10, 50)]
        self._common_ports = [80, 443, 22, 53, 3306, 8080]

    def _generate_normal_traffic(self, timestamp: float, burst_size: int) -> list[PacketConfig]:
        """Generate a micro-batch of legitimate background traffic."""
        packets = []
        for _ in range(burst_size):
            prot_rand = self.rng.rand()
            if prot_rand < 0.8:
                prot: Literal["TCP", "UDP", "ICMP"] = "TCP"
                size = int(self.rng.normal(800, 200))
            elif prot_rand < 0.95:
                prot = "UDP"
                size = int(self.rng.normal(200, 50))
            else:
                prot = "ICMP"
                size = 64

            # Ensure valid sizes
            size = max(64, min(1500, size))

            src = str(self.rng.choice(self._external_ips))
            dst = str(self.rng.choice(self._internal_ips))
            sport = int(self.rng.randint(1024, 65535))
            dport = int(self.rng.choice(self._common_ports))

            packets.append(
                PacketConfig(
                    timestamp=timestamp,
                    src_ip=src,
                    dst_ip=dst,
                    src_port=sport,
                    dst_port=dport,
                    protocol=prot,
                    size_bytes=size,
                )
            )
        return packets

    def _generate_ddos(self, timestamp: float, magnitude: int) -> list[PacketConfig]:
        """Flood a single IP with junk TCP SYN packets."""
        target_ip = self._internal_ips[0]
        packets = []
        for _ in range(magnitude):
            spoofed_src = f"{self.rng.randint(1, 255)}.{self.rng.randint(1, 255)}.{self.rng.randint(1, 255)}.{self.rng.randint(1, 255)}"
            packets.append(
                PacketConfig(
                    timestamp=timestamp,
                    src_ip=spoofed_src,
                    dst_ip=target_ip,
                    src_port=int(self.rng.randint(1024, 65535)),
                    dst_port=80,
                    protocol="TCP",
                    size_bytes=64,
                )
            )
        return packets

    def start(self, base_pps: int = 1000):
        """Starts the generator blocking loop. Should be run in a daemon thread."""
        self._running = True
        logger.info("network_generator_started", base_pps=base_pps)

        # Simulation clock (start slightly in past to immediately seed)
        sim_time = time.time()

        tick_interval = 0.1  # generate 10x a second

        while self._running:
            start_wall = time.time()

            # Decide on natural PPS fluctuation (+/- 20%)
            pps = int(self.rng.normal(base_pps, base_pps * 0.2))
            pps = max(100, pps)

            batch_size = int(pps * tick_interval)

            # Injection probabilities
            is_ddos = self.rng.rand() < 0.005  # 0.5% chance per tick to inject a mini burst

            packets = self._generate_normal_traffic(sim_time, batch_size)
            if is_ddos:
                packets.extend(self._generate_ddos(sim_time, 1000))  # 10k PPS extra spike

            # Randomly sort the batched items to realistically interleave them
            self.rng.shuffle(packets)  # type: ignore

            # Push to queue (blocking if extractor is too slow, preventing OOM)
            for pkt in packets:
                if not self._running:
                    break
                try:
                    self.packet_queue.put(pkt, timeout=1.0)
                except queue.Full:
                    logger.warning("network_queue_full", action="dropping_packets")
                    break

            sim_time += tick_interval

            # Real-time sleep matching
            elapsed = time.time() - start_wall
            if elapsed < tick_interval:
                time.sleep(tick_interval - elapsed)

    def stop(self):
        """Signals the generator to cleanly halt."""
        self._running = False
        logger.info("network_generator_stopped")
