
"""
Drowsiness Detector
===================
Uses MediaPipe Face Mesh to compute the Eye Aspect Ratio (EAR).
Also tracks PERCLOS — percentage of eye closure over a rolling window.

EAR formula (Soukupová & Čech, 2016):
    EAR = (‖p2-p6‖ + ‖p3-p5‖) / (2 · ‖p1-p4‖)
"""

import time
import collections
import numpy as np
import mediapipe as mp
from scipy.spatial.distance import euclidean
import config

# MediaPipe landmark indices for left / right eye
LEFT_EYE  = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33,  160, 158, 133, 153, 144]


class EyeDetector:
    def __init__(self):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh    = self.mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        # ✅ Cache for landmarks (FIX)
        self._last_landmarks = None

        # Rolling history for PERCLOS
        self._perclos_window = collections.deque(
            maxlen=config.FPS_TARGET * config.PERCLOS_WINDOW_SEC
        )

        self.consec_closed     = 0
        self.total_blinks      = 0
        self.last_blink_time   = time.time()
        self.avg_blink_rate    = 0.0
        self._blink_times      = collections.deque(maxlen=60)

        # Public state
        self.ear               = 1.0
        self.perclos           = 0.0
        self.is_drowsy         = False
        self.drowsiness_score  = 0.0

        # Face presence
        self.face_detected     = False

    # ------------------------------------------------------------------ #
    def _ear_from_landmarks(self, landmarks, indices, w, h):
        pts = np.array(
            [(landmarks[i].x * w, landmarks[i].y * h) for i in indices],
            dtype=np.float32,
        )

        v1 = euclidean(pts[1], pts[5])
        v2 = euclidean(pts[2], pts[4])
        hz = euclidean(pts[0], pts[3])

        return (v1 + v2) / (2.0 * hz + 1e-6)

    # ------------------------------------------------------------------ #
    def process(self, frame_rgb, frame_shape):
        h, w = frame_shape[:2]

        results = self.face_mesh.process(frame_rgb)
        self.face_detected = results.multi_face_landmarks is not None

        if not self.face_detected:
            self._last_landmarks = None  # ✅ clear cache
            self._perclos_window.append(0)
            self.drowsiness_score = 0.0
            return self._state()

        # ✅ Cache landmarks (FIX)
        self._last_landmarks = results.multi_face_landmarks[0].landmark
        landmarks = self._last_landmarks

        left_ear  = self._ear_from_landmarks(landmarks, LEFT_EYE,  w, h)
        right_ear = self._ear_from_landmarks(landmarks, RIGHT_EYE, w, h)
        self.ear  = (left_ear + right_ear) / 2.0

        eye_closed = self.ear < config.EAR_THRESHOLD
        self._perclos_window.append(1 if eye_closed else 0)

        if eye_closed:
            self.consec_closed += 1
        else:
            if self.consec_closed >= 2:
                self.total_blinks += 1
                now = time.time()
                self._blink_times.append(now)
                self.last_blink_time = now
            self.consec_closed = 0

        # Blink rate (last 60 sec)
        now = time.time()
        recent = [t for t in self._blink_times if now - t <= 60]
        self.avg_blink_rate = len(recent)

        # PERCLOS
        if len(self._perclos_window) > 0:
            self.perclos = sum(self._perclos_window) / len(self._perclos_window)

        # Drowsiness condition
        self.is_drowsy = (
            self.consec_closed >= config.EAR_CONSEC_FRAMES
            or self.perclos     >= config.PERCLOS_ALERT_THRESH
        )

        # Score
        ear_score     = max(0.0, 1.0 - self.ear / config.EAR_THRESHOLD) * 60
        perclos_score = min(self.perclos / config.PERCLOS_ALERT_THRESH, 1.0) * 40
        self.drowsiness_score = min(100.0, ear_score + perclos_score)

        return self._state()

    # ------------------------------------------------------------------ #
    def _state(self):
        return {
            "ear":              round(self.ear, 3),
            "perclos":          round(self.perclos * 100, 1),
            "consec_closed":    self.consec_closed,
            "blink_rate":       round(self.avg_blink_rate, 1),
            "is_drowsy":        self.is_drowsy,
            "drowsiness_score": round(self.drowsiness_score, 1),
            "face_detected":    self.face_detected,
        }

    # ------------------------------------------------------------------ #
    def get_eye_landmarks(self, frame_rgb, frame_shape):
        """Return pixel coords of both eye contours for visualisation."""
        h, w = frame_shape[:2]

        # ✅ Use cached landmarks (FIX)
        if self._last_landmarks is None:
            return [], []

        lm = self._last_landmarks

        left  = [(int(lm[i].x * w), int(lm[i].y * h)) for i in LEFT_EYE]
        right = [(int(lm[i].x * w), int(lm[i].y * h)) for i in RIGHT_EYE]

        return left, right

    # ------------------------------------------------------------------ #
    def reset(self):
        self.consec_closed    = 0
        self.total_blinks     = 0
        self.drowsiness_score = 0.0
        self._perclos_window.clear()
        self._blink_times.clear()
        self._last_landmarks = None  # ✅ reset cache

