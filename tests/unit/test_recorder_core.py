from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

import agent_droid_bridge.recorder as recorder_module
from agent_droid_bridge.recorder import get_session_logger, setup_logging
from agent_droid_bridge.recorder.config import LoggingConfig
from agent_droid_bridge.recorder.handlers import SessionLogger


@pytest.fixture(autouse=True)
def reset_session_logger():
    recorder_module._session_logger = None
    adb_bridge_logger = logging.getLogger("agent_droid_bridge")
    handlers_before = list(adb_bridge_logger.handlers)
    yield
    recorder_module._session_logger = None
    for h in list(adb_bridge_logger.handlers):
        if h not in handlers_before:
            adb_bridge_logger.removeHandler(h)
            h.close()


def _make_session_logger(session_dir: Path, tool_log_level: str = "INFO") -> SessionLogger:
    cfg = LoggingConfig(
        enabled=True,
        tool_log_level=tool_log_level,
        adb_log_level="INFO",
        max_file_size_mb=50,
    )
    return SessionLogger(cfg, session_dir)


class TestSessionLoggerToolCall:
    def test_writes_tool_name_duration_success(self, tmp_path) -> None:
        logger = _make_session_logger(tmp_path)
        logger.tool_call("my_tool", duration_ms=42.5, success=True)
        record = json.loads((tmp_path / "tool.log").read_text().strip())
        assert record["tool_name"] == "my_tool"
        assert record["duration_ms"] == 42.5
        assert record["success"] is True

    def test_info_level_includes_params_but_not_response(self, tmp_path) -> None:
        logger = _make_session_logger(tmp_path)
        logger.tool_call("my_tool", duration_ms=10.0, success=True, params={"x": 1}, response="ok")
        record = json.loads((tmp_path / "tool.log").read_text().strip())
        assert record["params"] == {"x": 1}
        assert "response" not in record

    def test_debug_level_includes_params_and_response(self, tmp_path) -> None:
        logger = _make_session_logger(tmp_path, tool_log_level="DEBUG")
        logger.tool_call("my_tool", duration_ms=10.0, success=True, params={"x": 1}, response="ok")
        record = json.loads((tmp_path / "tool.log").read_text().strip())
        assert record["params"] == {"x": 1}
        assert record["response"] == "ok"

    def test_debug_level_empty_params_still_included(self, tmp_path) -> None:
        logger = _make_session_logger(tmp_path, tool_log_level="DEBUG")
        logger.tool_call("my_tool", duration_ms=10.0, success=True, params={}, response="ok")
        record = json.loads((tmp_path / "tool.log").read_text().strip())
        assert "params" in record
        assert record["params"] == {}

    def test_empty_error_string_does_not_produce_unknown(self, tmp_path) -> None:
        logger = _make_session_logger(tmp_path)
        logger.tool_call("my_tool", duration_ms=5.0, success=False, error="")
        record = json.loads((tmp_path / "tool.log").read_text().strip())
        assert record.get("error") != "unknown"

    def test_failure_writes_success_false_and_error(self, tmp_path) -> None:
        logger = _make_session_logger(tmp_path)
        logger.tool_call("my_tool", duration_ms=5.0, success=False, error="timeout")
        record = json.loads((tmp_path / "tool.log").read_text().strip())
        assert record["success"] is False
        assert record["error"] == "timeout"


class TestSessionLoggerAdbCommand:
    def test_info_level_writes_command_exit_code_duration(self, tmp_path) -> None:
        logger = _make_session_logger(tmp_path)
        logger.adb_command(["adb", "shell", "ls"], exit_code=0, duration_ms=30.0)
        record = json.loads((tmp_path / "adb.log").read_text().strip())
        assert record["command"] == ["adb", "shell", "ls"]
        assert record["exit_code"] == 0
        assert record["duration_ms"] == 30.0

    def test_info_level_does_not_include_stdout_or_stderr(self, tmp_path) -> None:
        logger = _make_session_logger(tmp_path)
        logger.adb_command(
            ["adb", "shell"], exit_code=0, duration_ms=5.0, stdout="output", stderr="err"
        )
        record = json.loads((tmp_path / "adb.log").read_text().strip())
        assert "stdout" not in record
        assert "stderr" not in record

    def test_debug_level_empty_stdout_still_included(self, tmp_path) -> None:
        cfg = LoggingConfig(enabled=True, adb_log_level="DEBUG", max_file_size_mb=50)
        logger = SessionLogger(cfg, tmp_path)
        logger.adb_command(["adb", "shell"], exit_code=0, duration_ms=5.0, stdout="")
        record = json.loads((tmp_path / "adb.log").read_text().strip())
        assert "stdout" in record
        assert record["stdout"] == ""

    def test_debug_level_includes_stdout_and_stderr(self, tmp_path) -> None:
        cfg = LoggingConfig(enabled=True, adb_log_level="DEBUG", max_file_size_mb=50)
        logger = SessionLogger(cfg, tmp_path)
        logger.adb_command(
            ["adb", "logcat"], exit_code=0, duration_ms=10.0, stdout="line1", stderr=""
        )
        record = json.loads((tmp_path / "adb.log").read_text().strip())
        assert record["stdout"] == "line1"
        assert record["stderr"] == ""


