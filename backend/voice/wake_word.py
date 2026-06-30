"""
Wake-word listener.

Priority order:
  1. Custom "Hey Nova" openWakeWord model  — backend/voice/wakewords/hey_nova.onnx
     Train it once with:  python3 voice/train_hey_nova.py
  2. Built-in "hey_jarvis" fallback        — works out of the box, say "Hey Jarvis"

To train "Hey Nova" (one-time, ~30 min):
    cd backend && source .venv/bin/activate
    python3 voice/train_hey_nova.py
"""

import os
import threading
import numpy as np
import sounddevice as sd

COOLDOWN_SEC    = 3.0
OWW_THRESHOLD   = 0.5   # lower = more sensitive; raise if too many false positives
OWW_SAMPLE_RATE = 16000
OWW_CHUNK       = 1280


def _hey_nova_model_path() -> str | None:
    """Return path to trained hey_nova.onnx if it exists."""
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "wakewords", "hey_nova.onnx")
    return path if os.path.exists(path) else None


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
        nova_path = _hey_nova_model_path()
        if nova_path:
            print(f"[WakeWord] Loading custom 'Hey Nova' model: {nova_path}")
            self._openwakeword_loop(model_path=nova_path, wake_phrase="hey_nova")
        else:
            print("[WakeWord] hey_nova.onnx not found — using 'Hey Jarvis' fallback.")
            print("[WakeWord] Train 'Hey Nova' with: python3 voice/train_hey_nova.py")
            self._openwakeword_loop(model_path=None, wake_phrase="hey_jarvis")

    # ── openWakeWord loop (Hey Nova or Hey Jarvis fallback) ──────────────────
    def _openwakeword_loop(self, model_path: str | None, wake_phrase: str):
        try:
            from openwakeword.model import Model
        except ImportError:
            print("[WakeWord] openwakeword not installed — wake word disabled.")
            return

        try:
            if model_path:
                model = Model(wakeword_models=[model_path], inference_framework="onnx")
            else:
                model = Model(wakeword_models=["hey_jarvis"], inference_framework="onnx")
        except Exception as e:
            print(f"[WakeWord] Model failed to load: {e}")
            return

        label = "Hey Nova" if wake_phrase == "hey_nova" else "Hey Jarvis"
        print(f"[WakeWord] Listening — say '{label}'.")

        with sd.InputStream(samplerate=OWW_SAMPLE_RATE, channels=1, dtype="int16",
                            blocksize=OWW_CHUNK) as stream:
            while self._running:
                pcm, _ = stream.read(OWW_CHUNK)
                scores = model.predict(pcm.flatten().astype(np.int16))
                score = scores.get(wake_phrase, 0.0)
                if score >= OWW_THRESHOLD:
                    if self._is_busy():
                        for _ in range(int(1.0 * OWW_SAMPLE_RATE / OWW_CHUNK)):
                            stream.read(OWW_CHUNK)
                        continue
                    print(f"[WakeWord] '{label}' detected! (score={score:.2f})")
                    self._on_detected()
                    for _ in range(int(COOLDOWN_SEC * OWW_SAMPLE_RATE / OWW_CHUNK)):
                        if not self._running:
                            break
                        stream.read(OWW_CHUNK)
