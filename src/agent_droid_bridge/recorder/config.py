from __future__ import annotations

import os
from importlib.resources import files as _resource_files
from pathlib import Path

import yaml
from pydantic import BaseModel, field_validator

_VALID_LOG_LEVELS = {"INFO", "DEBUG"}


class LoggingConfig(BaseModel):
    enabled: bool = False
    log_dir: Path | None = None
    tool_log_level: str = "INFO"
    adb_log_level: str = "INFO"
    max_session_age_days: int = 7
    max_sessions_to_keep: int = 20
    server_log_backup_count: int = 7
    max_file_size_mb: int = 50

    @field_validator("tool_log_level", "adb_log_level")
    @classmethod
    def _validate_log_level(cls, v: str) -> str:
        upper = v.upper()
        if upper not in _VALID_LOG_LEVELS:
            raise ValueError(f"log level must be one of {_VALID_LOG_LEVELS}, got {v!r}")
        return upper

    @field_validator("max_session_age_days", "max_sessions_to_keep")
    @classmethod
    def _validate_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("value must be > 0")
        return v

    @field_validator("server_log_backup_count", "max_file_size_mb")
    @classmethod
    def _validate_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("value must be >= 0")
        return v

    @classmethod
    def load(cls) -> LoggingConfig:
        raw: dict = {}

        config_path = _resolve_config_path()
        if config_path is not None and config_path.exists():
            with config_path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            raw = data.get("logging", {})

        enabled_env = os.environ.get("MCP_LOG_ENABLED")
        if enabled_env is not None:
            lower = enabled_env.strip().lower()
            if lower == "true":
                raw["enabled"] = True
            elif lower == "false":
                raw["enabled"] = False
            else:
                raise ValueError(
                    f"MCP_LOG_ENABLED must be 'true' or 'false', got {enabled_env!r}"
                )

        log_dir_env = os.environ.get("MCP_LOG_DIR")
        if log_dir_env:
            raw["log_dir"] = Path(log_dir_env)

        return cls.model_validate(raw)


def _resolve_config_path() -> Path | None:
    env_path = os.environ.get("MCP_LOG_CONFIG_PATH")
    if env_path:
        return Path(env_path)
    root_copy = Path(__file__).parent.parent.parent.parent / "configs" / "logging_config.yaml"
    if root_copy.exists():
        return root_copy
    return Path(str(_resource_files("agent_droid_bridge") / "configs" / "logging_config.yaml"))
