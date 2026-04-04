# Configuration

The server loads its configuration from a YAML file on startup. Source installs read `configs/adb_config.yaml` at the project root directly. Installed users (`uvx` / `pip`) receive a bundled default copy. Set `ADB_CONFIG_PATH` to an absolute path to override both. All keys are optional — omitting a key leaves the default in place.

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
| `extra_tool_packs.packs` | `[]` | list of strings | Names of packs to load when `enabled` is `true`. Example: `["debugging"]`. |

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

These are set in your MCP client's `env` block (not in `adb_config.yaml`) and control the security behavior of `execute_adb_command`.

| Variable | Values | Default | Description |
|---|---|---|---|
| `ADB_EXECUTION_MODE` | `unrestricted` / `restricted` | `unrestricted` | In `restricted` mode, shell commands must match `security.shell_command_allowlist` and top-level ADB commands (`use_shell: false`) are blocked entirely. |
| `ADB_ALLOW_SHELL` | `true` / `false` | `true` | When `false`, `execute_adb_command` with `use_shell: true` is blocked entirely, regardless of execution mode. |
| `ADB_CONFIG_PATH` | absolute path | — | Path to a custom config file. Overrides both the project root copy and the bundled default. |
| `MCP_LOG_ENABLED` | `true` / `false` | `false` | Enables the session recorder. Requires `MCP_LOG_DIR` to be set. |
| `MCP_LOG_DIR` | absolute path | — | Directory where logs are written. Required when `MCP_LOG_ENABLED` is `true`. |

Internal tools (`get_ui_hierarchy`, `take_screenshot`, `tap_screen`, etc.) are not affected by `ADB_EXECUTION_MODE` or `ADB_ALLOW_SHELL`.

## Applying changes

The config file is loaded once at server startup and cached for the lifetime of the process. After editing the config file, restart the server for changes to take effect. If the file does not exist, the server starts with all defaults and logs a warning.
