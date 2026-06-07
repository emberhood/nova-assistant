"""PC control actions — open/close apps, lock, volume.
Works on Linux (X11/Wayland) and Windows.
"""

import os
import subprocess
import sys

_IS_LINUX = sys.platform.startswith("linux")
_IS_WIN   = sys.platform == "win32"

# Friendly name → Linux command / Windows executable
APP_MAP_LINUX = {
    "chrome":              "google-chrome",
    "google chrome":       "google-chrome",
    "chromium":            "chromium-browser",
    "firefox":             "firefox",
    "code":                "code",
    "vscode":              "code",
    "visual studio code":  "code",
    "spotify":             "spotify",
    "discord":             "discord",
    "steam":               "steam",
    "terminal":            "x-terminal-emulator",
    "nautilus":            "nautilus",
    "files":               "nautilus",
    "calculator":          "gnome-calculator",
    "settings":            "gnome-control-center",
    "vlc":                 "vlc",
}

APP_MAP_WIN = {
    "chrome":              "chrome",
    "google chrome":       "chrome",
    "firefox":             "firefox",
    "edge":                "msedge",
    "notepad":             "notepad",
    "calculator":          "calc",
    "explorer":            "explorer",
    "file explorer":       "explorer",
    "code":                "code",
    "vscode":              "code",
    "visual studio code":  "code",
    "spotify":             "spotify",
    "discord":             "discord",
    "steam":               "steam",
    "task manager":        "taskmgr",
    "settings":            "ms-settings:",
    "cmd":                 "cmd",
    "terminal":            "wt",
    "powershell":          "powershell",
}

_ARTICLES = {"το", "τον", "την", "τα", "τους", "της", "τη", "ο", "η", "οι",
             "the", "a", "an"}


def _resolve_app(name: str) -> str:
    words = name.strip().lower().split()
    words = [w for w in words if w not in _ARTICLES]
    key = " ".join(words)
    app_map = APP_MAP_LINUX if _IS_LINUX else APP_MAP_WIN
    return app_map.get(key, words[0] if words else name)


def open_app(name: str) -> str:
    cmd = _resolve_app(name)
    try:
        if _IS_LINUX:
            subprocess.Popen([cmd], start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif cmd.startswith("ms-"):
            subprocess.Popen(["start", cmd], shell=True)
        else:
            subprocess.Popen(cmd, shell=True)
        return f"Ανοίγω {name}."
    except Exception:
        return f"Δεν μπόρεσα να ανοίξω το {name}."


def close_app(name: str) -> str:
    key = name.strip().lower()
    try:
        if _IS_LINUX:
            subprocess.run(["pkill", "-f", key], capture_output=True)
        else:
            proc_map = {
                "chrome": "chrome.exe", "firefox": "firefox.exe",
                "notepad": "notepad.exe", "spotify": "spotify.exe",
                "discord": "discord.exe",
            }
            proc = proc_map.get(key, f"{key}.exe")
            subprocess.run(["taskkill", "/F", "/IM", proc], capture_output=True)
        return f"Έκλεισα το {name}."
    except Exception:
        return f"Δεν μπόρεσα να κλείσω το {name}."


def lock_pc() -> str:
    try:
        if _IS_LINUX:
            # Works on most GNOME/KDE/Wayland setups
            result = subprocess.run(["loginctl", "lock-session"], capture_output=True)
            if result.returncode != 0:
                # Fallback for X11
                subprocess.Popen(["xdg-screensaver", "lock"])
        else:
            os.system("rundll32.exe user32.dll,LockWorkStation")
    except Exception:
        pass
    return "Κλειδώνω τον υπολογιστή."


def volume_up() -> str:
    try:
        if _IS_LINUX:
            subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+5%"],
                           capture_output=True)
        else:
            _win_volume_key(0xAF)
    except Exception:
        pass
    return "Αυξάνω την ένταση."


def volume_down() -> str:
    try:
        if _IS_LINUX:
            subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-5%"],
                           capture_output=True)
        else:
            _win_volume_key(0xAE)
    except Exception:
        pass
    return "Μειώνω την ένταση."


def mute() -> str:
    try:
        if _IS_LINUX:
            subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"],
                           capture_output=True)
        else:
            _win_volume_key(0xAD)
    except Exception:
        pass
    return "Σίγαση."


def _win_volume_key(vk: int):
    import ctypes
    KEYEVENTF_KEYUP = 0x0002
    ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
    ctypes.windll.user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)
