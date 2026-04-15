from __future__ import annotations

import logging
import os
import re
from importlib.resources import files as _resource_files
from pathlib import Path
from typing import Annotated

import yaml
from pydantic import BaseModel, BeforeValidator, field_validator

from .recorder.config import LoggingConfig

DEVICE_SERIAL_PATTERN = re.compile(r"^[a-zA-Z0-9\-:.]+$")


def _resolve_config_path() -> Path:
    env_path = os.environ.get("ADB_CONFIG_PATH")
    if env_path:
        return Path(env_path)
    # Priority: project root copy (dev/source installs) → bundled package copy (uvx/pip installs)
    # This allows developers and source installers to edit configs/adb_config.yaml directly
    # without needing ADB_CONFIG_PATH. Installed users get bundled defaults automatically.
    root_copy = Path(__file__).parent.parent.parent / "configs" / "adb_config.yaml"
    if root_copy.exists():
        return root_copy
    return Path(str(_resource_files("agent_droid_bridge") / "configs" / "adb_config.yaml"))


CONFIG_PATH = _resolve_config_path()

logger = logging.getLogger(__name__)


def _split_comma_list(v: object) -> list[str]:
    if isinstance(v, str):
        if not v.strip():
            return []
        return [item.strip() for item in v.split(",") if item.strip()]
    return v  # type: ignore[return-value]


_CommaSplitList = Annotated[list[str], BeforeValidator(_split_comma_list)]


class ADBConfig(BaseModel):
    path: str = "adb"
    command_timeout: int = 30
    screenshot_timeout: int = 60
    ui_change_timeout: int = 10
    aapt_timeout: int = 10
    ui_change_poll_interval: float = 0.5

    @field_validator("command_timeout", "screenshot_timeout", "ui_change_timeout", "aapt_timeout")
    @classmethod
    def validate_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Timeout must be a positive integer")
        return v

    @field_validator("ui_change_poll_interval")
    @classmethod
    def validate_positive_float(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Poll interval must be positive")
        return v


class ServerConfig(BaseModel):
    log_level: str = "INFO"

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            raise ValueError(f"log_level must be one of {valid}")
        return upper


class SecurityConfig(BaseModel):
    shell_command_allowlist: _CommaSplitList = []
    shell_command_denylist: _CommaSplitList = []


class ToolsConfig(BaseModel):
    denied: _CommaSplitList = []


class ExtraToolPacksConfig(BaseModel):
    enabled: bool = False
    packs: _CommaSplitList = []


class Settings(BaseModel):
    adb: ADBConfig = ADBConfig()
    server: ServerConfig = ServerConfig()
    security: SecurityConfig = SecurityConfig()
    tools: ToolsConfig = ToolsConfig()
    extra_tool_packs: ExtraToolPacksConfig = ExtraToolPacksConfig()
    execution_mode: str = "unrestricted"
    allow_shell: bool = True

    @field_validator("execution_mode")
    @classmethod
    def validate_execution_mode(cls, v: str) -> str:
        allowed = {"unrestricted", "restricted"}
        if v not in allowed:
            raise ValueError(f"execution_mode must be one of {allowed}")
        return v

    @classmethod
    def load(cls, path: Path = CONFIG_PATH) -> Settings:
        if not path.exists():
            logger.warning("Config file not found at %s, using defaults", path)
            raw = {}
        else:
            with path.open("r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}
        raw["execution_mode"] = os.environ.get("ADB_EXECUTION_MODE", "unrestricted")
        allow_shell_raw = os.environ.get("ADB_ALLOW_SHELL", "true").lower()
        if allow_shell_raw not in {"true", "false"}:
            raise ValueError(f"ADB_ALLOW_SHELL must be 'true' or 'false', got '{allow_shell_raw}'")
        raw["allow_shell"] = allow_shell_raw == "true"
        return cls.model_validate(raw)

    @classmethod
    def load_from_env(cls) -> Settings:
        allow_shell_raw = os.environ.get("ADB_ALLOW_SHELL", "true").lower()
        if allow_shell_raw not in {"true", "false"}:
            raise ValueError(f"ADB_ALLOW_SHELL must be 'true' or 'false', got '{allow_shell_raw}'")

        packs_raw = os.environ.get("ADB_EXTRA_TOOL_PACKS", "")
        packs_list = _split_comma_list(packs_raw)

        adb_raw: dict[str, object] = {}
        _adb_env_map = {
            "ADB_PATH": "path",
            "ADB_COMMAND_TIMEOUT": "command_timeout",
            "ADB_SCREENSHOT_TIMEOUT": "screenshot_timeout",
            "ADB_UI_CHANGE_TIMEOUT": "ui_change_timeout",
            "ADB_AAPT_TIMEOUT": "aapt_timeout",
            "ADB_UI_CHANGE_POLL_INTERVAL": "ui_change_poll_interval",
        }
        for env_key, field_name in _adb_env_map.items():
            if (val := os.environ.get(env_key)) is not None:
                adb_raw[field_name] = val

        server_raw: dict[str, object] = {}
        if (log_level := os.environ.get("ADB_LOG_LEVEL")) is not None:
            server_raw["log_level"] = log_level

        raw: dict[str, object] = {
            "adb": adb_raw,
            "server": server_raw,
            "security": {
                "shell_command_allowlist": os.environ.get("ADB_SHELL_ALLOWLIST", ""),
                "shell_command_denylist": os.environ.get("ADB_SHELL_DENYLIST", ""),
            },
            "tools": {
                "denied": os.environ.get("ADB_DENIED_TOOLS", ""),
            },
            "extra_tool_packs": {
                "enabled": bool(packs_list),
                "packs": packs_list,
            },
            "execution_mode": os.environ.get("ADB_EXECUTION_MODE", "unrestricted"),
            "allow_shell": allow_shell_raw == "true",
        }
        return cls.model_validate(raw)


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        source = os.environ.get("ADB_CONFIG_SOURCE", "env").lower()
        logger.info("config source: %s", source)
        if source == "yaml":
            _settings = Settings.load()
        else:
            _settings = Settings.load_from_env()
    return _settings


_logging_config: LoggingConfig | None = None


def get_logging_config() -> LoggingConfig:
    global _logging_config
    if _logging_config is None:
        _logging_config = LoggingConfig.load()
    return _logging_config
