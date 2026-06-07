"""Budget skill — reads Vibe-Budgeting SQLite directly."""

import os
import sqlite3
from datetime import date

BUDGET_DB = os.environ.get(
    "BUDGET_DB_PATH",
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "Vibe-Budgeting", "database.db"),
)


def _conn():
    path = os.path.abspath(BUDGET_DB)
    if not os.path.exists(path):
        return None
    conn = sqlite3.connect(path, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def get_balance_summary() -> str:
    conn = _conn()
    if not conn:
        return "Η βάση δεδομένων budget δεν είναι διαθέσιμη."
    try:
        row = conn.execute(
            """SELECT
                (SELECT COALESCE(SUM(opening_balance),0) FROM accounts WHERE user_id=1)
                + (SELECT COALESCE(SUM(amount),0) FROM income_entries WHERE user_id=1)
                + (SELECT COALESCE(SUM(amount),0) FROM expenses WHERE user_id=1)
                AS total"""
        ).fetchone()
        total = float(row["total"])
        today = date.today()
        m0 = f"{today.year:04d}-{today.month:02d}-01"
        m1 = f"{today.year:04d}-{today.month + 1:02d}-01" if today.month < 12 else f"{today.year+1:04d}-01-01"
        exp = conn.execute(
            "SELECT COALESCE(SUM(amount),0) as s FROM expenses WHERE user_id=1 AND spent_at>=? AND spent_at<?",
            (m0, m1)
        ).fetchone()["s"]
        return f"Το συνολικό σου υπόλοιπο είναι {total:.2f} ευρώ. Αυτόν τον μήνα έχεις ξοδέψει {abs(float(exp)):.2f} ευρώ."
    except Exception as e:
        return f"Σφάλμα ανάγνωσης budget: {e}"
    finally:
        conn.close()
