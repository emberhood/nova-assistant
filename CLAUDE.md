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

### /connect-feature <name>
Full onboarding flow for a new feature app — scaffolds MCP, writes CLAUDE.md, generates token,
sets env vars. Run this once when connecting a new app to Nova.

Prerequisites:
- App already cloned to `local_path` (add entry to `.claude/projects.json` first)
- `mcp_url_prod` set in `projects.json` if you want `--render` to work (after first deploy)

Steps:
1. Read `.claude/projects.json` → get `local_path`, `repo`, `mcp_url_prod`
2. Sync check: `git -C <local_path> fetch && git -C <local_path> status`
   — if dirty or behind, warn and ask how to proceed
3. Detect framework: check `package.json` for `"next"` dep (Next.js) or `requirements.txt` (FastAPI)
4. Scaffold MCP route if it doesn't already exist:
   - Next.js: copy `backend/scripts/templates/mcp_nextjs.ts` → `<local_path>/app/api/mcp/route.ts`
   - FastAPI: copy `backend/scripts/templates/mcp_fastapi.py` → `<local_path>/mcp_server.py`
   - Replace `{{NAME}}` placeholder with the feature name in the file
5. Write `<local_path>/CLAUDE.md` from `backend/scripts/templates/feature_claude_md.md`
   — replace `{{NAME}}` and `{{NAME_UPPER}}` — SKIP if CLAUDE.md already has real content
6. Run: `python3 backend/scripts/connect_feature.py <name>`
   — generates token, saves to `backend/.env`, prints env vars to set
7. Set token on feature app deployment:
   - Vercel: `printf '<TOKEN>' | vercel --cwd <local_path> env add NOVA_MCP_TOKEN production`
   - Other: print the value and instruct user to set it manually
8. If `mcp_url_prod` is set: run `python3 backend/scripts/connect_feature.py <name> --render`
   — pushes NOVA_MCP_<NAME>_URL + NOVA_MCP_<NAME>_TOKEN to Render via API
   — requires RENDER_API_KEY + RENDER_SERVICE_ID in `backend/.env`
9. Commit and push the feature app's new/changed files (MCP route + CLAUDE.md)
10. Print checklist:
    - [ ] Deploy feature app on Vercel/Render so MCP route is live
    - [ ] Run `/check-services` to verify Nova can reach it
    - [ ] Restart Nova backend on Render to load new env vars

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
| `backend/scripts/connect_feature.py` | Token generation + Render API env var push |
| `backend/scripts/templates/` | MCP boilerplate (Next.js, FastAPI) + CLAUDE.md template |

## Adding a new tool to Nova's brain

1. Add a tool schema to `TOOLS` list in `backend/skills/nova_brain.py`
2. Add a `case "tool_name":` handler in `_execute_tool()`
3. No changes needed anywhere else — Claude will start using the tool automatically

## Working on feature projects (vromomarket, budget, etc.)

Each feature app lives in `/home/kontis/Projects/<name>/` and has its own CLAUDE.md explaining
the MCP contract. Claude has full read/write/bash access to the entire `/home/kontis/Projects/`
tree without per-command approval (set in `.claude/settings.local.json`).

**Pattern for feature work:**
- Small changes (add a tool, fix a bug): work directly in the feature's directory
- Larger refactors or exploration: spawn a subagent scoped to that project

```
Agent({
  description: "vromomarket feature work",
  prompt: "Working in /home/kontis/Projects/vromomarket. Read CLAUDE.md first for MCP context. Task: <description>"
})
```

**When a new feature is connected to Nova:**
1. Add entry to `.claude/projects.json` with `local_path`, `repo`, `status: "active"`
2. Run `/connect-feature <name>` — handles scaffolding, token generation, and env vars
3. After first deploy: set `mcp_url_prod` in `projects.json`, then rerun `python3 backend/scripts/connect_feature.py <name> --render`
4. Run `/check-services` to verify the connection

**One-time Render setup** (needed for `--render` flag to work):
Add to `backend/.env`:
```
RENDER_API_KEY=rnd_xxxx        # Render → Account → API Keys
RENDER_SERVICE_ID=srv-xxxx     # Render → nova-backend → Settings → Service ID
```
