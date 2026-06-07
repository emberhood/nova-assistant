"""
Local intent classifier — zero tokens, zero API calls.
Pattern-match → action. Claude Haiku called only for unrecognised intents (Phase 3).
"""

import re
from dataclasses import dataclass
from typing import Callable


@dataclass
class Intent:
    name: str
    slots: dict


_OPEN_APP_PATTERNS = [
    r"(?:άνοιξε?|open|ανοιγε?|ξεκίνα|launch)\s+(.+)",
]

_CLOSE_APP_PATTERNS = [
    r"(?:κλείσε?|close|κλεινε?)\s+(.+)",
]

_WHAT_TIME_PATTERNS = [
    r"τι (?:ωρα|ώρα)",
    r"what(?:'s| is) the time",
    r"ώρα",
]

_BALANCE_PATTERNS = [
    r"(?:ποσα|πόσα|πόσο|ποσο) (?:εχω|έχω|μου έχουν|μου εχουν)",
    r"(?:υπόλοιπο|υπολοιπο|balance|balance μου)",
    r"what(?:'s| is) my balance",
]

_EXPENSE_PATTERNS = [
    r"(?:ξόδεψα|εξοδο|εξοδα|πλήρωσα|πληρωσα|expense|ξοδεψα)\s+(.+)",
]

_STOP_PATTERNS = [
    r"(?:σταμάτα|σταματα|stop|exit|ησυχία|ησυχια|quiet)",
]

_CALENDAR_PATTERNS = [
    r"(?:τι έχω|τι εχω|τι έχεις|τι εχεις|calendar|ημερολόγιο|ημερολογιο|agenda|events?|πρόγραμμα|προγραμμα)",
]

# Date references for calendar queries
_DATE_TOMORROW   = r"(?:αύριο|αυριο|tomorrow)"
_DATE_TODAY      = r"(?:σήμερα|σημερα|today)"
_DATE_WEEK       = r"(?:εβδομάδα|εβδομαδα|week|επόμενες?\s+\d+\s+μέρες?)"
_DATE_DAY_NAMED  = r"(?:δευτέρα|δευτερα|τρίτη|τριτη|τετάρτη|τεταρτη|πέμπτη|πεμπτη|παρασκευή|παρασκευη|σάββατο|σαββατο|κυριακή|κυριακη|monday|tuesday|wednesday|thursday|friday|saturday|sunday)"

_ADD_EVENT_PATTERNS = [
    # Any of these verbs + anything → treat as add_event, let Groq parse details
    r"(?:βάλε|βαλε|βάλτε|βαλτε|πρόσθεσε|προσθεσε|προσθήκη|προσθηκη|add|create|νέο\s+event|νεο\s+event|φτιάξε|φτιαξε)\s+.{2,}",
    # "κλείσε ραντεβού" — book/schedule
    r"(?:κλείσε|κλεισε|κράτησε|κρατησε|βόλεψε|βολεψε)\s+(?:ραντεβού|ραντεβου|appointment|συνάντηση|συναντηση|τραπέζι|τραπεζι)",
]

_LOCK_PATTERNS = [
    r"(?:κλείδωσε?|κλειδωσε?|lock)",
]

# Tab navigation
_NAV_VERB = r"(?:δείξε?|πάμε|παμε|άνοιξε?|ανοιξε?|πήγαινε?|πηγαινε?|γύρισε?|γυρισε?|γύρνα|γυρνα|βάλε?|πέρνα|περνα|αλλαξε?|άλλαξε?|πίσω|πισω|back)"
# .*? after the verb catches anything in between (π.χ. "πήγαινέ με στο", "γύρνα με πίσω στο")
_NAV_CALENDAR_PATTERNS = [
    rf"{_NAV_VERB}.*?(?:calendar|καλέντ|καλεντ|ημερολόγ|ημερολογ)",
]
_NAV_BUDGET_PATTERNS = [
    rf"{_NAV_VERB}.*?(?:budget|προϋπολογισμ|εξοδ|έξοδ|χρήματ|χρηματ|οικονομικ)",
]
_NAV_DASHBOARD_PATTERNS = [
    rf"{_NAV_VERB}.*?(?:dashboard|αρχικ|κεντρικ|home)",
]

