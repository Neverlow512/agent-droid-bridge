# Logging

The session recorder writes structured logs for every tool call, ADB command, and security event. Logging is disabled by default and must be explicitly enabled via environment variables.

## What gets recorded

Each server startup creates an isolated session directory at `{MCP_LOG_DIR}/session_YYYYMMDD_HHMMSS/`. Four files are written inside it:

| File | Format | What it captures |
|---|---|---|
| `tool.log` | JSONL | Every MCP tool call: name, duration, success/failure, input parameters, and error message if the call failed. At `DEBUG` level, also includes the full response string. |
| `adb.log` | JSONL | Every ADB command executed: command array, exit code, and duration. At `DEBUG` level, also includes stdout and stderr. |
| `security.log` | JSONL | Security events: event type, detail, blocked command, and device serial. Written regardless of log level. |
| `general.log` | plaintext | Human-readable aggregator. Mirrors tool call outcomes (`INFO`/`ERROR`) and security events (`WARNING`). |

A persistent `server.log` lives at `{MCP_LOG_DIR}/server.log` — outside any session directory. It captures server lifecycle events and rotates daily.

## Log levels

`tool_log_level` and `adb_log_level` each accept `INFO` or `DEBUG`.

**`tool.log`**

- `INFO`: tool name, duration, success or failure flag, input parameters, error message (if any).
- `DEBUG`: all of the above, plus the full response string returned by the tool.

**`adb.log`**

- `INFO`: command array, exit code, duration.
- `DEBUG`: all of the above, plus stdout and stderr.

**`security.log`**

Always written at every level. Each record includes event type, detail, blocked command, and device serial.

**`general.log`**

A plaintext aggregator that mirrors tool call outcomes at `INFO` or `ERROR` and security events at `WARNING`. Not affected by `tool_log_level` or `adb_log_level`.

## Session isolation

Each server startup creates a new session directory named `session_YYYYMMDD_HHMMSS`. All per-session files (`tool.log`, `adb.log`, `security.log`, `general.log`) are written exclusively to that directory. Multiple simultaneous server instances each create their own session directory and do not share files.

## Retention

On each startup, the recorder applies two retention rules in order:

1. Sessions older than `max_session_age_days` are deleted.
2. If the remaining session count exceeds `max_sessions_to_keep`, the oldest sessions are removed until the limit is met.

`server.log` rotates daily. The number of daily backup files retained is controlled by `server_log_backup_count`.

## Enabling logging

Logging requires two environment variables set in your MCP client config:

| Variable | Required | Description |
|---|---|---|
| `MCP_LOG_ENABLED` | Yes | Set to `"true"` to enable the recorder. |
| `MCP_LOG_DIR` | Yes (when enabled) | Absolute path to the directory where logs are written. |

If `MCP_LOG_ENABLED` is `true` but `MCP_LOG_DIR` is not set, the server prints a warning to stderr and continues without logging — it does not crash.

Example `env` block (Cursor):

```json
"env": {
  "ADB_EXECUTION_MODE": "unrestricted",
  "ADB_ALLOW_SHELL": "true",
  "MCP_LOG_ENABLED": "true",
  "MCP_LOG_DIR": "/home/youruser/logs/agent-droid-bridge"
}
```

## Configuration reference

All keys live in `configs/logging_config.yaml` (source installs) or the bundled default (uvx installs). Set `ADB_CONFIG_PATH` to override for `adb_config.yaml`; for source installs, `logging_config.yaml` is read from the project root. For `uvx` and `pip` installs, the bundled default copy inside the package is used. Set `MCP_LOG_CONFIG_PATH` to an absolute path to override both.

| Key | Default | Type | Description |
|---|---|---|---|
| `logging.enabled` | `false` | boolean | Master switch. Can be overridden with `MCP_LOG_ENABLED`. |
| `logging.tool_log_level` | `INFO` | string | `INFO` or `DEBUG`. DEBUG adds the full tool response to `tool.log`. |
| `logging.adb_log_level` | `INFO` | string | `INFO` or `DEBUG`. DEBUG adds stdout and stderr to `adb.log`. |
| `logging.max_session_age_days` | `7` | integer | Sessions older than this are deleted on startup. Must be > 0. |
| `logging.max_sessions_to_keep` | `20` | integer | Maximum number of session directories to retain. Oldest are removed first. Must be > 0. |
| `logging.server_log_backup_count` | `7` | integer | Number of daily `server.log` rotations to keep. |
| `logging.max_file_size_mb` | `50` | integer | Per-file size cap in MB. Writes stop when a log file reaches this limit. |

## JSONL format

Each log file (`tool.log`, `adb.log`, `security.log`) is newline-delimited JSON — one JSON object per line. Every record contains a `timestamp` field in ISO 8601 UTC format.
