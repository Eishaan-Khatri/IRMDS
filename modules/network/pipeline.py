"""
Network Traffic Analysis Pipeline.

Orchestrates the entire module. Starts background threads for packet generation 
and extraction, securely pushing output to the global EventBus and MetricsCollector.
"""

import threading
import time

from structlog import get_logger

from core.base_module import BaseModule, ModuleStatus
from core.event_bus import Event
from modules.network.anomaly_detector import NetworkAnomalyDetector
from modules.network.feature_extractor import FeatureExtractor
from modules.network.traffic_generator import TrafficGenerator

logger = get_logger("network_pipeline")


class NetworkPipeline(BaseModule):
    module_id = "network"
    display_name = "Network Security Analytics"
    version = "1.0.0"

    def __init__(self):
        self.status = ModuleStatus.STOPPED
        self.generator = TrafficGenerator()
        self.extractor = FeatureExtractor(window_seconds=1.0)
        self.detector = NetworkAnomalyDetector()
        
        self.event_bus = None
        self.metrics = None
        
        # Thread sync
        self._running_flag = [False]
        self._threads = []

    async def start(self, event_bus=None, metrics=None) -> None:
        """Kicks off the multithreaded network ingestion layer."""
        if self._running_flag[0]:
            return
            
        self.status = ModuleStatus.STARTING
        self.event_bus = event_bus
        self.metrics = metrics
        self._running_flag[0] = True
        
        # Start generator daemon
        t_gen = threading.Thread(target=self.generator.start, args=(800,), daemon=True, name="Network-Gen-Thread")
        t_gen.start()
        
        # Start extractor consumer loop
        t_ml = threading.Thread(target=self._extractor_loop, daemon=True, name="Network-ML-Thread")
        t_ml.start()
        
        self._threads.extend([t_gen, t_ml])
        self.status = ModuleStatus.RUNNING
        logger.info("network_pipeline_running")

    def _extractor_loop(self):
        """Consumes queue, extracts windows, pushes to ML."""
        while self._running_flag[0]:
            try:
                windows = self.extractor.process_queue(self.generator.packet_queue, self._running_flag)
                for window in windows:
                    # 1. Run ML
                    result = self.detector.process(window)
                    
                    # 2. Sink to Global Metrics Collector
                    if self.metrics:
                        # Map to agnostic dict for metrics collector
                        self.metrics.update(self.module_id, {
                            "packets_per_second": window.packets_per_second,
                            "bytes_per_second": window.bytes_per_second,
                            "unique_src_ips": window.unique_src_ips,
                            "unique_dst_ports": window.unique_dst_ports,
                            "anomaly_score": result.isolation_forest_score,
                            "is_baseline_ready": self.detector.baseline_ready
                        })
                    
                    # 3. Sink to Global EventBus if anomaly
                    if result.is_anomaly and self.event_bus:
                        evt = Event(
                            module=self.module_id,
                            type="NET_ANOMALY",
                            severity="CRITICAL",
                            data={
                                "alert_type": result.anomaly_type,
                                "triggers": result.triggers,
                                "pps": window.packets_per_second,
                                "bps": window.bytes_per_second
                            }
                        )
                        self.event_bus.publish(evt)
                        
            except Exception as e:
                logger.error("network_extractor_crash", error=str(e), exc_info=True)
                time.sleep(1.0) # Backoff on crash

    async def stop(self) -> None:
        """Halt threads and cleanly unmount."""
        if not self._running_flag[0]:
            return
            
        self.status = ModuleStatus.STOPPED
        logger.info("network_pipeline_stopping")
        self._running_flag[0] = False
        self.generator.stop()
        
        # We don't join on bounded shutdown to prevent deadlock during rapid api stops,
        # thread daemons will naturally die shortly.
        self._threads.clear()

    async def health_check(self) -> dict:
        return {
            "healthy": self._running_flag[0] and any(t.is_alive() for t in self._threads),
            "details": {
                "queue_size": self.generator.packet_queue.qsize(),
                "baseline_ready": self.detector.baseline_ready
            }
        }
