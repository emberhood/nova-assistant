"""
Jarvis Telegram bot — remote control from anywhere.

Usage:
1. Create a bot via @BotFather, get the token
2. Add JARVIS_BOT_TOKEN to .env
3. Start Jarvis backend — bot starts polling automatically

Supported commands:
  /start          — welcome message
  /help           — list commands
  /status         — is Jarvis online?
  /balance        — budget summary
  /lock           — lock the PC
  /volume up|down — adjust volume
  /mute           — mute audio
  Any free text   — routed through intent classifier (same as voice)
"""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from skills.intent import classify
from skills import pc_control, budget_skill, calendar_skill, haiku_skill

BOT_TOKEN: str = os.getenv("JARVIS_BOT_TOKEN", "").strip()

_POLL_TIMEOUT = 30
_ERROR_SLEEP   = 5
_IDLE_SLEEP    = 10

# chat_ids allowed to control Jarvis (populated from JARVIS_ALLOWED_CHAT_IDS env)
_ALLOWED: set[str] = set(filter(None, os.getenv("JARVIS_ALLOWED_CHAT_IDS", "").split(",")))

_START_TIME = datetime.now()

# broadcast callback (set by main.py) to push state to UI when triggered remotely
_broadcast: Callable | None = None


def set_broadcast(fn: Callable) -> None:
    global _broadcast
    _broadcast = fn


def _api_post(method: str, payload: dict, token: str = BOT_TOKEN) -> dict | None:
    body = json.dumps(payload).encode()
    req = Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())
    except (HTTPError, URLError, OSError, json.JSONDecodeError):
        return None


def _api_get(method: str, params: dict, token: str = BOT_TOKEN) -> dict | None:
    url = f"https://api.telegram.org/bot{token}/{method}?{urlencode(params)}"
    req = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(req, timeout=_POLL_TIMEOUT + 10) as r:
            return json.loads(r.read().decode())
    except (HTTPError, URLError, OSError, json.JSONDecodeError):
        return None


def send(chat_id: str | int, text: str) -> None:
    _api_post("sendMessage", {"chat_id": str(chat_id), "text": text, "parse_mode": "HTML"})


def _handle_text(text: str) -> str:
    """Route free-text through the intent classifier (same as voice pipeline)."""
    intent = classify(text)
    print(f"[Telegram] Intent: {intent.name} | slots: {intent.slots}")

    match intent.name:
        case "open_app":
            return pc_control.open_app(intent.slots["app"])
        case "close_app":
            return pc_control.close_app(intent.slots["app"])
        case "what_time":
            return f"It's {datetime.now().strftime('%H:%M')}."
        case "get_balance":
            return budget_skill.get_balance_summary()
        case "lock_pc":
            return pc_control.lock_pc()
        case "volume_up":
            return pc_control.volume_up()
        case "volume_down":
            return pc_control.volume_down()
        case "mute":
            return pc_control.mute()
        case "add_event":
            result = calendar_skill.parse_event_from_text(intent.slots["text"])
            if result:
                title, start_dt = result
                return calendar_skill.create_event(title, start_dt)
            return "Δεν κατάλαβα τις λεπτομέρειες. Πες π.χ. 'βάλε γιατρό Τρίτη στις 10'."
        case "get_calendar":
            return calendar_skill.get_today_events()
        case "stop":
            return "Εντάξει."
        case _:
            return haiku_skill.ask_haiku(text)


def _process_update(update: dict) -> None:
    msg = update.get("message") or update.get("edited_message")
    if not msg or "text" not in msg:
        return

    chat_id = str((msg.get("chat") or {}).get("id", ""))
    text = msg["text"].strip()

    # Security: ignore if allowlist is set and this chat isn't in it
    if _ALLOWED and chat_id not in _ALLOWED:
        send(chat_id, "Μη εξουσιοδοτημένος χρήστης. Πρόσθεσε το chat ID σου στο JARVIS_ALLOWED_CHAT_IDS στο .env")
        return

    # --- Slash commands ---
    if text.startswith("/start"):
        uptime = datetime.now() - _START_TIME
        hrs, rem = divmod(int(uptime.total_seconds()), 3600)
        mins = rem // 60
        send(chat_id,
             f"<b>JARVIS online</b> ⚡\n"
             f"Uptime: {hrs}ω {mins}λ\n\n"
             f"Στείλε οποιαδήποτε εντολή ή:\n"
             f"/help  /status  /balance  /lock\n"
             f"/volume up  /volume down  /mute")
        return

    if text.startswith("/help"):
        send(chat_id,
             "<b>Εντολές Jarvis</b>\n\n"
             "<b>Slash:</b>\n"
             "/status — κατάσταση συστήματος\n"
             "/balance — σύνοψη budget\n"
             "/lock — κλείδωμα PC\n"
             "/volume up|down — ένταση ήχου\n"
             "/mute — σίγαση\n\n"
             "<b>Ελεύθερο κείμενο (ίδιο με φωνή):</b>\n"
             "άνοιξε chrome\n"
             "κλείσε spotify\n"
             "τι ώρα είναι\n"
             "πόσα έχω\n"
             "volume up")
        return

    if text.startswith("/status"):
        uptime = datetime.now() - _START_TIME
        hrs, rem = divmod(int(uptime.total_seconds()), 3600)
        mins = rem // 60
        send(chat_id,
             f"✅ Jarvis online\n"
             f"Uptime: {hrs}ω {mins}λ\n"
             f"Wake word: openWakeWord (hey_jarvis)\n"
             f"STT: faster-whisper (base)\n"
             f"TTS: edge-tts (Ελληνικά)")
        return

    if text.startswith("/balance"):
        send(chat_id, budget_skill.get_balance_summary())
        return

    if text.startswith("/lock"):
        reply = pc_control.lock_pc()
        send(chat_id, reply)
        return

    if text.lower().startswith("/volume"):
        parts = text.lower().split()
        direction = parts[1] if len(parts) > 1 else ""
        if direction == "up":
            send(chat_id, pc_control.volume_up())
        elif direction == "down":
            send(chat_id, pc_control.volume_down())
        else:
            send(chat_id, "Usage: /volume up or /volume down")
        return

    if text.startswith("/mute"):
        send(chat_id, pc_control.mute())
        return

    # --- Free-text intent routing ---
    reply = _handle_text(text)
    if _broadcast:
        _broadcast({"type": "jarvis_state", "payload": "idle", "text": reply, "heard": f"[Telegram] {text}"})
    send(chat_id, reply)


def _poll_loop(token: str) -> None:
    print("[Telegram] Bot polling started.")
    offset = 0
    while True:
        data = _api_get("getUpdates", {"offset": offset, "timeout": _POLL_TIMEOUT}, token)
        if not data or not data.get("ok"):
            time.sleep(_ERROR_SLEEP)
            continue

        for update in data.get("result") or []:
            update_id = int(update.get("update_id", 0))
            try:
                _process_update(update)
            except Exception as e:
                print(f"[Telegram] Update error: {e}")
            offset = max(offset, update_id + 1)


def start_bot() -> None:
    """Start the Telegram polling loop in a daemon thread. No-op if token is missing."""
    token = os.getenv("JARVIS_BOT_TOKEN", "").strip()
    if not token:
        print("[Telegram] JARVIS_BOT_TOKEN not set — Telegram bot disabled.")
        return

    global BOT_TOKEN
    BOT_TOKEN = token

    thread = threading.Thread(target=_poll_loop, args=(token,), daemon=True, name="jarvis-telegram")
    thread.start()
    print(f"[Telegram] Bot started. Allowed chats: {_ALLOWED or 'all (no allowlist)'}")
