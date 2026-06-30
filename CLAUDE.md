# Nova Assistant — Claude Code Guide

## Project overview

Nova is a Claude-native personal AI assistant (voice + web UI) built on the Anthropic API.
The backend (Python/FastAPI) uses Claude native tool use as its brain. External "feature apps"
connect via MCP. The frontend (Next.js) serves as a dashboard + voice interface, deployable as a PWA.

## Stack

- **Frontend**: `ui/` — Next.js 16 App Router + TypeScript + Tailwind v4 + shadcn/ui + Zustand
- **Backend**: `backend/` — Python/FastAPI + WebSocket (port 8765)
- **Brain**: `backend/skills/nova_brain.py` — Claude API + native tool_use agent loop
- **Voice**: `backend/voice/` — wake word → STT → brain → TTS pipeline

## How to run (dev)

```bash
# Backend
cd backend && source .venv/bin/activate && uvicorn main:app --port 8765 --reload

# Frontend
cd ui && npm run dev   # → http://localhost:3000
```

## Feature project registry

External apps that connect to Nova via MCP are tracked in `.claude/projects.json`.
Each entry maps a feature name to its local path, git repo, and production MCP URL.

## Skills

### /sync-feature <name>
Check and sync a feature repo before making any changes to it.

Steps:
1. Read `.claude/projects.json` to find the project's `local_path`
2. Run `git -C <local_path> fetch`
3. Run `git -C <local_path> status` — report branch, last commit, dirty files
4. If behind origin: run `git -C <local_path> pull` and report
5. If there are uncommitted changes: warn and ask the user how to proceed
6. Only report success when the repo is clean and up to date

### /sync-all
Run `/sync-feature` for every project with `"status": "active"` in `.claude/projects.json`.

### /feature-status
Show a table of all projects from `.claude/projects.json`:
- git sync status (clean / dirty / behind)
- MCP registration status (registered / not yet)
- overall status field

Steps:
1. Read `.claude/projects.json`
2. For each project, run `git -C <local_path> status --short` and `git -C <local_path> log -1 --format="%h %s"`
3. Print a summary table

### /scaffold-mcp <name>
Generate the MCP server boilerplate for an existing app so it can be registered with Nova.

Steps:
1. Read `.claude/projects.json` to find the project path
2. Determine the app's framework (Next.js / FastAPI / other) by reading its package.json or requirements
3. Create `<local_path>/app/mcp/route.ts` (Next.js) or `<local_path>/mcp_server.py` (FastAPI)
   with: tool listing endpoint, tool call endpoint, auth header check (X-Nova-Token)
4. Add a placeholder tool definition based on the app's name
5. Update `.claude/projects.json` with the local MCP URL
6. Print next steps: deploy the app, add prod URL, register with Nova

### /check-services
Ping all MCP endpoints that have a non-null `mcp_url_prod` in `.claude/projects.json`.

Steps:
1. Read `.claude/projects.json`
2. For each service with a prod URL, run a curl health check
3. Report: up / down / unreachable for each

## Key files

| File | Purpose |
|------|---------|
| `backend/skills/nova_brain.py` | Claude agent loop — TOOLS definitions + executor |
| `backend/voice/pipeline.py` | Voice orchestrator (STT → brain → TTS) |
| `backend/main.py` | FastAPI app, WebSocket, calendar/budget REST endpoints |
| `backend/skills/calendar_skill.py` | iCloud CalDAV integration |
| `backend/skills/budget_skill.py` | Budget SQLite reader (temporary — will become MCP) |
| `.claude/projects.json` | Feature app registry |
| `ui/src/lib/store.ts` | Zustand global state + WebSocket listener |

## Adding a new tool to Nova's brain

1. Add a tool schema to `TOOLS` list in `backend/skills/nova_brain.py`
2. Add a `case "tool_name":` handler in `_execute_tool()`
3. No changes needed anywhere else — Claude will start using the tool automatically
