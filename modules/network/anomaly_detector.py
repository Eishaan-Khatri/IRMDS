"""
Hybrid Machine Learning Anomaly Detector for Network Traces.

Combines an Isolation Forest for multivariate unlabeled anomaly detection
with robust Exponential Moving Average (EMA) Z-scores to mitigate noisy 
concept drift, and absolute domain-heuristic hard limits to guarantee
bounded attack capture.
"""

import math

import numpy as np
from sklearn.ensemble import IsolationForest
from structlog import get_logger

from modules.network.schemas import FeatureWindow, NetworkAnomalyResult

logger = get_logger("network_ml")


class EMAZscoreDetector:
    """Detects anomalies using Exponential Moving Average Z-Scores."""
    
    def __init__(self, alpha: float = 0.1, threshold: float = 3.0):
        self.alpha = alpha  # Weight of current observation (closer to 1 -> fast response)
        self.threshold = threshold
        self.means: dict[str, float] = {}
        self.variances: dict[str, float] = {}

    def update_and_score(self, features: dict[str, float]) -> dict[str, float]:
        """Updates internal EMA state and returns current z-scores."""
        z_scores = {}
        
        for k, curr_val in features.items():
            if k not in self.means:
                self.means[k] = curr_val
                self.variances[k] = 0.0
                z_scores[k] = 0.0
                continue
                
            # EMA equations
            diff = curr_val - self.means[k]
            incrp = self.alpha * diff
            self.means[k] += incrp
            self.variances[k] = (1 - self.alpha) * (self.variances[k] + diff * incrp)
            
            std_dev = math.sqrt(self.variances[k])
            if std_dev > 0.0001:
                z_scores[k] = abs(curr_val - self.means[k]) / std_dev
            else:
                z_scores[k] = 0.0
                
        return z_scores


class NetworkAnomalyDetector:
    """Enterprise-grade hybrid anomaly classifier."""
    
    def __init__(self, baseline_windows: int = 60, contamination: float = 0.05):
        self.baseline_windows = baseline_windows
        self._history: list[list[float]] = []
        
        self.iso_forest = IsolationForest(contamination=contamination, random_state=42)
        self.ema_detector = EMAZscoreDetector(alpha=0.1, threshold=3.5)
        self.baseline_ready = False
        
        # Hard limits bypassing ML logic
        self.DDOS_PPS_THRESHOLD = 5000 
        self.PORT_SCAN_THRESHOLD = 150
        
    def _extract_vector(self, window: FeatureWindow) -> list[float]:
        return [
            window.packets_per_second,
            window.bytes_per_second,
            window.unique_src_ips,
            window.unique_dst_ports,
            window.tcp_ratio,
            window.dst_ip_entropy
        ]

    def process(self, window: FeatureWindow) -> NetworkAnomalyResult:
        """Evaluates a single window against the hybrid ensemble."""
        features_dict = {
            "pps": window.packets_per_second,
            "bps": window.bytes_per_second,
            "u_dst_ports": float(window.unique_dst_ports),
            "entropy": window.dst_ip_entropy
        }
        
        vector = self._extract_vector(window)
        
        # 1. Update EMA
        z_scores = self.ema_detector.update_and_score(features_dict)
        
        # 2. Maintain Baseline / Retrain
        # Online learning: keep a rolling buffer of 3x baseline for recalibration
        if len(self._history) < self.baseline_windows * 3:
            self._history.append(vector)
            
        if len(self._history) == self.baseline_windows and not self.baseline_ready:
            logger.info("network_ml_training_baseline", windows=self.baseline_windows)
            self.iso_forest.fit(self._history)
            self.baseline_ready = True
            
        # Optional: Offline batch retrain if history hits 3x baseline to counter concept drift
        if len(self._history) == self.baseline_windows * 3:
            self._history = self._history[-self.baseline_windows:] # Drop oldest 2/3rds
            self.iso_forest.fit(self._history)

        # 3. Detection Phase
        is_anomaly = False
        iso_score = 0.0
        triggers = []
        anomaly_type = None
        
        # ML check ONLY if baseline is trained
        if self.baseline_ready:
            pred = self.iso_forest.predict([vector])[0]  # 1 (normal) or -1 (anomaly)
            iso_score = self.iso_forest.score_samples([vector])[0]
            if pred == -1:
                is_anomaly = True
                triggers.append("IsolationForest")
                
        # Z-score checks (Fast response even during baseline)
        if any(z > self.ema_detector.threshold for z in z_scores.values()):
            is_anomaly = True
            for k, z in z_scores.items():
                if z > self.ema_detector.threshold:
                    triggers.append(f"Z-Score Spike ({k}): {z:.2f}")
                    
        # Hard Heuristics (Absolute boundary enforcement)
        if window.packets_per_second > self.DDOS_PPS_THRESHOLD:
            is_anomaly = True
            anomaly_type = "DDOS_SUSPECT"
            triggers.append(f"PPS Hard Limit Exceeded: {window.packets_per_second}")
            
        elif window.unique_dst_ports > self.PORT_SCAN_THRESHOLD:
            is_anomaly = True
            anomaly_type = "PORT_SCAN_SUSPECT"
            triggers.append(f"Dest Ports Hard Limit Exceeded: {window.unique_dst_ports}")
            
        elif z_scores.get("bps", 0.0) > 5.0 and window.bytes_per_second > 5000000:
            # Huge BPS spike -> Exfil
            is_anomaly = True
            anomaly_type = "DATA_EXFILTRATION_SUSPECT"
            triggers.append("BPS Mass Flow Spike")

        if is_anomaly and not anomaly_type:
            anomaly_type = "GENERIC_TRAFFIC_ANOMALY"

        return NetworkAnomalyResult(
            is_anomaly=is_anomaly,
            anomaly_type=anomaly_type,
            isolation_forest_score=iso_score,
            z_scores=z_scores,
            triggers=triggers
        )
