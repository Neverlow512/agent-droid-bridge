![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue?style=flat-square) ![License MIT](https://img.shields.io/badge/license-MIT-green?style=flat-square) ![MCP Compatible](https://img.shields.io/badge/MCP-compatible-purple?style=flat-square) [![PyPI](https://img.shields.io/pypi/v/agent-droid-bridge?style=flat-square&cacheSeconds=300)](https://pypi.org/project/agent-droid-bridge/) [![MCP Registry](https://img.shields.io/badge/MCP%20Registry-listed-orange?style=flat-square)](https://vemonet.github.io/mcp-registry/?search=agent-droid-bridge)

# Agent Droid Bridge

Agent Droid Bridge is an MCP server that connects AI agents to Android devices and emulators over ADB. It is built for mobile automation, app testing, dynamic analysis, and reverse engineering: exposing the full surface of ADB as structured tools that any MCP-compatible AI client can call directly. If ADB can do it, an agent can do it.

> Note: Purpose-built tools return structured, minimal responses instead of raw XML dumps, keeping agent workflows fast and context consumption low, while keeping performance high.

[![agent-droid-bridge MCP server](https://glama.ai/mcp/servers/Neverlow512/agent-droid-bridge/badges/card.svg)](https://glama.ai/mcp/servers/Neverlow512/agent-droid-bridge)

## Demo

[![Agent Droid Bridge Demo](https://img.youtube.com/vi/otIWBBNe-VU/maxresdefault.jpg)](https://youtu.be/otIWBBNe-VU)

The demo above runs through a few straightforward tasks to show what a connected agent can do, and this is just scratching the surface:

- Installs the Paint app, opens it, and draws a house by calculating pixel coordinates for the walls and roof
- Opens the device browser, searches for "MCP Wikipedia", navigates to the result page, and takes a screenshot
- Opens the Calculator, computes 1337 × 42, and extracts the result to the host machine
- Opens Contacts, creates a new entry with a name and phone number, and confirms it saved
- Opens the Calendar and schedules an appointment for a specific date
- Opens Settings and toggles dark mode
- Extracts the Calculator APK from the device to the host machine
- Installs Notepad, writes a one-sentence summary of every task completed, and takes a final screenshot

## What it does

- Exposes 13 MCP tools covering screen capture, UI inspection, screen reading, element extraction, touch and swipe input, text entry, keycode events, app launching, and arbitrary ADB commands
- Auto-detects the connected device when only one is present; presents a device list and requires the user to choose when multiple are connected
- All commands parsed via `shlex` — no shell injection possible
- Runs over stdio, compatible with any MCP-capable AI client
- Purpose-built screen reading and element extraction tools return structured, minimal responses — a fraction of the size of a raw XML hierarchy — keeping agent context lean across long automation runs

## Install

```bash
uvx agent-droid-bridge
```

No cloning or virtual environments needed. Requires Python 3.11+ and ADB installed on your host.

`uvx` is provided by [uv](https://docs.astral.sh/uv/). If you don't have it: `curl -LsSf https://astral.sh/uv/install.sh | sh`

To install from source instead, see [docs/setup.md — Option B](docs/setup.md#option-b--from-source).

To verify the install: `uvx agent-droid-bridge --help`

## Quick start

1. Install ADB — see [docs/setup.md](docs/setup.md) for platform-specific instructions
2. Connect an Android device or start an emulator
3. Add the server to your MCP client config:

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

1. Prompt your agent to use the `agent-droid-bridge` MCP tools

Full setup guide: [docs/setup.md](docs/setup.md)

## Tools


| Tool                  | What it does                                                                                                                                                      |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `get_ui_hierarchy`    | Returns the current screen as an XML UI hierarchy                                                                                                                 |
| `take_screenshot`     | Captures the screen as a base64-encoded PNG                                                                                                                       |
| `tap_screen`          | Sends a tap gesture at pixel coordinates                                                                                                                          |
| `swipe_screen`        | Sends a swipe gesture between two points over a given duration                                                                                                    |
| `type_text`           | Types text into the focused input field                                                                                                                           |
| `press_key`           | Sends an Android keycode event (Back, Home, Enter, etc.)                                                                                                          |
| `launch_app`          | Launches an app by its `package/activity` component name                                                                                                          |
| `execute_adb_command` | Runs an arbitrary ADB or ADB shell command                                                                                                                        |
| `list_devices`        | Lists all Android devices currently visible to ADB with their serial, state, and model                                                                            |
| `snapshot_ui`         | Takes a lightweight UI snapshot and returns a token for use with `detect_ui_change`                                                                               |
| `detect_ui_change`    | Polls for a UI change after an action; accepts a snapshot token as baseline; returns hierarchy only when requested                                                |
| `get_screen_elements` | Parses the UI hierarchy and returns structured elements with coordinates and interaction properties; supports `tappable`, `interactive`, `input`, and `all` modes |
| `get_screen_text`     | Returns all visible text on screen sorted top-to-bottom, as plain text                                                                                            |


Full parameter reference: [docs/tools.md](docs/tools.md)

## Documentation


| File                                           | Description                                               |
| ---------------------------------------------- | --------------------------------------------------------- |
| [docs/setup.md](docs/setup.md)                 | Prerequisites, installation, and MCP client configuration |
| [docs/tools.md](docs/tools.md)                 | Full parameter reference for all 13 tools                 |
| [docs/configuration.md](docs/configuration.md) | Reference for `adb_config.yaml` and environment variables |


## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on setup, code standards, and submitting pull requests.

To report a security vulnerability, follow the process in [SECURITY.md](SECURITY.md) — do not open a public issue.

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Neverlow512/agent-droid-bridge&type=Date)](https://star-history.com/#Neverlow512/agent-droid-bridge&Date)
<!-- mcp-name: io.github.Neverlow512/agent-droid-bridge -->

