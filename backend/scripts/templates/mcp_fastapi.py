"""
Nova MCP server — {{NAME}}

Implements MCP Streamable HTTP (JSON-RPC 2.0).
Mount this in your FastAPI app or run standalone.

Auth: X-Nova-Token header must match NOVA_MCP_TOKEN env var.
"""

import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()
NOVA_TOKEN = os.getenv("NOVA_MCP_TOKEN")

TOOLS = [
    {
        "name": "{{NAME}}__example_tool",
        "description": "TODO: describe what this tool does",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "TODO: describe the input"},
            },
            "required": ["query"],
        },
    }
]


def rpc_result(id_, result):
    return {"jsonrpc": "2.0", "result": result, "id": id_}


def rpc_error(id_, code, message):
    return {"jsonrpc": "2.0", "error": {"code": code, "message": message}, "id": id_}


async def handle_tool(name: str, args: dict) -> str:
    match name:
        case "{{NAME}}__example_tool":
            # TODO: implement
            return f"Got query: {args.get('query')}"
        case _:
            return f"Unknown tool: {name}"


@app.post("/api/mcp")
async def mcp(request: Request):
    if NOVA_TOKEN and request.headers.get("x-nova-token") != NOVA_TOKEN:
        return JSONResponse(
            {"jsonrpc": "2.0", "error": {"code": -32001, "message": "Unauthorized"}, "id": None},
            status_code=401,
        )

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(rpc_error(None, -32700, "Parse error"))

    method = body.get("method")
    params = body.get("params", {})
    id_ = body.get("id")

    match method:
        case "initialize":
            return JSONResponse(rpc_result(id_, {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "{{NAME}}", "version": "1.0.0"},
                "capabilities": {"tools": {}},
            }))
        case "tools/list":
            return JSONResponse(rpc_result(id_, {"tools": TOOLS}))
        case "tools/call":
            name = params.get("name")
            if not name:
                return JSONResponse(rpc_error(id_, -32602, "Missing tool name"))
            result = await handle_tool(name, params.get("arguments", {}))
            return JSONResponse(rpc_result(id_, {"content": [{"type": "text", "text": result}]}))
        case _:
            return JSONResponse(rpc_error(id_, -32601, "Method not found"))
