# Nova — Roadmap

## Why this project exists

Mario is a frontend-leaning web developer (Next.js/React/JS, some TS, some PHP/Drupal)
pivoting toward **AI engineering** after a layoff, with ~3 months to build a portfolio.
Nova (renamed from "Jarvis" in Phase 0 — see below) is portfolio project #1: an AI assistant
built on the **Claude API** that demonstrates agents, tools, MCP, and production-grade
engineering — not just a chatbot wrapper.

The existing codebase is **not a prototype to throw away** — it already has real,
demo-worthy infrastructure:

- A full **voice pipeline**: custom wake-word ("Arthur"), STT (Groq Whisper / local
  fallback), TTS (edge-tts), speaker verification
- An **LLM-based command router** (currently Groq `llama-3.3-70b`) that returns
  structured JSON actions — i.e. a hand-rolled tool-calling system
- A **skills layer**: calendar (CalDAV/iCloud, multi-user — owner/Andriana/shared),
  budget (reads a friend's "Vibe-Budgeting" SQLite DB), PC control, Telegram bot
- A **websocket-driven React + Vite + Framer Motion UI** with a live dashboard,
  calendar/budget panels, and a voice "orb" visualizer

Notably, `.env.example` already has a stubbed `ANTHROPIC_API_KEY` section labeled
"Claude Haiku fallback (Phase 3)" and a skill called `haiku_skill.py` — the pivot to
Claude was already on the original roadmap. We're just making it the centerpiece
instead of a fallback.

## Decisions locked in (2026-06-07)

- **Interface**: keep voice as the flagship "wow" feature (it's genuinely
  differentiating), but add a first-class **text-mode chat** so anyone reviewing
  the portfolio can interact with it in two minutes without a mic/Greek fluency.
- **Budget integration**: Mario has access to the friend's Vibe-Budgeting code —
  integration can be planned directly, not stubbed.
- **Second portfolio project / time split**: not yet decided — revisit once Nova's
  plan is concrete.

## Phase 0 — Identity & foundation
Rename Jarvis → Nova, set up clean config, scaffold docs, decide repo/sanitization
strategy. *(Broken down into tasks below — this is what we're starting now.)*

## Phase 1 — Claude-native brain *(core pivot, highest portfolio value)*
- Replace the Groq JSON-action router (`ai_router.py`) and `haiku_skill.py` with the
  **Anthropic Messages API + native tool use** (`tool_use` / `tool_result` blocks)
- Formalize each existing skill (calendar, budget, PC control, Telegram) as a real
  **tool schema** with a handler — not regex/JSON-blob parsing
- Build a proper **agent loop** with conversation-state management
- Add **cost-aware model routing**: Haiku for cheap/fast intents, Sonnet for complex
  reasoning — a concrete, interview-ready design decision

## Phase 2 — MCP integration *(the differentiator)*
- Convert one or two tools (e.g. email) into real **MCP servers**, with Nova acting
  as an MCP client
- Document the architecture distinction between native function-calling tools and
  MCP-served tools — this is *the* hot topic in AI engineering hiring right now

## Phase 3 — New features
- **Task manager** (mini-Jira): schema + CRUD API + Claude tools for natural-language
  task management + a kanban-style panel
- **Budget**: formalize the Vibe-Budgeting integration into a clean adapter/service
  layer; add Claude tools for spend queries and insights
- **Email** via MCP — read-only / draft-only by default (a strong "responsible agent
  design / human-in-the-loop" talking point for interviews)
- **Calendar**: extend with agentic reasoning — conflict detection, smart scheduling

## Phase 4 — Dashboard & UX
Unify everything into one cohesive chat + visual dashboard. Add text-mode chat
alongside voice. Polish the visual "wow" layer (orb, panels, theming, transitions).

## Phase 5 — Production polish & portfolio packaging
- Tests, including a small **eval set** for agent routing accuracy
- An **observability/trace panel**: tool calls, model choice, latency, cost per turn
- Docker + CI (GitHub Actions)
- Sanitized `.env.example` + seed/sample data so reviewers can run it without
  Mario's personal Apple/Telegram/budget accounts
- Architecture diagrams + a README that tells the pivot story: why this was built
  and what AI-engineering concepts it demonstrates

---

## Phase 0 — Detailed breakdown

1. ✅ **Rename Jarvis → Nova across the codebase** — done (2026-06-07)
   ~100 occurrences across ~25 files renamed: component files (`JarvisOrb.jsx` →
   `NovaOrb.jsx`, `JarvisOverlay.jsx/css` → `NovaOverlay.jsx/css`), the FastAPI app
   title, `JarvisPipeline` class, the `jarvis_state` websocket message type,
   `JARVIS_BOT_TOKEN`/`JARVIS_ALLOWED_CHAT_IDS` env vars (renamed in code, `.env`,
   and `.env.example`), package names, scripts (`start.sh`, `setup_linux.sh`),
   `.claude/launch.json`, the orb's letter glyph (J → N), and the Greek system
   prompts — including fixing grammatical gender agreement ("ο Jarvis" → "η Nova",
   "ο προσωπικός" → "η προσωπική") since Nova is female in Mario's mind.

   Deliberately **left untouched**: every string tied to the *actual* wake-word
   model — `hey_jarvis` (the real openWakeWord model identifier) and the
   user-facing "Hey Jarvis" prompts in `Dashboard.jsx` and `speaker_verify.py`
   (marked with inline comments). Renaming these now would tell users to say
   something the system doesn't yet detect — they'll flip to "Hey Nova" together
   with the custom wake-word training in the persona-pass task. Wake-word
   "Arthur" (Porcupine) is unrelated and stays as-is.

2. **`.env` setup**
   Already done — your real `.env` is in place at `backend/.env`
   (confirmed gitignored, permissions locked to 600).

3. **Repo & sanitization strategy**
   Decide how the *public* portfolio repo will differ from your working copy:
   personal Apple IDs, Andriana's data, Telegram tokens, and the friend's budget DB
   path can't be in a public README/demo. Plan for seed/sample data (e.g. a demo
   SQLite budget DB, mock calendar events) so a reviewer can clone-and-run.

4. **Scaffold portfolio docs**
   Create `README.md` (project pitch, setup, screenshots/demo placeholder) and an
   `ARCHITECTURE.md` placeholder (system diagram, data flow, tool/MCP boundary) —
   these get filled in progressively as later phases land, but the skeleton goes in
   now so docs aren't a last-minute scramble.

5. **Baseline cleanup**
   Quick pass to confirm the project runs end-to-end as-is (`setup_linux.sh` /
   `start.sh`) before we start swapping out the brain — we want a known-good
   checkpoint to diff against.
