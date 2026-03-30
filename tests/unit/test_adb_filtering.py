from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_droid_bridge.adb import ADBError, ADBService
from agent_droid_bridge.config import SecurityConfig, Settings


def _make_service(**kwargs) -> ADBService:
    return ADBService(Settings(**kwargs))


def _mock_proc() -> MagicMock:
    proc = MagicMock()
    proc.returncode = 0
    proc.communicate = AsyncMock(return_value=(b"ok", b""))
    return proc


class TestRestrictedModeAllowlist:
    async def test_allowed_command_passes(self) -> None:
        service = _make_service(
            execution_mode="restricted",
            security=SecurityConfig(shell_command_allowlist=["dumpsys"]),
        )
        cmd = ["adb", "shell", "dumpsys"]
        mock_exec = AsyncMock(return_value=_mock_proc())
        with patch("asyncio.create_subprocess_exec", mock_exec):
            await service._run(cmd, trusted=False)

    async def test_command_not_in_allowlist_raises(self) -> None:
        service = _make_service(
            execution_mode="restricted",
            security=SecurityConfig(shell_command_allowlist=["dumpsys"]),
        )
        cmd = ["adb", "shell", "pm"]
        with pytest.raises(ADBError, match="not permitted"):
            await service._run(cmd, trusted=False)

    async def test_empty_allowlist_raises(self) -> None:
        service = _make_service(
            execution_mode="restricted",
            security=SecurityConfig(shell_command_allowlist=[]),
        )
        cmd = ["adb", "shell", "dumpsys"]
        with pytest.raises(ADBError, match="allowlist is empty"):
            await service._run(cmd, trusted=False)

    async def test_top_level_adb_command_blocked_in_restricted(self) -> None:
        service = _make_service(
            execution_mode="restricted",
            security=SecurityConfig(shell_command_allowlist=["dumpsys"]),
        )
        cmd = ["adb", "install", "app.apk"]
        with pytest.raises(ADBError, match="Top-level"):
            await service._run(cmd, trusted=False)


class TestUnrestrictedModeDenylist:
    async def test_denied_command_raises(self) -> None:
        service = _make_service(
            execution_mode="unrestricted",
            security=SecurityConfig(shell_command_denylist=["rm"]),
        )
        cmd = ["adb", "shell", "rm"]
        with pytest.raises(ADBError, match="blocked"):
            await service._run(cmd, trusted=False)

    async def test_command_not_in_denylist_passes(self) -> None:
        service = _make_service(
            execution_mode="unrestricted",
            security=SecurityConfig(shell_command_denylist=["rm"]),
        )
        cmd = ["adb", "shell", "dumpsys"]
        mock_exec = AsyncMock(return_value=_mock_proc())
        with patch("asyncio.create_subprocess_exec", mock_exec):
            await service._run(cmd, trusted=False)

    async def test_empty_denylist_passes_all(self) -> None:
        service = _make_service(
            execution_mode="unrestricted",
            security=SecurityConfig(shell_command_denylist=[]),
        )
        cmd = ["adb", "shell", "rm"]
        mock_exec = AsyncMock(return_value=_mock_proc())
        with patch("asyncio.create_subprocess_exec", mock_exec):
            await service._run(cmd, trusted=False)

    async def test_full_path_basename_blocked(self) -> None:
        service = _make_service(
            execution_mode="unrestricted",
            security=SecurityConfig(shell_command_denylist=["rm"]),
        )
        cmd = ["adb", "shell", "/system/bin/rm"]
        with pytest.raises(ADBError, match="blocked"):
            await service._run(cmd, trusted=False)

    async def test_full_path_not_in_denylist_passes(self) -> None:
        service = _make_service(
            execution_mode="unrestricted",
            security=SecurityConfig(shell_command_denylist=["rm"]),
        )
        cmd = ["adb", "shell", "/system/bin/dumpsys"]
        mock_exec = AsyncMock(return_value=_mock_proc())
        with patch("asyncio.create_subprocess_exec", mock_exec):
            await service._run(cmd, trusted=False)


class TestAllowShellFalse:
    async def test_shell_command_blocked_when_allow_shell_false(self) -> None:
        service = _make_service(allow_shell=False)
        cmd = ["adb", "shell", "dumpsys"]
        with pytest.raises(ADBError, match="ADB_ALLOW_SHELL"):
            await service._run(cmd, trusted=False)

    async def test_non_shell_command_passes_when_allow_shell_false(self) -> None:
        service = _make_service(allow_shell=False)
        cmd = ["adb", "devices"]
        mock_exec = AsyncMock(return_value=_mock_proc())
        with patch("asyncio.create_subprocess_exec", mock_exec):
            await service._run(cmd, trusted=False)


class TestTrustedBypass:
    async def test_trusted_bypasses_restricted_mode(self) -> None:
        service = _make_service(
            execution_mode="restricted",
            security=SecurityConfig(shell_command_allowlist=[]),
        )
        cmd = ["adb", "shell", "dumpsys"]
        mock_exec = AsyncMock(return_value=_mock_proc())
        with patch("asyncio.create_subprocess_exec", mock_exec):
            await service._run(cmd, trusted=True)

    async def test_trusted_bypasses_denylist(self) -> None:
        service = _make_service(
            execution_mode="unrestricted",
            security=SecurityConfig(shell_command_denylist=["rm"]),
        )
        cmd = ["adb", "shell", "rm"]
        mock_exec = AsyncMock(return_value=_mock_proc())
        with patch("asyncio.create_subprocess_exec", mock_exec):
            await service._run(cmd, trusted=True)

    async def test_trusted_bypasses_allow_shell_false(self) -> None:
        service = _make_service(allow_shell=False)
        cmd = ["adb", "shell", "dumpsys"]
        mock_exec = AsyncMock(return_value=_mock_proc())
        with patch("asyncio.create_subprocess_exec", mock_exec):
            await service._run(cmd, trusted=True)
