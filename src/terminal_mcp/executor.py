"""Terminal MCP - Command executor."""
import os
import shutil
import subprocess
import sys
import time
from typing import Any, Dict, Optional

IS_WINDOWS = sys.platform == "win32"

SSH_OPTIONS = [
    "-o", "BatchMode=yes",
    "-o", "StrictHostKeyChecking=no",
    "-o", "ConnectTimeout=30",
    "-o", "UserKnownHostsFile=/dev/null",
    "-o", "LogLevel=ERROR",
]

DEFAULT_TIMEOUT_MS = 120000


def _add_git_to_path() -> None:
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


def _find_shell(shell_name: str) -> Optional[str]:
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
    _add_git_to_path()
    SHELLS: Dict[str, list] = {
        "powershell": ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command"],
        "cmd": ["cmd.exe", "/c"],
        "bash": ["bash", "-c"],
        "ssh": ["ssh"],
    }
    DEFAULT_SHELL = "cmd"
    AVAILABLE_SHELLS = ["cmd", "powershell", "bash", "ssh"]
else:
    SHELLS = {
        "zsh": ["zsh", "-c"],
        "bash": ["bash", "-c"],
        "sh": ["sh", "-c"],
        "ssh": ["ssh"],
    }
    DEFAULT_SHELL = "zsh" if shutil.which("zsh") else "bash"
    AVAILABLE_SHELLS = ["zsh", "bash", "sh", "ssh"]


def build_ssh_command(host: str, remote_cmd: str, key_path: Optional[str] = None) -> list:
    ssh_cmd = ["ssh"] + SSH_OPTIONS
    if key_path:
        ssh_cmd.extend(["-i", os.path.expanduser(key_path)])
    ssh_cmd.append(host)
    if remote_cmd:
        ssh_cmd.append(remote_cmd)
    return ssh_cmd


def execute_command(
    command: str,
    shell: str = DEFAULT_SHELL,
    working_dir: Optional[str] = None,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    ssh_key: Optional[str] = None,
) -> Dict[str, Any]:
    if not command:
        return {"stdout": "", "stderr": "No command provided", "exit_code": -1, "execution_time": 0}

    if shell not in SHELLS:
        shell = DEFAULT_SHELL

    if shell == "ssh":
        parts = command.split(None, 1)
        if len(parts) < 2:
            return {
                "stdout": "",
                "stderr": "Invalid SSH command. Use: user@host command",
                "exit_code": -1,
                "execution_time": 0,
            }
        host, remote_cmd = parts[0], parts[1].strip("\"'")
        shell_cmd_list = build_ssh_command(host, remote_cmd, ssh_key)
    else:
        shell_cmd_list = SHELLS[shell][:]
        shell_exe = shell_cmd_list[0]
        if not shutil.which(shell_exe):
            found = _find_shell(shell_exe)
            if found:
                shell_cmd_list = [found] + shell_cmd_list[1:]
            elif IS_WINDOWS and shell == "powershell":
                shell_cmd_list = SHELLS["cmd"][:]
        shell_cmd_list.append(command)

    start_time = time.time()

    try:
        result = subprocess.run(
            shell_cmd_list,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
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
