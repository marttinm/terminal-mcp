"""Windows Terminal MCP - Command executor."""
import subprocess
import time
from typing import Optional, Dict, Any
import os
import shutil

# Shell configurations for Windows - try to find shells in common locations
def _find_shell(shell_name: str) -> Optional[str]:
    """Find shell executable in PATH or common locations."""
    # First try PATH
    path_shell = shutil.which(shell_name)
    if path_shell:
        return path_shell
    
    # Common PowerShell locations on Windows
    powershell_paths = [
        r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
        r"C:\Program Files\PowerShell\7\pwsh.exe",
        r"C:\Program Files (x86)\PowerShell\7\pwsh.exe",
    ]
    
    if shell_name in ["powershell", "pwsh"]:
        for p in powershell_paths:
            if os.path.exists(p):
                return p
    
    return None


# Shell configurations - use shell=True to resolve from PATH
SHELLS = {
    "powershell": ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command"],
    "cmd": ["cmd.exe", "/c"],
    "bash": ["bash", "-c"],
}


def execute_command(
    command: str,
    shell: str = "powershell",
    working_dir: Optional[str] = None,
    timeout_ms: int = 30000,
) -> Dict[str, Any]:
    """
    Execute a command in Windows terminal.
    
    Args:
        command: Command to execute
        shell: Shell to use - "powershell", "cmd", or "bash"
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
    
    # Select shell command
    if shell not in SHELLS:
        shell = "powershell"
    
    # Get shell command, try to find executable if not in PATH
    shell_cmd_list = SHELLS[shell]
    shell_exe = shell_cmd_list[0]
    
    # Try to find shell if not found directly
    if not shutil.which(shell_exe):
        found = _find_shell(shell_exe)
        if found:
            shell_cmd_list = [found] + shell_cmd_list[1:]
        elif shell == "powershell":
            # Fall back to cmd if powershell not found
            shell_cmd_list = SHELLS["cmd"]
    
    start_time = time.time()
    
    try:
        result = subprocess.run(
            shell_cmd_list + [command],
            capture_output=True,
            text=True,
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