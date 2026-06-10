"""
Apple Calendar skill for Nova via iCloud CalDAV.
Supports multiple users (owner, andriana) and a shared calendar.

Setup (one-time per user):
1. appleid.apple.com → Sign-In and Security → App-Specific Passwords → Generate
2. Add to .env:
     OWNER_APPLE_ID=your@icloud.com
     OWNER_APPLE_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
     ANDRIANA_APPLE_ID=andriana@icloud.com
     ANDRIANA_APPLE_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
     SHARED_CALENDAR_NAME=Together   (name of your shared Apple Calendar)

Dependencies:
  caldav==1.3.9
  icalendar==6.0.0
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, date, timezone

CALDAV_URL = "https://caldav.icloud.com/"

# Explicit display timezone — change via env var TIMEZONE if needed
import os as _os
try:
    from zoneinfo import ZoneInfo as _ZoneInfo
    _LOCAL_TZ = _ZoneInfo(_os.getenv("TIMEZONE", "Europe/Athens"))
except Exception:
    _LOCAL_TZ = timezone.utc

# per-user CalDAV client cache: {"owner": (client, principal), ...}
_cache: dict[str, tuple] = {}


def _is_configured(user_id: str = "owner") -> bool:
    from config.user_config import get_calendar_creds
    apple_id, pwd = get_calendar_creds(user_id)
    return bool(apple_id and pwd)


def _get_client_principal(user_id: str):
    """Return (principal, error). Cached per user."""
    from config.user_config import get_calendar_creds
    if not _is_configured(user_id):
        return None, f"Credentials not configured for {user_id}"
    try:
        import caldav
    except ImportError:
        return None, "caldav not installed"
    apple_id, pwd = get_calendar_creds(user_id)
    try:
        if user_id not in _cache:
            client = caldav.DAVClient(url=CALDAV_URL, username=apple_id, password=pwd)
            principal = client.principal()
            _cache[user_id] = (client, principal)
        return _cache[user_id][1], None
    except Exception as e:
        _cache.pop(user_id, None)
        return None, str(e)


def _get_calendar(user_id: str = "owner", calendar_name: str | None = None):
    """
    Return (caldav_calendar, error_str).
    Caches the connection per user. If calendar_name given, finds that specific calendar.
    """
    global _cache

    from config.user_config import get_calendar_creds, SHARED_CALENDAR_NAME

    if not _is_configured(user_id):
        return None, f"Το Apple Calendar δεν έχει ρυθμιστεί. Συμπλήρωσε το .env."

    try:
        import caldav
    except ImportError:
        return None, "Η βιβλιοθήκη caldav δεν είναι εγκατεστημένη. Τρέξε: pip install caldav icalendar"

    apple_id, pwd = get_calendar_creds(user_id)

    try:
        if user_id not in _cache:
            client = caldav.DAVClient(url=CALDAV_URL, username=apple_id, password=pwd)
            principal = client.principal()
            _cache[user_id] = (client, principal)

        _, principal = _cache[user_id]
        calendars = principal.calendars()
        if not calendars:
            return None, "Δεν βρέθηκαν ημερολόγια στον λογαριασμό."

        target_name = calendar_name  # None means "first calendar"

        if target_name:
            for cal in calendars:
            # find by display name
                try:
                    props = cal.get_properties([caldav.dav.DisplayName()])
                    display = props.get("{DAV:}displayname", "")
                    if display.lower() == target_name.lower():
                        return cal, None
                except Exception:
                    continue
            return None, f"Δεν βρέθηκε ημερολόγιο με όνομα '{target_name}'."

        return calendars[0], None

    except Exception as e:
        _cache.pop(user_id, None)
        return None, f"Could not connect to iCloud ({user_id}): {e}"


def _get_shared_calendar():
    """Return the shared calendar — tries owner first, then andriana."""
    from config.user_config import SHARED_CALENDAR_NAME
    for uid in ("owner", "andriana"):
        if not _is_configured(uid):
            continue
        cal, err = _get_calendar(uid, calendar_name=SHARED_CALENDAR_NAME)
        if cal:
            return cal, None
    return None, f"Shared calendar '{SHARED_CALENDAR_NAME}' not found. Check SHARED_CALENDAR_NAME in .env."


# ── Public API ─────────────────────────────────────────────────────────────────

def get_today_events(user_id: str = "owner") -> str:
    return get_events_for_date(user_id=user_id, date_ref="today")


def get_events_for_date(user_id: str = "owner", date_ref: str = "today") -> str:
    """
    date_ref: "today" | "tomorrow" | "week" | weekday name (e.g. "τρίτη")
    """
    from datetime import timedelta

    _DAY_MAP = {
        "δευτέρα": 0, "δευτερα": 0, "monday": 0,
        "τρίτη": 1, "τριτη": 1, "tuesday": 1,
        "τετάρτη": 2, "τεταρτη": 2, "wednesday": 2,
        "πέμπτη": 3, "πεμπτη": 3, "thursday": 3,
        "παρασκευή": 4, "παρασκευη": 4, "friday": 4,
        "σάββατο": 5, "σαββατο": 5, "saturday": 5,
        "κυριακή": 6, "κυριακη": 6, "sunday": 6,
    }
    _DAY_GR = ["Δευτέρα", "Τρίτη", "Τετάρτη", "Πέμπτη", "Παρασκευή", "Σάββατο", "Κυριακή"]

    today = date.today()

    if date_ref == "today":
        target = today
        label = "σήμερα"
    elif date_ref == "tomorrow":
        target = today + timedelta(days=1)
        label = "αύριο"
    elif date_ref == "week":
        # Return next 7 days summary
        return get_upcoming_events(user_id=user_id, days=7)
    elif date_ref in _DAY_MAP:
        wd = _DAY_MAP[date_ref]
        days_ahead = (wd - today.weekday()) % 7 or 7
        target = today + timedelta(days=days_ahead)
        label = _DAY_GR[wd]
    else:
        target = today
        label = "σήμερα"

    events_list = get_month_events(user_id=user_id, year=target.year, month=target.month)
    day_events = [e for e in events_list if e["date"] == target.isoformat()]

    if not day_events:
        return f"Δεν έχεις κανένα event {label}."

    day_events.sort(key=lambda e: "00:00" if e["time"] == "all day" else e["time"])
    count = len(day_events)
    lines = [f"Έχεις {count} event{'s' if count > 1 else ''} {label}:"]
    for ev in day_events:
        time_label = "ολοήμερο" if ev["time"] == "all day" else ev["time"]
        lines.append(f"• {time_label} — {ev['title']}")
    return "\n".join(lines)


def get_upcoming_events(user_id: str = "owner", days: int = 7) -> str:
    if user_id == "shared":
        cal, err = _get_shared_calendar()
    else:
        cal, err = _get_calendar(user_id)
    if err:
        return err

    now = datetime.now(tz=timezone.utc)
    end = now + timedelta(days=days)

    try:
        results = cal.search(start=now, end=end, event=True, expand=True)
    except Exception as e:
        return f"Calendar error: {e}"

    events = _parse_events(results)
    if not events:
        return f"Δεν έχεις events τις επόμενες {days} μέρες."

    lines = [f"Επόμενες {days} μέρες:"]
    for ev in sorted(events, key=lambda e: e["start"])[:10]:
        lines.append(f"• {ev['date_str']} — {ev['title']}")
    return "\n".join(lines)


def get_month_events(user_id: str = "owner", year: int | None = None, month: int | None = None) -> list[dict]:
    """Return list of events for a full month (for the calendar UI)."""
    from calendar import monthrange

    today = date.today()
    y = year or today.year
    m = month or today.month
    _, last_day = monthrange(y, m)

    start = datetime(y, m, 1, tzinfo=timezone.utc)
    end   = datetime(y, m, last_day, 23, 59, 59, tzinfo=timezone.utc)

    if user_id == "shared":
        # Search only the named shared calendar, not all calendars
        cal, err = _get_shared_calendar()
        if err:
            print(f"[Calendar] shared calendar error: {err}")
            return []
        try:
            results = cal.search(start=start, end=end, event=True, expand=True)
            print(f"[Calendar] shared: {len(results)} events for {y}/{m:02d}")
        except Exception as e:
            print(f"[Calendar] shared search error: {e}")
            return []
        events = _parse_events(results)
    else:
        # Search across ALL calendars for this user
        principal, perr = _get_client_principal(user_id)
        if perr:
            print(f"[Calendar] principal error: {perr}")
            return []

        all_calendars = principal.calendars()
        print(f"[Calendar] {user_id}: found {len(all_calendars)} calendars, searching {y}/{m:02d}")

        all_results = []
        for c in all_calendars:
            try:
                import caldav.lib.dav as dav
                props = c.get_properties([caldav.lib.dav.DisplayName()])
                cal_name = props.get("{DAV:}displayname", "?")
            except Exception:
                cal_name = "?"
            try:
                res = c.search(start=start, end=end, event=True, expand=True)
                if res:
                    print(f"[Calendar]   '{cal_name}': {len(res)} events")
                all_results.extend(res)
            except Exception as e:
                print(f"[Calendar]   '{cal_name}': search error: {e}")

        events = _parse_events(all_results)

    print(f"[Calendar] {user_id}: total parsed {len(events)} events")
    return [
        {"title": ev["title"], "date": ev["date_iso"], "time": ev["time_str"]}
        for ev in events
    ]


def create_event(title: str, start_dt: datetime, duration_minutes: int = 60, user_id: str = "owner") -> str:
    if user_id == "shared":
        cal, err = _get_shared_calendar()
    else:
        cal, err = _get_calendar(user_id)
    if err:
        return err

    end_dt = start_dt + timedelta(minutes=duration_minutes)

    try:
        from icalendar import Calendar as iCal, Event as iEvent
        import uuid

        ical = iCal()
        ical.add("prodid", "-//Nova//EN")
        ical.add("version", "2.0")
        event = iEvent()
        event.add("summary", title)
        event.add("dtstart", start_dt.replace(tzinfo=_LOCAL_TZ))
        event.add("dtend",   end_dt.replace(tzinfo=_LOCAL_TZ))
        event.add("uid", str(uuid.uuid4()))
        ical.add_component(event)

        cal.save_event(ical.to_ical().decode())
        t = start_dt.strftime("%A %d/%m στις %H:%M")
        return f"Δημιούργησα το event '{title}' για {t}."
    except Exception as e:
        return f"Δεν μπόρεσα να δημιουργήσω το event: {e}"


def delete_event(title: str, event_date: str, user_id: str = "owner") -> str:
    """Delete event(s) matching title on a specific date. event_date: YYYY-MM-DD."""
    from icalendar import Calendar as iCal

    try:
        target = date.fromisoformat(event_date)
    except ValueError:
        return f"Μη έγκυρη ημερομηνία: {event_date}"

    start = datetime(target.year, target.month, target.day, tzinfo=timezone.utc)
    end   = datetime(target.year, target.month, target.day, 23, 59, 59, tzinfo=timezone.utc)

    if user_id == "shared":
        calendars_to_search = []
        cal, err = _get_shared_calendar()
        if cal:
            calendars_to_search = [cal]
    else:
        principal, perr = _get_client_principal(user_id)
        if perr:
            return f"Σφάλμα σύνδεσης: {perr}"
        calendars_to_search = principal.calendars()

    deleted = []
    for c in calendars_to_search:
        try:
            results = c.search(start=start, end=end, event=True, expand=False)
            for item in results:
                try:
                    ical = iCal.from_ical(item.data)
                    for component in ical.walk():
                        if component.name != "VEVENT":
                            continue
                        summary = str(component.get("SUMMARY", ""))
                        if title.lower() in summary.lower():
                            item.delete()
                            deleted.append(summary)
                            print(f"[Calendar] deleted: '{summary}'")
                except Exception as e:
                    print(f"[Calendar] delete item error: {e}")
        except Exception as e:
            print(f"[Calendar] search for delete error: {e}")

    if deleted:
        return f"Έσβησα: {', '.join(deleted)}."
    return f"Δεν βρήκα event με τίτλο '{title}' στις {event_date}."


# ── Helpers ────────────────────────────────────────────────────────────────────

def _parse_events(results) -> list[dict]:
    from icalendar import Calendar as iCal

    events = []
    seen_uids: set[str] = set()   # deduplicate by UID (shared events appear in multiple calendars)

    for item in results:
        try:
            ical = iCal.from_ical(item.data)
            for component in ical.walk():
                if component.name != "VEVENT":
                    continue

                uid = str(component.get("UID", ""))
                title = str(component.get("SUMMARY", "No title"))
                dtstart = component.get("DTSTART").dt

                if isinstance(dtstart, date) and not isinstance(dtstart, datetime):
                    time_str = "all day"
                    date_str = dtstart.strftime("%a %d/%m (all day)")
                    date_iso = dtstart.isoformat()
                    start_key = datetime.combine(dtstart, datetime.min.time(), tzinfo=timezone.utc)
                else:
                    if dtstart.tzinfo is None:
                        dtstart = dtstart.replace(tzinfo=timezone.utc)
                    local = dtstart.astimezone(_LOCAL_TZ)
                    time_str = local.strftime("%H:%M")
                    date_str = local.strftime("%a %d/%m %H:%M")
                    date_iso = local.date().isoformat()
                    start_key = dtstart

                # Use UID+date as dedup key (recurring events have same UID, different dates)
                dedup_key = f"{uid}_{date_iso}"
                if dedup_key in seen_uids:
                    continue
                seen_uids.add(dedup_key)

                events.append({
                    "title": title,
                    "start": start_key,
                    "time_str": time_str,
                    "date_str": date_str,
                    "date_iso": date_iso,
                })
        except Exception:
            continue
    return events


# ── Voice parsing ──────────────────────────────────────────────────────────────

def _next_weekday(weekday: int) -> date:
    today = date.today()
    days_ahead = weekday - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return today + timedelta(days=days_ahead)


def parse_event_from_text(text: str) -> tuple[str, datetime] | None:
    """
    Parse natural language event description → (title, datetime).
    Uses Groq (llama) if available, falls back to regex.
    """
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    if groq_key:
        result = _parse_event_groq(text, groq_key)
        if result:
            return result
    return _parse_event_regex(text)


def _parse_event_groq(text: str, api_key: str) -> tuple[str, datetime] | None:
    """Ask Groq/llama to extract title, date, time from natural language."""
    import json as _json
    from urllib.request import Request, urlopen
    from urllib.error import URLError

    today = date.today()
    prompt = (
        f"Today is {today.strftime('%A %d %B %Y')} (weekday={today.weekday()}, 0=Monday).\n"
        f"Extract the calendar event from this Greek text: \"{text}\"\n\n"
        "Reply with ONLY valid JSON, no explanation:\n"
        '{"title": "event title in Greek", "date": "YYYY-MM-DD", "hour": 12, "minute": 0}\n\n'
        "Rules:\n"
        "- μεσημέρι = 13:00, πρωί = 09:00, απόγευμα = 17:00, βράδυ = 20:00\n"
        "- αύριο = tomorrow, σήμερα = today\n"
        "- If no time mentioned, use 10:00\n"
        "- Title should be clean, no date/time words"
    )

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 80,
        "temperature": 0,
    }

    try:
        req = Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=_json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=10) as r:
            data = _json.loads(r.read().decode())
        raw = data["choices"][0]["message"]["content"].strip()
        # extract JSON even if wrapped in markdown
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if not m:
            return None
        ev = _json.loads(m.group())
        event_date = date.fromisoformat(ev["date"])
        hour   = int(ev.get("hour", 10))
        minute = int(ev.get("minute", 0))
        title  = ev.get("title", "Event").strip() or "Event"
        print(f"[Calendar/Groq] parsed: '{title}' on {event_date} at {hour:02d}:{minute:02d}")
        return title, datetime(event_date.year, event_date.month, event_date.day, hour, minute)
    except Exception as e:
        print(f"[Calendar/Groq] parse error: {e}")
        return None


def _parse_event_regex(text: str) -> tuple[str, datetime] | None:
    """Regex fallback for event parsing."""
    _DAY_MAP = {
        "δευτέρα": 0, "δευτερα": 0, "monday": 0,
        "τρίτη": 1, "τριτη": 1, "tuesday": 1,
        "τετάρτη": 2, "τεταρτη": 2, "wednesday": 2,
        "πέμπτη": 3, "πεμπτη": 3, "thursday": 3,
        "παρασκευή": 4, "παρασκευη": 4, "friday": 4,
        "σάββατο": 5, "σαββατο": 5, "saturday": 5,
        "κυριακή": 6, "κυριακη": 6, "sunday": 6,
    }
    _TIME_WORDS = {
        "μεσημέρι": (13, 0), "μεσημερι": (13, 0),
        "πρωί": (9, 0),  "πρωι": (9, 0),
        "απόγευμα": (17, 0), "απογευμα": (17, 0),
        "βράδυ": (20, 0), "βραδυ": (20, 0),
        "μεσάνυχτα": (0, 0), "μεσανυχτα": (0, 0),
    }

    t = text.lower().strip()

    # Named time words first
    hour, minute = 10, 0
    for word, (h, m) in _TIME_WORDS.items():
        if word in t:
            hour, minute = h, m
            break
    else:
        time_match = re.search(r"(?:στις?|at)\s+(\d{1,2})(?::(\d{2}))?", t) or \
                     re.search(r"\b(\d{1,2}):(\d{2})\b", t)
        if time_match:
            hour   = int(time_match.group(1))
            minute = int(time_match.group(2)) if time_match.group(2) else 0

    event_date, matched_day = None, None
    if re.search(r"\bαύριο\b|\bαυριο\b|\btomorrow\b", t):
        event_date, matched_day = date.today() + timedelta(days=1), "αύριο"
    elif re.search(r"\bσήμερα\b|\bσημερα\b|\btoday\b", t):
        event_date, matched_day = date.today(), "σήμερα"
    else:
        for day_word, idx in _DAY_MAP.items():
            if day_word in t:
                event_date, matched_day = _next_weekday(idx), day_word
                break

    if event_date is None:
        return None

    # Clean up title
    title = t
    for kw in ["βάλε", "βαλε", "προσθήκη", "add", "create", "νέο event", matched_day or ""]:
        title = title.replace(kw, "")
    title = re.sub(r"(?:στις?|at)\s+\d{1,2}(?::\d{2})?", "", title)
    for word in _TIME_WORDS:
        title = title.replace(word, "")
    title = re.sub(r"\s+", " ", title).strip().title() or "Event"

    return title, datetime(event_date.year, event_date.month, event_date.day, hour, minute)
