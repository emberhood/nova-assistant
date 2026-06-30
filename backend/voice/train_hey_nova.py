#!/usr/bin/env python3
"""
Train a custom "Hey Nova" wake word model using openWakeWord.

How it works:
1. Generates ~500 synthetic "hey nova" audio clips via edge-tts (many voices/rates)
2. Generates ~500 negative clips (other phrases) so the model learns what NOT to trigger on
3. Extracts audio embeddings using openWakeWord's pre-trained feature extractor
4. Trains a small DNN classifier with auto_train()
5. Exports to hey_nova.onnx → drop-in replacement in the wake word pipeline

Run from nova-assistant root:
    cd backend && source .venv/bin/activate
    python3 voice/train_hey_nova.py

Output: backend/voice/wakewords/hey_nova.onnx  (~50 KB)
Total time: ~20-40 minutes on CPU
"""

import logging
import os
import random
import sys
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

WAKEWORD_PHRASE    = "hey nova"
N_POSITIVE         = 300   # synthetic "hey nova" clips
N_NEGATIVE         = 300   # synthetic "other phrase" clips
TRAIN_STEPS        = 10000 # reduce to 5000 for a quick test
SAMPLE_RATE        = 16000
CLIP_DURATION_S    = 4.0   # seconds per clip — needs ≥16 embedding frames
OUTPUT_DIR         = Path(__file__).parent / "wakewords"
OUTPUT_MODEL       = OUTPUT_DIR / "hey_nova.onnx"

# espeak-ng voice variants for variety (offline, no rate limits)
ESPEAK_VOICES = [
    "en-us", "en-gb", "en-au", "en-sc", "en-029",
    "en-us+m1", "en-us+m2", "en-us+m3",
    "en-us+f1", "en-us+f2", "en-us+f3",
    "en-gb+m1", "en-gb+f1",
]
ESPEAK_SPEEDS  = [120, 140, 160, 180, 200]   # words per minute (default 175)
ESPEAK_PITCHES = [30, 45, 55, 65, 75]         # pitch 0-99 (default 50)

# Negative phrases — things that sound vaguely similar but shouldn't trigger
NEGATIVE_PHRASES = [
    "hey there", "okay google", "hello", "hey siri", "hey alexa",
    "hey cortana", "good morning", "good evening", "excuse me",
    "what time is it", "open calendar", "play music", "stop music",
    "hey you", "nova", "hey", "hey no", "novak", "bova", "heyno",
    "the weather today", "set a timer", "remind me later",
    "turn on the lights", "what's the news", "call mom",
    "send a message", "navigate home", "hey robot", "okay now",
    "grey nova", "hey local", "he nova", "hay nova",
]


# ── Audio helpers ─────────────────────────────────────────────────────────────

def mp3_bytes_to_pcm(audio_bytes: bytes, target_sr: int = SAMPLE_RATE) -> np.ndarray:
    """Decode audio bytes (WAV/MP3) → numpy int16 array at target_sr."""
    import miniaudio
    decoded = miniaudio.decode(audio_bytes, nchannels=1, sample_rate=target_sr)
    return np.frombuffer(decoded.samples, dtype=np.int16)


