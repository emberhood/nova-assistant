"""
User profiles for Nova multi-user support.
Reads from environment variables — set them in .env
"""
import os

USERS = {
    "owner": {
        "name": "You",
        "short": "Me",
        "apple_id":          os.getenv("OWNER_APPLE_ID", ""),
        "apple_app_password": os.getenv("OWNER_APPLE_APP_PASSWORD", ""),
        "budget_db":          os.getenv("BUDGET_DB_PATH", ""),
        "budget_user_id":     1,
        "voice_profile":      "voice_profile_owner.npy",
        "theme":              "owner",
    },
    "andriana": {
        "name": "Andriana",
        "short": "A",
        "apple_id":          os.getenv("ANDRIANA_APPLE_ID", ""),
        "apple_app_password": os.getenv("ANDRIANA_APPLE_APP_PASSWORD", ""),
        "budget_db":          os.getenv("ANDRIANA_BUDGET_DB_PATH", ""),
        "budget_user_id":     1,
        "voice_profile":      "voice_profile_andriana.npy",
        "theme":              "andriana",
    },
}

SHARED_CALENDAR_NAME = os.getenv("SHARED_CALENDAR_NAME", "Shared")


def get_user(user_id: str) -> dict | None:
    return USERS.get(user_id)


def get_calendar_creds(user_id: str) -> tuple[str, str]:
    """Return (apple_id, app_password) for the given user."""
    u = USERS.get(user_id, USERS["owner"])
    return u["apple_id"], u["apple_app_password"]
