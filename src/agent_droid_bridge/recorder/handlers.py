from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import LoggingConfig
from .writers import JSONLWriter


class SessionLogger:
    def __init__(self, config: LoggingConfig, session_dir: Path) -> None:
        self._config = config
        max_size_bytes = config.max_file_size_mb * 1024 * 1024

        self._tool_writer = JSONLWriter(session_dir / "tool.log", max_size_bytes)
        self._adb_writer = JSONLWriter(session_dir / "adb.log", max_size_bytes)
        self._security_writer = JSONLWriter(session_dir / "security.log", max_size_bytes)

        self._general_logger = logging.getLogger(f"recorder.general.{session_dir.name}")
        self._general_logger.setLevel(logging.DEBUG)
        self._general_logger.propagate = False

        handler = logging.FileHandler(session_dir / "general.log", encoding="utf-8")
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )
        self._general_logger.addHandler(handler)

    def tool_call(
        self,
        tool_name: str,
        duration_ms: float,
        success: bool,
        error: str | None = None,
        params: dict | None = None,
        response: str | None = None,
    ) -> None:
        record: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "tool_name": tool_name,
            "duration_ms": round(duration_ms, 2),
            "success": success,
        }
        if error:
            record["error"] = error
        if params is not None:
            record["params"] = params
        if self._config.tool_log_level == "DEBUG" and response is not None:
            record["response"] = response

        self._tool_writer.write(record)

        if success:
            self._general_logger.info("tool_call: %s %.2fms OK", tool_name, duration_ms)
        else:
            self._general_logger.error(
                "tool_call: %s %.2fms FAIL: %s",
                tool_name,
                duration_ms,
                error if error is not None else "unknown",
            )

    def adb_command(
        self,
        command: list[str],
        exit_code: int,
        duration_ms: float,
        stdout: str | None = None,
        stderr: str | None = None,
    ) -> None:
        record: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "command": command,
            "exit_code": exit_code,
            "duration_ms": round(duration_ms, 2),
        }
        if self._config.adb_log_level == "DEBUG" and stdout is not None:
            record["stdout"] = stdout
        if self._config.adb_log_level == "DEBUG" and stderr is not None:
            record["stderr"] = stderr

        self._adb_writer.write(record)

        if exit_code != 0:
            self._general_logger.error(
                "adb_command failed: exit=%d cmd=%s",
                exit_code,
                command[0] if command else "unknown",
            )

    def security_event(
        self,
        event_type: str,
        detail: str,
        command: list[str] | None = None,
        serial: str | None = None,
    ) -> None:
        record: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "event_type": event_type,
            "detail": detail,
        }
        if command:
            record["command"] = command
        if serial:
            record["serial"] = serial

        self._security_writer.write(record)
        self._general_logger.warning("[SECURITY] %s: %s", event_type, detail)
