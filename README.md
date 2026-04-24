# windows-terminal-mcp

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that lets any LLM execute commands on a Windows terminal — including local shells and remote SSH connections.

## Features

- Run commands via `cmd`, `powershell`, or `bash` (Git Bash)
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

> Requires Python 3.11+ on Windows.

## Configuration

Add the server to your Claude Desktop config file (`%APPDATA%\Claude\claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "windows-terminal": {
      "command": "cmd",
      "args": ["/c", "python", "-m", "windows_terminal_mcp.server"]
    }
  }
}
```

Or point directly to the script:

```json
{
  "mcpServers": {
    "windows-terminal": {
      "command": "cmd",
      "args": ["/c", "python", "C:/path/to/windows-terminal-mcp/src/windows_terminal_mcp/server.py"]
    }
  }
}
```

## Tool: `execute_command`

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `command` | string | required | Command to run. For SSH: `user@host command` |
| `shell` | string | `cmd` | Shell: `cmd`, `powershell`, `bash`, `ssh` |
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

### Local commands

```
Run: dir C:\Users
Shell: cmd

Run: Get-Process | Select-Object -First 5
Shell: powershell

Run: git status
Shell: bash
```

### SSH commands

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
`echo`, `dir`, `type`, `git`, `npm`, `node`, `python`, `pip`, `curl`, and most read-only commands.

**Dangerous** — Claude will warn before executing  
`del`, `rmdir`, `rm`, `taskkill`, `net stop`, `net start`, `sc delete`, `reg add`, etc.

**Blocked** — always rejected  
`format`, `del /s /q`, `rd /s /q`, `reg delete`, `regedit`, `shutdown`, `net user`, `rm -rf`, `mkfs`, `fdisk`, and similar destructive operations.

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

result = execute_command("echo hello", shell="cmd")
print(result)
# {'stdout': 'hello\n', 'stderr': '', 'exit_code': 0, 'execution_time': 0.02}

result = execute_command(
    "ubuntu@192.168.1.10 uptime",
    shell="ssh",
    ssh_key="~/.ssh/id_rsa",
    timeout_ms=10000,
)
print(result)
```

## Changelog

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
