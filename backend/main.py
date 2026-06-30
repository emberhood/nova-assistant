from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import os
import json
import calendar
import asyncio
from datetime import datetime, date
from typing import Optional
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

app = FastAPI(title="Nova Backend")

_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:4173",
    "https://nova-backend-bmsm.onrender.com",
    # Vercel frontend URL goes here once deployed
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

BUDGET_DB = os.environ.get(
    "BUDGET_DB_PATH",
    os.path.join(os.path.dirname(__file__), "..", "..", "Vibe-Budgeting", "database.db"),
)

connected_clients: list[WebSocket] = []


# ── WebSocket broadcast ────────────────────────────────────────────────────────

def broadcast_sync(msg: dict):
    """Called from voice pipeline threads to push state to all UI clients."""
    for ws in list(connected_clients):
        asyncio.run_coroutine_threadsafe(
            ws.send_text(json.dumps(msg)),
            _loop,
        )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            # manual trigger from UI (for testing without mic)
            if msg.get("type") == "trigger":
                from voice import pipeline as vp
                import threading
                threading.Thread(target=vp._on_wake_word, daemon=True).start()
    except WebSocketDisconnect:
        if websocket in connected_clients:
            connected_clients.remove(websocket)


# ── Startup ────────────────────────────────────────────────────────────────────

_loop: asyncio.AbstractEventLoop | None = None
_pipeline = None


@app.on_event("startup")
async def startup():
    global _loop, _pipeline
    _loop = asyncio.get_running_loop()

    # Local voice pipeline (wake word + mic) only runs when LOCAL_VOICE=true.
    # On Railway/cloud the browser sends audio via WebSocket instead (Phase 5).
    if os.getenv("LOCAL_VOICE", "").lower() == "true":
        try:
            from voice import pipeline as vp
            vp.set_broadcast(broadcast_sync)
            _pipeline = vp.NovaPipeline()
            _pipeline.start()
        except ImportError as e:
            print(f"[Startup] Voice pipeline deps not installed yet: {e}")
        except Exception as e:
            print(f"[Startup] Voice pipeline error: {e}")
    else:
        print("[Startup] Local voice pipeline disabled (set LOCAL_VOICE=true to enable)")

    try:
        from skills import telegram_skill
        telegram_skill.set_broadcast(broadcast_sync)
        telegram_skill.start_bot()
    except Exception as e:
        print(f"[Startup] Telegram bot error: {e}")


@app.on_event("shutdown")
async def shutdown():
    if _pipeline:
        _pipeline.stop()


# ── Status ─────────────────────────────────────────────────────────────────────

@app.get("/api/status")
def status():
    return {"status": "online", "timestamp": datetime.now().isoformat()}


# ── Calendar ───────────────────────────────────────────────────────────────────

@app.get("/api/calendar/month")
def get_calendar_month(year: Optional[int] = None, month: Optional[int] = None, user: str = "owner"):
    today = date.today()
    y = year or today.year
    m = month or today.month

    cal = calendar.Calendar(firstweekday=0)
    weeks = cal.monthdatescalendar(y, m)

    weeks_out = []
    for week in weeks:
        days = []
        for d in week:
            days.append({
                "date": d.isoformat(),
                "day": d.day,
                "month": d.month,
                "year": d.year,
                "isCurrentMonth": d.month == m,
                "isToday": d == today,
                "isWeekend": d.weekday() >= 5,
            })
        weeks_out.append(days)

    # Apple Calendar events overlay (optional — works only if CalDAV configured)
    apple_events: dict[str, list] = {}
    try:
        from skills.calendar_skill import get_month_events
        ev_list = get_month_events(user_id=user, year=y, month=m)
        print(f"[Calendar] got {len(ev_list)} events for {user} {y}/{m}")
        for ev in ev_list:
            apple_events.setdefault(ev["date"], []).append({"title": ev["title"], "time": ev["time"]})
    except Exception as e:
        print(f"[Calendar] ERROR loading events: {e}")

    # Attach events to each day
    for week in weeks_out:
        for d in week:
            d["events"] = apple_events.get(d["date"], [])

    return {
        "year": y,
        "month": m,
        "monthName": calendar.month_name[m],
        "today": today.isoformat(),
        "weeks": weeks_out,
        "user": user,
    }


# ── Budget ─────────────────────────────────────────────────────────────────────

def _budget_conn(user: str = "owner"):
    from config.user_config import USERS
    u = USERS.get(user, USERS["owner"])
    db_path = u["budget_db"] or BUDGET_DB
    path = os.path.abspath(db_path)
    if not os.path.exists(path):
        return None, 1
    conn = sqlite3.connect(path, timeout=5.0)
    conn.row_factory = sqlite3.Row
    return conn, u["budget_user_id"]


@app.get("/api/users")
def get_users():
    from config.user_config import USERS, SHARED_CALENDAR_NAME
    return {
        "users": [
            {"id": uid, "name": u["name"], "short": u["short"], "theme": u["theme"]}
            for uid, u in USERS.items()
        ],
        "shared_calendar": SHARED_CALENDAR_NAME,
    }


