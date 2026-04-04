from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path


class JSONLWriter:
    def __init__(self, path: Path, max_size_bytes: int) -> None:
        self._path = path
        self._max_size_bytes = max_size_bytes
        self._suppressed = False
        self._current_size = path.stat().st_size if path.exists() else 0

    @property
    def suppressed(self) -> bool:
        return self._suppressed

    def write(self, record: dict) -> None:
        if self._suppressed:
            return

        line = json.dumps(record, default=str) + "\n"

        line_size = len(line.encode("utf-8"))
        if self._max_size_bytes > 0 and self._current_size + line_size > self._max_size_bytes:
            suppression = {
                "event": "log_suppressed",
                "reason": "max_file_size_reached",
                "timestamp": datetime.now(UTC).isoformat(),
            }
            with self._path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(suppression, default=str) + "\n")
            self._suppressed = True
            return

        with self._path.open("a", encoding="utf-8") as f:
            f.write(line)
        self._current_size += line_size
