import cv2
import mediapipe as mp

class PhoneDetector:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(max_num_hands=2)
        self.mp_face = mp.solutions.face_detection
        self.face = self.mp_face.FaceDetection()

        self.phone_detected = False
        self.consec_detected = 0

    def process(self, frame_bgr):
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        hand_result = self.hands.process(frame_rgb)
        face_result = self.face.process(frame_rgb)

        detected = False

        # ── Get face box ─────────────────────────
        face_box = None
        if face_result.detections:
            for det in face_result.detections:
                bbox = det.location_data.relative_bounding_box
                h, w, _ = frame_bgr.shape
                x1 = int(bbox.xmin * w)
                y1 = int(bbox.ymin * h)
                x2 = int((bbox.xmin + bbox.width) * w)
                y2 = int((bbox.ymin + bbox.height) * h)
                face_box = (x1, y1, x2, y2)

        # ── Check hand near face ─────────────────
        if hand_result.multi_hand_landmarks and face_box:
            fx1, fy1, fx2, fy2 = face_box

            for hand_landmarks in hand_result.multi_hand_landmarks:
                for lm in hand_landmarks.landmark:
                    h, w, _ = frame_bgr.shape
                    x = int(lm.x * w)
                    y = int(lm.y * h)

                    # if hand point inside face region
                    if fx1 < x < fx2 and fy1 < y < fy2:
                        detected = True
                        break

        # ── Smoothing ───────────────────────────
        if detected:
            self.consec_detected += 1
        else:
            self.consec_detected = max(0, self.consec_detected - 1)

        self.phone_detected = self.consec_detected >= 3

        return {
            "phone_detected": self.phone_detected,
            "distraction_score": 100.0 if self.phone_detected else 0.0,
            "boxes": [],
        }

    def draw_boxes(self, frame):
        return frame