@app.get("/api/budget/summary")
def budget_summary(user: str = "owner"):
    conn, uid = _budget_conn(user)
    if conn is None:
        return {"available": False}

    today = date.today()
    month_start = f"{today.year:04d}-{today.month:02d}-01"
    nm = today.month + 1
    ny = today.year
    if nm > 12:
        nm = 1; ny += 1
    month_end = f"{ny:04d}-{nm:02d}-01"

    try:
        income_month = conn.execute(
            "SELECT COALESCE(SUM(amount),0) as total FROM income_entries WHERE user_id=? AND received_at>=? AND received_at<?",
            (uid, month_start, month_end),
        ).fetchone()["total"]

        expense_month = conn.execute(
            "SELECT COALESCE(SUM(amount),0) as total FROM expenses WHERE user_id=? AND spent_at>=? AND spent_at<?",
            (uid, month_start, month_end),
        ).fetchone()["total"]

        recent = conn.execute(
            """SELECT e.notes, e.amount, e.spent_at, c.name as category
               FROM expenses e LEFT JOIN categories c ON c.id=e.category_id
               WHERE e.user_id=? ORDER BY e.spent_at DESC, e.id DESC LIMIT 5""",
            (uid,)
        ).fetchall()

        balance_row = conn.execute(
            """SELECT
                (SELECT COALESCE(SUM(opening_balance),0) FROM accounts WHERE user_id=?)
                + (SELECT COALESCE(SUM(amount),0) FROM income_entries WHERE user_id=?)
                + (SELECT COALESCE(SUM(amount),0) FROM expenses WHERE user_id=?)
                AS total_balance""",
            (uid, uid, uid)
        ).fetchone()

        accounts = conn.execute(
            "SELECT name, opening_balance FROM accounts WHERE user_id=?", (uid,)
        ).fetchall()

        return {
            "available": True,
            "totalBalance": float(balance_row["total_balance"]),
            "monthIncome": float(income_month),
            "monthExpenses": float(expense_month),
            "accounts": [{"name": r["name"], "balance": float(r["opening_balance"])} for r in accounts],
            "recentExpenses": [
                {"notes": r["notes"], "amount": float(r["amount"]), "date": r["spent_at"], "category": r["category"]}
                for r in recent
            ],
        }
    except Exception as e:
        return {"available": False, "error": str(e)}
    finally:
        conn.close()


# ── Calendar debug ─────────────────────────────────────────────────────────────

@app.get("/api/calendar/debug")
def calendar_debug(user: str = "owner"):
    """List all calendars available for a user — helps find the right calendar name."""
    try:
        from skills.calendar_skill import _get_client_principal
        principal, err = _get_client_principal(user)
        if err:
            return {"error": err}
        calendars = principal.calendars()
        result = []
        for cal in calendars:
            try:
                import caldav.lib.dav as dav
                props = cal.get_properties([caldav.lib.dav.DisplayName()])
                name = props.get("{DAV:}displayname", "(no name)")
            except Exception:
                name = "(unknown)"
            result.append({"name": name, "url": str(cal.url)})
        return {"calendars": result, "count": len(result)}
    except Exception as e:
        return {"error": str(e)}


# ── Voice trigger (for testing) ────────────────────────────────────────────────

@app.post("/api/voice/trigger")
async def voice_trigger():
    """Manually trigger voice pipeline (for testing without mic/wake-word)."""
    import threading
    try:
        from voice import pipeline as vp
        threading.Thread(target=vp._on_wake_word, daemon=True).start()
        return {"status": "triggered"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ── Speaker enrollment ──────────────────────────────────────────────────────────

@app.post("/api/voice/enroll")
async def voice_enroll():
    """
    Record 12 seconds of audio and save as the owner voice profile.
    Call this once to enroll. After that, only your voice triggers commands.
    """
    import threading
    import numpy as np

    result = {"status": "recording"}

    def _do_enroll():
        try:
            from voice.recorder import record_until_silence
            from voice import speaker_verify
            import sounddevice as sd

            broadcast_sync({"type": "nova_state", "payload": "listening", "text": "Enrolling voice — speak for 12 seconds..."})

            # Record a fixed 12 seconds for enrollment (more data = better profile)
            sample_rate = 16000
            duration = 12
            audio = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype="int16")
            sd.wait()
            audio_flat = audio.flatten()

            msg = speaker_verify.enroll_voice(audio_flat, sample_rate)
            print(f"[Enroll] {msg}")
            broadcast_sync({"type": "nova_state", "payload": "idle", "text": msg})
        except Exception as e:
            broadcast_sync({"type": "nova_state", "payload": "idle", "text": f"Enrollment error: {e}"})

    threading.Thread(target=_do_enroll, daemon=True).start()
    return {"status": "started", "message": "Recording 12 seconds — speak normally for best results"}


@app.get("/api/voice/enroll/status")
def enroll_status():
    from voice import speaker_verify
    return {
        "enrolled": speaker_verify.is_enrolled(),
        "available": speaker_verify.is_available(),
        "threshold": speaker_verify.THRESHOLD,
    }
