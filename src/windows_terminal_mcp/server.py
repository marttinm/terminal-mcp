#!/usr/bin/env python
"""
Windows Terminal MCP Server.

Uses the official MCP Python SDK.
"""
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions
import mcp.types as types

import subprocess
import shutil
import os
import time
from typing import Optional, Dict, Any


# Add Git paths to PATH for SSH
def add_git_to_path():
    """Add Git paths to PATH for SSH access."""
    git_paths = [
        r"C:\Program Files\Git\usr\bin",
        r"C:\Program Files\Git\mingw64\bin",
        r"C:\Program Files\Git\cmd",
    ]
    current_path = os.environ.get("PATH", "")
    new_path = current_path
    for p in git_paths:
        if os.path.exists(p) and p not in current_path:
            new_path = p + os.pathsep + new_path
    os.environ["PATH"] = new_path


add_git_to_path()


# Shell configurations
SHELLS = {
    "powershell": ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command"],
    "cmd": ["cmd.exe", "/c"],
    "bash": ["bash", "-c"],
    "ssh": ["ssh"],  # For SSH commands
}

# SSH options for non-interactive execution
SSH_OPTIONS = [
    "-o", "BatchMode=yes",
    "-o", "StrictHostKeyChecking=no",
    "-o", "ConnectTimeout=30",
    "-o", "UserKnownHostsFile=/dev/null",
    "-o", "LogLevel=ERROR",
]


def build_ssh_command(host: str, remote_cmd: str, key_path: Optional[str] = None) -> list[str]:
    """Build SSH command with non-interactive options."""
    ssh_cmd = ["ssh"] + SSH_OPTIONS

    if key_path:
        expanded = os.path.expanduser(key_path)
        ssh_cmd.extend(["-i", expanded])

    ssh_cmd.append(host)
    if remote_cmd:
        ssh_cmd.append(remote_cmd)

    return ssh_cmd

# Default timeout
DEFAULT_TIMEOUT_MS = 120000


# Security: Dangerous commands
VERY_DANGEROUS = [
    "format", "del /s /q", "rd /s /q", "rmdir /s /q",
    "reg delete", "regedit", "shutdown", "net user",
    "Remove-Item -Recurse", "rm -rf", "mkfs", "fdisk",
]

DANGEROUS = [
    "del ", "rmdir ", "rm ", "erase ", "taskkill",
    "tasklist", "net stop", "net start", "sc delete",
    "reg add", "reg import", "bcdedit", "diskpart",
]


def find_shell(shell_name: str) -> Optional[str]:
    """Find shell executable."""
    path_shell = shutil.which(shell_name)
    if path_shell:
        return path_shell
    
    powershell_paths = [
        r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
        r"C:\Program Files\PowerShell\7\pwsh.exe",
    ]
    
    if shell_name in ["powershell", "pwsh"]:
        for p in powershell_paths:
            if os.path.exists(p):
                return p
    return None


def check_safety(command: str) -> tuple[str, Optional[str]]:
    """Check command safety."""
    cmd_lower = command.lower().strip()
    
    for dangerous in VERY_DANGEROUS:
        if dangerous in cmd_lower:
            return "blocked", f"Command blocked: '{dangerous}' is too dangerous"
    
    for risky in DANGEROUS:
        if cmd_lower.startswith(risky) or risky in cmd_lower:
            return "dangerous", f"Command requires confirmation"
    
    return "safe", None


def execute_command(
    command: str,
    shell: str = "cmd",
    working_dir: Optional[str] = None,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    ssh_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute a command."""
    if not command:
        return {"stdout": "", "stderr": "No command", "exit_code": -1, "execution_time": 0}
    
    if shell not in SHELLS:
        shell = "cmd"
    
    # Handle SSH specially - add non-interactive options
    if shell == "ssh":
        # Split only on first whitespace so the remote command stays intact
        parts = command.split(None, 1)
        if len(parts) >= 2:
            host = parts[0]  # e.g., "ubuntu@147.15.42.100"
            remote_cmd = parts[1].strip("\"'")  # strip surrounding quotes if present
            shell_cmd_list = build_ssh_command(host, remote_cmd, ssh_key)
        else:
            return {"stdout": "", "stderr": "Invalid SSH command. Use: user@host command", "exit_code": -1, "execution_time": 0}
    else:
        shell_cmd_list = SHELLS[shell][:]
        shell_exe = shell_cmd_list[0]
        
        if not shutil.which(shell_exe):
            found = find_shell(shell_exe)
            if found:
                shell_cmd_list = [found] + shell_cmd_list[1:]
            elif shell == "powershell":
                shell_cmd_list = SHELLS["cmd"]
        
        shell_cmd_list += [command]
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            shell_cmd_list,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout_ms / 1000,
            cwd=working_dir,
        )
        
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "execution_time": round(time.time() - start_time, 3),
        }
    except subprocess.TimeoutExpired as e:
        partial_stderr = (e.stderr or "").strip() if isinstance(e.stderr, str) else ""
        stderr_msg = f"Timed out after {timeout_ms}ms"
        if partial_stderr:
            stderr_msg += f"\n{partial_stderr}"
        return {
            "stdout": (e.stdout or "").strip() if isinstance(e.stdout, str) else "",
            "stderr": stderr_msg,
            "exit_code": -1,
            "execution_time": timeout_ms / 1000,
        }
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "exit_code": -1, "execution_time": 0}


app = Server("windows-terminal")


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="execute_command",
            description="Execute a Windows command or SSH command. Supports cmd, powershell, bash, and ssh.",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Command to execute. For SSH: user@host command"},
                    "shell": {
                        "type": "string",
                        "enum": ["cmd", "powershell", "bash", "ssh"],
                        "description": "Shell type (default: cmd)",
                        "default": "cmd",
                    },
                    "working_dir": {"type": "string", "description": "Working directory"},
                    "timeout_ms": {
                        "type": "integer",
                        "description": "Timeout ms (default: 120000)",
                        "default": 120000,
                    },
                    "ssh_key": {
                        "type": "string", 
                        "description": "SSH key path (optional)"
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
    shell = arguments.get("shell", "cmd")
    working_dir = arguments.get("working_dir")
    timeout_ms = arguments.get("timeout_ms", DEFAULT_TIMEOUT_MS)
    ssh_key = arguments.get("ssh_key")
    
    status, msg = check_safety(command)
    
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
                server_name="windows-terminal",
                server_version="0.2.0",
                capabilities=app.get_capabilities(
                    NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(run())