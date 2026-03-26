
"""
Frame Annotator (Emoji-safe version)
"""

import cv2
import numpy as np
import config

GREEN   = (55,  200, 60)
YELLOW  = (0,   210, 220)
ORANGE  = (0,   140, 255)
RED     = (60,  50,  245)
WHITE   = (230, 230, 230)
GRAY    = (120, 120, 120)
BLUE    = (255, 140, 60)

RISK_BGR = {
    "SAFE":     GREEN,
    "LOW":      (80, 220, 120),
    "MODERATE": YELLOW,
    "HIGH":     ORANGE,
    "CRITICAL": RED,
}


def annotate(
    frame:         np.ndarray,
    eye_state:     dict,
    phone_state:   dict,
    emotion_state: dict,
    risk_state:    dict,
    fps:           float,
    left_eye_pts:  list,
    right_eye_pts: list,
) -> np.ndarray:

    out = frame.copy()
    h, w = out.shape[:2]

    # ── Eye contours ─────────────────────────────────────────────────
    if eye_state.get("face_detected"):
        ear    = eye_state.get("ear", 1.0)
        closed = ear < config.EAR_THRESHOLD
        col    = RED if closed else GREEN

        for pts in (left_eye_pts, right_eye_pts):
            if pts:
                hull = cv2.convexHull(np.array(pts, dtype=np.int32))
                cv2.drawContours(out, [hull], -1, col, 1)
                cv2.polylines(out, [np.array(pts, np.int32)], True, col, 1)

    # ── Phone boxes ───────────────────────────────────────────────────
    for box in phone_state.get("boxes", []):
        x1, y1, x2, y2 = box["xyxy"]
        conf = box["conf"]
        cv2.rectangle(out, (x1, y1), (x2, y2), ORANGE, 2)
        label = f"PHONE {conf:.0%}"
        _text_bg(out, label, (x1, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, ORANGE)

    # ── Risk bar ──────────────────────────────────────────────────────
    level = risk_state.get("risk_level", "SAFE")
    score = risk_state.get("smooth_score", 0.0)
    bar_w = int(w * score / 100.0)
    color = RISK_BGR[level]
    cv2.rectangle(out, (0, 0), (bar_w, 6), color, -1)

    # ── HUD ───────────────────────────────────────────────────────────
    hud_x, hud_y = 10, h - 150
    _hud_bg(out, hud_x, hud_y, 210, 140)

    texts = [
        (f"RISK : {score:5.1f}  [{level}]", color),
        (f"EAR  : {eye_state.get('ear', 0):.3f}", WHITE),
        (f"PERCL: {eye_state.get('perclos', 0):.1f}%", WHITE),
        (f"BLINK: {eye_state.get('blink_rate', 0):.0f}/min", WHITE),
        (f"PHONE: {'YES' if phone_state.get('phone_detected') else 'NO '}  {phone_state.get('confidence', 0):.0f}%",
         ORANGE if phone_state.get("phone_detected") else WHITE),

        # ✅ FIX: remove emoji from HUD
        (f"EMOT : {emotion_state.get('emotion', 'NONE')[:9]:9s}", WHITE),

        (f"FPS  : {fps:.0f}", GRAY),
    ]

    for i, (txt, col) in enumerate(texts):
        cv2.putText(out, txt, (hud_x + 6, hud_y + 18 + i * 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, col, 1, cv2.LINE_AA)

    # ── Alert banner (ASCII safe) ─────────────────────────────────────
    if eye_state.get("is_drowsy"):
        _alert_banner(out, "[WARNING] DROWSY DRIVER!", RED, w)

    elif phone_state.get("phone_detected"):
        _alert_banner(out, "[ALERT] DRIVER DISTRACTED (PHONE)", ORANGE, w)

    elif emotion_state.get("is_high_stress"):
        _alert_banner(out, "[CAUTION] HIGH STRESS DETECTED", (200, 80, 200), w)

    return out


# ── Helpers ─────────────────────────────────────────────────────────── #
def _hud_bg(frame, x, y, bw, bh, alpha=0.45):
    overlay = frame.copy()
    cv2.rectangle(overlay, (x, y), (x + bw, y + bh), (20, 20, 20), -1)
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)


def _text_bg(frame, text, org, font, scale, color):
    (tw, th), baseline = cv2.getTextSize(text, font, scale, 1)
    x, y = org
    cv2.rectangle(frame, (x, y - th - 4), (x + tw + 4, y + baseline), (20, 20, 20), -1)
    cv2.putText(frame, text, (x + 2, y - 2), font, scale, color, 1, cv2.LINE_AA)


def _alert_banner(frame, text, color, frame_w):
    h_f = frame.shape[0]
    banner_h = 38

    overlay = frame.copy()
    cv2.rectangle(overlay, (0, h_f - banner_h), (frame_w, h_f), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.85, 2)
    x = (frame_w - tw) // 2

    cv2.putText(frame, text, (x, h_f - 9),
                cv2.FONT_HERSHEY_SIMPLEX, 0.85, color, 2, cv2.LINE_AA)

