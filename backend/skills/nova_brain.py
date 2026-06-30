"""
Nova's Claude-native brain — replaces the Groq JSON router.

Uses Anthropic Messages API with native tool_use / tool_result.
Agent loop: Claude decides which tools to call, we execute them,
return results, Claude generates the final natural-language response.

Model routing:
  claude-haiku-4-5-20251001  (default — fast, ~$0.001/turn)
  claude-sonnet-4-6           (complex reasoning, triggered by heuristic)
"""

import os
from collections import deque
from datetime import date, datetime, timedelta
from typing import Callable

import anthropic

MODEL_HAIKU  = "claude-haiku-4-5-20251001"
MODEL_SONNET = "claude-sonnet-4-6"

_client: anthropic.Anthropic | None = None
_history: deque = deque(maxlen=20)
_broadcast_fn: Callable | None = None

_SONNET_HINTS = [
    "ανάλυσε", "ανάλυση", "σύγκρινε", "σύγκριση",
    "explain", "analyze", "compare", "γιατί", "why",
    "εξήγησε", "πρότεινε", "suggest", "plan",
]


def set_broadcast(fn: Callable):
    global _broadcast_fn
    _broadcast_fn = fn


def reset_history():
    _history.clear()


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY not set in .env")
        _client = anthropic.Anthropic(api_key=key)
    return _client


def _pick_model(text: str) -> str:
    if any(h in text.lower() for h in _SONNET_HINTS):
        return MODEL_SONNET
    return MODEL_HAIKU


def _build_system(active_user: str) -> str:
    today    = date.today()
    tomorrow = today + timedelta(days=1)
    import time as _t
    offset   = -(_t.timezone if not _t.daylight else _t.altzone) // 3600
    tz_str   = f"UTC+{offset}" if offset >= 0 else f"UTC{offset}"

    return f"""Είσαι η Nova, η προσωπική AI βοηθός των Mario (owner) και Andriana.
Σήμερα: {today.strftime("%A %d %B %Y")} (ISO: {today.isoformat()})
Αύριο: {tomorrow.isoformat()}
Ενεργός χρήστης: {active_user}
Τοπική ώρα: {tz_str} (Αθήνα, 24ωρη)

Κανόνες:
- Απαντάς ΠΑΝΤΑ στα Ελληνικά, φυσικά και συνοπτικά (1-2 προτάσεις)
- Χρησιμοποιείς τα tools όταν χρειάζεται — ΜΗΝ επινοείς δεδομένα
- Ώρες: "στις 3" = 15:00, "στις 8" = 20:00 (προτίμα απόγευμα/βράδυ αν αμφίβολο)
- Αν ο χρήστης δεν αναφέρει user, χρησιμοποίησε "{active_user}"
- navigate/set_user: εκτέλεσε αμέσως χωρίς επιβεβαίωση"""


TOOLS = [
    {
        "name": "get_calendar_events",
        "description": "Ανάκτηση events ημερολογίου για συγκεκριμένη ημερομηνία ή περίοδο",
        "input_schema": {
            "type": "object",
            "properties": {
                "user": {
                    "type": "string",
                    "enum": ["owner", "andriana", "shared"],
                    "description": "Ποιου το ημερολόγιο",
                },
                "date_ref": {
                    "type": "string",
                    "description": "'today', 'tomorrow', 'week', όνομα ημέρας (π.χ. 'τρίτη'), ή YYYY-MM-DD",
                },
            },
            "required": ["user", "date_ref"],
        },
    },
    {
        "name": "create_calendar_event",
        "description": "Δημιουργία νέου event στο ημερολόγιο",
        "input_schema": {
            "type": "object",
            "properties": {
                "title":  {"type": "string", "description": "Τίτλος event"},
                "date":   {"type": "string", "description": "YYYY-MM-DD"},
                "hour":   {"type": "integer", "description": "Ώρα σε 24ωρη μορφή"},
                "minute": {"type": "integer", "description": "Λεπτά"},
                "user":   {"type": "string", "enum": ["owner", "andriana", "shared"]},
            },
            "required": ["title", "date", "hour", "minute", "user"],
        },
    },
    {
        "name": "delete_calendar_event",
        "description": "Διαγραφή event από ημερολόγιο βάσει τίτλου και ημερομηνίας",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "date":  {"type": "string", "description": "YYYY-MM-DD"},
                "user":  {"type": "string", "enum": ["owner", "andriana", "shared"]},
            },
            "required": ["title", "date", "user"],
        },
    },
    {
        "name": "get_budget_summary",
        "description": "Ανάκτηση οικονομικής σύνοψης: υπόλοιπο, έξοδα μήνα, πρόσφατα transactions",
        "input_schema": {
            "type": "object",
            "properties": {
                "user": {"type": "string", "enum": ["owner", "andriana"]},
            },
            "required": ["user"],
        },
    },
    {
        "name": "get_current_time",
        "description": "Επιστρέφει την τρέχουσα ώρα",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "navigate_to",
        "description": "Πλοήγηση σε σελίδα/panel του Nova UI",
        "input_schema": {
            "type": "object",
            "properties": {
                "tab": {"type": "string", "enum": ["dashboard", "calendar", "budget"]},
            },
            "required": ["tab"],
        },
    },
    {
        "name": "set_active_user",
        "description": "Αλλαγή ενεργού χρήστη στο UI",
        "input_schema": {
            "type": "object",
            "properties": {
                "user": {"type": "string", "enum": ["owner", "andriana", "shared"]},
            },
            "required": ["user"],
        },
    },
    {
        "name": "control_pc",
        "description": "Έλεγχος PC: άνοιγμα/κλείσιμο εφαρμογών, volume, κλείδωμα",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["open_app", "close_app", "volume_up", "volume_down", "mute", "lock"],
                },
                "app": {"type": "string", "description": "Όνομα εφαρμογής (για open_app/close_app)"},
            },
            "required": ["action"],
        },
    },
]


