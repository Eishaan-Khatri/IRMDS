"""
Finance feature extractor: computes technical indicators.
"""

import math
from collections import deque

import numpy as np


class FinanceFeatureExtractor:
    """Compute technical indicators from a rolling window of price ticks."""

    def __init__(self, window_size: int = 50):
        self.window_size = window_size
        self.history: deque[float] = deque(maxlen=window_size)
        self.returns_history: deque[float] = deque(maxlen=window_size)

    def update(self, close_price: float) -> dict[str, float] | None:
        """Add a new price and return features if history is sufficient."""
        if self.history:
            prev_close = self.history[-1]
            log_return = math.log(close_price / prev_close)
            self.returns_history.append(log_return)

        self.history.append(close_price)

        if len(self.history) < self.window_size:
            return None

        returns_arr = np.array(self.returns_history)
        volatility = float(np.std(returns_arr))
        rsi = self._compute_rsi(14)

        prices_arr = np.array(self.history)
        sma = np.mean(prices_arr[-20:])
        std = np.std(prices_arr[-20:])
        bollinger = (close_price - sma) / (2 * std) if std > 0 else 0
        momentum = (close_price / self.history[-10]) - 1 if len(self.history) >= 10 else 0

        return {
            "log_return": self.returns_history[-1] if self.returns_history else 0,
            "volatility": volatility,
            "rsi": rsi,
            "bollinger_position": bollinger,
            "momentum": momentum,
        }

    def _compute_rsi(self, period: int) -> float:
        """Compute Relative Strength Index."""
        if len(self.returns_history) < period:
            return 50.0

        returns = list(self.returns_history)[-period:]
        gains = [r for r in returns if r > 0]
        losses = [abs(r) for r in returns if r < 0]

        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