def pad_or_trim(audio: np.ndarray, length: int, tile: bool = False) -> np.ndarray:
    """Pad/tile or trim to exactly `length` samples."""
    if len(audio) >= length:
        return audio[:length]
    if tile and len(audio) > 0:
        repeats = (length // len(audio)) + 1
        audio = np.tile(audio, repeats)
        return audio[:length]
    return np.pad(audio, (0, length - len(audio)))


def add_noise(audio: np.ndarray, snr_db: float = 20.0) -> np.ndarray:
    """Add Gaussian noise at given SNR."""
    signal_power = np.mean(audio.astype(np.float32) ** 2)
    noise_power  = signal_power / (10 ** (snr_db / 10))
    noise        = np.random.normal(0, np.sqrt(noise_power), audio.shape).astype(np.int16)
    noisy        = np.clip(audio.astype(np.int32) + noise.astype(np.int32), -32768, 32767)
    return noisy.astype(np.int16)


# ── TTS generation (espeak-ng — offline, no rate limits) ─────────────────────

def _espeak_clip(text: str, voice: str, speed: int, pitch: int) -> bytes:
    """Return WAV bytes via espeak-ng subprocess."""
    import subprocess
    import tempfile
    import os
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        out_path = f.name
    try:
        subprocess.run(
            ["espeak-ng", "-v", voice, "-s", str(speed), "-p", str(pitch),
             "-w", out_path, text],
            check=True, capture_output=True,
        )
        with open(out_path, "rb") as f:
            return f.read()
    finally:
        os.unlink(out_path)


def generate_clips(phrases: list[str], n: int, label: str) -> list[np.ndarray]:
    """Generate n audio clips with varied voices/speeds/pitches via espeak-ng."""
    target_len = int(CLIP_DURATION_S * SAMPLE_RATE)
    clips: list[np.ndarray] = []

    log.info(f"Generating {n} {label} clips via espeak-ng...")
    for i in range(n):
        phrase = random.choice(phrases)
        voice  = random.choice(ESPEAK_VOICES)
        speed  = random.choice(ESPEAK_SPEEDS)
        pitch  = random.choice(ESPEAK_PITCHES)

        try:
            wav_bytes = _espeak_clip(phrase, voice, speed, pitch)
            pcm = mp3_bytes_to_pcm(wav_bytes)
            is_positive = (len(phrases) == 1)
            pcm = pad_or_trim(pcm, target_len, tile=is_positive)
            if random.random() < 0.5:
                snr = random.uniform(15, 40)
                pcm = add_noise(pcm, snr_db=snr)
            clips.append(pcm)
        except Exception as e:
            log.warning(f"espeak error ({phrase!r}, {voice}): {e} — skipping")

        if (i + 1) % 20 == 0:
            log.info(f"  {i+1}/{n} {label} clips done ({len(clips)} valid)")

    log.info(f"Generated {len(clips)} valid {label} clips")
    return clips


# ── Feature extraction ────────────────────────────────────────────────────────

def extract_embeddings(clips: list[np.ndarray]) -> np.ndarray:
    """
    Run all clips through openWakeWord's pre-trained audio embedding model.
    Returns array of shape (N, frames, 96).
    """
    from openwakeword.utils import AudioFeatures

    log.info(f"Extracting embeddings for {len(clips)} clips...")
    af = AudioFeatures(device="cpu")

    # embed_clips expects (N, samples) int16
    arr = np.stack(clips).astype(np.int16)
    embeddings = af.embed_clips(arr)   # (N, frames, 96)
    log.info(f"  Embedding shape: {embeddings.shape}")
    return embeddings


def embeddings_to_windows(embeddings: np.ndarray, window: int = 16) -> np.ndarray:
    """
    Slice each (frames, 96) embedding into overlapping (window, 96) windows.
    The model input_shape is (16, 96).
    """
    N, F, D = embeddings.shape
    windows = []
    for i in range(N):
        for start in range(0, F - window + 1, 1):
            windows.append(embeddings[i, start:start+window, :])
    return np.array(windows, dtype=np.float32)  # (M, 16, 96)


def make_dataloader(pos_emb: np.ndarray, neg_emb: np.ndarray,
                    batch_size: int = 64, infinite: bool = True):
    X = np.concatenate([pos_emb, neg_emb], axis=0)
    y = np.concatenate([
        np.ones(len(pos_emb), dtype=np.float32),
        np.zeros(len(neg_emb), dtype=np.float32),
    ])
    idx = np.random.permutation(len(X))
    X, y = X[idx], y[idx]
    ds = TensorDataset(torch.tensor(X), torch.tensor(y))
    dl = DataLoader(ds, batch_size=batch_size, shuffle=True)

    if not infinite:
        return dl

    # auto_train iterates until steps exhausted — train/val must cycle infinitely
    def _infinite():
        while True:
            yield from dl

    return _infinite()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── 1. Generate audio ──────────────────────────────────────────────────────
    pos_clips = generate_clips(phrases=[WAKEWORD_PHRASE], n=N_POSITIVE, label="positive")
    neg_clips = generate_clips(phrases=NEGATIVE_PHRASES, n=N_NEGATIVE, label="negative")

    if len(pos_clips) < 50:
        log.error("Not enough positive clips generated.")
        sys.exit(1)

    # ── 2. Extract embeddings ──────────────────────────────────────────────────
    pos_emb = extract_embeddings(pos_clips)
    neg_emb = extract_embeddings(neg_clips)

    pos_windows = embeddings_to_windows(pos_emb)
    neg_windows = embeddings_to_windows(neg_emb)
    log.info(f"Windows — positive: {len(pos_windows)}, negative: {len(neg_windows)}")

    # Split 80/20 for train/val
    def split(arr, ratio=0.8):
        n = int(len(arr) * ratio)
        return arr[:n], arr[n:]

    pos_train, pos_val = split(pos_windows)
    neg_train, neg_val = split(neg_windows)

    # Training loader cycles infinitely (auto_train iterates until steps exhausted)
    train_dl  = make_dataloader(pos_train, neg_train, infinite=True)
    # Validation loaders must be finite — auto_train iterates them to exhaustion each checkpoint
    val_dl    = make_dataloader(pos_val, neg_val, infinite=False)
    fp_val_dl = make_dataloader(np.zeros((10, 16, 96), dtype=np.float32), neg_val, infinite=False)

    # ── 3. Train ───────────────────────────────────────────────────────────────
    from openwakeword.train import Model as OWWTrainModel

    log.info(f"Training for {TRAIN_STEPS} steps...")
    model = OWWTrainModel(n_classes=1, input_shape=(16, 96), model_type="dnn", layer_dim=128)
    model.auto_train(
        X_train=train_dl,
        X_val=val_dl,
        false_positive_val_data=fp_val_dl,
        steps=TRAIN_STEPS,
    )

    # ── 4. Export ──────────────────────────────────────────────────────────────
    model.export_to_onnx(str(OUTPUT_MODEL), class_mapping="hey_nova")
    log.info(f"\n✓ Model saved to {OUTPUT_MODEL}")
    log.info("Next: restart the backend — it will load hey_nova.onnx automatically.")


if __name__ == "__main__":
    main()
