from __future__ import annotations

import logging
import sys
from logging.handlers import TimedRotatingFileHandler

from .config import LoggingConfig
from .handlers import SessionLogger
from .session import cleanup_old_sessions, create_session_dir

__all__ = ["setup_logging", "get_session_logger", "LoggingConfig", "SessionLogger"]

_session_logger: SessionLogger | None = None


def setup_logging(config: LoggingConfig) -> None:
    global _session_logger

    if not config.enabled:
        return

    if config.log_dir is None:
        print(
            "[agent-droid-bridge] WARNING: MCP_LOG_ENABLED is set but MCP_LOG_DIR is not. "
            "Set MCP_LOG_DIR to an absolute path and restart the server to enable logging. "
            "Continuing without logging.",
            file=sys.stderr,
        )
        return

    server_handler = None
    try:
        config.log_dir.mkdir(parents=True, exist_ok=True)
        cleanup_old_sessions(
            config.log_dir, config.max_session_age_days, config.max_sessions_to_keep
        )
        session_dir = create_session_dir(config.log_dir)

        server_log_path = config.log_dir / "server.log"
        server_handler = TimedRotatingFileHandler(
            server_log_path,
            when="midnight",
            backupCount=config.server_log_backup_count,
            encoding="utf-8",
        )
        server_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        logging.getLogger("agent_droid_bridge").addHandler(server_handler)

        _session_logger = SessionLogger(config, session_dir)
        logging.getLogger("agent_droid_bridge").info(
            "Recorder started — session: %s", session_dir.name
        )
    except OSError as e:
        if server_handler is not None:
            logging.getLogger("agent_droid_bridge").removeHandler(server_handler)
        _session_logger = None
        print(
            f"[agent-droid-bridge] WARNING: Logging could not be started — {e}. "
            "Fix the issue and restart the server to enable logging. Continuing without logging.",
            file=sys.stderr,
        )


def get_session_logger() -> SessionLogger | None:
    return _session_logger
