#!/usr/bin/env python
"""
Windows Terminal MCP - Entry point.

This MCP allows any LLM to execute Windows commands.
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

from windows_terminal_mcp.executor import execute_command
from windows_terminal_mcp.security import check_command_safety, is_blocked, get_block_message


def main():
    """Read request from stdin, execute command, write response to stdout."""
    try:
        # Read JSON from stdin
        request = json.load(sys.stdin)
        
        # Extract parameters
        command = request.get("command", "")
        shell = request.get("shell", "cmd")  # Default to cmd
        working_dir = request.get("working_dir")
        timeout_ms = request.get("timeout_ms", 30000)
        
        # Security check
        status, msg = check_command_safety(command)
        
        if status == "blocked":
            # Block very dangerous commands
            result = {
                "stdout": "",
                "stderr": f"BLOCKED: {msg}",
                "exit_code": -1,
                "execution_time": 0,
                "blocked": True,
            }
        else:
            # Execute command
            result = execute_command(
                command=command,
                shell=shell,
                working_dir=working_dir,
                timeout_ms=timeout_ms,
            )
            # Add security info to result
            result["confirmation_required"] = status == "dangerous"
            if status == "dangerous":
                result["confirmation_warning"] = msg
        
        # Write response
        print(json.dumps(result))
        
    except json.JSONDecodeError as e:
        error_response = {
            "stdout": "",
            "stderr": f"Invalid JSON: {e}",
            "exit_code": -1,
            "execution_time": 0,
        }
        print(json.dumps(error_response))
        
    except Exception as e:
        error_response = {
            "stdout": "",
            "stderr": str(e),
            "exit_code": -1,
            "execution_time": 0,
        }
        print(json.dumps(error_response))


if __name__ == "__main__":
    main()