# terminal-mcp

An [MCP (Model Context Protocol)](https://modelcontextprotocol.io) server that lets any LLM execute commands on a local terminal or over SSH — works on **Windows and macOS**.

- Run commands via native shells (`cmd`/`powershell`/`bash` on Windows, `zsh`/`bash`/`sh` on macOS)
- Execute remote commands over **SSH** with key-based authentication
- 3-level security model: safe / confirm / blocked

## Requirements

- Python 3.11+
- [Claude Desktop](https://claude.ai/download) or any MCP-compatible client

## Installation

```bash
git clone https://github.com/marttinm/windows-terminal-mcp.git
cd windows-terminal-mcp
pip install -e .
```

## Configure Claude Desktop

### macOS

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "terminal": {
      "command": "python3",
      "args": ["-m", "terminal_mcp.server"]
    }
  }
}
```

### Windows

Edit `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "terminal": {
      "command": "cmd",
      "args": ["/c", "python", "-m", "terminal_mcp.server"]
    }
  }
}
```

Restart Claude Desktop after saving the config.

## Security

Commands fall into three categories:

| Level | Behavior | Examples |
|-------|----------|---------|
| **Safe** | Executed directly | `ls`, `git`, `npm`, `python`, `curl` |
| **Dangerous** | Claude warns before executing | `rm`, `rmdir`, `launchctl`, `diskutil` |
| **Blocked** | Always rejected | `rm -rf /`, `format`, `shutdown`, `mkfs` |

## License

MIT — see [LICENSE](LICENSE)
