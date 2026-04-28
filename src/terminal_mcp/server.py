#!/usr/bin/env python
"""Terminal MCP Server."""
import asyncio

from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
import mcp.types as types

from terminal_mcp import __version__
from terminal_mcp.executor import AVAILABLE_SHELLS, DEFAULT_SHELL, DEFAULT_TIMEOUT_MS, execute_command
from terminal_mcp.security import check_command_safety

app = Server("terminal-mcp")


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="execute_command",
            description=(
                "Execute a terminal command or SSH command. "
                f"Supported shells on this platform: {', '.join(AVAILABLE_SHELLS)}."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Command to execute. For SSH: user@host command",
                    },
                    "shell": {
                        "type": "string",
                        "enum": AVAILABLE_SHELLS,
                        "description": f"Shell type (default: {DEFAULT_SHELL})",
                        "default": DEFAULT_SHELL,
                    },
                    "working_dir": {
                        "type": "string",
                        "description": "Working directory (local commands only)",
                    },
                    "timeout_ms": {
                        "type": "integer",
                        "description": f"Timeout in milliseconds (default: {DEFAULT_TIMEOUT_MS})",
                        "default": DEFAULT_TIMEOUT_MS,
                    },
                    "ssh_key": {
                        "type": "string",
                        "description": "SSH key path (optional, e.g. ~/.ssh/id_rsa)",
                    },
                },
                "required": ["command"],
            },
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name != "execute_command":
        return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

    command = arguments.get("command", "")
    shell = arguments.get("shell", DEFAULT_SHELL)
    working_dir = arguments.get("working_dir")
    timeout_ms = arguments.get("timeout_ms", DEFAULT_TIMEOUT_MS)
    ssh_key = arguments.get("ssh_key")

    status, msg = check_command_safety(command)

    if status == "blocked":
        return [types.TextContent(type="text", text=f"BLOCKED: {msg}")]

    result = execute_command(command, shell, working_dir, timeout_ms, ssh_key)

    output = f"stdout: {result['stdout']}"
    if result["stderr"]:
        output += f"\nstderr: {result['stderr']}"
    output += f"\nexit_code: {result['exit_code']}"
    output += f"\nexecution_time: {result['execution_time']}s"

    if status == "dangerous":
        output += f"\n⚠️ {msg}"

    return [types.TextContent(type="text", text=output)]


async def run():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="terminal-mcp",
                server_version=__version__,
                capabilities=app.get_capabilities(
                    NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(run())
