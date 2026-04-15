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
        "ADB_PATH": "adb",
        "ADB_EXTRA_TOOL_PACKS": "",
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
        "ADB_PATH": "adb",
        "ADB_EXTRA_TOOL_PACKS": "",
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
          "ADB_PATH": "adb",
          "ADB_EXTRA_TOOL_PACKS": "",
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
  "ADB_PATH": "adb",
  "ADB_EXTRA_TOOL_PACKS": "",
  "MCP_LOG_ENABLED": "false",
  "MCP_LOG_DIR": "~/logs/agent-droid-bridge"
}
```

## Optional environment variables

**Core behavior**

| Variable | Default | Description |
|---|---|---|
| `ADB_EXECUTION_MODE` | `unrestricted` | Security mode. `unrestricted` allows all shell commands (with optional denylist); `restricted` allows only commands in `ADB_SHELL_ALLOWLIST`. |
| `ADB_ALLOW_SHELL` | `true` | Set to `false` to block all `adb shell` commands regardless of execution mode. |
| `ADB_PATH` | `adb` | Path to the ADB binary. Use a full path if `adb` is not on your system PATH (e.g. `C:\platform-tools\adb.exe` on Windows, `/opt/homebrew/bin/adb` on macOS with Homebrew). |
| `ADB_LOG_LEVEL` | `INFO` | Server process log level. Accepted: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. |

**Tools**

| Variable | Default | Description |
|---|---|---|
| `ADB_EXTRA_TOOL_PACKS` | *(empty)* | Comma-separated list of extra tool packs to load at startup. Available: `app_manager`. Example: `app_manager`. |
| `ADB_DENIED_TOOLS` | *(empty)* | Comma-separated list of tool names to hide from the agent at startup. Example: `execute_adb_command,get_ui_hierarchy`. |
| `ADB_SHELL_ALLOWLIST` | *(empty)* | Comma-separated list of shell commands permitted in `restricted` mode. Empty = block all. Example: `dumpsys,pm,am`. |
| `ADB_SHELL_DENYLIST` | *(empty)* | Comma-separated list of shell commands blocked in `unrestricted` mode (basename-matched). Example: `rm,reboot,su`. |

**Config source**

| Variable | Default | Description |
|---|---|---|
| `ADB_CONFIG_SOURCE` | `env` | Set to `yaml` to load configuration from `adb_config.yaml` instead of environment variables. Use `ADB_CONFIG_PATH` to point to a custom YAML file when in `yaml` mode. |
| `ADB_CONFIG_PATH` | *(bundled default)* | Absolute path to a custom `adb_config.yaml`. Only used when `ADB_CONFIG_SOURCE=yaml`. |

**Logging**

| Variable | Default | Description |
|---|---|---|
| `MCP_LOG_ENABLED` | `false` | Set to `true` to enable session logging. Requires `MCP_LOG_DIR`. |
| `MCP_LOG_DIR` | *(none)* | Absolute path to the directory where session logs are written. Required when `MCP_LOG_ENABLED` is `true`. |

**Timeouts (advanced)**

| Variable | Default | Description |
|---|---|---|
| `ADB_COMMAND_TIMEOUT` | `30` | Maximum seconds to wait for any ADB command. |
| `ADB_SCREENSHOT_TIMEOUT` | `60` | Maximum seconds to wait for a screenshot capture. |
| `ADB_UI_CHANGE_TIMEOUT` | `10` | Default timeout for `detect_ui_change`. |
| `ADB_UI_CHANGE_POLL_INTERVAL` | `0.5` | How often (in seconds) `detect_ui_change` polls the UI hierarchy. |
| `ADB_AAPT_TIMEOUT` | `10` | Maximum seconds to wait for `aapt dump badging` (used by `app_manager` pack). |

For the full YAML configuration reference, see [configuration.md](configuration.md).

For common setup issues, see [docs/troubleshooting.md](troubleshooting.md).

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
