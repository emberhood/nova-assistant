# {{NAME}} — Nova Feature App

## Role
TODO: describe what this app does and why it's connected to Nova.

## MCP Contract
- **Endpoint**: `POST /api/mcp` (JSON-RPC 2.0)
- **Auth header**: `X-Nova-Token: <token>` must match `NOVA_MCP_TOKEN` env var
- **Methods**: `initialize`, `tools/list`, `tools/call`
- **File**: `app/api/mcp/route.ts`

### Tools
| Tool | Description |
|------|-------------|
| `{{NAME}}__example_tool` | TODO: replace with real tools |

## Database
TODO: document your DB schema, tables, and client here.

## When adding a new MCP tool
1. Add to the `TOOLS` array in `app/api/mcp/route.ts`
2. Add a handler case in `handleToolCall()`
3. Deploy — Nova picks up new tools on next backend restart (tools are cached per session)

## Key env vars
- `NOVA_MCP_TOKEN` — shared secret with Nova backend (set on Vercel)

## Nova registration
In nova-assistant: `.claude/projects.json` → `{{NAME}}.mcp_url_prod`
Nova backend env: `NOVA_MCP_{{NAME_UPPER}}_URL` + `NOVA_MCP_{{NAME_UPPER}}_TOKEN`
