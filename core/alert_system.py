import time
import queue
import threading
import collections
import os
import config

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

try:
    from twilio.rest import Client
    TWILIO_OK = True
except:
    TWILIO_OK = False


AlertEvent = collections.namedtuple(
    "AlertEvent", ["timestamp", "alert_type", "message", "risk_level"]
)


class AlertSystem:
    def __init__(self):
        self._cooldowns = {}
        self._log = []
        self._tts_queue = queue.Queue(maxsize=5)

        self.engine = None
        self.twilio_client = None

        print("🔊 TTS Enabled:", config.ENABLE_TTS and TTS_OK)
        print("📱 SMS Enabled:", config.ENABLE_SMS and TWILIO_OK and config.TWILIO_ACCOUNT_SID)

        if config.ENABLE_TTS and TTS_OK:
            try:
                self.engine = pyttsx3.init()
                self.engine.setProperty("rate", 165)

                threading.Thread(target=self._tts_worker, daemon=True).start()
            except Exception as e:
                print("[TTS INIT ERROR]", e)

        if config.ENABLE_SMS and TWILIO_OK and config.TWILIO_ACCOUNT_SID:
            try:
                self.twilio_client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
            except Exception as e:
                print("[SMS INIT ERROR]", e)

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

        # For SMS, send every time without cooldown
        send_sms = config.ENABLE_SMS and self.twilio_client and config.ALERT_TO_NUMBERS

        if send_sms:
            msg = config.ALERT_MESSAGES.get(alert_type, "Alert!")
            threading.Thread(target=self._send_sms, args=(msg,), daemon=True).start()
            print(f"[ALERT] {msg} (SMS sent)")

        # Apply cooldown only for non-SMS alerts
        if not send_sms and now - last < config.ALERT_COOLDOWN_SEC:
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

    def _send_sms(self, message):
        for number in config.ALERT_TO_NUMBERS:
            if number.strip():
                try:
                    self.twilio_client.messages.create(
                        body=message,
                        from_=config.TWILIO_FROM_NUMBER,
                        to=number.strip()
                    )
                    print(f"[SMS] Sent to {number}: {message}")
                except Exception as e:
                    print(f"[SMS ERROR] Failed to send to {number}: {e}")

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