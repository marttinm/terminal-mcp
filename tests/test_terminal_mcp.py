"""Tests for Terminal MCP."""
import sys
from unittest.mock import patch

import pytest

from terminal_mcp.executor import DEFAULT_SHELL, build_ssh_command, execute_command
from terminal_mcp.security import check_command_safety, get_block_message, is_blocked, needs_confirmation
from terminal_mcp.server import call_tool

IS_WINDOWS = sys.platform == "win32"
WORKING_DIR = "C:\\" if IS_WINDOWS else "/tmp"


class TestExecutor:

    def test_echo_command(self):
        result = execute_command("echo hello", shell=DEFAULT_SHELL)
        assert result["exit_code"] == 0
        assert "hello" in result["stdout"]

    def test_list_command(self):
        cmd = "dir" if IS_WINDOWS else "ls"
        result = execute_command(cmd, shell=DEFAULT_SHELL)
        assert result["exit_code"] == 0

    def test_working_dir(self):
        cmd = "cd" if IS_WINDOWS else "pwd"
        result = execute_command(cmd, shell=DEFAULT_SHELL, working_dir=WORKING_DIR)
        assert result["exit_code"] == 0

    def test_invalid_command(self):
        result = execute_command("nonexistentcommand12345", shell=DEFAULT_SHELL)
        assert result["exit_code"] != 0

    def test_timeout(self):
        cmd = "ping -n 6 127.0.0.1" if IS_WINDOWS else "ping -c 6 127.0.0.1"
        result = execute_command(cmd, shell=DEFAULT_SHELL, timeout_ms=1000)
        assert result["exit_code"] == -1
        assert "timed out" in result["stderr"].lower()

    def test_empty_command(self):
        result = execute_command("")
        assert result["exit_code"] == -1
        assert result["stderr"] == "No command provided"

    def test_unknown_shell_falls_back_to_default(self):
        result = execute_command("echo hello", shell="notashell")
        assert result["exit_code"] == 0
        assert "hello" in result["stdout"]

    def test_invalid_ssh_format(self):
        result = execute_command("onlyhost", shell="ssh")
        assert result["exit_code"] == -1
        assert "user@host" in result["stderr"]

    def test_execution_time_is_positive(self):
        result = execute_command("echo hi", shell=DEFAULT_SHELL)
        assert result["execution_time"] >= 0


class TestSSH:

    def test_build_ssh_command_basic(self):
        cmd = build_ssh_command("user@host", "uptime")
        assert cmd[0] == "ssh"
        assert "user@host" in cmd
        assert "uptime" in cmd

    def test_build_ssh_command_with_key(self):
        cmd = build_ssh_command("user@host", "ls", key_path="~/.ssh/id_rsa")
        assert "-i" in cmd
        key_index = cmd.index("-i")
        assert not cmd[key_index + 1].startswith("~")

    def test_build_ssh_command_no_key(self):
        cmd = build_ssh_command("user@host", "ls")
        assert "-i" not in cmd

    def test_build_ssh_command_includes_batch_options(self):
        cmd = build_ssh_command("user@host", "ls")
        assert "BatchMode=yes" in " ".join(cmd)
        assert "StrictHostKeyChecking=no" in " ".join(cmd)

    def test_build_ssh_command_strips_quotes(self):
        # Quotes are stripped and SSH is invoked — confirmed by absence of our validation error.
        # SSH itself will fail (host unreachable), but that's exit_code 255, not our -1.
        result = execute_command('user@host "df -h"', shell="ssh")
        assert "Invalid SSH command" not in result["stderr"]


class TestSecurity:

    def test_safe_command(self):
        assert is_blocked("echo hello") is False
        assert needs_confirmation("echo hello") is False

    def test_blocked_unix_commands(self):
        assert is_blocked("rm -rf /") is True
        assert is_blocked("rm -r /home") is True
        assert is_blocked("mkfs.ext4 /dev/sda") is True

    def test_blocked_windows_commands(self):
        assert is_blocked("format c:") is True
        assert is_blocked("del /s /q c:\\") is True
        assert is_blocked("rmdir /s /q c:\\windows") is True
        assert is_blocked("reg delete HKLM\\Software") is True

    def test_blocked_macos_commands(self):
        assert is_blocked("diskutil eraseDisk APFS MyDisk /dev/disk2") is True
        assert is_blocked("launchctl bootout system /Library/LaunchDaemons/foo") is True

    def test_dangerous_windows_commands(self):
        assert needs_confirmation("del file.txt") is True
        assert needs_confirmation("taskkill /f /im process.exe") is True

    def test_dangerous_unix_commands(self):
        assert needs_confirmation("rm file.txt") is True

    def test_dangerous_macos_commands(self):
        assert needs_confirmation("diskutil list") is True
        assert needs_confirmation("launchctl list") is True
        assert needs_confirmation("networksetup -listallnetworkservices") is True

    def test_check_command_safety_returns_tuple(self):
        status, msg = check_command_safety("echo hi")
        assert status == "safe"
        assert msg is None

    def test_get_block_message(self):
        msg = get_block_message("rm -rf /")
        assert "blocked" in msg.lower()


class TestServer:

    @pytest.mark.anyio
    async def test_call_tool_blocked_command(self):
        result = await call_tool("execute_command", {"command": "rm -rf /"})
        assert len(result) == 1
        assert result[0].text.startswith("BLOCKED:")

    @pytest.mark.anyio
    async def test_call_tool_safe_command(self):
        with patch("terminal_mcp.server.execute_command") as mock_exec:
            mock_exec.return_value = {
                "stdout": "hello\n",
                "stderr": "",
                "exit_code": 0,
                "execution_time": 0.01,
            }
            result = await call_tool("execute_command", {"command": "echo hello"})

        assert len(result) == 1
        assert "exit_code: 0" in result[0].text
        assert "⚠️" not in result[0].text

    @pytest.mark.anyio
    async def test_call_tool_dangerous_command_appends_warning(self):
        with patch("terminal_mcp.server.execute_command") as mock_exec:
            mock_exec.return_value = {
                "stdout": "",
                "stderr": "no such file",
                "exit_code": 1,
                "execution_time": 0.01,
            }
            result = await call_tool("execute_command", {"command": "rm file.txt"})

        assert len(result) == 1
        assert "⚠️" in result[0].text

    @pytest.mark.anyio
    async def test_call_tool_unknown_tool(self):
        result = await call_tool("unknown_tool", {"command": "echo hi"})
        assert len(result) == 1
        assert "Unknown tool" in result[0].text

    @pytest.mark.anyio
    async def test_call_tool_output_format(self):
        with patch("terminal_mcp.server.execute_command") as mock_exec:
            mock_exec.return_value = {
                "stdout": "output\n",
                "stderr": "some error",
                "exit_code": 0,
                "execution_time": 0.05,
            }
            result = await call_tool("execute_command", {"command": "echo output"})

        text = result[0].text
        assert "stdout:" in text
        assert "stderr:" in text
        assert "exit_code:" in text
        assert "execution_time:" in text
