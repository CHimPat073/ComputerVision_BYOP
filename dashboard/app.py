"""
Driver Safety Dashboard
========================
A Tkinter window with:
  • Left  panel → live video feed (annotated)
  • Center panel → risk gauge + component score bars
  • Right  panel → alert log + scrolling risk history chart

Thread-safe: the main processing loop (OpenCV) pushes data via queue;
the Tkinter mainloop reads it on its own thread.
"""

import time
import queue
import threading
import collections
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.patches as mpatches

import config

# ── Palette ───────────────────────────────────────────────────────────
BG          = "#0d1117"
PANEL_BG    = "#161b22"
CARD_BG     = "#1c2333"
TEXT_MAIN   = "#e6edf3"
TEXT_DIM    = "#8b949e"
ACCENT      = "#58a6ff"
SUCCESS     = "#3fb950"
WARNING     = "#d29922"
DANGER      = "#f85149"
CRITICAL    = "#ff0000"
FONT_HEAD   = ("Courier New", 13, "bold")
FONT_BODY   = ("Courier New", 11)
FONT_SMALL  = ("Courier New", 9)

RISK_HEX = {
    "SAFE":     SUCCESS,
    "LOW":      "#b5e853",
    "MODERATE": WARNING,
    "HIGH":     DANGER,
    "CRITICAL": CRITICAL,
}


