#!/usr/bin/env python3
"""
connect_feature.py — automates Nova MCP feature onboarding.

Usage:
  python3 backend/scripts/connect_feature.py <name>           # generate/show token + env vars
  python3 backend/scripts/connect_feature.py <name> --render  # also push to Render API

Run from the nova-assistant root directory.
"""

import json
import os
import secrets
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PROJECTS_FILE = ROOT / ".claude" / "projects.json"
BACKEND_ENV = ROOT / "backend" / ".env"


# ── .env helpers ──────────────────────────────────────────────────────────────

def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip()
    return env


def save_env_key(path: Path, key: str, value: str):
    """Add or update a single key=value in a .env file."""
    lines = path.read_text().splitlines() if path.exists() else []
    found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}=") or line.startswith(f"{key} ="):
            lines[i] = f"{key}={value}"
            found = True
            break
    if not found:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append(f"{key}={value}")
    path.write_text("\n".join(lines) + "\n")


# ── projects.json helpers ─────────────────────────────────────────────────────

def load_projects() -> dict:
    with open(PROJECTS_FILE) as f:
        return json.load(f)


def save_projects(data: dict):
    with open(PROJECTS_FILE, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


# ── Render API ────────────────────────────────────────────────────────────────

def render_request(method: str, path: str, api_key: str, body=None):
    url = f"https://api.render.com/v1{path}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"Render API error {e.code}: {e.read().decode()}")
        sys.exit(1)


def push_to_render(name: str, url: str, token: str, api_key: str, service_id: str):
    url_key = f"NOVA_MCP_{name.upper()}_URL"
    token_key = f"NOVA_MCP_{name.upper()}_TOKEN"

    # GET current env vars
    current = render_request("GET", f"/services/{service_id}/env-vars", api_key)
    # Render returns [{"envVar": {"key": "...", "value": "..."}}, ...]
    env_vars = [item["envVar"] for item in current]

    # Remove stale entries for this feature
    env_vars = [e for e in env_vars if e["key"] not in (url_key, token_key)]
    env_vars.append({"key": url_key, "value": url})
    env_vars.append({"key": token_key, "value": token})

    render_request("PUT", f"/services/{service_id}/env-vars", api_key, env_vars)
    print(f"  ✓ Render: {url_key}={url}")
    print(f"  ✓ Render: {token_key}=<token>")
    print()
    print("Render will apply the new env vars on the next deploy.")
    print("Trigger a deploy in the Render dashboard, or:")
    print(f"  curl -X POST https://api.render.com/v1/services/{service_id}/deploys \\")
    print(f"    -H 'Authorization: Bearer $RENDER_API_KEY' -H 'Content-Type: application/json' -d '{{}}'")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    name = sys.argv[1]
    do_render = "--render" in sys.argv

    # Load project registry
    projects = load_projects()
    if name not in projects:
        print(f"ERROR: '{name}' not in .claude/projects.json")
        print("Add it first with at least: local_path, repo, status")
        sys.exit(1)

    project = projects[name]
    local_path = project.get("local_path", "")
    mcp_url_prod = project.get("mcp_url_prod", "")

    # Load backend .env for existing token + Render creds
    env = load_env(BACKEND_ENV)
    env.update(os.environ)

    token_key = f"NOVA_MCP_{name.upper()}_TOKEN"
    url_key = f"NOVA_MCP_{name.upper()}_URL"

    # Generate or reuse token
    token = env.get(token_key)
    if token:
        print(f"Reusing existing token from backend/.env ({token_key})")
    else:
        token = secrets.token_urlsafe(32)
        save_env_key(BACKEND_ENV, token_key, token)
        print(f"Generated new token → saved to backend/.env as {token_key}")

    # Ensure URL is in .env too
    if mcp_url_prod and not env.get(url_key):
        save_env_key(BACKEND_ENV, url_key, mcp_url_prod)
        print(f"Saved {url_key}={mcp_url_prod} to backend/.env")

    # Mark project active
    if project.get("status") != "active":
        projects[name]["status"] = "active"
        save_projects(projects)
        print(f"Marked {name} as active in projects.json")

    print()
    print("=" * 60)
    print(f"  FEATURE: {name}")
    print("=" * 60)
    print()
    print("1. Set this on the FEATURE APP deployment (e.g. Vercel):")
    print(f"   NOVA_MCP_TOKEN={token}")
    print()

    if local_path:
        print("   Vercel CLI shortcut (run from nova-assistant root):")
        print(f"   printf '{token}' | vercel --cwd {local_path} env add NOVA_MCP_TOKEN production")
        print()

    print("2. Set these on the NOVA BACKEND (Render):")
    print(f"   {url_key}={mcp_url_prod or '<set mcp_url_prod in projects.json first>'}")
    print(f"   {token_key}={token}")
    print()

    if do_render:
        if not mcp_url_prod:
            print("ERROR: mcp_url_prod not set in projects.json — cannot push to Render.")
            print("Set it first, then rerun with --render")
            sys.exit(1)

        api_key = env.get("RENDER_API_KEY", "")
        service_id = env.get("RENDER_SERVICE_ID", "")

        if not api_key or not service_id:
            print("ERROR: RENDER_API_KEY and RENDER_SERVICE_ID must be in backend/.env")
            print()
            print("Get them from:")
            print("  API key:    https://dashboard.render.com/u/settings#api-keys")
            print("  Service ID: Render dashboard → nova-backend → Settings → Service ID")
            sys.exit(1)

        print("Pushing to Render API...")
        push_to_render(name, mcp_url_prod, token, api_key, service_id)

    print("Next: deploy the feature app, then run /check-services to verify.")


if __name__ == "__main__":
    main()
