# Nova — Roadmap

## Why this project exists

Mario is a frontend-leaning web developer (Next.js/React/JS, some TS, some PHP/Drupal)
pivoting toward **AI engineering** after a layoff, with ~3 months to build a portfolio.
Nova is portfolio project #1: a Claude-native AI assistant demonstrating agents, tool use,
MCP, voice pipelines, and production-grade engineering — not just a chatbot wrapper.

---

## Architecture

```
Your Phone / Browser
  Next.js PWA (Vercel)
  push-to-talk → WebSocket
        │
Nova Backend (Railway / Fly.io)
  FastAPI + WebSocket
  ├── Voice pipeline: Whisper API (STT) → nova_brain → OpenAI TTS
  ├── nova_brain.py: Claude API + native tool_use agent loop
  │     Haiku (fast/cheap) ↔ Sonnet (complex reasoning)
  └── MCP Client Hub
        ├── Service registry (Postgres: name, url, token, enabled)
        ├── → vromomarket /mcp  (active)
        ├── → budget /mcp      (Phase 4b)
        └── → [new app] /mcp   ← one INSERT to add
        
Nova's Postgres (Neon)
  conversations, users, services (registry)

External apps (each owns its own DB):
  vromomarket  budget  [future apps]
  each exposes a /mcp route — Nova never touches their DB directly
```

**Adding a new app:** build it → deploy it → add `/mcp` route → one INSERT in services table. No Nova code changes.

---

## Completed

### Phase 0 — Identity & foundation ✅ (2026-06-07)
Renamed Jarvis → Nova across ~100 occurrences. Wake-word "Hey Jarvis" left for later
(requires custom wake-word model retraining). Config, docs, sanitization plan.

### Phase 0.5 — Frontend migration ✅ (2026-06-11)
`ui/` migrated from Vite + React + JS to **Next.js App Router + TypeScript +
Tailwind v4 + shadcn/ui + Zustand + react-three-fiber 3D orb**.
Three routes: `/` (Dashboard), `/calendar`, `/budget`.

### Phase 0.6 — Claude dev environment ✅ (2026-06-30)
- Root `CLAUDE.md` with project skills: `/sync-feature`, `/sync-all`, `/feature-status`,
  `/scaffold-mcp`, `/check-services`
- `.claude/projects.json` feature registry (vromomarket active, budget pending)
- Updated `ROADMAP.md` with full MCP architecture

### Phase 1 — Claude-native brain ✅ (2026-06-30)
- **Replaced** Groq JSON router (`ai_router.py` + `intent.py`) with **Claude API native
  tool use** in `backend/skills/nova_brain.py`
- Tools: calendar CRUD, budget summary, time, navigate, set_user, PC control
- Agent loop: Claude → tool calls → execute → results → Claude → final Greek response
- Cost-aware model routing: Haiku (default) → Sonnet (complex reasoning hints)
- Conversation history: rolling 20-message deque (text-only, lean)
- `pipeline.py` simplified: STT text → `nova_brain.route()` → TTS

---

## Up next

### Phase 2 — Deploy foundation
- **Postgres** on [Neon](https://neon.tech) (free tier, serverless)
  - Tables: `conversations`, `users`, `services` (MCP registry)
- **Backend** deployed to Railway or Fly.io
- **Frontend** deployed to Vercel (already the right target)
- Secrets in Railway/Vercel env dashboards — no secrets in code
- GitHub Actions CI: lint + typecheck on push, deploy on merge to main
- CORS updated for production URLs

### Phase 3 — MCP foundation
- MCP client in Nova's backend (Python `mcp` SDK or lightweight HTTP client)
- `services` table becomes the live registry — dynamic tool loading on conversation start
- Auth: Nova sends `X-Nova-Token` header, each feature app verifies it
- Internal skills (calendar, PC control) stay as native tools — no need to MCP-ify them
- End-to-end test: register a dummy MCP server, confirm Claude calls its tools

### Phase 4a — Vromomarket MCP integration *(first real external app)*
Before starting: `/sync-feature vromomarket` to ensure repo is fresh.
- Add `/mcp` route to vromomarket (Next.js API route)
- Define tools: whatever vromomarket offers (lists, items, etc.)
- Register in Nova's services table
- Test: voice command → Claude → vromomarket MCP → response
- This proves the "add a new app in one day" pattern works

### Phase 4b — Budget app
- Build budget as a proper standalone deployable app (not a SQLite file reader)
- Add `/mcp` route
- Register in Nova
- `backend/skills/budget_skill.py` (SQLite reader) can be retired

### Phase 5 — Voice pipeline (deployed)
- Replace local `edge-tts` with **OpenAI TTS** (deployed, no local deps)
- Replace local `faster-whisper` with **Whisper API** (cloud STT)
- WebSocket audio streaming: browser → Nova backend → STT → brain → TTS → browser
- Session management: conversation context persists across voice turns per session
- Works from phone browser — push-to-talk via `MediaRecorder` API

### Phase 6 — PWA + phone UX
- `next-pwa` → "Add to Home Screen" on iOS/Android
- Push-to-talk UI: hold button to speak, release to send
- Mobile-optimized layout (orb may need lighter mobile version)
- Push notifications (PWA)

### Phase 7 — Production polish & portfolio packaging
- Observability panel: tool calls, model used, latency, cost per turn
- Eval set: 20-30 voice commands, measure routing accuracy
- Docker Compose for local dev
- Architecture diagrams + README that tells the AI engineering story
- Sample/demo data for reviewers who don't have personal Apple/Telegram accounts

---

## Portfolio signal map

| Phase | What it demonstrates |
|-------|---------------------|
| 1 | Claude API, native tool_use, agentic loops, model routing |
| 3 | MCP — the hottest topic in AI engineering hiring right now |
| 4a | System integration, clean external API design |
| 5 | Real-time audio streaming, multimodal pipeline |
| 6 | PWA, production deployment |
| 7 | Observability, evals — the senior engineering signals |
