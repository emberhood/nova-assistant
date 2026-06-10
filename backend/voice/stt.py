"""Speech-to-text via Groq API (Whisper large-v3, free tier).

Sends audio to Groq cloud — no local AI model, no CPU heat.
Fallback to local Whisper base if GROQ_API_KEY is not set.
"""

import os
import tempfile
import numpy as np
from scipy.io import wavfile

# Domain hint — reduces hallucinations on app names / Greek commands
_PROMPT = (
    "Nova. Άνοιξε, κλείσε, γύρνα, πήγαινε, δείξε, σταμάτα, κλείδωσε. "
    "Spotify, Chrome, Firefox, Discord, Notepad, Visual Studio Code. "
    "Calendar, ημερολόγιο, budget, έξοδα, υπόλοιπο, dashboard, αρχική. "
    "Ανδριανά, εφαρμογή, application, tab. "
    "Αύξησε, μείωσε, σίγαση, ένταση. Τι ώρα είναι; Πόσα έχω;"
)

_groq_client = None
_local_model  = None


def _get_groq():
    global _groq_client
    if _groq_client is not None:
        return _groq_client
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        return None
    try:
        from groq import Groq
        _groq_client = Groq(api_key=key)
        print("[STT] Using Groq (Whisper large-v3)")
        return _groq_client
    except ImportError:
        print("[STT] groq package not installed — run: pip install groq")
        return None


def _get_local_model():
    global _local_model
    if _local_model is not None:
        return _local_model
    from faster_whisper import WhisperModel
    size = os.getenv("WHISPER_MODEL", "base")
    print(f"[STT] Loading local Whisper '{size}' (fallback)...")
    _local_model = WhisperModel(size, device="cpu", compute_type="int8")
    return _local_model


def _audio_to_wav_bytes(audio_np: np.ndarray, sample_rate: int) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp = f.name
    wavfile.write(tmp, sample_rate, audio_np)
    with open(tmp, "rb") as f:
        data = f.read()
    os.unlink(tmp)
    return data


def transcribe(audio_np: np.ndarray, sample_rate: int = 16000) -> str:
    """Transcribe numpy int16 audio → text string."""

    client = _get_groq()

    if client:
        # --- Groq cloud path ---
        try:
            wav_bytes = _audio_to_wav_bytes(audio_np, sample_rate)
            result = client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=("audio.wav", wav_bytes, "audio/wav"),
                language="el",
                prompt=_PROMPT,
            )
            text = result.text.strip()
            print(f"[STT/Groq] '{text}'")
            return text
        except Exception as e:
            print(f"[STT/Groq] Error: {e} — falling back to local Whisper")

    # --- Local Whisper fallback ---
    model = _get_local_model()
    audio_f32 = audio_np.astype(np.float32) / 32768.0
    segments, _ = model.transcribe(
        audio_f32,
        language="el",
        beam_size=5,
        vad_filter=True,
        initial_prompt=_PROMPT,
    )
    text = " ".join(s.text.strip() for s in segments).strip()
    print(f"[STT/local] '{text}'")
    return text


def preload():
    """Warm up at startup — only loads local model if no Groq key."""
    if not os.getenv("GROQ_API_KEY", "").strip():
        _get_local_model()
    else:
        _get_groq()
