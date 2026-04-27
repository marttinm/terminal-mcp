"""Tests for Terminal MCP."""
import sys
import pytest
from terminal_mcp.executor import execute_command, DEFAULT_SHELL
from terminal_mcp.security import check_command_safety, is_blocked, needs_confirmation, get_block_message

IS_WINDOWS = sys.platform == "win32"
WORKING_DIR = "C:\\" if IS_WINDOWS else "/tmp"


class TestExecutor:
    """Test command execution."""

    def test_echo_command(self):
        """Test basic echo command."""
        result = execute_command("echo hello", shell=DEFAULT_SHELL)
        assert result["exit_code"] == 0
        assert "hello" in result["stdout"]

    def test_list_command(self):
        """Test directory listing command."""
        cmd = "dir" if IS_WINDOWS else "ls"
        result = execute_command(cmd, shell=DEFAULT_SHELL)
        assert result["exit_code"] == 0

    def test_invalid_command(self):
        """Test handling of invalid command."""
        result = execute_command("nonexistentcommand12345", shell=DEFAULT_SHELL)
        assert result["exit_code"] != 0

    def test_timeout(self):
        """Test timeout handling."""
        cmd = "ping -n 6 127.0.0.1" if IS_WINDOWS else "ping -c 6 127.0.0.1"
        result = execute_command(cmd, shell=DEFAULT_SHELL, timeout_ms=1000)
        assert result["exit_code"] == -1
        assert "timed out" in result["stderr"].lower()

    def test_working_dir(self):
        """Test working directory."""
        cmd = "cd" if IS_WINDOWS else "pwd"
        result = execute_command(cmd, shell=DEFAULT_SHELL, working_dir=WORKING_DIR)
        assert result["exit_code"] == 0


class TestSecurity:
    """Test security checks."""

    def test_safe_command(self):
        """Test safe commands pass."""
        assert is_blocked("echo hello") is False
        assert needs_confirmation("echo hello") is False

    def test_blocked_unix_commands(self):
        """Test Unix destructive commands are always blocked."""
        assert is_blocked("rm -rf /") is True
        assert is_blocked("rm -r /home") is True
        assert is_blocked("mkfs.ext4 /dev/sda") is True

    def test_blocked_windows_commands(self):
        """Test Windows destructive commands are always blocked."""
        assert is_blocked("format c:") is True
        assert is_blocked("del /s /q c:\\") is True
        assert is_blocked("rmdir /s /q c:\\windows") is True
        assert is_blocked("reg delete HKLM\\Software") is True

    def test_blocked_macos_commands(self):
        """Test macOS destructive commands are always blocked."""
        assert is_blocked("diskutil eraseDisk APFS MyDisk /dev/disk2") is True
        assert is_blocked("launchctl bootout system /Library/LaunchDaemons/foo") is True

    def test_dangerous_windows_commands(self):
        """Test Windows risky commands require confirmation."""
        assert needs_confirmation("del file.txt") is True
        assert needs_confirmation("taskkill /f /im process.exe") is True

    def test_dangerous_unix_commands(self):
        """Test Unix risky commands require confirmation."""
        assert needs_confirmation("rm file.txt") is True

    def test_dangerous_macos_commands(self):
        """Test macOS risky commands require confirmation."""
        assert needs_confirmation("diskutil list") is True
        assert needs_confirmation("launchctl list") is True
        assert needs_confirmation("networksetup -listallnetworkservices") is True

    def test_get_block_message(self):
        """Test block message returned."""
        msg = get_block_message("rm -rf /")
        assert "blocked" in msg.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
