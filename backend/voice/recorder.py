"""
Voice recorder with energy-based VAD.
Pure numpy — no C compilation needed.

Stops recording after SILENCE_SEC seconds of silence.
Safety cap at MAX_SEC seconds total.
"""

import numpy as np
import sounddevice as sd

SAMPLE_RATE    = 16000
FRAME_MS       = 30
FRAME_SAMPLES  = int(SAMPLE_RATE * FRAME_MS / 1000)  # 480 samples
SILENCE_SEC    = 2.0
MAX_SEC        = 15
SILENCE_FRAMES = int(SILENCE_SEC * 1000 / FRAME_MS)  # ~40 frames

# RMS energy threshold (int16 units). Tune up if background noise triggers,
# down if your voice gets cut off early.
ENERGY_THRESHOLD = 200


def _rms(frame: np.ndarray) -> float:
    return float(np.sqrt(np.mean(frame.astype(np.float32) ** 2)))


def record_until_silence() -> np.ndarray:
    """
    Record from mic until silence is detected.
    Returns int16 numpy array at 16 kHz.
    """
    frames: list[np.ndarray] = []
    silent_count  = 0
    max_frames    = int(MAX_SEC * 1000 / FRAME_MS)
    speech_started = False

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16",
                        blocksize=FRAME_SAMPLES) as stream:
        for _ in range(max_frames):
            chunk, _ = stream.read(FRAME_SAMPLES)
            frame = chunk.flatten()
            frames.append(frame)

            if _rms(frame) > ENERGY_THRESHOLD:
                speech_started = True
                silent_count   = 0
            elif speech_started:
                silent_count += 1

            if speech_started and silent_count >= SILENCE_FRAMES:
                break

    return np.concatenate(frames) if frames else np.array([], dtype=np.int16)
