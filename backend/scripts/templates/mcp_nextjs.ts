/**
 * Nova MCP server — {{NAME}}
 *
 * Implements MCP Streamable HTTP (JSON-RPC 2.0).
 * Nova calls tools/list to discover tools, tools/call to execute them.
 * Auth: X-Nova-Token header must match NOVA_MCP_TOKEN env var.
 */

import { NextRequest, NextResponse } from "next/server";

const NOVA_TOKEN = process.env.NOVA_MCP_TOKEN;

function unauthorized() {
  return NextResponse.json(
    { jsonrpc: "2.0", error: { code: -32001, message: "Unauthorized" }, id: null },
    { status: 401 }
  );
}

function rpcError(id: unknown, code: number, message: string) {
  return NextResponse.json({ jsonrpc: "2.0", error: { code, message }, id });
}

function rpcResult(id: unknown, result: unknown) {
  return NextResponse.json({ jsonrpc: "2.0", result, id });
}

// ── Tool definitions ──────────────────────────────────────────────────────────

const TOOLS = [
  {
    name: "{{NAME}}__example_tool",
    description: "TODO: describe what this tool does",
    inputSchema: {
      type: "object",
      properties: {
        query: { type: "string", description: "TODO: describe the input" },
      },
      required: ["query"],
    },
  },
];

// ── Tool handlers ─────────────────────────────────────────────────────────────

type Args = Record<string, unknown>;

async function handleToolCall(name: string, args: Args): Promise<string> {
  switch (name) {
    case "{{NAME}}__example_tool": {
      // TODO: implement
      return `Got query: ${args.query}`;
    }
    default:
      return `Unknown tool: ${name}`;
  }
}

// ── Request handler ───────────────────────────────────────────────────────────

export async function POST(request: NextRequest) {
  if (NOVA_TOKEN && request.headers.get("x-nova-token") !== NOVA_TOKEN) {
    return unauthorized();
  }

  let body: {
    jsonrpc: string;
    method: string;
    params?: Args & { name?: string; arguments?: Args };
    id: unknown;
  };

  try {
    body = await request.json();
  } catch {
    return rpcError(null, -32700, "Parse error");
  }

  const { method, params, id } = body;

  switch (method) {
    case "initialize":
      return rpcResult(id, {
        protocolVersion: "2024-11-05",
        serverInfo: { name: "{{NAME}}", version: "1.0.0" },
        capabilities: { tools: {} },
      });

    case "tools/list":
      return rpcResult(id, { tools: TOOLS });

    case "tools/call": {
      if (!params?.name) return rpcError(id, -32602, "Missing tool name");
      const result = await handleToolCall(params.name, params.arguments ?? {});
      return rpcResult(id, { content: [{ type: "text", text: result }] });
    }

    default:
      return rpcError(id, -32601, "Method not found");
  }
}
