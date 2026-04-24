"""Windows Terminal MCP - Security checks."""
import re
from typing import Tuple, Optional

# Commands that are blocked automatically (very dangerous)
VERY_DANGEROUS = [
    "format",
    "del /s /q",
    "rd /s /q",
    "rmdir /s /q",
    "reg delete",
    "regedit",
    "shutdown",
    "net user",
    "net localgroup",
    "Remove-Item -Recurse",
    "Remove-Item -Force",
    "rm -rf",
    "rm -r",
    "mkfs",
    "fdisk",
]

# Commands that require user confirmation (risky)
DANGEROUS = [
    "del ",
    "rmdir ",
    "rm ",
    "erase ",
    "taskkill",
    "tasklist",
    "net stop",
    "net start",
    "sc delete",
    "reg add",
    "reg import",
    "reg export",
    "bcdedit",
    "diskpart",
    "cipher",
    "takeown",
    "icacls",
    "runas",
    "powershell -Command",
]


def check_command_safety(command: str) -> Tuple[str, Optional[str]]:
    """
    Check if a command is safe to execute.
    
    Returns:
        (status, confirmation_message)
        - status: "safe", "dangerous", or "blocked"
        - confirmation_message: message if user confirmation needed
    """
    cmd_lower = command.lower().strip()
    
    # Check very dangerous commands (block immediately)
    for dangerous in VERY_DANGEROUS:
        if dangerous in cmd_lower:
            return "blocked", f"Command blocked: '{dangerous}' is too dangerous"
    
    # Check dangerous commands (need user confirmation)
    for risky in DANGEROUS:
        if cmd_lower.startswith(risky) or dangerous in cmd_lower:
            # Check if it's not in a safe context
            return "dangerous", f"Command '{command[:50]}...' requires user confirmation"
    
    return "safe", None


def needs_confirmation(command: str) -> bool:
    """Check if command requires user confirmation."""
    status, _ = check_command_safety(command)
    return status == "dangerous"


def is_blocked(command: str) -> bool:
    """Check if command should be blocked."""
    status, _ = check_command_safety(command)
    return status == "blocked"


def get_block_message(command: str) -> str:
    """Get block message for a dangerous command."""
    _, msg = check_command_safety(command)
    return msg or "Command blocked"