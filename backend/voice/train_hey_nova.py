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

import asyncio
import logging
import os
import random
import sys
import tempfile
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

WAKEWORD_PHRASE    = "hey nova"
N_POSITIVE         = 500   # synthetic "hey nova" clips
N_NEGATIVE         = 500   # synthetic "other phrase" clips
TRAIN_STEPS        = 10000 # reduce to 5000 for a quick test
SAMPLE_RATE        = 16000
CLIP_DURATION_S    = 1.5   # seconds per clip — long enough to say "hey nova"
OUTPUT_DIR         = Path(__file__).parent / "wakewords"
OUTPUT_MODEL       = OUTPUT_DIR / "hey_nova.onnx"

# English TTS voices — variety improves robustness
POSITIVE_VOICES = [
    "en-US-ChristopherNeural",
    "en-US-EricNeural",
    "en-US-GuyNeural",
    "en-US-JennyNeural",
    "en-US-AriaNeural",
    "en-GB-RyanNeural",
    "en-GB-SoniaNeural",
    "en-AU-WilliamNeural",
    "en-CA-LiamNeural",
    "en-IE-ConnorNeural",
]

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

NEGATIVE_VOICES = [
    "en-US-ChristopherNeural",
    "en-US-JennyNeural",
    "en-GB-RyanNeural",
    "en-AU-WilliamNeural",
]

# Speech rates for variation (normal is +0%)
RATES = ["-15%", "-5%", "+0%", "+5%", "+15%", "+25%"]


# ── Audio helpers ─────────────────────────────────────────────────────────────

def mp3_bytes_to_pcm(mp3_bytes: bytes, target_sr: int = SAMPLE_RATE) -> np.ndarray:
    """Decode mp3 bytes → numpy int16 array at target_sr."""
    import miniaudio
    decoded = miniaudio.decode(mp3_bytes, nchannels=1, sample_rate=target_sr)
    return np.frombuffer(decoded.samples, dtype=np.int16)


def pad_or_trim(audio: np.ndarray, length: int) -> np.ndarray:
    """Pad with zeros or trim to exactly `length` samples."""
    if len(audio) >= length:
        return audio[:length]
    return np.pad(audio, (0, length - len(audio)))


def add_noise(audio: np.ndarray, snr_db: float = 20.0) -> np.ndarray:
    """Add Gaussian noise at given SNR."""
    signal_power = np.mean(audio.astype(np.float32) ** 2)
    noise_power  = signal_power / (10 ** (snr_db / 10))
    noise        = np.random.normal(0, np.sqrt(noise_power), audio.shape).astype(np.int16)
    noisy        = np.clip(audio.astype(np.int32) + noise.astype(np.int32), -32768, 32767)
    return noisy.astype(np.int16)


# ── TTS generation ────────────────────────────────────────────────────────────

async def _tts_clip(text: str, voice: str, rate: str) -> bytes:
    """Return raw mp3 bytes from edge-tts."""
    import edge_tts
    mp3_chunks = []
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            mp3_chunks.append(chunk["data"])
    return b"".join(mp3_chunks)


async def generate_clips(phrases: list[str], voices: list[str], n: int,
                          label: str) -> list[np.ndarray]:
    """Generate n audio clips by cycling through phrases/voices/rates."""
    target_len = int(CLIP_DURATION_S * SAMPLE_RATE)
    clips: list[np.ndarray] = []

    log.info(f"Generating {n} {label} clips via edge-tts...")
    tasks_meta = [
        (random.choice(phrases), random.choice(voices), random.choice(RATES))
        for _ in range(n)
    ]

    # Generate in small concurrent batches to avoid rate-limiting
    BATCH = 20
    for i in range(0, n, BATCH):
        batch = tasks_meta[i:i+BATCH]
        tasks = [_tts_clip(p, v, r) for p, v, r in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for j, (mp3_or_exc, (phrase, voice, rate)) in enumerate(zip(results, batch)):
            if isinstance(mp3_or_exc, Exception):
                log.warning(f"TTS error ({phrase!r}, {voice}, {rate}): {mp3_or_exc} — skipping")
                continue
            try:
                pcm = mp3_bytes_to_pcm(mp3_or_exc)
                pcm = pad_or_trim(pcm, target_len)
                # Augment: add light noise to ~half the clips
                if random.random() < 0.5:
                    snr = random.uniform(15, 40)
                    pcm = add_noise(pcm, snr_db=snr)
                clips.append(pcm)
            except Exception as e:
                log.warning(f"Decode error: {e} — skipping")

        done = min(i + BATCH, n)
        log.info(f"  {done}/{n} {label} clips done")

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

    # embed_clips expects (N, samples) float32 normalised to [-1, 1]
    arr = np.stack(clips).astype(np.float32) / 32768.0
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
                    batch_size: int = 64) -> DataLoader:
    X = np.concatenate([pos_emb, neg_emb], axis=0)
    y = np.concatenate([
        np.ones(len(pos_emb), dtype=np.float32),
        np.zeros(len(neg_emb), dtype=np.float32),
    ])
    idx = np.random.permutation(len(X))
    X, y = X[idx], y[idx]
    ds = TensorDataset(torch.tensor(X), torch.tensor(y))
    return DataLoader(ds, batch_size=batch_size, shuffle=True)


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── 1. Generate audio ──────────────────────────────────────────────────────
    pos_clips = await generate_clips(
        phrases=[WAKEWORD_PHRASE],
        voices=POSITIVE_VOICES,
        n=N_POSITIVE,
        label="positive",
    )
    neg_clips = await generate_clips(
        phrases=NEGATIVE_PHRASES,
        voices=NEGATIVE_VOICES,
        n=N_NEGATIVE,
        label="negative",
    )

    if len(pos_clips) < 50:
        log.error("Not enough positive clips generated. Check edge-tts connectivity.")
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

    train_dl = make_dataloader(pos_train, neg_train)
    val_dl   = make_dataloader(pos_val, neg_val)
    # false_positive_val_data: DataLoader of purely negative samples (for FP/hr metric)
    fp_val_dl = make_dataloader(np.zeros((10, 16, 96), dtype=np.float32), neg_val)

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
    asyncio.run(main())
