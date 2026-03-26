
"""
Emotion Detector
================
Uses DeepFace (FER+ / AffectNet backend) to classify the driver's
facial expression every N seconds (configurable).
"""

import time
import collections
import numpy as np
import config

try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
except ImportError:
    DEEPFACE_AVAILABLE = False
    print("[EmotionDetector] deepface not installed — emotion detection disabled.")


# Stress weight per emotion (0 = no stress, 1 = max stress)
EMOTION_STRESS_WEIGHT = {
    "angry":    1.00,
    "fear":     0.85,
    "disgust":  0.75,
    "sad":      0.45,
    "surprise": 0.30,
    "neutral":  0.10,
    "happy":    0.00,
}

EMOJI_MAP = {
    "angry":    "😠",
    "fear":     "😨",
    "disgust":  "🤢",
    "sad":      "😢",
    "surprise": "😲",
    "neutral":  "😐",
    "happy":    "😊",
    "unknown":  "❓",
}


class EmotionDetector:
    def __init__(self):
        self._last_analysis_time = 0.0
        self._cached_result      = {
            "emotion":       "unknown",
            "emotion_emoji": "❓",
            "all_emotions":  {},
            "stress_level":  "LOW",
            "emotion_score": 0.0,
            "is_high_stress": False,
        }
        self._history = collections.deque(maxlen=config.EMOTION_HISTORY_LEN)
        self.emotion_score = 0.0

    # ------------------------------------------------------------------ #
    def process(self, frame_bgr):
        """
        Throttled — runs DeepFace every EMOTION_INTERVAL_SEC seconds.
        Returns cached result between runs.
        """
        now = time.time()
        if now - self._last_analysis_time < config.EMOTION_INTERVAL_SEC:
            return self._cached_result

        self._last_analysis_time = now

        if not DEEPFACE_AVAILABLE:
            return self._cached_result

        try:
            analysis = DeepFace.analyze(
                frame_bgr,
                actions=["emotion"],
                enforce_detection=False,
                silent=True,
            )

            if isinstance(analysis, list):
                analysis = analysis[0]

            dominant  = analysis.get("dominant_emotion", "unknown")
            all_emo   = analysis.get("emotion", {})

            # ✅ FIX: Convert percentages (0–100) → fractions (0–1)
            stress_raw = sum(
                (prob / 100.0) * EMOTION_STRESS_WEIGHT.get(emo, 0.0)
                for emo, prob in all_emo.items()
                if emo in EMOTION_STRESS_WEIGHT
            )

            # Convert to 0–100 scale
            stress_score = stress_raw * 100.0

            # Clamp safely
            stress_score = max(0.0, min(100.0, stress_score))

            # Smooth using history
            self._history.append(stress_score)
            self.emotion_score = float(np.mean(self._history))

            is_high = dominant in config.HIGH_STRESS_EMOTIONS

            self._cached_result = {
                "emotion":        dominant,
                "emotion_emoji":  EMOJI_MAP.get(dominant, "❓"),
                "all_emotions":   {k: round(v, 1) for k, v in all_emo.items()},
                "stress_level":   "HIGH" if is_high else "NORMAL",
                "emotion_score":  round(self.emotion_score, 1),
                "is_high_stress": is_high,
            }

        except Exception:
            # DeepFace can fail if no face is found — return cached result
            pass

        return self._cached_result

    # ------------------------------------------------------------------ #
    def reset(self):
        self.emotion_score = 0.0
        self._history.clear()
        self._last_analysis_time = 0.0