class TestSessionLoggerSecurityEvent:
    def test_writes_event_type_and_detail(self, tmp_path) -> None:
        logger = _make_session_logger(tmp_path)
        logger.security_event("invalid_serial", "serial failed validation")
        record = json.loads((tmp_path / "security.log").read_text().strip())
        assert record["event_type"] == "invalid_serial"
        assert record["detail"] == "serial failed validation"

    def test_with_command_includes_command_in_record(self, tmp_path) -> None:
        logger = _make_session_logger(tmp_path)
        logger.security_event(
            "injection_attempt", "suspicious input", command=["adb", "shell", "malicious"]
        )
        record = json.loads((tmp_path / "security.log").read_text().strip())
        assert record["command"] == ["adb", "shell", "malicious"]

    def test_without_command_command_key_absent(self, tmp_path) -> None:
        logger = _make_session_logger(tmp_path)
        logger.security_event("test_event", "some detail")
        record = json.loads((tmp_path / "security.log").read_text().strip())
        assert "command" not in record


class TestSessionLoggerLogFiles:
    def test_general_log_created_on_init(self, tmp_path) -> None:
        _make_session_logger(tmp_path)
        assert (tmp_path / "general.log").exists()

    def test_all_four_log_files_exist_after_calls(self, tmp_path) -> None:
        logger = _make_session_logger(tmp_path)
        logger.tool_call("my_tool", duration_ms=1.0, success=True)
        logger.adb_command(["adb", "devices"], exit_code=0, duration_ms=1.0)
        logger.security_event("test", "detail")
        assert (tmp_path / "tool.log").exists()
        assert (tmp_path / "adb.log").exists()
        assert (tmp_path / "security.log").exists()
        assert (tmp_path / "general.log").exists()


class TestSetupLogging:
    def test_get_session_logger_returns_none_before_setup(self) -> None:
        assert get_session_logger() is None

    def test_setup_logging_disabled_leaves_logger_none(self, tmp_path) -> None:
        cfg = LoggingConfig(enabled=False, log_dir=tmp_path / "logs")
        setup_logging(cfg)
        assert get_session_logger() is None

    def test_setup_logging_enabled_with_no_log_dir_prints_warning(self, capsys) -> None:
        cfg = LoggingConfig(enabled=True, log_dir=None)
        setup_logging(cfg)
        captured = capsys.readouterr()
        assert "WARNING" in captured.err
        assert get_session_logger() is None

    def test_setup_logging_valid_config_creates_session_dir(self, tmp_path) -> None:
        log_dir = tmp_path / "logs"
        cfg = LoggingConfig(enabled=True, log_dir=log_dir, max_file_size_mb=50)
        setup_logging(cfg)
        session_dirs = [d for d in log_dir.iterdir() if d.name.startswith("session_")]
        assert len(session_dirs) == 1

    def test_setup_logging_valid_config_sets_session_logger(self, tmp_path) -> None:
        log_dir = tmp_path / "logs"
        cfg = LoggingConfig(enabled=True, log_dir=log_dir, max_file_size_mb=50)
        setup_logging(cfg)
        assert isinstance(get_session_logger(), SessionLogger)

    def test_setup_logging_unwritable_log_dir_prints_warning(self, tmp_path, capsys) -> None:
        parent = tmp_path / "noaccess"
        parent.mkdir()
        parent.chmod(0o555)
        log_dir = parent / "logs"
        cfg = LoggingConfig(enabled=True, log_dir=log_dir, max_file_size_mb=50)
        try:
            setup_logging(cfg)
            captured = capsys.readouterr()
            assert "WARNING" in captured.err
            assert get_session_logger() is None
        finally:
            parent.chmod(0o755)
