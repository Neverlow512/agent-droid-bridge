# Configuration

The server reads `configs/adb_config.yaml` at the project root on startup. All keys are optional — omitting a key leaves the default in place. Edit this file to change the ADB binary location, adjust timeouts, or set the log verbosity.

## Configuration reference

| Key | Default | Type | Description |
|---|---|---|---|
| `adb.path` | `adb` | string | Path to the ADB binary. Use an absolute path if `adb` is not on your system PATH. |
| `adb.command_timeout` | `30` | integer (seconds) | Maximum time to wait for any ADB command before killing the process and returning an error. Must be a positive integer. |
| `adb.screenshot_timeout` | `60` | integer (seconds) | Maximum time to wait for a screenshot capture. Separate from `command_timeout` because screen capture can be slower on some devices. Must be a positive integer. |
| `server.log_level` | `INFO` | string | Python logging level. Accepted values: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. |
| `adb.allowed_shell_commands` | `[]` | list of strings | Commands permitted when `ADB_EXECUTION_MODE` is `restricted`. Each entry is the first token of the shell command (e.g. `ls`, `pm`). Empty list blocks all commands in restricted mode. |
| `adb.ui_change_timeout` | `10` | integer (seconds) | Default timeout for `detect_ui_change`. Must be a positive integer. |
| `adb.ui_change_poll_interval` | `0.5` | float (seconds) | How often `detect_ui_change` polls the UI hierarchy. Must be positive. |

## Applying changes

The config file is loaded once at server startup and cached for the lifetime of the process. After editing `adb_config.yaml`, restart the server for changes to take effect. If the file does not exist, the server starts with all defaults and logs a warning.

## Environment variables

These are set in your MCP client's `env` block (not in `adb_config.yaml`) and control the security behavior of `execute_adb_command`.

| Variable | Values | Default | Description |
|---|---|---|---|
| `ADB_EXECUTION_MODE` | `unrestricted` / `restricted` | `unrestricted` | In `restricted` mode, only commands listed in `adb.allowed_shell_commands` are permitted. Top-level ADB commands (`use_shell: false`) are also blocked in restricted mode. |
| `ADB_ALLOW_SHELL` | `true` / `false` | `true` | When `false`, `execute_adb_command` with `use_shell: true` is blocked entirely. |

Internal tools (`get_ui_hierarchy`, `take_screenshot`, `tap_screen`, etc.) are not affected by these settings.
