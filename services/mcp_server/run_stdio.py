"""Stdio entrypoint for Cursor MCP integration."""

from services.mcp_server.server import run_stdio

if __name__ == "__main__":
    run_stdio()
