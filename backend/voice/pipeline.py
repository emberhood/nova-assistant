"""
Nova voice pipeline orchestrator.
Wake word → Record → STT → AI Router → Execute Actions → TTS

Architecture:
- Groq decides WHAT to do (structured JSON actions + natural response)
- Pipeline executes the actions and speaks the response
- Conversation history in ai_router gives context across turns
- _pipeline_lock prevents concurrent runs (echo suppression)
"""

import threading
from datetime import datetime, date
from typing import Callable

from voice.wake_word import WakeWordListener
from voice.recorder import record_until_silence
from voice.stt import transcribe
from voice.tts import speak
from voice import speaker_verify
from skills import ai_router, pc_control, budget_skill, calendar_skill

_broadcast: Callable | None = None
_pipeline_lock = threading.Lock()
_is_busy = False
_active_user = "owner"   # tracked so router knows who's speaking


def set_broadcast(fn: Callable):
    global _broadcast
    _broadcast = fn


def is_busy() -> bool:
    return _is_busy


def _notify(state: str, payload: dict | None = None):
    if _broadcast:
        _broadcast({"type": "nova_state", "payload": state, **(payload or {})})


def _execute_action(action: dict, speaker_user: str) -> str | None:
    """
    Execute one action from the router.
    Returns a string for data-fetching actions (to be spoken),
    None for side-effect actions (navigate, create, etc.).
    """
    atype = action.get("type", "")
    user  = action.get("user", speaker_user)

    match atype:
        # ── Data-fetching (return spoken result) ──────────────────────────
        case "get_events":
            date_ref = action.get("date", "today")
            return calendar_skill.get_events_for_date(user, date_ref=date_ref)

        case "get_balance":
            return budget_skill.get_balance_summary(user)

        case "what_time":
            now = datetime.now()
            return f"Είναι {now.strftime('%H:%M')}."

        # ── Calendar mutations ────────────────────────────────────────────
        case "create_event":
            try:
                event_date = date.fromisoformat(action["date"])
                hour   = int(action.get("hour", 10))
                minute = int(action.get("minute", 0))
                from datetime import datetime as dt
                start_dt = dt(event_date.year, event_date.month, event_date.day, hour, minute)
                calendar_skill.create_event(action["title"], start_dt, user_id=user)
                if _broadcast:
                    _broadcast({"type": "refresh_calendar"})
                print(f"[Pipeline] Created event '{action['title']}' on {event_date} {hour:02d}:{minute:02d}")
            except Exception as e:
                print(f"[Pipeline] create_event error: {e}")
                return f"Δεν μπόρεσα να δημιουργήσω το event: {e}"
            return None

        case "delete_event":
            result = calendar_skill.delete_event(
                title=action.get("title", ""),
                event_date=action.get("date", date.today().isoformat()),
                user_id=user,
            )
            if _broadcast:
                _broadcast({"type": "refresh_calendar"})
            print(f"[Pipeline] delete_event: {result}")
            return None   # router's response covers this

        # ── Navigation / UI ───────────────────────────────────────────────
        case "navigate":
            if _broadcast:
                _broadcast({"type": "navigate", "tab": action["tab"]})

        case "set_user":
            global _active_user
            _active_user = action["user"]
            if _broadcast:
                _broadcast({"type": "set_user", "user": action["user"]})

        # ── PC control ────────────────────────────────────────────────────
        case "open_app":
            pc_control.open_app(action.get("app", ""))

        case "close_app":
            pc_control.close_app(action.get("app", ""))

        case "lock_pc":
            pc_control.lock_pc()

        case "volume_up":
            pc_control.volume_up()

        case "volume_down":
            pc_control.volume_down()

        case "mute":
            pc_control.mute()

        case "none" | _:
            pass

    return None


def _run_pipeline():
    global _is_busy, _active_user

    try:
        _notify("listening")

        try:
            audio = record_until_silence()
        except Exception as e:
            print(f"[Pipeline] Recording error: {e}")
            _notify("idle")
            return

        _notify("processing")

        # Speaker detection
        is_owner, _ = speaker_verify.verify(audio)
        if not is_owner:
            _speak_and_wait("Συγγνώμη, δεν αναγνωρίζω τη φωνή σου.")
            return

        gender = speaker_verify.detect_gender(audio)
        if gender == "female":
            speaker_user = "andriana"
        elif gender == "male":
            speaker_user = "owner"
        else:
            speaker_user = _active_user

        if _broadcast:
            _broadcast({"type": "set_user", "user": speaker_user})

        # STT
        try:
            text = transcribe(audio)
            if not text:
                _speak_and_wait("Δεν άκουσα τίποτα.")
                return
        except Exception as e:
            print(f"[Pipeline] STT error: {e}")
            _notify("idle")
            return

        print(f"[Pipeline] Heard: '{text}'")

        # AI Router — returns {actions, response}
        result = ai_router.route(text, active_user=speaker_user)
        actions  = result.get("actions", [])
        response = result.get("response", "")

        print(f"[Pipeline] Actions: {actions}")

        # Execute actions — data actions override/replace the response
        data_parts = []
        for action in actions:
            data = _execute_action(action, speaker_user)
            if data:
                data_parts.append(data)

        # If data was fetched (events, balance, time), speak that instead of router response
        final_response = "\n".join(data_parts) if data_parts else response
        if not final_response:
            final_response = "Εντάξει."

        _notify("speaking", {"text": final_response, "heard": text})
        _speak_and_wait(final_response)

        # Save turn to history for context in next turn
        ai_router.add_to_history(text, final_response)

    finally:
        _is_busy = False
        _notify("idle")


def _speak_and_wait(text: str):
    done = threading.Event()
    speak(text, on_done=lambda: done.set())
    done.wait(timeout=30)


def _on_wake_word():
    global _is_busy

    if not _pipeline_lock.acquire(blocking=False):
        print("[Pipeline] Busy — ignoring wake word.")
        return

    _is_busy = True
    try:
        _run_pipeline()
    finally:
        _pipeline_lock.release()


class NovaPipeline:
    def __init__(self):
        self._listener = WakeWordListener(
            on_detected=lambda: threading.Thread(target=_on_wake_word, daemon=True).start(),
            is_busy=is_busy,
        )

    def start(self):
        threading.Thread(target=_preload_models, daemon=True).start()
        self._listener.start()
        print("[Pipeline] Nova pipeline started.")

    def stop(self):
        self._listener.stop()


def _preload_models():
    try:
        from voice.stt import preload
        preload()
    except Exception as e:
        print(f"[Pipeline] Model preload error: {e}")
