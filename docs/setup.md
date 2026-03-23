# Setup

## Prerequisites

| Requirement | Minimum version | Notes |
|---|---|---|
| Python | 3.11 | Must be available in your PATH |
| ADB (Android Debug Bridge) | Any recent | Install via Android SDK Platform-Tools or your OS package manager |
| Android device or emulator | Any | USB debugging must be enabled; emulators connect automatically |

**ADB install paths by platform:**

| Platform | Command |
|---|---|
| macOS (Homebrew) | `brew install android-platform-tools` |
| Ubuntu / Debian | `sudo apt install adb` |
| Windows | Download [Android SDK Platform-Tools](https://developer.android.com/tools/releases/platform-tools) and add to PATH |

## Installation

### Option A — uvx (recommended)

No cloning or virtual environment needed. `uvx` fetches and runs the package directly from PyPI.

```bash
uvx agent-droid-bridge
```

Verify ADB is reachable:

```bash
adb devices
```

### Option B — From source

```bash
git clone https://github.com/Neverlow512/agent-droid-bridge.git
cd agent-droid-bridge
python3.11 -m venv venv
venv/bin/python -m pip install -r requirements.txt
```

## MCP configuration

### Cursor

Add to `~/.cursor/mcp.json` under the `mcpServers` key:

```json
{
  "mcpServers": {
    "agent-droid-bridge": {
      "command": "uvx",
      "args": ["agent-droid-bridge"],
      "env": {
        "ADB_EXECUTION_MODE": "unrestricted",
        "ADB_ALLOW_SHELL": "true"
      }
    }
  }
}
```

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "agent-droid-bridge": {
      "command": "uvx",
      "args": ["agent-droid-bridge"],
      "env": {
        "ADB_EXECUTION_MODE": "unrestricted",
        "ADB_ALLOW_SHELL": "true"
      }
    }
  }
}
```

### VS Code

Add to your workspace or user `settings.json` under the `mcp.servers` key:

```json
{
  "mcp": {
    "servers": {
      "agent-droid-bridge": {
        "type": "stdio",
        "command": "uvx",
        "args": ["agent-droid-bridge"],
        "env": {
          "ADB_EXECUTION_MODE": "unrestricted",
          "ADB_ALLOW_SHELL": "true"
        }
      }
    }
  }
}
```

### From source (all clients)

If running from a local clone instead of `uvx`, replace `command` and `args` with:

```json
"command": "/absolute/path/to/agent-droid-bridge/venv/bin/python",
"args": ["-m", "agent_droid_bridge.server"],
"env": {
  "PYTHONPATH": "/absolute/path/to/agent-droid-bridge/src",
  "ADB_EXECUTION_MODE": "unrestricted",
  "ADB_ALLOW_SHELL": "true"
}
```

## Optional environment variables

| Variable | Values | Default | Description |
|---|---|---|---|
| `ADB_EXECUTION_MODE` | `unrestricted`, `restricted` | `unrestricted` | In `restricted` mode only commands in the allowlist are permitted |
| `ADB_ALLOW_SHELL` | `true`, `false` | `true` | Set to `false` to block all `adb shell` commands |
| `ADB_CONFIG_PATH` | Absolute path | bundled default | Path to a custom `adb_config.yaml` |

See [configuration.md](configuration.md) for the full YAML reference.

## Verification

### uvx install

```bash
uvx agent-droid-bridge --help
```

### From source

```bash
PYTHONPATH=src venv/bin/python -m agent_droid_bridge.server
```

A successful start produces no output and the process blocks waiting for MCP messages over stdio.
