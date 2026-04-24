"""Tests for Windows Terminal MCP."""
import pytest
from windows_terminal_mcp.executor import execute_command
from windows_terminal_mcp.security import check_command_safety, is_blocked, needs_confirmation, get_block_message


class TestExecutor:
    """Test command execution."""
    
    def test_echo_command(self):
        """Test basic echo command."""
        result = execute_command("echo hello", shell="cmd")
        assert result["exit_code"] == 0
        assert "hello" in result["stdout"]
    
    def test_dir_command(self):
        """Test dir command."""
        result = execute_command("dir", shell="cmd")
        assert result["exit_code"] == 0
    
    def test_invalid_command(self):
        """Test handling of invalid command."""
        result = execute_command("nonexistentcommand12345", shell="cmd")
        assert result["exit_code"] != 0
    
    def test_timeout(self):
        """Test timeout handling."""
        # ping -n 6 = 5 seconds timeout
        result = execute_command("ping -n 6 127.0.0.1", shell="cmd", timeout_ms=1000)
        assert result["exit_code"] == -1
        assert "timed out" in result["stderr"]
    
    def test_working_dir(self):
        """Test working directory."""
        result = execute_command("cd", shell="cmd", working_dir="C:\\")
        assert result["exit_code"] == 0


class TestSecurity:
    """Test security checks."""
    
    def test_safe_command(self):
        """Test safe commands pass."""
        assert is_blocked("echo hello") is False
        assert needs_confirmation("echo hello") is False
    
    def test_blocked_command(self):
        """Test blocked commands."""
        assert is_blocked("format c:") is True
        assert is_blocked("del /s /q") is True
        assert is_blocked("rmdir /s /q") is True
    
    def test_dangerous_command(self):
        """Test dangerous commands require confirmation."""
        assert needs_confirmation("del file.txt") is True
        assert needs_confirmation("taskkill /f") is True
    
    def test_get_block_message(self):
        """Test block message returned."""
        msg = get_block_message("format c:")
        assert "blocked" in msg.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])