class DriverDashboard:
    def __init__(self, data_queue: queue.Queue):
        self._q     = data_queue
        self._root  = tk.Tk()
        self._root.title(config.DASHBOARD_TITLE)
        self._root.configure(bg=BG)
        self._root.resizable(False, False)

        # History for chart
        self._risk_history   = collections.deque(maxlen=config.HISTORY_PLOT_POINTS)
        self._time_axis      = collections.deque(maxlen=config.HISTORY_PLOT_POINTS)
        self._start_time     = time.time()

        self._alert_log_items: list[str] = []

        self._build_ui()
        self._poll()   # start polling the queue

    # ================================================================== #
    #  UI CONSTRUCTION
    # ================================================================== #
    def _build_ui(self):
        W, H = 1280, 760
        self._root.geometry(f"{W}x{H}")

        # ── Header ────────────────────────────────────────────────────
        hdr = tk.Frame(self._root, bg=BG, pady=6)
        hdr.pack(fill=tk.X, padx=10)
        tk.Label(hdr, text="🚗  DRIVER SAFETY MONITOR",
                 font=("Courier New", 18, "bold"), bg=BG, fg=ACCENT).pack(side=tk.LEFT)
        self._lbl_time = tk.Label(hdr, text="", font=FONT_BODY, bg=BG, fg=TEXT_DIM)
        self._lbl_time.pack(side=tk.RIGHT)

        # ── Main 3-column layout ──────────────────────────────────────
        body = tk.Frame(self._root, bg=BG)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Column widths
        left  = tk.Frame(body, bg=BG, width=480)
        mid   = tk.Frame(body, bg=BG, width=340)
        right = tk.Frame(body, bg=BG, width=430)
        for col in (left, mid, right):
            col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        self._build_left(left)
        self._build_mid(mid)
        self._build_right(right)

    # ── LEFT: Video feed ───────────────────────────────────────────── #
    def _build_left(self, parent):
        card = self._card(parent, "📷  LIVE FEED")
        self._video_label = tk.Label(card, bg="black")
        self._video_label.pack(padx=4, pady=4)

        # Status row
        row = tk.Frame(card, bg=CARD_BG)
        row.pack(fill=tk.X, padx=6, pady=4)
        self._lbl_fps   = self._stat_lbl(row, "FPS",  "–")
        self._lbl_face  = self._stat_lbl(row, "FACE", "–")
        self._lbl_ear   = self._stat_lbl(row, "EAR",  "–")

        # Drowsiness bar
        self._build_h_bar(card, "DROWSINESS",  "drowsiness_bar",  config.RISK_COLORS["HIGH"])
        self._build_h_bar(card, "DISTRACTION", "distraction_bar", config.RISK_COLORS["MODERATE"])
        self._build_h_bar(card, "EMOTION STRESS", "emotion_bar",  config.RISK_COLORS["LOW"])

        # Detection tags
        tag_row = tk.Frame(card, bg=CARD_BG)
        tag_row.pack(fill=tk.X, padx=6, pady=(4, 6))
        self._tag_drowsy  = self._tag(tag_row, "DROWSY",  DANGER)
        self._tag_phone   = self._tag(tag_row, "PHONE",   "#ff6b00")
        self._tag_stress  = self._tag(tag_row, "STRESS",  "#b37feb")
        self._tag_emotion = tk.Label(tag_row, text="😐", font=("Segoe UI Emoji", 22),
                                     bg=CARD_BG, fg=TEXT_MAIN)
        self._tag_emotion.pack(side=tk.RIGHT, padx=4)

    # ── MID: Risk gauge + info ─────────────────────────────────────── #
    def _build_mid(self, parent):
        card = self._card(parent, "⚡  RISK SCORE")

        # Big score number
        self._lbl_score = tk.Label(card, text="0", font=("Courier New", 64, "bold"),
                                   bg=CARD_BG, fg=SUCCESS)
        self._lbl_score.pack(pady=(10, 0))
        self._lbl_level = tk.Label(card, text="SAFE", font=("Courier New", 16, "bold"),
                                   bg=CARD_BG, fg=SUCCESS)
        self._lbl_level.pack()

        # Gauge (matplotlib arc)
        fig, ax = plt.subplots(figsize=(3.2, 1.7), facecolor=CARD_BG)
        ax.set_facecolor(CARD_BG)
        self._gauge_ax = ax
        self._gauge_fig = fig
        self._gauge_canvas = FigureCanvasTkAgg(fig, master=card)
        self._gauge_canvas.get_tk_widget().pack(padx=4, pady=4)
        self._draw_gauge(0, SUCCESS)

        # Component breakdown
        sep = tk.Frame(card, bg="#30363d", height=1)
        sep.pack(fill=tk.X, padx=10, pady=6)

        tk.Label(card, text="COMPONENT BREAKDOWN",
                 font=FONT_SMALL, bg=CARD_BG, fg=TEXT_DIM).pack()
        self._comp_bars = {}
        for name, color in [("drowsiness", DANGER),
                             ("distraction", WARNING),
                             ("emotion", "#b37feb")]:
            self._comp_bars[name] = self._build_v_bar(card, name.upper(), color)

        # Stats
        sep2 = tk.Frame(card, bg="#30363d", height=1)
        sep2.pack(fill=tk.X, padx=10, pady=6)
        stats = tk.Frame(card, bg=CARD_BG)
        stats.pack(fill=tk.X, padx=10)
        self._lbl_blink  = self._kv(stats, "Blink Rate", "– /min")
        self._lbl_perclos = self._kv(stats, "PERCLOS",   "–%")
        self._lbl_phone_conf = self._kv(stats, "Phone Conf", "–%")
        self._lbl_emotion    = self._kv(stats, "Emotion",    "–")
        self._lbl_session    = self._kv(stats, "Session",    "0:00")

    # ── RIGHT: Chart + log ────────────────────────────────────────────#
    def _build_right(self, parent):
        # Risk chart
        chart_card = self._card(parent, "📈  RISK HISTORY (2 min)")
        fig, ax = plt.subplots(figsize=(4.1, 2.2), facecolor=PANEL_BG)
        ax.set_facecolor(PANEL_BG)
        ax.tick_params(colors=TEXT_DIM, labelsize=7)
        ax.spines[:].set_color("#30363d")
        ax.set_ylim(0, 105)
        ax.set_xlabel("seconds ago", color=TEXT_DIM, fontsize=7)
        ax.set_ylabel("risk", color=TEXT_DIM, fontsize=7)
        self._chart_ax  = ax
        self._chart_fig = fig
        self._chart_canvas = FigureCanvasTkAgg(fig, master=chart_card)
        self._chart_canvas.get_tk_widget().pack(padx=4, pady=4)

        # Alert log
        log_card = self._card(parent, "🔔  ALERT LOG")
        self._log_text = tk.Text(
            log_card, bg=CARD_BG, fg=TEXT_MAIN, font=FONT_SMALL,
            height=14, state=tk.DISABLED, wrap=tk.WORD,
            insertbackground=TEXT_MAIN, relief=tk.FLAT,
        )
        scroll = ttk.Scrollbar(log_card, command=self._log_text.yview)
        self._log_text.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._log_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        btn_row = tk.Frame(log_card, bg=CARD_BG)
        btn_row.pack(fill=tk.X, padx=6, pady=(0, 6))
        tk.Button(btn_row, text="Clear Log", font=FONT_SMALL, bg="#21262d",
                  fg=TEXT_DIM, relief=tk.FLAT,
                  command=self._clear_log).pack(side=tk.RIGHT)
        self._lbl_alert_count = tk.Label(btn_row, text="0 alerts",
                                          font=FONT_SMALL, bg=CARD_BG, fg=TEXT_DIM)
        self._lbl_alert_count.pack(side=tk.LEFT)

    # ================================================================== #
    #  HELPER BUILDERS
    # ================================================================== #
    def _card(self, parent, title: str):
        frame = tk.Frame(parent, bg=CARD_BG, bd=0,
                         highlightthickness=1, highlightbackground="#30363d")
        frame.pack(fill=tk.BOTH, expand=True, pady=4)
        tk.Label(frame, text=title, font=FONT_HEAD, bg=CARD_BG,
                 fg=ACCENT, anchor="w").pack(fill=tk.X, padx=8, pady=(6, 2))
        return frame

    def _stat_lbl(self, parent, key, val):
        f = tk.Frame(parent, bg=CARD_BG)
        f.pack(side=tk.LEFT, padx=8)
        tk.Label(f, text=key, font=FONT_SMALL, bg=CARD_BG, fg=TEXT_DIM).pack()
        lbl = tk.Label(f, text=val, font=FONT_BODY, bg=CARD_BG, fg=TEXT_MAIN)
        lbl.pack()
        return lbl

    def _build_h_bar(self, parent, label, attr, color):
        row = tk.Frame(parent, bg=CARD_BG)
        row.pack(fill=tk.X, padx=8, pady=2)
        tk.Label(row, text=label, font=FONT_SMALL, bg=CARD_BG,
                 fg=TEXT_DIM, width=16, anchor="w").pack(side=tk.LEFT)
        canvas = tk.Canvas(row, bg="#21262d", height=14,
                           highlightthickness=0, bd=0)
        canvas.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        lbl = tk.Label(row, text="0%", font=FONT_SMALL, bg=CARD_BG,
                       fg=TEXT_MAIN, width=5)
        lbl.pack(side=tk.RIGHT)
        setattr(self, f"_{attr}_canvas", canvas)
        setattr(self, f"_{attr}_lbl",    lbl)
        setattr(self, f"_{attr}_color",  color)
        return canvas

    def _update_h_bar(self, attr, value: float):
        canvas = getattr(self, f"_{attr}_canvas")
        lbl    = getattr(self, f"_{attr}_lbl")
        color  = getattr(self, f"_{attr}_color")
        canvas.update_idletasks()
        w = canvas.winfo_width()
        canvas.delete("all")
        fill_w = int(w * min(value / 100.0, 1.0))
        if fill_w > 0:
            canvas.create_rectangle(0, 0, fill_w, 14, fill=color, outline="")
        lbl.configure(text=f"{value:.0f}%")

    def _build_v_bar(self, parent, label, color):
        row = tk.Frame(parent, bg=CARD_BG)
        row.pack(fill=tk.X, padx=8, pady=2)
        tk.Label(row, text=label, font=FONT_SMALL, bg=CARD_BG,
                 fg=TEXT_DIM, width=12, anchor="w").pack(side=tk.LEFT)
        canvas = tk.Canvas(row, bg="#21262d", height=12,
                           highlightthickness=0, bd=0)
        canvas.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        lbl = tk.Label(row, text="0", font=FONT_SMALL, bg=CARD_BG,
                       fg=TEXT_MAIN, width=4)
        lbl.pack(side=tk.RIGHT)
        return {"canvas": canvas, "lbl": lbl, "color": color}

    def _update_v_bar(self, name, value: float):
        bar = self._comp_bars[name]
        canvas, lbl, color = bar["canvas"], bar["lbl"], bar["color"]
        canvas.update_idletasks()
        w = canvas.winfo_width()
        canvas.delete("all")
        fw = int(w * min(value / 100.0, 1.0))
        if fw > 0:
            canvas.create_rectangle(0, 0, fw, 12, fill=color, outline="")
        lbl.configure(text=f"{value:.0f}")

    def _tag(self, parent, text, color):
        lbl = tk.Label(parent, text=text, font=FONT_SMALL,
                       bg="#21262d", fg=TEXT_DIM, padx=6, pady=2,
                       relief=tk.FLAT, bd=0)
        lbl.pack(side=tk.LEFT, padx=2)
        return lbl

    def _set_tag(self, tag_lbl, active: bool, active_color: str):
        if active:
            tag_lbl.configure(bg=active_color, fg="white")
        else:
            tag_lbl.configure(bg="#21262d", fg=TEXT_DIM)

    def _kv(self, parent, key, val):
        row = tk.Frame(parent, bg=CARD_BG)
        row.pack(fill=tk.X, pady=1)
        tk.Label(row, text=key, font=FONT_SMALL, bg=CARD_BG,
                 fg=TEXT_DIM, width=12, anchor="w").pack(side=tk.LEFT)
        lbl = tk.Label(row, text=val, font=FONT_SMALL, bg=CARD_BG, fg=TEXT_MAIN)
        lbl.pack(side=tk.LEFT)
        return lbl

    # ================================================================== #
    #  GAUGE DRAWING
    # ================================================================== #
    def _draw_gauge(self, score: float, color: str):
        ax = self._gauge_ax
        ax.clear()
        ax.set_facecolor(CARD_BG)
        ax.set_aspect("equal")
        ax.axis("off")

        # Background arc
        theta = np.linspace(np.pi, 0, 100)
        ax.plot(np.cos(theta), np.sin(theta), color="#30363d", lw=14,
                solid_capstyle="round")

        # Value arc
        fraction = min(score / 100.0, 1.0)
        theta_v  = np.linspace(np.pi, np.pi - fraction * np.pi, 100)
        ax.plot(np.cos(theta_v), np.sin(theta_v), color=color, lw=14,
                solid_capstyle="round")

        # Zone tick marks
        for pct, label in [(0, "0"), (25, "25"), (50, "50"),
                           (75, "75"), (100, "100")]:
            angle = np.pi - (pct / 100) * np.pi
            x = np.cos(angle) * 1.18
            y = np.sin(angle) * 1.18
            ax.text(x, y, label, ha="center", va="center",
                    fontsize=6, color=TEXT_DIM,
                    fontfamily="Courier New")

        ax.set_xlim(-1.35, 1.35)
        ax.set_ylim(-0.2, 1.35)
        self._gauge_canvas.draw()

    # ================================================================== #
    #  CHART UPDATE
    # ================================================================== #
    def _update_chart(self):
        ax = self._chart_ax
        ax.clear()
        ax.set_facecolor(PANEL_BG)
        ax.tick_params(colors=TEXT_DIM, labelsize=7)
        ax.spines[:].set_color("#30363d")
        ax.set_ylim(0, 105)
        ax.set_xlabel("seconds ago", color=TEXT_DIM, fontsize=7)

        if len(self._time_axis) < 2:
            self._chart_canvas.draw()
            return

        times  = list(self._time_axis)
        scores = list(self._risk_history)
        # time axis = seconds since session start
        t_max  = times[-1]
        t_rel  = [t_max - t for t in times]   # seconds ago (reversed)

        # Gradient fill using step segments
        for i in range(len(scores) - 1):
            sc = scores[i]
            color = (
                SUCCESS if sc < 30 else
                WARNING if sc < 55 else
                DANGER  if sc < 75 else
                CRITICAL
            )
            ax.fill_between(
                [t_rel[i+1], t_rel[i]], [scores[i+1], sc], alpha=0.25, color=color
            )
            ax.plot([t_rel[i+1], t_rel[i]], [scores[i+1], sc],
                    color=color, linewidth=1.2)

        ax.invert_xaxis()
        # Legend patches
        patches = [
            mpatches.Patch(color=SUCCESS, label="Safe"),
            mpatches.Patch(color=WARNING, label="Moderate"),
            mpatches.Patch(color=DANGER,  label="High"),
            mpatches.Patch(color=CRITICAL,label="Critical"),
        ]
        ax.legend(handles=patches, fontsize=6, loc="upper left",
                  facecolor=PANEL_BG, edgecolor="#30363d",
                  labelcolor=TEXT_DIM)

        self._chart_canvas.draw()

    # ================================================================== #
    #  LOG
    # ================================================================== #
    def _add_log_entry(self, alert_events: list):
        for ev in alert_events:
            ts_str  = time.strftime("%H:%M:%S", time.localtime(ev.timestamp))
            icon    = {"drowsiness_mild":  "😴",
                       "drowsiness_severe":"😵",
                       "phone_detected":   "📱",
                       "stress_high":      "😤",
                       "risk_critical":    "🚨"}.get(ev.alert_type, "⚠️")
            entry   = f"[{ts_str}] {icon} {ev.message}\n"
            self._alert_log_items.append(entry)

            self._log_text.configure(state=tk.NORMAL)
            self._log_text.insert(tk.END, entry)
            self._log_text.see(tk.END)
            self._log_text.configure(state=tk.DISABLED)

        self._lbl_alert_count.configure(
            text=f"{len(self._alert_log_items)} alerts"
        )

    def _clear_log(self):
        self._alert_log_items.clear()
        self._log_text.configure(state=tk.NORMAL)
        self._log_text.delete("1.0", tk.END)
        self._log_text.configure(state=tk.DISABLED)
        self._lbl_alert_count.configure(text="0 alerts")

    # ================================================================== #
    #  POLL QUEUE (main Tkinter loop)
    # ================================================================== #
    def _poll(self):
        try:
            while True:
                data = self._q.get_nowait()
                self._update(data)
        except queue.Empty:
            pass
        self._root.after(33, self._poll)   # ~30 Hz

    # ================================================================== #
    #  UPDATE UI
    # ================================================================== #
    def _update(self, data: dict):
        frame_data    = data.get("frame")
        eye_state     = data.get("eye", {})
        phone_state   = data.get("phone", {})
        emotion_state = data.get("emotion", {})
        risk_state    = data.get("risk", {})
        fps           = data.get("fps", 0)
        alert_events  = data.get("alerts", [])

        # ── Video frame ───────────────────────────────────────────────
        if frame_data is not None:
            img = Image.fromarray(frame_data)
            img = img.resize((464, 348), Image.BILINEAR)
            photo = ImageTk.PhotoImage(img)
            self._video_label.configure(image=photo)
            self._video_label.image = photo

        # ── Status row ────────────────────────────────────────────────
        self._lbl_fps.configure(text=f"{fps:.0f}")
        face_ok = eye_state.get("face_detected", False)
        self._lbl_face.configure(
            text="✓" if face_ok else "✗",
            fg=SUCCESS if face_ok else DANGER,
        )
        self._lbl_ear.configure(text=f"{eye_state.get('ear', 0):.3f}")

        # ── H-Bars ────────────────────────────────────────────────────
        self._update_h_bar("drowsiness_bar",  eye_state.get("drowsiness_score", 0))
        self._update_h_bar("distraction_bar", phone_state.get("distraction_score", 0))
        self._update_h_bar("emotion_bar",     emotion_state.get("emotion_score", 0))

        # ── Detection tags ────────────────────────────────────────────
        self._set_tag(self._tag_drowsy, eye_state.get("is_drowsy", False),   DANGER)
        self._set_tag(self._tag_phone,  phone_state.get("phone_detected", False), "#ff6b00")
        self._set_tag(self._tag_stress, emotion_state.get("is_high_stress", False), "#b37feb")
        self._tag_emotion.configure(
            text=emotion_state.get("emotion_emoji", "❓")
        )

        # ── Risk score ───────────────────────────────────────────────
        score = risk_state.get("smooth_score", 0)
        level = risk_state.get("risk_level", "SAFE")
        color = RISK_HEX.get(level, SUCCESS)
        self._lbl_score.configure(text=f"{score:.0f}", fg=color)
        self._lbl_level.configure(text=level, fg=color)
        self._draw_gauge(score, color)

        # ── Comp bars ─────────────────────────────────────────────────
        comp = risk_state.get("component_scores", {})
        for name in ("drowsiness", "distraction", "emotion"):
            self._update_v_bar(name, comp.get(name, 0))

        # ── Stats ─────────────────────────────────────────────────────
        self._lbl_blink.configure(text=f"{eye_state.get('blink_rate', 0):.0f}/min")
        self._lbl_perclos.configure(text=f"{eye_state.get('perclos', 0):.1f}%")
        self._lbl_phone_conf.configure(text=f"{phone_state.get('confidence', 0):.0f}%")
        self._lbl_emotion.configure(text=emotion_state.get("emotion", "–"))

        elapsed = int(time.time() - self._start_time)
        m, s = divmod(elapsed, 60)
        self._lbl_session.configure(text=f"{m}:{s:02d}")
        self._lbl_time.configure(text=time.strftime("%H:%M:%S"))

        # ── Chart ─────────────────────────────────────────────────────
        self._risk_history.append(score)
        self._time_axis.append(time.time() - self._start_time)
        self._update_chart()

        # ── Alerts ───────────────────────────────────────────────────
        if alert_events:
            self._add_log_entry(alert_events)

    # ================================================================== #
    def run(self):
        self._root.mainloop()

    def stop(self):
        try:
            self._root.quit()
        except Exception:
            pass
