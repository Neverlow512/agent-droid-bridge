# Extra Tool Packs

The core server ships with 14 built-in tools. Extra tool packs are optional modules that add domain-specific tools on top of those — without touching the core. They are disabled by default and loaded at startup when enabled in `adb_config.yaml`.

Use a pack when you need capabilities that go beyond basic screen interaction, input, and ADB commands. The `app_manager` pack, for example, adds package management, app lifecycle control, APK extraction, and intent injection — functionality that would clutter the core toolset for users who don't need it.

## Enabling a pack

In `adb_config.yaml`, set `enabled` to `true` and list the pack names in `packs`:

```yaml
extra_tool_packs:
  enabled: true
  packs: ["app_manager"]
```

Restart the server after editing the config. See [configuration.md](configuration.md) for the full key reference.

## Available packs

**app_manager** — 9 tools for package management, app lifecycle control, APK extraction, runtime permission management, and intent injection. Designed for app testing, dynamic analysis, and automated setup and teardown workflows. Full parameter reference: [tools.md](tools.md#app_manager-pack).

## Writing a pack

A pack is a Python package at `src/agent_droid_bridge/extra_tool_packs/<name>/`. It requires an `__init__.py` that exposes a `register()` function with this exact signature:

```python
from fastmcp import FastMCP
from agent_droid_bridge.adb.service import ADBService

async def register(mcp: FastMCP, adb: ADBService) -> None:
    ...
```

The function registers tools on the `mcp` instance using `@mcp.tool()` decorators. Both `mcp` and `adb` are provided by the server at startup — the pack does not instantiate either.

Optionally, expose a `PACK_META` dict at module level. When present, the pack's description appears in the server's startup instructions:

```python
PACK_META = {"name": "my_pack", "description": "What this pack provides."}
```

Minimal example:

```python
from fastmcp import FastMCP
from agent_droid_bridge.adb.service import ADBService

PACK_META = {"name": "my_pack", "description": "A minimal example pack."}


async def register(mcp: FastMCP, adb: ADBService) -> None:
    @mcp.tool()
    async def my_tool(message: str) -> str:
        """Returns the message unchanged."""
        return message
```

To enable the pack during development, set `enabled: true` and add the pack name to `packs` in `adb_config.yaml`, then restart the server. See [CONTRIBUTING.md](../CONTRIBUTING.md) for test expectations and code standards.