# User switching
_USER_OWNER_MARKERS = r"(?:δικό\s+μου|δικα\s+μου|εμένα|εμενα|\bμου\b|εγω\b)"
_USER_ANDRIANA_MARKERS = r"(?:Ανδριαν|ανδριαν|δικό\s+της|δικα\s+της|δική\s+της)"
_USER_SHARED_MARKERS = r"(?:κοιν|shared|μας\b|μαζί|μαζι)"

_VOLUME_PATTERNS = [
    r"(?:αύξησε?|αυξησε?|raise|increase|volume up|ηχος)\s*(?:volume|ήχο|ηχο)?",
    r"(?:μείωσε?|μειωσε?|lower|decrease|volume down)\s*(?:volume|ήχο|ηχο)?",
    r"(?:σίγαση|σιγαση|mute)",
]


def _match(patterns: list[str], text: str) -> re.Match | None:
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m
    return None


def _detect_user(text: str) -> str:
    """Detect which user the command refers to. Defaults to 'owner'."""
    if re.search(_USER_ANDRIANA_MARKERS, text, re.IGNORECASE):
        return "andriana"
    if re.search(_USER_SHARED_MARKERS, text, re.IGNORECASE):
        return "shared"
    return "owner"


def classify(text: str) -> Intent:
    t = text.strip().lower()

    if m := _match(_OPEN_APP_PATTERNS, t):
        return Intent("open_app", {"app": m.group(1).strip()})

    if m := _match(_CLOSE_APP_PATTERNS, t):
        return Intent("close_app", {"app": m.group(1).strip()})

    if _match(_WHAT_TIME_PATTERNS, t):
        return Intent("what_time", {})

    if _match(_BALANCE_PATTERNS, t):
        return Intent("get_balance", {"user": _detect_user(t)})

    if m := _match(_EXPENSE_PATTERNS, t):
        return Intent("add_expense", {"raw": m.group(1).strip()})

    if _match(_STOP_PATTERNS, t):
        return Intent("stop", {})

    if _match(_NAV_CALENDAR_PATTERNS, t):
        return Intent("nav_tab", {"tab": "calendar"})

    if _match(_NAV_BUDGET_PATTERNS, t):
        return Intent("nav_tab", {"tab": "budget"})

    if _match(_NAV_DASHBOARD_PATTERNS, t):
        return Intent("nav_tab", {"tab": "dashboard"})

    # "δείξε μου Ανδριανα" / "άλλαξε σε Ανδριανα"
    _SET_USER_PATTERNS = [r"(?:άλλαξε|αλλαξε|πάμε|παμε|δείξε|δεξε)\s+(?:σε\s+|στην?\s+|του\s+)?(?:Ανδριαν|ανδριαν|owner|shared|κοιν)"]
    if _match(_SET_USER_PATTERNS, t):
        return Intent("set_user", {"user": _detect_user(t) if _detect_user(t) != "owner" else ("andriana" if re.search(r"ανδριαν", t, re.IGNORECASE) else "owner")})

    if _match(_ADD_EVENT_PATTERNS, t):
        return Intent("add_event", {"text": text, "user": _detect_user(t)})

    if _match(_CALENDAR_PATTERNS, t):
        # Extract date reference from the query
        if re.search(_DATE_TOMORROW, t, re.IGNORECASE):
            date_ref = "tomorrow"
        elif re.search(_DATE_TODAY, t, re.IGNORECASE):
            date_ref = "today"
        elif re.search(_DATE_WEEK, t, re.IGNORECASE):
            date_ref = "week"
        elif m2 := re.search(_DATE_DAY_NAMED, t, re.IGNORECASE):
            date_ref = m2.group(0).lower()
        else:
            date_ref = "today"
        return Intent("get_calendar", {"user": _detect_user(t), "date_ref": date_ref})

    if _match(_LOCK_PATTERNS, t):
        return Intent("lock_pc", {})

    if _match(_VOLUME_PATTERNS, t):
        if re.search(r"(?:αύξ|αυξ|raise|increase|up)", t):
            return Intent("volume_up", {})
        if re.search(r"(?:μείω|μειω|lower|decrease|down)", t):
            return Intent("volume_down", {})
        return Intent("mute", {})

    return Intent("unknown", {"text": text})
