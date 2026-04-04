from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from agent_droid_bridge.recorder.config import LoggingConfig


class TestLoggingConfigDefaults:
    def test_enabled_default(self) -> None:
        cfg = LoggingConfig()
        assert cfg.enabled is False

    def test_log_dir_default(self) -> None:
        cfg = LoggingConfig()
        assert cfg.log_dir is None

    def test_tool_log_level_default(self) -> None:
        cfg = LoggingConfig()
        assert cfg.tool_log_level == "INFO"

    def test_adb_log_level_default(self) -> None:
        cfg = LoggingConfig()
        assert cfg.adb_log_level == "INFO"

    def test_max_session_age_days_default(self) -> None:
        cfg = LoggingConfig()
        assert cfg.max_session_age_days == 7

    def test_max_sessions_to_keep_default(self) -> None:
        cfg = LoggingConfig()
        assert cfg.max_sessions_to_keep == 20

    def test_server_log_backup_count_default(self) -> None:
        cfg = LoggingConfig()
        assert cfg.server_log_backup_count == 7

    def test_max_file_size_mb_default(self) -> None:
        cfg = LoggingConfig()
        assert cfg.max_file_size_mb == 50


class TestLoggingConfigValidation:
    def test_invalid_tool_log_level_raises(self) -> None:
        with pytest.raises(ValidationError):
            LoggingConfig(tool_log_level="WARN")

    def test_invalid_adb_log_level_raises(self) -> None:
        with pytest.raises(ValidationError):
            LoggingConfig(adb_log_level="ERROR")

    def test_debug_tool_log_level_accepted(self) -> None:
        cfg = LoggingConfig(tool_log_level="DEBUG")
        assert cfg.tool_log_level == "DEBUG"

    def test_debug_adb_log_level_accepted(self) -> None:
        cfg = LoggingConfig(adb_log_level="DEBUG")
        assert cfg.adb_log_level == "DEBUG"

    def test_max_file_size_mb_zero_is_valid(self) -> None:
        cfg = LoggingConfig(max_file_size_mb=0)
        assert cfg.max_file_size_mb == 0

    def test_negative_max_session_age_days_raises(self) -> None:
        with pytest.raises(ValidationError):
            LoggingConfig(max_session_age_days=-1)

    def test_zero_max_session_age_days_raises(self) -> None:
        with pytest.raises(ValidationError):
            LoggingConfig(max_session_age_days=0)

    def test_negative_max_file_size_mb_raises(self) -> None:
        with pytest.raises(ValidationError):
            LoggingConfig(max_file_size_mb=-1)


class TestLoggingConfigLoad:
    def test_load_mcp_log_enabled_true(self, monkeypatch, tmp_path) -> None:
        monkeypatch.setenv("MCP_LOG_CONFIG_PATH", str(tmp_path / "missing.yaml"))
        monkeypatch.setenv("MCP_LOG_ENABLED", "true")
        monkeypatch.delenv("MCP_LOG_DIR", raising=False)
        cfg = LoggingConfig.load()
        assert cfg.enabled is True

    def test_load_mcp_log_enabled_false(self, monkeypatch, tmp_path) -> None:
        monkeypatch.setenv("MCP_LOG_CONFIG_PATH", str(tmp_path / "missing.yaml"))
        monkeypatch.setenv("MCP_LOG_ENABLED", "false")
        monkeypatch.delenv("MCP_LOG_DIR", raising=False)
        cfg = LoggingConfig.load()
        assert cfg.enabled is False

    def test_load_mcp_log_enabled_case_insensitive(self, monkeypatch, tmp_path) -> None:
        monkeypatch.setenv("MCP_LOG_CONFIG_PATH", str(tmp_path / "missing.yaml"))
        monkeypatch.setenv("MCP_LOG_ENABLED", "TRUE")
        monkeypatch.delenv("MCP_LOG_DIR", raising=False)
        cfg = LoggingConfig.load()
        assert cfg.enabled is True

    def test_load_invalid_mcp_log_enabled_raises(self, monkeypatch, tmp_path) -> None:
        monkeypatch.setenv("MCP_LOG_CONFIG_PATH", str(tmp_path / "missing.yaml"))
        monkeypatch.setenv("MCP_LOG_ENABLED", "yes")
        with pytest.raises(ValueError, match="MCP_LOG_ENABLED"):
            LoggingConfig.load()

    def test_load_mcp_log_dir_sets_log_dir(self, monkeypatch, tmp_path) -> None:
        monkeypatch.setenv("MCP_LOG_CONFIG_PATH", str(tmp_path / "missing.yaml"))
        monkeypatch.delenv("MCP_LOG_ENABLED", raising=False)
        monkeypatch.setenv("MCP_LOG_DIR", str(tmp_path / "logs"))
        cfg = LoggingConfig.load()
        assert cfg.log_dir == Path(str(tmp_path / "logs"))

    def test_load_defaults_when_no_env_and_no_file(self, monkeypatch, tmp_path) -> None:
        monkeypatch.setenv("MCP_LOG_CONFIG_PATH", str(tmp_path / "missing.yaml"))
        monkeypatch.delenv("MCP_LOG_ENABLED", raising=False)
        monkeypatch.delenv("MCP_LOG_DIR", raising=False)
        cfg = LoggingConfig.load()
        assert cfg.enabled is False
        assert cfg.log_dir is None

    def test_load_reads_values_from_yaml(self, monkeypatch, tmp_path) -> None:
        cfg_file = tmp_path / "logging_config.yaml"
        cfg_file.write_text(
            "logging:\n"
            "  enabled: true\n"
            "  tool_log_level: DEBUG\n"
            "  max_session_age_days: 14\n"
        )
        monkeypatch.setenv("MCP_LOG_CONFIG_PATH", str(cfg_file))
        monkeypatch.delenv("MCP_LOG_ENABLED", raising=False)
        monkeypatch.delenv("MCP_LOG_DIR", raising=False)
        cfg = LoggingConfig.load()
        assert cfg.enabled is True
        assert cfg.tool_log_level == "DEBUG"
        assert cfg.max_session_age_days == 14

    def test_load_env_overrides_yaml_enabled(self, monkeypatch, tmp_path) -> None:
        cfg_file = tmp_path / "logging_config.yaml"
        cfg_file.write_text("logging:\n  enabled: false\n")
        monkeypatch.setenv("MCP_LOG_CONFIG_PATH", str(cfg_file))
        monkeypatch.setenv("MCP_LOG_ENABLED", "true")
        monkeypatch.delenv("MCP_LOG_DIR", raising=False)
        cfg = LoggingConfig.load()
        assert cfg.enabled is True
