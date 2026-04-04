from __future__ import annotations

import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path

SESSION_DIR_PREFIX = "session_"
SESSION_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"

_logger = logging.getLogger(__name__)


def create_session_dir(log_dir: Path) -> Path:
    timestamp = datetime.now(UTC).strftime(SESSION_TIMESTAMP_FORMAT)
    session_dir = log_dir / f"{SESSION_DIR_PREFIX}{timestamp}"
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def parse_session_timestamp(dir_name: str) -> datetime | None:
    if not dir_name.startswith(SESSION_DIR_PREFIX):
        return None
    name = dir_name[len(SESSION_DIR_PREFIX):]
    try:
        return datetime.strptime(name, SESSION_TIMESTAMP_FORMAT)
    except (ValueError, TypeError):
        return None


def cleanup_old_sessions(log_dir: Path, max_age_days: int, max_sessions: int) -> None:
    if not log_dir.exists():
        return

    candidates: list[tuple[datetime, Path]] = []
    for entry in log_dir.iterdir():
        if not entry.is_dir() or not entry.name.startswith(SESSION_DIR_PREFIX):
            continue
        ts = parse_session_timestamp(entry.name)
        if ts is None:
            continue
        candidates.append((ts, entry))

    now = datetime.now(UTC).replace(tzinfo=None)
    surviving: list[tuple[datetime, Path]] = []
    for ts, path in candidates:
        if (now - ts).days > max_age_days:
            try:
                shutil.rmtree(path)
            except OSError as e:
                _logger.warning("Failed to remove old session dir %s: %s", path, e)
        else:
            surviving.append((ts, path))

    if len(surviving) > max_sessions:
        surviving.sort(key=lambda x: x[0])
        to_delete = surviving[: len(surviving) - max_sessions]
        for _, path in to_delete:
            try:
                shutil.rmtree(path)
            except OSError as e:
                _logger.warning("Failed to remove excess session dir %s: %s", path, e)
