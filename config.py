"""
Driver Safety System — Central Configuration
"""

import os

# CAMERA
CAMERA_INDEX = 0
FRAME_WIDTH  = 640
FRAME_HEIGHT = 480
FPS_TARGET   = 30

# EYE / DROWSINESS
EAR_THRESHOLD        = 0.25
EAR_CONSEC_FRAMES    = 20
PERCLOS_WINDOW_SEC   = 60
PERCLOS_ALERT_THRESH = 0.30

# PHONE DETECTION
YOLO_MODEL          = "yolov8m.pt"
YOLO_CONF_THRESHOLD = 0.15
PHONE_CLASS_ID      = 67
PHONE_CONSEC_FRAMES = 1

# EMOTION
EMOTION_INTERVAL_SEC = 1.5
HIGH_STRESS_EMOTIONS = {"angry", "fear", "disgust"}
EMOTION_HISTORY_LEN  = 20

# RISK ENGINE
RISK_WEIGHTS = {
    "drowsiness":  0.45,
    "distraction": 0.35,
    "emotion":     0.20,
}

RISK_UPDATE_ALPHA = 0.3

RISK_LEVELS = {
    "SAFE":     (0,  30),
    "LOW":      (30, 55),
    "MODERATE": (55, 75),
    "HIGH":     (75, 90),
    "CRITICAL": (90, 101),
}

RISK_COLORS = {
    "SAFE":     "#00e676",
    "LOW":      "#ffee58",
    "MODERATE": "#ffa726",
    "HIGH":     "#ef5350",
    "CRITICAL": "#b71c1c",
}

# ALERT SYSTEM
ENABLE_TTS         = True
ENABLE_SOUND       = True
ENABLE_SMS         = True  # New: Enable SMS alerts
ALERT_COOLDOWN_SEC = 2
ALERT_SOUND_FILE   = "assets/alert.wav"

# Twilio SMS Configuration (use environment variables for security)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER")  # Your Twilio phone number
ALERT_TO_NUMBERS   = os.getenv("ALERT_TO_NUMBERS", "").split(",")  # Comma-separated list of recipient numbers

ALERT_MESSAGES = {
    "drowsiness_mild":  "Stay alert",
    "drowsiness_severe":"Wake up immediately",
    "phone_detected":   "Do not use phone while driving",
    "stress_high":      "You seem stressed",
    "risk_critical":    "Critical driving condition",
}

# DASHBOARD
HISTORY_PLOT_POINTS = 120
LOG_MAX_EVENTS      = 200