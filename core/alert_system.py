import time
import queue
import threading
import collections
import os
import config
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

try:
    import pygame
    pygame.mixer.init()
    PYGAME_OK = True
except:
    PYGAME_OK = False

try:
    import pyttsx3
    TTS_OK = True
except:
    TTS_OK = False

EMAIL_OK = True  # smtplib is built-in


AlertEvent = collections.namedtuple(
    "AlertEvent", ["timestamp", "alert_type", "message", "risk_level"]
)


class AlertSystem:
    def __init__(self):
        self._cooldowns = {}
        self._log = []
        self._tts_queue = queue.Queue(maxsize=5)

        self.engine = None
        self.email_configured = False

        print("🔊 TTS Enabled:", config.ENABLE_TTS and TTS_OK)
        print("📧 Email Alerts Enabled:", config.ENABLE_EMAIL and EMAIL_OK and config.EMAIL_SENDER)

        if config.ENABLE_TTS and TTS_OK:
            try:
                self.engine = pyttsx3.init()
                self.engine.setProperty("rate", 165)

                threading.Thread(target=self._tts_worker, daemon=True).start()
            except Exception as e:
                print("[TTS INIT ERROR]", e)

        if config.ENABLE_EMAIL and EMAIL_OK and config.EMAIL_SENDER and config.EMAIL_PASSWORD:
            try:
                self.email_configured = True
            except Exception as e:
                print("[EMAIL INIT ERROR]", e)

        self._alert_sound = None
        if config.ENABLE_SOUND and PYGAME_OK:
            self._alert_sound = self._make_beep()

    def evaluate(self, eye, phone, emo, risk):
        fired = []

        if eye["is_drowsy"]:
            fired += self._fire("drowsiness_mild", risk["risk_level"])

        if phone["phone_detected"]:
            print(f"[DEBUG] Phone detected: {phone}")  # Debug print
            fired += self._fire("phone_detected", risk["risk_level"])

        if risk["risk_level"] == "CRITICAL":
            fired += self._fire("risk_critical", risk["risk_level"])

        return fired

    def _fire(self, alert_type, risk_level):
        now = time.time()
        last = self._cooldowns.get(alert_type, 0)

        # For email, send every time without cooldown
        send_email = config.ENABLE_EMAIL and self.email_configured and config.ALERT_TO_EMAILS

        if send_email:
            msg = config.ALERT_MESSAGES.get(alert_type, "Alert!")
            threading.Thread(target=self._send_email, args=(alert_type, msg), daemon=True).start()
            print(f"[ALERT] {msg} (Email sent)")

        # Apply cooldown only for non-email alerts
        if not send_email and now - last < config.ALERT_COOLDOWN_SEC:
            return []

        self._cooldowns[alert_type] = now

        msg = config.ALERT_MESSAGES.get(alert_type, "Alert!")

        if self._alert_sound:
            self._alert_sound.play()

        if config.ENABLE_TTS and TTS_OK:
            if not self._tts_queue.full():
                self._tts_queue.put_nowait(msg)

        print(f"[ALERT] {msg}")
        return [msg]

    def _send_email(self, alert_type, message):
        """Send alert via email"""
        for email in config.ALERT_TO_EMAILS:
            email = email.strip()
            if email:
                try:
                    # Create email message
                    msg = MIMEMultipart()
                    msg["From"] = config.EMAIL_SENDER
                    msg["To"] = email
                    msg["Subject"] = f"[Driver Safety Alert] {alert_type.upper()}"
                    
                    body = f"""Driver Safety System Alert
                    
Alert Type: {alert_type}
Message: {message}
Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}

Please take immediate action if necessary.
"""
                    msg.attach(MIMEText(body, "plain"))
                    
                    # Send email via SMTP
                    with smtplib.SMTP(config.EMAIL_SMTP_SERVER, config.EMAIL_SMTP_PORT) as server:
                        server.starttls()  # Secure the connection
                        server.login(config.EMAIL_SENDER, config.EMAIL_PASSWORD)
                        server.send_message(msg)
                    
                    print(f"[EMAIL] Sent to {email}: {message}")
                except Exception as e:
                    print(f"[EMAIL ERROR] Failed to send to {email}: {e}")

    def _tts_worker(self):
        while True:
            msg = self._tts_queue.get()
            if self.engine:
                self.engine.stop()
                self.engine.say(msg)
                self.engine.runAndWait()

    def _make_beep(self):
        try:
            import numpy as np
            t = np.linspace(0, 0.3, 44100)
            wave = (np.sin(2*np.pi*440*t)*32767).astype("int16")
            stereo = np.column_stack([wave, wave])
            return pygame.sndarray.make_sound(stereo)
        except:
            return None