def _execute_tool(name: str, inputs: dict, active_user: str) -> tuple[str, dict | None]:
    """
    Execute a tool call. Returns (result_text, ws_event | None).
    ws_event is broadcast to all connected WebSocket clients.
    """
    match name:
        case "get_calendar_events":
            from skills.calendar_skill import get_events_for_date
            return get_events_for_date(inputs["user"], date_ref=inputs["date_ref"]), None

        case "create_calendar_event":
            from skills.calendar_skill import create_event
            d = date.fromisoformat(inputs["date"])
            start = datetime(d.year, d.month, d.day, int(inputs["hour"]), int(inputs["minute"]))
            result = create_event(inputs["title"], start, user_id=inputs["user"])
            return result, {"type": "refresh_calendar"}

        case "delete_calendar_event":
            from skills.calendar_skill import delete_event
            result = delete_event(
                title=inputs["title"],
                event_date=inputs["date"],
                user_id=inputs["user"],
            )
            return result, {"type": "refresh_calendar"}

        case "get_budget_summary":
            from skills.budget_skill import get_balance_summary
            return get_balance_summary(), None

        case "get_current_time":
            return f"Είναι {datetime.now().strftime('%H:%M')}.", None

        case "navigate_to":
            tab = inputs["tab"]
            return f"Πλοήγηση στο {tab}.", {"type": "navigate", "tab": tab}

        case "set_active_user":
            user = inputs["user"]
            return f"Αλλαγή σε {user}.", {"type": "set_user", "user": user}

        case "control_pc":
            from skills import pc_control
            action = inputs["action"]
            app    = inputs.get("app", "")
            match action:
                case "open_app":
                    pc_control.open_app(app)
                    return f"Άνοιξα {app}.", None
                case "close_app":
                    pc_control.close_app(app)
                    return f"Έκλεισα {app}.", None
                case "volume_up":
                    pc_control.volume_up()
                    return "Volume up.", None
                case "volume_down":
                    pc_control.volume_down()
                    return "Volume down.", None
                case "mute":
                    pc_control.mute()
                    return "Σίγαση.", None
                case "lock":
                    pc_control.lock_pc()
                    return "Κλείδωσα τον υπολογιστή.", None

    return f"Άγνωστο tool: {name}", None


def route(text: str, active_user: str = "owner") -> str:
    """
    Main entry point. Returns Nova's Greek response string.

    Runs the agent loop:
      user text → Claude (may call tools) → execute tools → Claude (final response)
    """
    client  = _get_client()
    model   = _pick_model(text)
    system  = _build_system(active_user)

    messages = list(_history)
    messages.append({"role": "user", "content": text})

    print(f"[Brain] {model.split('-')[1].upper()} | user={active_user} | '{text}'")

    for _ in range(5):  # max tool-call rounds per turn
        try:
            response = client.messages.create(
                model=model,
                max_tokens=1024,
                system=system,
                tools=TOOLS,
                messages=messages,
            )
        except Exception as e:
            print(f"[Brain] API error: {e}")
            return "Συγγνώμη, κάτι πήγε στραβά."

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            break

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            print(f"[Brain] → {block.name}({block.input})")
            result_text, ws_event = _execute_tool(block.name, block.input, active_user)
            print(f"[Brain] ← {result_text[:80]}")
            if ws_event and _broadcast_fn:
                _broadcast_fn(ws_event)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result_text,
            })

        messages.append({"role": "user", "content": tool_results})

    final = "Εντάξει."
    for block in response.content:
        if hasattr(block, "text") and block.text:
            final = block.text
            break

    # Persist text-only summary to history (keeps it lean across turns)
    _history.append({"role": "user", "content": text})
    _history.append({"role": "assistant", "content": final})

    print(f"[Brain] ✓ '{final}'")
    return final
