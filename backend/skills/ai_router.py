"""
AI-based command router — replaces the regex intent classifier.

Groq (llama-3.3-70b) reads the user's speech, conversation history,
and returns structured JSON actions to execute.

Supports multi-step commands, corrections, context-aware responses.
"""

import os
import json
from collections import deque
from datetime import date, timedelta

# Conversation history — shared across all calls in a session
_history: deque = deque(maxlen=16)


def reset_history():
    _history.clear()


def add_to_history(user_text: str, jarvis_response: str):
    _history.append({"role": "user",      "content": user_text})
    _history.append({"role": "assistant", "content": jarvis_response})


def route(text: str, active_user: str = "owner") -> dict:
    """
    Returns:
    {
      "actions": [{"type": "...", ...}, ...],
      "response": "Natural Greek response to speak"
    }
    """
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    if not groq_key:
        return {"actions": [], "response": "Δεν έχω Groq API key."}

    today      = date.today()
    tomorrow   = today + timedelta(days=1)
    system_msg = _build_system(today, tomorrow, active_user)

    messages = [{"role": "system", "content": system_msg}]
    messages.extend(list(_history))
    messages.append({"role": "user", "content": text})

    try:
        from groq import Groq
        client = Groq(api_key=groq_key)
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=300,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content.strip()
        print(f"[Router] raw: {raw}")
        result = json.loads(raw)
        # Normalize
        if "actions" not in result:
            result["actions"] = []
        if "response" not in result:
            result["response"] = "Εντάξει."
        return result
    except Exception as e:
        print(f"[Router] error: {e}")
        return {"actions": [], "response": "Συγγνώμη, κάτι πήγε στραβά."}


def _build_system(today: date, tomorrow: date, active_user: str) -> str:
    import time as _time
    utc_offset = -(_time.timezone if not _time.daylight else _time.altzone) // 3600
    offset_str = f"UTC+{utc_offset}" if utc_offset >= 0 else f"UTC{utc_offset}"

    return f"""Είσαι ο Jarvis, AI βοηθός των Mario (owner) και Andriana.
Σήμερα: {today.strftime("%A %d %B %Y")} (ISO: {today.isoformat()})
Αύριο: {tomorrow.isoformat()}
Ενεργός χρήστης: {active_user}
Τοπική ώρα: {offset_str} (Αθήνα)

Απάντα ΠΑΝΤΑ με έγκυρο JSON:
{{"actions": [...], "response": "..."}}

━━━ ΔΙΑΘΕΣΙΜΕΣ ΕΝΕΡΓΕΙΕΣ ━━━

ΗΜΕΡΟΛΟΓΙΟ:
{{"type": "get_events", "user": "owner|andriana|shared", "date": "today|tomorrow|YYYY-MM-DD|week"}}
{{"type": "create_event", "title": "...", "date": "YYYY-MM-DD", "hour": 10, "minute": 0, "user": "owner|andriana|shared"}}
{{"type": "delete_event", "title": "...", "date": "YYYY-MM-DD", "user": "owner|andriana|shared"}}

ΠΛΟΗΓΗΣΗ:
{{"type": "navigate", "tab": "calendar|budget|dashboard"}}
{{"type": "set_user", "user": "owner|andriana|shared"}}

PC:
{{"type": "open_app", "app": "chrome|spotify|discord|code|..."}}
{{"type": "close_app", "app": "..."}}
{{"type": "lock_pc"}}
{{"type": "volume_up"}}, {{"type": "volume_down"}}, {{"type": "mute"}}

ΠΛΗΡΟΦΟΡΙΕΣ:
{{"type": "get_balance", "user": "owner|andriana|shared"}}
{{"type": "what_time"}}

━━━ ΚΑΝΟΝΕΣ ΩΡΩΝ (ΣΗΜΑΝΤΙΚΟ) ━━━
- Όλες οι ώρες είναι ΤΟΠΙΚΗ ΩΡΑ Αθήνας, 24ωρη μορφή στο JSON
- "στις 3" χωρίς πλαίσιο = 15:00 (απόγευμα), ΟΧΙ 03:00
- "στις 8" χωρίς πλαίσιο = 20:00 (βράδυ), ΟΧΙ 08:00
- "στις 8 το πρωί" = 08:00, "στις 8 το βράδυ" = 20:00
- "μεσημέρι" = 13:00, "απόγευμα" = 17:00, "βράδυ" = 20:00, "πρωί" = 09:00
- Αμφίβολες ώρες (3, 4, 5, 6, 7, 8): προτίμησε απόγευμα/βράδυ (π.χ. +12 αν <9)

━━━ ΓΕΝΙΚΟΙ ΚΑΝΟΝΕΣ ━━━
- actions = [] αν είναι απλή συνομιλία
- Μεταφορά/διόρθωση event ("λάθος", "άλλαξέ το", "μετάφερέ το") → delete_event + create_event
- Για get_events/get_balance/what_time: response = "" (το σύστημα βάζει τα πραγματικά δεδομένα)
- user default = "{active_user}" αν δεν αναφέρεται άλλος
- response ΠΑΝΤΑ στα Ελληνικά, 1-2 προτάσεις, φυσικά
- ΜΗΝ επινοείς events — αν δεν ξέρεις τι υπάρχει, κάνε get_events πρώτα
- Πολλές ενέργειες μαζί είναι εντάξει"""
