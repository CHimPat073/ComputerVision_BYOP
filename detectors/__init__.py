
"""
Detectors Package
=================
Exports all detector classes for easy import.
"""

from .eye_detector import EyeDetector
from .phone_detector import PhoneDetector
from .emotion_detector import EmotionDetector

__all__ = [
    "EyeDetector",
    "PhoneDetector",
    "EmotionDetector",
]

