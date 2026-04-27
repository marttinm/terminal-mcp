#!/usr/bin/env python
"""
Terminal MCP - Entry point.

Reads JSON from stdin, writes JSON to stdout.

Security:
- Very dangerous commands are blocked
- Risky commands require user confirmation
"""
import json
import sys
import os

# Add parent directory to path for direct execution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from terminal_mcp.executor import execute_command, DEFAULT_SHELL
from terminal_mcp.security import check_command_safety, is_blocked, get_block_message


def main():
    """Read request from stdin, execute command, write response to stdout."""
    try:
        request = json.load(sys.stdin)

        command = request.get("command", "")
        shell = request.get("shell", DEFAULT_SHELL)
        working_dir = request.get("working_dir")
        timeout_ms = request.get("timeout_ms", 30000)

        status, msg = check_command_safety(command)

        if status == "blocked":
            result = {
                "stdout": "",
                "stderr": f"BLOCKED: {msg}",
                "exit_code": -1,
                "execution_time": 0,
                "blocked": True,
            }
        else:
            result = execute_command(
                command=command,
                shell=shell,
                working_dir=working_dir,
                timeout_ms=timeout_ms,
            )
            result["confirmation_required"] = status == "dangerous"
            if status == "dangerous":
                result["confirmation_warning"] = msg

        print(json.dumps(result))

    except json.JSONDecodeError as e:
        print(json.dumps({"stdout": "", "stderr": f"Invalid JSON: {e}", "exit_code": -1, "execution_time": 0}))

    except Exception as e:
        print(json.dumps({"stdout": "", "stderr": str(e), "exit_code": -1, "execution_time": 0}))


if __name__ == "__main__":
    main()
