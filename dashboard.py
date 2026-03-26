import tkinter as tk
from tkinter import ttk
import cv2
from PIL import Image, ImageTk
import numpy as np


class DriverDashboard:
    def __init__(self, data_queue):
        self.root = tk.Tk()
        self.root.title("🚗 Driver Safety Dashboard")
        self.root.geometry("1200x700")
        self.root.configure(bg="#0f172a")

        self.data_queue = data_queue
        self.running = True

        # ── Layout ─────────────────────────────────────────
        self.setup_ui()

        # ── Update loop ────────────────────────────────────
        self.update_dashboard()

    def setup_ui(self):
        # Left: Video Feed
        self.video_label = tk.Label(self.root, bg="black")
        self.video_label.place(x=20, y=20, width=800, height=500)

        # Right Panel
        panel = tk.Frame(self.root, bg="#1e293b")
        panel.place(x=850, y=20, width=320, height=500)

        # ── Info Labels ────────────────────────────────────
        self.risk_label = tk.Label(panel, text="Risk: --",
                                   font=("Arial", 16, "bold"),
                                   fg="white", bg="#1e293b")
        self.risk_label.pack(pady=10)

        self.score_label = tk.Label(panel, text="Score: --",
                                    font=("Arial", 14),
                                    fg="white", bg="#1e293b")
        self.score_label.pack(pady=5)

        self.fps_label = tk.Label(panel, text="FPS: --",
                                  font=("Arial", 14),
                                  fg="white", bg="#1e293b")
        self.fps_label.pack(pady=5)

        self.emotion_label = tk.Label(panel, text="Emotion: --",
                                      font=("Arial", 14),
                                      fg="white", bg="#1e293b")
        self.emotion_label.pack(pady=5)

        self.phone_label = tk.Label(panel, text="Phone: --",
                                    font=("Arial", 14),
                                    fg="white", bg="#1e293b")
        self.phone_label.pack(pady=5)

        self.drowsy_label = tk.Label(panel, text="Drowsy: --",
                                     font=("Arial", 14),
                                     fg="white", bg="#1e293b")
        self.drowsy_label.pack(pady=5)

        # ── Alerts Box ─────────────────────────────────────
        alert_frame = tk.Frame(self.root, bg="#111827")
        alert_frame.place(x=20, y=550, width=1150, height=120)

        tk.Label(alert_frame, text="⚠ Alerts",
                 font=("Arial", 16, "bold"),
                 fg="white", bg="#111827").pack(anchor="w")

        self.alert_box = tk.Text(alert_frame, height=5,
                                 bg="#020617", fg="red",
                                 font=("Arial", 12))
        self.alert_box.pack(fill="both", expand=True)

    # ──────────────────────────────────────────────────────
    def update_dashboard(self):
        if not self.running:
            return

        try:
            while not self.data_queue.empty():
                data = self.data_queue.get_nowait()

                self.update_video(data["frame"])
                self.update_stats(data)

        except Exception as e:
            print("[Dashboard Error]", e)

        self.root.after(30, self.update_dashboard)

    # ──────────────────────────────────────────────────────
    def update_video(self, frame):
        # Convert RGB → Image
        frame = cv2.resize(frame, (800, 500))
        img = Image.fromarray(frame)
        imgtk = ImageTk.PhotoImage(image=img)

        self.video_label.imgtk = imgtk
        self.video_label.configure(image=imgtk)

    # ──────────────────────────────────────────────────────
    def update_stats(self, data):
        risk = data["risk"]
        eye = data["eye"]
        phone = data["phone"]
        emo = data["emotion"]

        # Risk
        self.risk_label.config(
            text=f"Risk: {risk['risk_level']}",
            fg=self.get_risk_color(risk["risk_level"])
        )

        self.score_label.config(
            text=f"Score: {risk['smooth_score']:.1f}"
        )

        self.fps_label.config(
            text=f"FPS: {data['fps']:.0f}"
        )

        self.emotion_label.config(
            text=f"Emotion: {emo['emotion']}"
        )

        self.phone_label.config(
            text=f"Phone: {'Detected' if phone['phone_detected'] else 'No'}"
        )

        self.drowsy_label.config(
            text=f"Drowsy: {'Yes' if eye['is_drowsy'] else 'No'}"
        )

        # Alerts
        for alert in data["alerts"]:
            self.alert_box.insert(tk.END, f"{alert}\n")
            self.alert_box.see(tk.END)

    # ──────────────────────────────────────────────────────
    def get_risk_color(self, level):
        if level == "LOW":
            return "green"
        elif level == "MEDIUM":
            return "orange"
        elif level == "HIGH":
            return "red"
        return "white"

    # ──────────────────────────────────────────────────────
    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.mainloop()

    def on_close(self):
        self.running = False
        self.root.destroy()