"""
Conversational AI via Groq (llama-3.3-70b).
Handles two cases:
  1. Pure conversation ("ευχαριστώ", ερωτήσεις, κτλ.)
  2. Natural-language confirmation after an action ("έφτιαξα event, πες το φυσικά")

Keeps a short in-session conversation history so replies feel continuous.
"""

import os
from collections import deque

_SYSTEM = """Είσαι ο Jarvis, ο προσωπικός AI βοηθός των Mario και Andriana.
Τρέχεις σε PC και έχεις πρόσβαση στο ημερολόγιο, τον προϋπολογισμό και τον υπολογιστή τους.

Χαρακτήρας:
- Μιλάς ΠΑΝΤΑ Ελληνικά, φυσικά και ζεστά — σαν έξυπνος φίλος, όχι ρομπότ
- Θυμάσαι τι είπε ο χρήστης νωρίτερα στη συνομιλία
- Για απλές επιβεβαιώσεις μπορείς να είσαι σύντομος και να προσθέσεις κάτι ανθρώπινο
- Για ερωτήσεις δίνεις χρήσιμη, συνοπτική απάντηση
- ΜΗΝ ξεκινάς πάντα με "Βεβαίως" ή "Ορίστε" — ποίκιλε
- ΜΗΝ επαναλαμβάνεις αυτολεξεί την ενέργεια — πες το διαφορετικά
- Μέγιστο 2 προτάσεις"""

# In-session conversation history (last 10 turns)
_history: deque = deque(maxlen=10)


def reset_history():
    _history.clear()


def ask_haiku(user_text: str, action_context: str | None = None) -> str:
    """
    action_context: description of what just happened,
    e.g. "Άνοιξα το tab ημερολόγιο" or "Έφτιαξα event 'Γιατρός' για Τρίτη στις 10"
    """
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    if groq_key:
        result = _ask_groq(user_text, action_context, groq_key)
        if result:
            _history.append({"role": "user",     "content": user_text})
            _history.append({"role": "assistant", "content": result})
            return result

    # Offline fallbacks
    t = user_text.lower().strip()
    if any(w in t for w in ["ευχαριστ", "thank"]):
        return "Παρακαλώ, πάντα στη διάθεσή σου!"
    if any(w in t for w in ["καλημέρα", "καλησπέρα", "γεια", "hello"]):
        return "Γεια! Τι κάνουμε σήμερα;"
    if any(w in t for w in ["μπράβο", "τέλεια", "ωραία", "super"]):
        return "Χαίρομαι που βοήθησα!"
    if any(w in t for w in ["συγγνώμη", "sorry"]):
        return "Κανένα πρόβλημα!"
    return "Δεν κατάλαβα καλά — πες μου ξανά;"


def _ask_groq(user_text: str, action_context: str | None, api_key: str) -> str | None:
    try:
        from groq import Groq
    except ImportError:
        print("[Groq/chat] groq library not installed — run: pip install groq")
        return None

    messages = [{"role": "system", "content": _SYSTEM}]
    messages.extend(list(_history))

    if action_context:
        content = (
            f"[Ενέργεια που εκτελέστηκε: {action_context}]\n"
            f"Χρήστης είπε: \"{user_text}\"\n"
            "Επιβεβαίωσε φυσικά αυτό που έγινε σε 1-2 προτάσεις."
        )
    else:
        content = user_text

    messages.append({"role": "user", "content": content})

    try:
        client = Groq(api_key=api_key)
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=100,
            temperature=0.7,
        )
        text = resp.choices[0].message.content.strip()
        print(f"[Groq/chat] '{text}'")
        return text
    except Exception as e:
        print(f"[Groq/chat] error: {e}")
        return None
