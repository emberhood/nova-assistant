"""
Wake-word listener.

Primary:  Picovoice Porcupine with a custom "Arthur" keyword (.ppn).
Fallback: openWakeWord built-in "hey_jarvis" (used until the Porcupine
          key + keyword file are configured, so the app never breaks).

Setup for Porcupine (one-time):
  1. Create a free account at https://console.picovoice.ai
  2. Copy your AccessKey → add to .env:   PICOVOICE_ACCESS_KEY=xxxxxxxx
  3. In the console: "Porcupine" → create wake word "Arthur" (or "Hey Arthur")
     → pick your platform (Windows now / Linux for the final box) → download the .ppn
  4. Drop the file in:  backend/voice/wakewords/arthur_<platform>.ppn
     (or set WAKEWORD_PPN_PATH in .env to its absolute path)

NOTE: Porcupine .ppn keyword files are PLATFORM-SPECIFIC. Generate a Windows
file for testing now and a Linux file for the migrated machine.
"""

import os
import sys
import threading
import numpy as np
import sounddevice as sd

# Tunables
PORCUPINE_SENSITIVITY = float(os.environ.get("WAKEWORD_SENSITIVITY", "0.6"))  # 0–1
COOLDOWN_SEC = 3.0
OWW_THRESHOLD = 0.7          # fallback path only
OWW_SAMPLE_RATE = 16000
OWW_CHUNK = 1280


def _default_ppn_path() -> str | None:
    """Look for a platform-appropriate Arthur keyword file."""
    explicit = os.environ.get("WAKEWORD_PPN_PATH", "").strip()
    if explicit and os.path.exists(explicit):
        return explicit

    here = os.path.dirname(os.path.abspath(__file__))
    plat = "windows" if sys.platform == "win32" else ("linux" if sys.platform.startswith("linux") else "mac")
    candidates = [
        os.path.join(here, "wakewords", f"arthur_{plat}.ppn"),
        os.path.join(here, "wakewords", "arthur.ppn"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


class WakeWordListener:
    def __init__(self, on_detected: callable, is_busy: callable = None):
        self._on_detected = on_detected
        self._is_busy = is_busy or (lambda: False)
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    # ── Loop dispatcher ──────────────────────────────────────────────────────
    def _listen_loop(self):
        access_key = os.environ.get("PICOVOICE_ACCESS_KEY", "").strip()
        ppn_path = _default_ppn_path()

        if access_key and ppn_path:
            try:
                self._porcupine_loop(access_key, ppn_path)
                return
            except Exception as e:
                print(f"[WakeWord] Porcupine failed ({e}) — falling back to hey_jarvis.")
        else:
            missing = []
            if not access_key:
                missing.append("PICOVOICE_ACCESS_KEY")
            if not ppn_path:
                missing.append("Arthur .ppn file")
            print(f"[WakeWord] Porcupine not configured (missing: {', '.join(missing)}) — using hey_jarvis fallback.")

        self._openwakeword_loop()

    # ── Primary: Porcupine "Arthur" ──────────────────────────────────────────
    def _porcupine_loop(self, access_key: str, ppn_path: str):
        import pvporcupine

        porcupine = pvporcupine.create(
            access_key=access_key,
            keyword_paths=[ppn_path],
            sensitivities=[PORCUPINE_SENSITIVITY],
        )
        frame_len = porcupine.frame_length          # 512
        sample_rate = porcupine.sample_rate          # 16000
        print(f"[WakeWord] Porcupine loaded — say 'Arthur'. ({os.path.basename(ppn_path)})")

        try:
            with sd.InputStream(samplerate=sample_rate, channels=1, dtype="int16",
                                blocksize=frame_len) as stream:
                while self._running:
                    pcm, _ = stream.read(frame_len)
                    frame = pcm.flatten().astype(np.int16)
                    result = porcupine.process(frame)
                    if result >= 0:
                        if self._is_busy():
                            self._drain(stream, frame_len, sample_rate, 1.0)
                            continue
                        print("[WakeWord] 'Arthur' detected!")
                        self._on_detected()
                        self._drain(stream, frame_len, sample_rate, COOLDOWN_SEC)
        finally:
            porcupine.delete()

    @staticmethod
    def _drain(stream, frame_len, sample_rate, seconds):
        for _ in range(int(seconds * sample_rate / frame_len)):
            stream.read(frame_len)

    # ── Fallback: openWakeWord "hey_jarvis" ──────────────────────────────────
    def _openwakeword_loop(self):
        try:
            from openwakeword.model import Model
        except ImportError:
            print("[WakeWord] openwakeword not installed — wake word disabled.")
            return
        try:
            model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
        except Exception as e:
            print(f"[WakeWord] Fallback model failed to load: {e}")
            return

        print("[WakeWord] Fallback active — say 'Hey Jarvis'.")
        with sd.InputStream(samplerate=OWW_SAMPLE_RATE, channels=1, dtype="int16",
                            blocksize=OWW_CHUNK) as stream:
            while self._running:
                pcm, _ = stream.read(OWW_CHUNK)
                score = model.predict(pcm.flatten().astype(np.int16)).get("hey_jarvis", 0.0)
                if score >= OWW_THRESHOLD:
                    if self._is_busy():
                        for _ in range(int(1.0 * OWW_SAMPLE_RATE / OWW_CHUNK)):
                            stream.read(OWW_CHUNK)
                        continue
                    print(f"[WakeWord] 'Hey Jarvis' detected! (score={score:.2f})")
                    self._on_detected()
                    for _ in range(int(COOLDOWN_SEC * OWW_SAMPLE_RATE / OWW_CHUNK)):
                        if not self._running:
                            break
                        stream.read(OWW_CHUNK)
