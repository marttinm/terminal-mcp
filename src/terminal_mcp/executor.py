"""Terminal MCP - Command executor."""
import subprocess
import sys
import time
from typing import Optional, Dict, Any
import os
import shutil

IS_WINDOWS = sys.platform == "win32"


def _find_shell(shell_name: str) -> Optional[str]:
    """Find shell executable in PATH or common locations."""
    path_shell = shutil.which(shell_name)
    if path_shell:
        return path_shell

    if IS_WINDOWS and shell_name in ["powershell", "pwsh"]:
        powershell_paths = [
            r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
            r"C:\Program Files\PowerShell\7\pwsh.exe",
            r"C:\Program Files (x86)\PowerShell\7\pwsh.exe",
        ]
        for p in powershell_paths:
            if os.path.exists(p):
                return p

    return None


if IS_WINDOWS:
    SHELLS: Dict[str, list] = {
        "powershell": ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command"],
        "cmd": ["cmd.exe", "/c"],
        "bash": ["bash", "-c"],
    }
    DEFAULT_SHELL = "powershell"
else:
    SHELLS = {
        "zsh": ["zsh", "-c"],
        "bash": ["bash", "-c"],
        "sh": ["sh", "-c"],
    }
    DEFAULT_SHELL = "zsh" if shutil.which("zsh") else "bash"


def execute_command(
    command: str,
    shell: str = DEFAULT_SHELL,
    working_dir: Optional[str] = None,
    timeout_ms: int = 30000,
) -> Dict[str, Any]:
    """
    Execute a command in the terminal.

    Args:
        command: Command to execute
        shell: Shell to use
        working_dir: Working directory (optional)
        timeout_ms: Timeout in milliseconds

    Returns:
        dict with stdout, stderr, exit_code, execution_time
    """
    if not command:
        return {
            "stdout": "",
            "stderr": "No command provided",
            "exit_code": -1,
            "execution_time": 0,
        }

    if shell not in SHELLS:
        shell = DEFAULT_SHELL

    shell_cmd_list = SHELLS[shell][:]
    shell_exe = shell_cmd_list[0]

    if not shutil.which(shell_exe):
        found = _find_shell(shell_exe)
        if found:
            shell_cmd_list = [found] + shell_cmd_list[1:]
        elif IS_WINDOWS and shell == "powershell":
            shell_cmd_list = SHELLS["cmd"][:]

    start_time = time.time()

    try:
        result = subprocess.run(
            shell_cmd_list + [command],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_ms / 1000,
            cwd=working_dir,
        )
        execution_time = time.time() - start_time

        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "execution_time": execution_time,
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": f"Command timed out after {timeout_ms}ms",
            "exit_code": -1,
            "execution_time": timeout_ms / 1000,
        }
    except FileNotFoundError:
        return {
            "stdout": "",
            "stderr": f"Shell not found: {shell}",
            "exit_code": -1,
            "execution_time": 0,
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": str(e),
            "exit_code": -1,
            "execution_time": 0,
        }
