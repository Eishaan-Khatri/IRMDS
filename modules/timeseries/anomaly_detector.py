"""
Finance anomaly detector — Isolation Forest + CUSUM change-point.
"""

from sklearn.ensemble import IsolationForest
import numpy as np


class FinanceAnomalyDetector:
    """Hybrid detector for financial anomalies."""

    def __init__(self, baseline_ticks: int = 100, contamination: float = 0.05):
        self.baseline_ticks = baseline_ticks
        self.iso_forest = IsolationForest(contamination=contamination, random_state=42)
        self.baseline_ready = False
        self._history: list[list[float]] = []
        
        # CUSUM State
        self.cusum_pos = 0.0
        self.cusum_neg = 0.0
        self.cusum_threshold = 5.0  # 5 sigma
        self.cusum_drift = 0.5

    def detect(self, features: dict[str, float]) -> tuple[bool, str | None, float]:
        """Classify features as normal or anomalous."""
        vector = [
            features["log_return"],
            features["volatility"],
            features["rsi"],
            features["bollinger_position"],
            features["momentum"]
        ]
        
        # 1. Train/Update Baseline
        if not self.baseline_ready:
            self._history.append(vector)
            if len(self._history) >= self.baseline_ticks:
                self.iso_forest.fit(self._history)
                self.baseline_ready = True
            return False, None, 0.0

        # 2. Isolation Forest Score
        pred = self.iso_forest.predict([vector])[0]
        score = float(self.iso_forest.score_samples([vector])[0])
        
        is_anomaly = False
        anomaly_type = None
        
        if pred == -1:
            is_anomaly = True
            anomaly_type = "UNSUPERVISED_ANOMALY"

        # 3. Deterministic Flash Crash Rule
        if abs(features["log_return"]) > 0.04:  # 4% move in one tick
            is_anomaly = True
            anomaly_type = "FLASH_CRASH_SUSPECT"
            
        # 4. CUSUM Logic (Simplistic)
        # We monitor volatility shifts
        dev = (features["volatility"] - np.mean([v[1] for v in self._history[-50:]])) / (np.std([v[1] for v in self._history[-50:]]) + 1e-6)
        self.cusum_pos = max(0, self.cusum_pos + dev - self.cusum_drift)
        self.cusum_neg = max(0, self.cusum_neg - dev - self.cusum_drift)
        
        if self.cusum_pos > self.cusum_threshold or self.cusum_neg > self.cusum_threshold:
            is_anomaly = True
            anomaly_type = "VOLATILITY_REGIME_SHIFT"
            self.cusum_pos = 0  # Reset
            self.cusum_neg = 0

        return is_anomaly, anomaly_type, score
