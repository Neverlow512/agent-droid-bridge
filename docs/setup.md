# Setup

## Prerequisites

| Requirement | Minimum version | Notes |
|---|---|---|
| Python | 3.11 | Must be available in your PATH |
| uv | Latest | Required for `uvx` install. Install: `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| ADB (Android Debug Bridge) | Any recent | Install via Android SDK Platform-Tools or your OS package manager |
| Android device or emulator | Any | USB debugging must be enabled; emulators connect automatically |

**ADB install paths by platform:**

| Platform | Command |
|---|---|
| macOS (Homebrew) | `brew install android-platform-tools` |
| Debian | `sudo apt install adb` |
| Fedora | `sudo dnf install android-tools` |
| Arch | `sudo pacman -S android-tools` |
| Other Linux | Download [Android SDK Platform-Tools](https://developer.android.com/tools/releases/platform-tools) and add to PATH |
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
venv/bin/pip install -e .
```

To run the server directly:

```bash
venv/bin/python -m agent_droid_bridge.server
```

For the MCP client config when running from source, see the "From source" config block in the MCP configuration section below.

## MCP configuration

### Cursor

To enable session logging, set `MCP_LOG_ENABLED` to `"true"` and update `MCP_LOG_DIR` to a writable path on your machine.

Add to `~/.cursor/mcp.json` under the `mcpServers` key:

```json
{
  "mcpServers": {
    "agent-droid-bridge": {
      "command": "uvx",
      "args": ["agent-droid-bridge"],
      "env": {
        "ADB_EXECUTION_MODE": "unrestricted",
        "ADB_ALLOW_SHELL": "true",
        "MCP_LOG_ENABLED": "false",
        "MCP_LOG_DIR": "~/logs/agent-droid-bridge"
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
        "ADB_ALLOW_SHELL": "true",
        "MCP_LOG_ENABLED": "false",
        "MCP_LOG_DIR": "~/logs/agent-droid-bridge"
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
          "ADB_ALLOW_SHELL": "true",
          "MCP_LOG_ENABLED": "false",
          "MCP_LOG_DIR": "~/logs/agent-droid-bridge"
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
  "ADB_ALLOW_SHELL": "true",
  "MCP_LOG_ENABLED": "false",
  "MCP_LOG_DIR": "~/logs/agent-droid-bridge"
}
```

## Optional environment variables

| Variable | Values | Default | Description |
|---|---|---|---|
| `ADB_EXECUTION_MODE` | `unrestricted`, `restricted` | `unrestricted` | In `restricted` mode only commands in the allowlist are permitted |
| `ADB_ALLOW_SHELL` | `true`, `false` | `true` | Set to `false` to block all `adb shell` commands |
| `ADB_CONFIG_PATH` | Absolute path | bundled default | Path to a custom `adb_config.yaml` |
| `MCP_LOG_ENABLED` | `true`, `false` | `false` | Enables session logging. Requires `MCP_LOG_DIR`. |
| `MCP_LOG_DIR` | Absolute path | — | Directory where session logs are written. |

See [configuration.md](configuration.md) for the full YAML reference.

## Verification

### uvx install

Confirm the server starts and the help flag works:

```bash
uvx agent-droid-bridge --help
```

This prints the available tools, environment variables, and documentation link, then exits. If it blocks instead of printing, the installed version predates `--help` support — run `uvx agent-droid-bridge` to start the server normally and verify it connects.

To confirm the installed version:

```bash
uvx run --no-project agent-droid-bridge pip show agent-droid-bridge
```

### From source

```bash
PYTHONPATH=src venv/bin/python -m agent_droid_bridge.server --help
```

Same output as above. To start the server instead:

```bash
venv/bin/python -m agent_droid_bridge.server
```

A successful start produces no output and the process blocks waiting for MCP messages over stdio. Press `Ctrl+C` to stop it.
