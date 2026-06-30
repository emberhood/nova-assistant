"""
MCP client — connects Nova to external feature apps via the MCP protocol.

Each feature app exposes POST /api/mcp (JSON-RPC 2.0).
Nova calls tools/list to discover tools, tools/call to execute them.

Tool names are namespaced: vromomarket__get_active_shopping_lists
so multiple services never clash in Claude's tool list.
"""

import httpx


class MCPClient:
    def __init__(self, name: str, url: str, token: str):
        self.name = name
        self.url = url.rstrip("/")
        self.token = token
        self._tools_cache: list[dict] | None = None

    def _headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "X-Nova-Token": self.token,
        }

    def _rpc(self, method: str, params: dict | None = None, timeout: int = 10) -> dict:
        payload = {"jsonrpc": "2.0", "method": method, "id": 1}
        if params:
            payload["params"] = params
        resp = httpx.post(
            f"{self.url}/api/mcp",
            json=payload,
            headers=self._headers(),
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def list_tools(self, force_refresh: bool = False) -> list[dict]:
        """Return tools from this service formatted for Claude API. Cached."""
        if self._tools_cache is not None and not force_refresh:
            return self._tools_cache

        data = self._rpc("tools/list")
        mcp_tools = data.get("result", {}).get("tools", [])
        self._tools_cache = [self._to_claude_tool(t) for t in mcp_tools]
        print(f"[MCP] {self.name}: loaded {len(self._tools_cache)} tools")
        return self._tools_cache

    def call_tool(self, tool_name: str, args: dict) -> str:
        """Call a tool and return the text result."""
        data = self._rpc(
            "tools/call",
            params={"name": tool_name, "arguments": args},
            timeout=30,
        )
        if "error" in data:
            return f"MCP error: {data['error'].get('message', 'unknown')}"
        content = data.get("result", {}).get("content", [])
        return "\n".join(c["text"] for c in content if c.get("type") == "text")

    def _to_claude_tool(self, mcp_tool: dict) -> dict:
        """Convert MCP tool schema → Claude API tool schema with namespace prefix."""
        return {
            "name": f"{self.name}__{mcp_tool['name']}",
            "description": f"[{self.name}] {mcp_tool.get('description', '')}",
            "input_schema": mcp_tool.get("inputSchema", {"type": "object", "properties": {}}),
        }
