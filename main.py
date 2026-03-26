import argparse
import queue
import sys
import os
import threading
import time
import cv2

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# ── Ensure project root in path ───────────────────────────
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import config
from detectors import EyeDetector, PhoneDetector, EmotionDetector
from core import RiskEngine, AlertSystem
from annotator import annotate

# ── Optional dashboard ────────────────────────────────────
try:
    from dashboard import DriverDashboard
    DASHBOARD_AVAILABLE = True
except Exception as e:
    print(f"[main] Dashboard not available: {e}")
    DASHBOARD_AVAILABLE = False


_args = None


# ═══════════════════════════════════════════════════════════
# CAPTURE LOOP
# ═══════════════════════════════════════════════════════════
def capture_loop(camera_source, data_queue, stop_event):
    cap = cv2.VideoCapture(camera_source)

    if not cap.isOpened():
        print(f"[capture_loop] ERROR: Cannot open camera: {camera_source}")
        stop_event.set()
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS, config.FPS_TARGET)

    # ── Initialize modules ────────────────────────────────
    eye_det = EyeDetector()
    phone_det = PhoneDetector()
    emo_det = EmotionDetector()
    risk_eng = RiskEngine()
    alert_sys = AlertSystem()

    fps_counter = 0
    fps_timer = time.time()
    fps = 0.0

    print("[capture_loop] Started successfully")

    while not stop_event.is_set():
        try:
            ret, frame_bgr = cap.read()
            if not ret:
                print("[capture_loop] Frame read failed")
                break

            # Convert to RGB
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

            # ── DETECTORS ───────────────────────────────
            eye_state = eye_det.process(frame_rgb, frame_bgr.shape)
            phone_state = phone_det.process(frame_bgr)
            emo_state = emo_det.process(frame_bgr)

            # ── SAFETY CHECK (prevents crash)
            if "distraction_score" not in phone_state:
                phone_state["distraction_score"] = 0.0

            # ── RISK ENGINE ─────────────────────────────
            risk_state = risk_eng.update(
                drowsiness_score=eye_state.get("drowsiness_score", 0.0),
                distraction_score=phone_state.get("distraction_score", 0.0),
                emotion_score=emo_state.get("emotion_score", 0.0),
            )

            # ── ALERT SYSTEM ────────────────────────────
            new_alerts = alert_sys.evaluate(
                eye_state, phone_state, emo_state, risk_state
            )

            # ── ANNOTATION ─────────────────────────────
            left_pts, right_pts = eye_det.get_eye_landmarks(
                frame_rgb, frame_bgr.shape
            )

            annotated_rgb = annotate(
                frame_rgb,
                eye_state,
                phone_state,
                emo_state,
                risk_state,
                fps,
                left_pts,
                right_pts,
            )

            # ── DRAW PHONE BOXES (SAFE RGB↔BGR FIX) ─────
            frame_bgr_draw = cv2.cvtColor(annotated_rgb, cv2.COLOR_RGB2BGR)
            frame_bgr_draw = phone_det.draw_boxes(frame_bgr_draw)
            annotated_rgb = cv2.cvtColor(frame_bgr_draw, cv2.COLOR_BGR2RGB)

            # ── FPS CALCULATION ────────────────────────
            fps_counter += 1
            if time.time() - fps_timer >= 1.0:
                fps = fps_counter / (time.time() - fps_timer)
                fps_counter = 0
                fps_timer = time.time()

            # ── SEND DATA TO DASHBOARD ────────────────
            payload = {
                "frame": annotated_rgb,
                "eye": eye_state,
                "phone": phone_state,
                "emotion": emo_state,
                "risk": risk_state,
                "fps": fps,
                "alerts": new_alerts,
            }

            try:
                data_queue.put_nowait(payload)
            except queue.Full:
                pass

            # ── HEADLESS OUTPUT ───────────────────────
            if not DASHBOARD_AVAILABLE or _args.no_dashboard:
                print(
                    f"\r[{risk_state.get('risk_level','SAFE')}] "
                    f"Score={risk_state.get('smooth_score',0):.1f} | "
                    f"Phone={phone_state.get('phone_detected', False)} | "
                    f"FPS={fps:.0f}",
                    end=""
                )

        except Exception as e:
            print("[capture_loop CRASH]", e)

    cap.release()
    print("\n[capture_loop] Stopped")


# ═══════════════════════════════════════════════════════════
# MAIN FUNCTION
# ═══════════════════════════════════════════════════════════
def main():
    global _args

    parser = argparse.ArgumentParser()
    parser.add_argument("--camera", type=int, default=config.CAMERA_INDEX)
    parser.add_argument("--demo", type=str, default=None)
    parser.add_argument("--no-dashboard", action="store_true")

    _args = parser.parse_args()

    camera_source = _args.demo if _args.demo else _args.camera

    data_queue = queue.Queue(maxsize=5)
    stop_event = threading.Event()

    # Start capture thread
    capture_thread = threading.Thread(
        target=capture_loop,
        args=(camera_source, data_queue, stop_event),
        daemon=True,
    )
    capture_thread.start()

    # ── DASHBOARD ─────────────────────────────
    if DASHBOARD_AVAILABLE and not _args.no_dashboard:
        dashboard = DriverDashboard(data_queue)
        try:
            dashboard.run()
        except KeyboardInterrupt:
            pass
        finally:
            stop_event.set()
    else:
        try:
            while capture_thread.is_alive():
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n[main] Interrupted")
        finally:
            stop_event.set()

    capture_thread.join(timeout=3)
    print("[main] Exit cleanly")


if __name__ == "__main__":
    main()