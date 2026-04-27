# windows-terminal-mcp

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that lets any LLM execute commands on a local terminal or over SSH — works on **Windows and macOS**.

## Features

- Run commands via native shells (`cmd`/`powershell`/`bash` on Windows, `zsh`/`bash`/`sh` on macOS)
- Execute remote commands over **SSH** with key-based authentication
- 3-level security model (safe / confirm / blocked)
- Configurable timeout per command
- Works with Claude Desktop and any MCP-compatible client

## Installation

```bash
git clone https://github.com/marttinm/windows-terminal-mcp.git
cd windows-terminal-mcp
pip install -e .
```

> Requires Python 3.11+. Works on Windows and macOS.

## Configuration

### macOS

Add the server to your Claude Desktop config file (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "terminal": {
      "command": "python3",
      "args": ["-m", "windows_terminal_mcp.server"]
    }
  }
}
```

Or point directly to the script:

```json
{
  "mcpServers": {
    "terminal": {
      "command": "python3",
      "args": ["/path/to/windows-terminal-mcp/src/windows_terminal_mcp/server.py"]
    }
  }
}
```

### Windows

Add the server to your Claude Desktop config file (`%APPDATA%\Claude\claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "terminal": {
      "command": "cmd",
      "args": ["/c", "python", "-m", "windows_terminal_mcp.server"]
    }
  }
}
```

## Tool: `execute_command`

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `command` | string | required | Command to run. For SSH: `user@host command` |
| `shell` | string | `zsh` / `cmd` | Shell: `zsh`/`bash`/`sh`/`ssh` (macOS) or `cmd`/`powershell`/`bash`/`ssh` (Windows) |
| `working_dir` | string | — | Working directory (local commands only) |
| `timeout_ms` | integer | `120000` | Timeout in milliseconds |
| `ssh_key` | string | — | Path to SSH private key (e.g. `~/.ssh/id_rsa`) |

### Response

```json
{
  "stdout": "...",
  "stderr": "...",
  "exit_code": 0,
  "execution_time": 0.42
}
```

## Usage Examples

### Local commands — macOS

```
Run: ls -la ~/Documents
Shell: zsh

Run: git status
Shell: zsh

Run: brew list
Shell: bash
```

### Local commands — Windows

```
Run: dir C:\Users
Shell: cmd

Run: Get-Process | Select-Object -First 5
Shell: powershell

Run: git status
Shell: bash
```

### SSH commands (both platforms)

```
Run: ubuntu@192.168.1.10 "df -h && uptime"
Shell: ssh
SSH key: ~/.ssh/id_rsa
```

```
Run: ubuntu@192.168.1.10 "docker ps"
Shell: ssh
SSH key: ~/.ssh/my_key
Timeout: 30000
```

## Security

Commands are classified into three levels:

**Safe** — executed directly  
`echo`, `ls`, `dir`, `git`, `npm`, `node`, `python`, `pip`, `curl`, and most read-only commands.

**Dangerous** — Claude will warn before executing  
`rm`, `del`, `rmdir`, `taskkill`, `net stop`, `launchctl`, `diskutil`, `dscl`, `networksetup`, and similar system-modifying commands.

**Blocked** — always rejected  
`rm -rf`, `format`, `del /s /q`, `reg delete`, `shutdown`, `diskutil eraseDisk`, `launchctl bootout system`, `mkfs`, `fdisk`, and similar destructive operations.

## Development

### Project structure

```
windows-terminal-mcp/
├── src/windows_terminal_mcp/
│   ├── __init__.py
│   ├── server.py      # MCP server (main entry point)
│   ├── executor.py    # subprocess execution
│   ├── main.py        # simple stdin/stdout handler
│   └── security.py    # command safety checks
├── tests/
│   └── test_windows_terminal_mcp.py
├── pyproject.toml
├── LICENSE
└── README.md
```

### Run tests

```bash
pip install pytest
pytest tests/ -v
```

### Use as a Python module

```python
from windows_terminal_mcp.server import execute_command

# macOS
result = execute_command("echo hello", shell="zsh")
print(result)
# {'stdout': 'hello\n', 'stderr': '', 'exit_code': 0, 'execution_time': 0.02}

# SSH (both platforms)
result = execute_command(
    "ubuntu@192.168.1.10 uptime",
    shell="ssh",
    ssh_key="~/.ssh/id_rsa",
    timeout_ms=10000,
)
print(result)
```

## Changelog

### v0.3.0
- Added macOS support: `zsh`, `bash`, `sh` shells with auto-detection
- Shell selection is now platform-aware (Windows vs macOS/Linux)
- Added macOS-specific security rules (`diskutil`, `launchctl`, `dscl`, `networksetup`, etc.)
- Fixed logic bug in `check_command_safety` (wrong variable in inner loop)
- Added `encoding="utf-8"` to subprocess calls for cross-platform consistency
- Updated tool schema to expose platform-appropriate shells
- Server now imports security checks from `security.py` (removed duplication)

### v0.2.0
- Added SSH support with key-based authentication
- Fixed SSH command construction (host and remote command passed as separate arguments)
- Fixed `~` expansion in SSH key paths on Windows
- Fixed stdin inheritance that caused SSH to hang inside the MCP server process

### v0.1.0
- Basic command execution via cmd, powershell, bash
- stdout/stderr/exit_code capture
- 3-level security model
- Unit tests

## License

MIT — see [LICENSE](LICENSE)
