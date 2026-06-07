"""
Speaker verification — Jarvis responds only to the enrolled voice.

Workflow:
  1. First run: enroll by calling enroll_voice() or via POST /api/voice/enroll
  2. Every command: verify() is called automatically before routing
  3. If similarity < THRESHOLD, command is rejected

Profile saved to: jarvis/backend/voice_profile.npy
Threshold: 0.75 (tune up for stricter, down for more lenient)
"""

from __future__ import annotations

import os
import numpy as np

PROFILE_PATH = os.path.join(os.path.dirname(__file__), "..", "voice_profile.npy")
THRESHOLD = 0.75          # cosine similarity — 0.75 is a good starting point
ENROLL_SECONDS = 12       # how long to record during enrollment

_encoder = None


def _get_encoder():
    global _encoder
    if _encoder is not None:
        return _encoder
    try:
        from resemblyzer import VoiceEncoder
        _encoder = VoiceEncoder()
        return _encoder
    except ImportError:
        return None


def is_enrolled() -> bool:
    return os.path.exists(PROFILE_PATH)


def is_available() -> bool:
    """True if resemblyzer is installed."""
    return _get_encoder() is not None


def enroll_voice(audio_int16: np.ndarray, sample_rate: int = 16000) -> str:
    """
    Enroll the owner's voice from a numpy int16 audio array.
    Returns a status message.
    """
    enc = _get_encoder()
    if enc is None:
        return "resemblyzer not installed. Run: pip install resemblyzer"

    try:
        from resemblyzer import preprocess_wav
        audio_f32 = audio_int16.astype(np.float32) / 32768.0
        wav = preprocess_wav(audio_f32, source_sr=sample_rate)
        embedding = enc.embed_utterance(wav)
        np.save(PROFILE_PATH, embedding)
        return f"Voice enrolled. Profile saved. Say 'Hey Jarvis' to test."
    except Exception as e:
        return f"Enrollment failed: {e}"


def detect_gender(audio_int16: np.ndarray, sample_rate: int = 16000) -> str:
    """
    Estimate speaker gender from fundamental frequency (F0).
    Male voices: F0 typically 85–160 Hz → returns 'male'
    Female voices: F0 typically 160–255 Hz → returns 'female'
    Returns 'unknown' if pitch cannot be reliably estimated.
    """
    audio_f = audio_int16.astype(np.float32)
    frame_size = int(sample_rate * 0.03)      # 30ms frame
    hop = frame_size // 2
    min_lag = int(sample_rate / 270)           # 270 Hz upper bound
    max_lag = int(sample_rate / 75)            # 75 Hz lower bound
    GENDER_THRESHOLD = 165.0                   # Hz — below = male, above = female

    pitches = []
    for i in range(0, len(audio_f) - frame_size, hop):
        frame = audio_f[i : i + frame_size]
        rms = float(np.sqrt(np.mean(frame ** 2)))
        if rms < 300:          # skip silence / unvoiced
            continue
        # Autocorrelation pitch detection
        corr = np.correlate(frame, frame, mode="full")
        corr = corr[len(corr) // 2 :]
        if max_lag >= len(corr):
            continue
        segment = corr[min_lag : max_lag]
        peak_idx = int(np.argmax(segment)) + min_lag
        # Require peak to be meaningfully above the baseline
        if corr[0] > 0 and corr[peak_idx] / corr[0] > 0.25:
            pitches.append(sample_rate / peak_idx)

    if len(pitches) < 5:           # not enough voiced frames to decide
        return "unknown"

    median_f0 = float(np.median(pitches))
    print(f"[SpeakerVerify] Median F0={median_f0:.1f} Hz → {'female' if median_f0 >= GENDER_THRESHOLD else 'male'}")
    return "female" if median_f0 >= GENDER_THRESHOLD else "male"


def verify(audio_int16: np.ndarray, sample_rate: int = 16000) -> tuple[bool, float]:
    """
    Compare audio against the enrolled profile.
    Returns (is_owner, similarity_score).
    If not enrolled or resemblyzer not available, always returns (True, 1.0)
    so Jarvis keeps working without verification.
    """
    enc = _get_encoder()
    if enc is None or not is_enrolled():
        return True, 1.0

    try:
        from resemblyzer import preprocess_wav
        audio_f32 = audio_int16.astype(np.float32) / 32768.0
        wav = preprocess_wav(audio_f32, source_sr=sample_rate)
        embedding = enc.embed_utterance(wav)

        profile = np.load(PROFILE_PATH)
        similarity = float(np.dot(embedding, profile) / (np.linalg.norm(embedding) * np.linalg.norm(profile)))
        print(f"[SpeakerVerify] Similarity: {similarity:.3f} (threshold: {THRESHOLD})")
        return similarity >= THRESHOLD, similarity
    except Exception as e:
        print(f"[SpeakerVerify] Error: {e} — allowing command")
        return True, 0.0
