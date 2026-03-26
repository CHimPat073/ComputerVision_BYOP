"""
Risk Scoring Engine
===================
Fuses drowsiness, distraction and emotion sub-scores into a single
0–100 composite risk score, then classifies it into a risk level.

Uses Exponential Moving Average (EMA) to smooth rapid fluctuations
while still responding quickly to sustained danger.
"""

import time
import collections
import config


class RiskEngine:
    def __init__(self):
        self.raw_score      = 0.0    # unsmoothed
        self.smooth_score   = 0.0    # EMA-smoothed
        self.risk_level     = "SAFE"
        self.risk_color     = config.RISK_COLORS["SAFE"]

        # Keep a time-series for the dashboard chart
        self._history: list[tuple[float, float]] = []   # (timestamp, score)
        self._max_history = config.HISTORY_PLOT_POINTS * 2   # over-collect

        # Per-component scores (for breakdown display)
        self.component_scores = {
            "drowsiness":  0.0,
            "distraction": 0.0,
            "emotion":     0.0,
        }

    # ------------------------------------------------------------------ #
    def update(
        self,
        drowsiness_score:  float,
        distraction_score: float,
        emotion_score:     float,
    ) -> dict:
        """
        Call once per frame with the three sub-scores (each 0–100).
        Returns a result dict.
        """
        w = config.RISK_WEIGHTS

        self.component_scores = {
            "drowsiness":  round(drowsiness_score, 1),
            "distraction": round(distraction_score, 1),
            "emotion":     round(emotion_score, 1),
        }

        self.raw_score = (
            drowsiness_score  * w["drowsiness"]  +
            distraction_score * w["distraction"] +
            emotion_score     * w["emotion"]
        )
        self.raw_score = min(100.0, max(0.0, self.raw_score))

        # EMA
        α = config.RISK_UPDATE_ALPHA
        self.smooth_score = α * self.raw_score + (1 - α) * self.smooth_score

        # Classify level
        self.risk_level = self._classify(self.smooth_score)
        self.risk_color = config.RISK_COLORS[self.risk_level]

        # Record history
        self._history.append((time.time(), round(self.smooth_score, 2)))
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        return self.state()

    # ------------------------------------------------------------------ #
    def _classify(self, score: float) -> str:
        for level, (lo, hi) in config.RISK_LEVELS.items():
            if lo <= score < hi:
                return level
        return "CRITICAL"

    # ------------------------------------------------------------------ #
    def state(self) -> dict:
        return {
            "raw_score":        round(self.raw_score, 1),
            "smooth_score":     round(self.smooth_score, 1),
            "risk_level":       self.risk_level,
            "risk_color":       self.risk_color,
            "component_scores": self.component_scores.copy(),
        }

    # ------------------------------------------------------------------ #
    def get_history(self, last_n_seconds: int = 120):
        """Return list of (relative_seconds_ago, score) for plotting."""
        now   = time.time()
        cutoff = now - last_n_seconds
        recent = [(ts, sc) for ts, sc in self._history if ts >= cutoff]
        return [(round(now - ts, 1), sc) for ts, sc in recent]

    # ------------------------------------------------------------------ #
    def reset(self):
        self.raw_score    = 0.0
        self.smooth_score = 0.0
        self.risk_level   = "SAFE"
        self.risk_color   = config.RISK_COLORS["SAFE"]
        self._history.clear()
        self.component_scores = {k: 0.0 for k in self.component_scores}
