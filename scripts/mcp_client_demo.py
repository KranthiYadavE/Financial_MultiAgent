"""Demo MCP client — lists tools and calls one (learning exercise)."""

from __future__ import annotations

import asyncio
import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    python = sys.executable
    server_params = StdioServerParameters(
        command=python,
        args=["-m", "services.mcp_server.run_stdio"],
        env=None,
    )

    print("Connecting to Financial Multi-Agent MCP server (stdio)...\n")

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("=== Available Tools ===")
            for tool in tools.tools:
                print(f"  • {tool.name}: {tool.description or ''}")

            resources = await session.list_resources()
            print("\n=== Available Resources ===")
            for res in resources.resources:
                print(f"  • {res.uri}: {res.name}")

            prompts = await session.list_prompts()
            print("\n=== Available Prompts ===")
            for prompt in prompts.prompts:
                print(f"  • {prompt.name}")

            print("\n=== Calling mcp_agents_health ===")
            result = await session.call_tool("mcp_agents_health", arguments={})
            for block in result.content:
                if block.type == "text":
                    print(block.text)

            print("\n=== Reading resource schema://gold/postgresql (first 500 chars) ===")
            schema = await session.read_resource("schema://gold/postgresql")
            for block in schema.contents:
                text = block.text if hasattr(block, "text") else str(block)
                print(text[:500] + "..." if len(text) > 500 else text)


if __name__ == "__main__":
    asyncio.run(main())
