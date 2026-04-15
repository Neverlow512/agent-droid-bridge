# Configuration

By default, the server loads all configuration from environment variables set in your MCP client's `env` block (`ADB_CONFIG_SOURCE=env`). No file editing is required. Set `ADB_CONFIG_SOURCE=yaml` to switch to legacy YAML-based configuration — the server will then read from `configs/adb_config.yaml`. Source installs read the file at the project root; installed users (`uvx` / `pip`) receive a bundled default. Set `ADB_CONFIG_PATH` to an absolute path to override the YAML file location. All keys are optional — omitting a key leaves the default in place.

## Configuration reference

### `adb`

| Key | Default | Type | Description |
|---|---|---|---|
| `adb.path` | `adb` | string | Path to the ADB binary. Use an absolute path if `adb` is not on your system PATH. |
| `adb.command_timeout` | `30` | integer (seconds) | Maximum time to wait for any ADB command before killing the process and returning an error. Must be a positive integer. |
| `adb.screenshot_timeout` | `60` | integer (seconds) | Maximum time to wait for a screenshot capture. Separate from `command_timeout` because screen capture can be slower on some devices. Must be a positive integer. |
| `adb.ui_change_timeout` | `10` | integer (seconds) | Default timeout for `detect_ui_change`. Must be a positive integer. |
| `adb.ui_change_poll_interval` | `0.5` | float (seconds) | How often `detect_ui_change` polls the UI hierarchy. Must be positive. |

### `server`

| Key | Default | Type | Description |
|---|---|---|---|
| `server.log_level` | `INFO` | string | Python logging level. Accepted values: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. |

### `security`

Controls which shell commands are permitted or blocked when `execute_adb_command` is called. The active mode is set via the `ADB_EXECUTION_MODE` environment variable.

| Key | Default | Type | Description |
|---|---|---|---|
| `security.shell_command_allowlist` | `[]` | list of strings | Used in `restricted` mode. Only commands whose first token matches an entry in this list are permitted. An empty list blocks all shell commands in restricted mode. |
| `security.shell_command_denylist` | `[]` | list of strings | Used in `unrestricted` mode. Commands whose basename matches an entry in this list are blocked. An empty list permits all commands. |

### `tools`

| Key | Default | Type | Description |
|---|---|---|---|
| `tools.denied` | `[]` | list of strings | Tool names listed here are hidden from the agent at server startup. Hidden tools are not registered with the MCP server and cannot be called. Example: `["execute_adb_command", "get_ui_hierarchy"]`. |

### `extra_tool_packs`

Optional feature modules that register additional tool groups at startup.

| Key | Default | Type | Description |
|---|---|---|---|
| `extra_tool_packs.enabled` | `false` | boolean | When `false`, no extra packs are loaded regardless of the `packs` list. |
| `extra_tool_packs.packs` | `[]` | list of strings | Names of packs to load when `enabled` is `true`. Example: `["app_manager"]`. |

Pack authors can optionally expose a module-level `PACK_META = {"description": "..."}` dict in their pack module. When present, the description appears in the server's startup instructions under that pack's section. The `app_manager` pack is the available pack. For the pack contract and instructions on writing your own pack, see [extra-tool-packs.md](extra-tool-packs.md).

### `logging`

| Key | Default | Type | Description |
|---|---|---|---|
| `logging.enabled` | `false` | boolean | Master switch for the recorder. Set via `MCP_LOG_ENABLED` environment variable or this key. |
| `logging.tool_log_level` | `INFO` | string | Accepted: `INFO`, `DEBUG`. At DEBUG, tool responses are included in `tool.log`. |
| `logging.adb_log_level` | `INFO` | string | Accepted: `INFO`, `DEBUG`. At DEBUG, stdout and stderr are included in `adb.log`. |
| `logging.max_session_age_days` | `7` | integer | Sessions older than this are deleted on server startup. Must be > 0. |
| `logging.max_sessions_to_keep` | `20` | integer | Max session directories to retain. Oldest removed first. Must be > 0. |
| `logging.server_log_backup_count` | `7` | integer | Number of daily `server.log` backups to keep. |
| `logging.max_file_size_mb` | `50` | integer | Per-file size cap in megabytes. Writes stop when the limit is reached. |

See [logging.md](logging.md) for a full explanation of session structure, log levels, and retention behaviour.

## Environment variables

All environment variables are set in your MCP client's `env` block. For the full reference grouped by category, see [setup.md](setup.md#optional-environment-variables).

**Key variables for env mode (default):**

| Variable | Default | Description |
|---|---|---|
| `ADB_CONFIG_SOURCE` | `env` | `env` loads from environment variables (default). `yaml` loads from `adb_config.yaml`. |
| `ADB_EXECUTION_MODE` | `unrestricted` | `unrestricted` = denylist-based; `restricted` = allowlist-only. |
| `ADB_ALLOW_SHELL` | `true` | `false` blocks all `adb shell` commands. |
| `ADB_PATH` | `adb` | ADB binary path. Use full path if not on system PATH. |
| `ADB_EXTRA_TOOL_PACKS` | *(empty)* | Comma-separated pack names. Example: `app_manager`. |
| `ADB_DENIED_TOOLS` | *(empty)* | Comma-separated tool names to hide at startup. |
| `ADB_SHELL_ALLOWLIST` | *(empty)* | Allowed shell commands in `restricted` mode. |
| `ADB_SHELL_DENYLIST` | *(empty)* | Blocked shell commands in `unrestricted` mode. |
| `ADB_COMMAND_TIMEOUT` | `30` | ADB command timeout in seconds. |
| `ADB_SCREENSHOT_TIMEOUT` | `60` | Screenshot timeout in seconds. |
| `ADB_UI_CHANGE_TIMEOUT` | `10` | `detect_ui_change` timeout in seconds. |
| `ADB_UI_CHANGE_POLL_INTERVAL` | `0.5` | `detect_ui_change` poll interval in seconds. |
| `ADB_AAPT_TIMEOUT` | `10` | `aapt` timeout in seconds (`app_manager` pack). |
| `ADB_LOG_LEVEL` | `INFO` | Server log level. Accepted: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. |
| `ADB_CONFIG_PATH` | *(bundled)* | Custom YAML file path. Only used when `ADB_CONFIG_SOURCE=yaml`. |
| `MCP_LOG_ENABLED` | `false` | Enables the session recorder. |
| `MCP_LOG_DIR` | *(none)* | Log directory. Required when `MCP_LOG_ENABLED=true`. |

Internal tools (`get_ui_hierarchy`, `take_screenshot`, `tap_screen`, etc.) are not affected by `ADB_EXECUTION_MODE` or `ADB_ALLOW_SHELL`.

## Applying changes

The config file is loaded once at server startup and cached for the lifetime of the process. After editing the config file, restart the server for changes to take effect. If the file does not exist, the server starts with all defaults and logs a warning.

In `env` mode, configuration changes take effect on the next server restart — no file editing needed. In `yaml` mode, edit `adb_config.yaml` and restart the server.
