from __future__ import annotations

import json
import stat
from datetime import UTC, datetime, timedelta
from pathlib import Path

from agent_droid_bridge.recorder.session import (
    SESSION_DIR_PREFIX,
    SESSION_TIMESTAMP_FORMAT,
    cleanup_old_sessions,
    create_session_dir,
    parse_session_timestamp,
)
from agent_droid_bridge.recorder.writers import JSONLWriter


class TestJSONLWriter:
    def test_write_single_record_produces_valid_jsonl_line(self, tmp_path) -> None:
        path = tmp_path / "test.log"
        writer = JSONLWriter(path, max_size_bytes=1024 * 1024)
        writer.write({"key": "value"})
        lines = path.read_text().splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["key"] == "value"

    def test_write_multiple_records_produces_one_line_each(self, tmp_path) -> None:
        path = tmp_path / "test.log"
        writer = JSONLWriter(path, max_size_bytes=1024 * 1024)
        for i in range(5):
            writer.write({"index": i})
        lines = path.read_text().splitlines()
        assert len(lines) == 5

    def test_each_line_is_valid_json(self, tmp_path) -> None:
        path = tmp_path / "test.log"
        writer = JSONLWriter(path, max_size_bytes=1024 * 1024)
        writer.write({"a": 1})
        writer.write({"b": "two"})
        for line in path.read_text().splitlines():
            json.loads(line)

    def test_size_cap_writes_suppression_entry_and_sets_suppressed(self, tmp_path) -> None:
        path = tmp_path / "test.log"
        writer = JSONLWriter(path, max_size_bytes=50)
        writer.write({"data": "x" * 100})
        assert writer.suppressed is True
        last_line = path.read_text().splitlines()[-1]
        record = json.loads(last_line)
        assert record["event"] == "log_suppressed"
        assert record["reason"] == "max_file_size_reached"

    def test_writes_after_suppression_are_noop(self, tmp_path) -> None:
        path = tmp_path / "test.log"
        writer = JSONLWriter(path, max_size_bytes=50)
        writer.write({"data": "x" * 100})
        size_after_suppression = path.stat().st_size
        writer.write({"extra": "record"})
        writer.write({"another": "record"})
        assert path.stat().st_size == size_after_suppression
        assert writer.suppressed is True

    def test_max_size_bytes_zero_means_no_limit(self, tmp_path) -> None:
        path = tmp_path / "test.log"
        writer = JSONLWriter(path, max_size_bytes=0)
        for i in range(50):
            writer.write({"index": i, "payload": "x" * 200})
        assert writer.suppressed is False
        assert len(path.read_text().splitlines()) == 50

    def test_non_serializable_value_uses_str_default(self, tmp_path) -> None:
        path = tmp_path / "test.log"
        writer = JSONLWriter(path, max_size_bytes=1024 * 1024)
        writer.write({"path": Path("/some/path")})
        record = json.loads(path.read_text().strip())
        assert record["path"] == "/some/path"

    def test_suppressed_property_false_initially(self, tmp_path) -> None:
        path = tmp_path / "test.log"
        writer = JSONLWriter(path, max_size_bytes=1024 * 1024)
        assert writer.suppressed is False


class TestCreateSessionDir:
    def test_creates_a_directory_that_exists(self, tmp_path) -> None:
        session_dir = create_session_dir(tmp_path)
        assert session_dir.exists()
        assert session_dir.is_dir()

    def test_directory_name_starts_with_session_prefix(self, tmp_path) -> None:
        session_dir = create_session_dir(tmp_path)
        assert session_dir.name.startswith(SESSION_DIR_PREFIX)

    def test_directory_name_has_valid_timestamp_format(self, tmp_path) -> None:
        session_dir = create_session_dir(tmp_path)
        ts_part = session_dir.name[len(SESSION_DIR_PREFIX):]
        parsed = datetime.strptime(ts_part, SESSION_TIMESTAMP_FORMAT)
        assert isinstance(parsed, datetime)


class TestParseSessionTimestamp:
    def test_valid_name_returns_datetime(self) -> None:
        dt = parse_session_timestamp("session_20240101_120000")
        assert isinstance(dt, datetime)
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 1

    def test_non_session_name_returns_none(self) -> None:
        assert parse_session_timestamp("not_a_session") is None

    def test_bad_timestamp_suffix_returns_none(self) -> None:
        assert parse_session_timestamp("session_bad") is None

    def test_empty_string_returns_none(self) -> None:
        assert parse_session_timestamp("") is None

    def test_partial_prefix_only_returns_none(self) -> None:
        assert parse_session_timestamp("session_") is None


class TestCleanupOldSessions:
    def _make_session_dir(self, log_dir: Path, days_ago: int) -> Path:
        ts = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days_ago)
        name = f"{SESSION_DIR_PREFIX}{ts.strftime(SESSION_TIMESTAMP_FORMAT)}"
        session_dir = log_dir / name
        session_dir.mkdir()
        return session_dir

    def test_deletes_session_older_than_max_age(self, tmp_path) -> None:
        old_dir = self._make_session_dir(tmp_path, days_ago=10)
        cleanup_old_sessions(tmp_path, max_age_days=7, max_sessions=20)
        assert not old_dir.exists()

    def test_keeps_session_within_max_age(self, tmp_path) -> None:
        recent_dir = self._make_session_dir(tmp_path, days_ago=3)
        cleanup_old_sessions(tmp_path, max_age_days=7, max_sessions=20)
        assert recent_dir.exists()

    def test_trims_to_max_sessions_keeping_newest(self, tmp_path) -> None:
        dirs = [self._make_session_dir(tmp_path, days_ago=i) for i in range(5, 0, -1)]
        cleanup_old_sessions(tmp_path, max_age_days=30, max_sessions=3)
        surviving = [d for d in dirs if d.exists()]
        assert len(surviving) == 3

    def test_ignores_directories_that_do_not_match_session_format(self, tmp_path) -> None:
        other_dir = tmp_path / "unrelated_dir"
        other_dir.mkdir()
        cleanup_old_sessions(tmp_path, max_age_days=7, max_sessions=20)
        assert other_dir.exists()

    def test_nonexistent_log_dir_does_not_crash(self, tmp_path) -> None:
        missing = tmp_path / "no_such_dir"
        cleanup_old_sessions(missing, max_age_days=7, max_sessions=20)

    def test_oserror_on_one_dir_does_not_crash(self, tmp_path) -> None:
        old_dir = self._make_session_dir(tmp_path, days_ago=10)
        old_dir.chmod(0o000)
        try:
            cleanup_old_sessions(tmp_path, max_age_days=7, max_sessions=20)
        finally:
            old_dir.chmod(stat.S_IRWXU)
