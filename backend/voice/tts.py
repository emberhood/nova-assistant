"""
TTS — edge-tts primary, gTTS fallback.
Playback: miniaudio (mp3→WAV) + winsound on Windows, aplay on Linux.
No ffmpeg, no pygame, no sounddevice conflicts.
"""

import asyncio
import os
import sys
import subprocess
import tempfile
import threading
import wave

VOICE = os.environ.get("TTS_VOICE", "el-GR-NestorasNeural")
_VOICE_FALLBACKS = [VOICE, "el-GR-AthinaNeural"]

_IS_WIN   = sys.platform == "win32"
_IS_LINUX = sys.platform.startswith("linux")


def _play_wav(wav_path: str) -> bool:
    """Play a WAV file — winsound on Windows, aplay on Linux."""
    try:
        if _IS_WIN:
            import winsound
            winsound.PlaySound(wav_path, winsound.SND_FILENAME)
            return True
        else:
            result = subprocess.run(["aplay", "-q", wav_path], timeout=30)
            return result.returncode == 0
    except Exception as e:
        print(f"[TTS] playback error: {e}")
        return False


def _mp3_to_wav(mp3_path: str) -> str | None:
    """Decode mp3 → temp WAV file using miniaudio. Returns WAV path or None."""
    try:
        import miniaudio
        decoded = miniaudio.decode_file(
            mp3_path,
            output_format=miniaudio.SampleFormat.SIGNED16,
            nchannels=1,
        )
        wav_path = mp3_path.replace(".mp3", ".wav")
        with wave.open(wav_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(decoded.sample_rate)
            wf.writeframes(decoded.samples)
        print(f"[TTS] decoded {len(decoded.samples)//2} samples @ {decoded.sample_rate}Hz")
        return wav_path
    except ImportError:
        print("[TTS] miniaudio not installed — run: pip install miniaudio")
        return None
    except Exception as e:
        print(f"[TTS] mp3→wav decode error: {e}")
        return None


def _play_mp3(mp3_path: str) -> bool:
    wav_path = _mp3_to_wav(mp3_path)
    if not wav_path:
        return False
    ok = _play_wav(wav_path)
    try:
        os.unlink(wav_path)
    except Exception:
        pass
    return ok


async def _edge_synthesize(text: str, voice: str) -> bytes:
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    chunks = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            chunks.append(chunk["data"])
    return b"".join(chunks)


def _speak_edge(text: str) -> bool:
    for voice in _VOICE_FALLBACKS:
        try:
            print(f"[TTS] edge-tts {voice}...")
            mp3_bytes = asyncio.run(_edge_synthesize(text, voice))
            if not mp3_bytes:
                print(f"[TTS] {voice}: empty response")
                continue
            print(f"[TTS] got {len(mp3_bytes)} bytes")
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                f.write(mp3_bytes)
                tmp = f.name
            ok = _play_mp3(tmp)
            try:
                os.unlink(tmp)
            except Exception:
                pass
            if ok:
                return True
        except Exception as e:
            print(f"[TTS] edge-tts {voice} failed: {e}")
    return False


def _speak_gtts(text: str) -> bool:
    try:
        print("[TTS] gTTS fallback...")
        from gtts import gTTS
        tts = gTTS(text=text, lang="el", slow=False)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tmp = f.name
        tts.save(tmp)
        ok = _play_mp3(tmp)
        try:
            os.unlink(tmp)
        except Exception:
            pass
        return ok
    except Exception as e:
        print(f"[TTS] gTTS error: {e}")
        return False


def _speak_pyttsx3(text: str) -> bool:
    print("[TTS] pyttsx3 subprocess fallback...")
    script = f"import pyttsx3; e=pyttsx3.init(); e.say({repr(text)}); e.runAndWait()"
    try:
        subprocess.run([sys.executable, "-c", script], timeout=8, capture_output=True)
        return True
    except Exception as e:
        print(f"[TTS] pyttsx3 error: {e}")
        return False


def speak(text: str, on_start=None, on_done=None):
    def _run():
        try:
            print(f"[TTS] speaking: '{text[:80]}'")
            if on_start:
                on_start()
            if _speak_edge(text):
                return
            print("[TTS] edge-tts failed → gTTS")
            if _speak_gtts(text):
                return
            print("[TTS] gTTS failed → pyttsx3")
            _speak_pyttsx3(text)
        except Exception as e:
            print(f"[TTS] unhandled: {e}")
        finally:
            if on_done:
                on_done()

    threading.Thread(target=_run, daemon=True).start()
