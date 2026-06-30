"""
Service registry — discovers enabled MCP feature apps from env vars.

Pattern: add two env vars to Render and the service is live.
  NOVA_MCP_VROMOMARKET_URL=https://vromomarket.vercel.app
  NOVA_MCP_VROMOMARKET_TOKEN=<shared-secret>

No code changes to Nova needed to add a new service.
"""

import os
from mcp_client import MCPClient

_clients: list[MCPClient] | None = None


def get_clients(force_refresh: bool = False) -> list[MCPClient]:
    """Return all configured MCP clients. Cached after first load."""
    global _clients
    if _clients is not None and not force_refresh:
        return _clients

    _clients = []
    prefix = "NOVA_MCP_"

    for key, url in os.environ.items():
        if not (key.startswith(prefix) and key.endswith("_URL")):
            continue
        service_name = key[len(prefix):-4].lower()          # VROMOMARKET
        token_key    = f"{prefix}{service_name.upper()}_TOKEN"
        token        = os.environ.get(token_key, "").strip()
        url          = url.strip()

        if url and token:
            _clients.append(MCPClient(name=service_name, url=url, token=token))
            print(f"[Registry] Registered service: {service_name} → {url}")
        else:
            print(f"[Registry] Skipping {service_name}: missing URL or TOKEN")

    print(f"[Registry] {len(_clients)} MCP service(s) loaded")
    return _clients


def get_all_external_tools() -> list[dict]:
    """Fetch and merge tools from all registered MCP services."""
    tools = []
    for client in get_clients():
        try:
            tools.extend(client.list_tools())
        except Exception as e:
            print(f"[Registry] {client.name} unavailable: {e}")
    return tools


def call_external_tool(namespaced_name: str, args: dict) -> str:
    """
    Execute a namespaced external tool (e.g. 'vromomarket__get_active_shopping_lists').
    Returns the result text.
    """
    if "__" not in namespaced_name:
        return f"Invalid tool name: {namespaced_name}"

    service_name, tool_name = namespaced_name.split("__", 1)
    for client in get_clients():
        if client.name == service_name:
            return client.call_tool(tool_name, args)

    return f"Service '{service_name}' not found in registry."
