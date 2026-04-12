from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_droid_bridge.adb import ADBError, ADBService
from agent_droid_bridge.config import Settings
from agent_droid_bridge.extra_tool_packs.app_manager.control_service import AppControlService
from agent_droid_bridge.extra_tool_packs.app_manager.models import (
    InjectIntentResult,
    LaunchAppExtraResult,
    ManageAppResult,
)

PKG = "com.example.app"

PM_RESOLVE_OUTPUT = (
    "priority=0 preferredOrder=0\n"
    f"  {PKG}/.MainActivity\n"
    "label=Example App\n"
    "icon=0x7f0e0000\n"
)
PM_RESOLVE_INNER = (
    "priority=0 preferredOrder=0\n"
    f"  {PKG}/.ui.MainActivity$Launcher\n"
    "label=Example\n"
)
PM_RESOLVE_NO_MATCH = "No activity found\n"
AM_START_SUCCESS = f"Starting: Intent {{ cmp={PKG}/.MainActivity }}\n"
AM_START_ERROR = "Error type 3\nError: Activity class not found.\n"
PIDOF_OUTPUT = b"12345\n"

_PROC = (
    "agent_droid_bridge.extra_tool_packs.app_manager"
    ".control_service.asyncio.create_subprocess_exec"
)
_SLEEP = "agent_droid_bridge.extra_tool_packs.app_manager.control_service.asyncio.sleep"


def _make_control_service() -> tuple[AppControlService, ADBService]:
    adb = ADBService(Settings())
    return AppControlService(adb), adb


def _mock_proc(returncode: int = 0, stdout: bytes = b"", stderr: bytes = b"") -> MagicMock:
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    return proc


class TestManageAppValidation:
    async def test_invalid_action_returns_error_result(self) -> None:
        service, _ = _make_control_service()
        result = await service.manage_app(PKG, "badaction")
        assert not result.success
        assert result.action == "badaction"
        assert "stop" in result.error and "clear_data" in result.error

    @pytest.mark.parametrize("action", ["stop", "clear_data", "clear_cache", "enable", "disable"])
    async def test_valid_actions_are_accepted(self, action: str) -> None:
        service, adb = _make_control_service()
        adb._resolve_serial = AsyncMock(return_value=None)
        adb._run = AsyncMock(return_value=(b"Success\n", b""))
        service._get_root_available = AsyncMock(return_value=False)
        result = await service.manage_app(PKG, action)
        assert result.action == action


class TestManageAppStop:
    async def test_stop_sends_force_stop_command(self) -> None:
        service, adb = _make_control_service()
        adb._resolve_serial = AsyncMock(return_value=None)
        adb._run = AsyncMock(return_value=(b"", b""))
        await service.manage_app(PKG, "stop")
        assert adb._run.call_args[0][0][-4:] == ["shell", "am", "force-stop", PKG]

    async def test_stop_returns_success(self) -> None:
        service, adb = _make_control_service()
        adb._resolve_serial = AsyncMock(return_value=None)
        adb._run = AsyncMock(return_value=(b"", b""))
        result = await service.manage_app(PKG, "stop")
        assert result.success and result.action == "stop"

    async def test_stop_adb_error_returns_failure(self) -> None:
        service, adb = _make_control_service()
        adb._resolve_serial = AsyncMock(return_value=None)
        adb._run = AsyncMock(side_effect=ADBError("device offline"))
        result = await service.manage_app(PKG, "stop")
        assert not result.success and "device offline" in result.error


class TestManageAppClearData:
    async def test_clear_data_sends_pm_clear_command(self) -> None:
        service, adb = _make_control_service()
        adb._resolve_serial = AsyncMock(return_value=None)
        adb._run = AsyncMock(return_value=(b"Success\n", b""))
        await service.manage_app(PKG, "clear_data")
        assert adb._run.call_args[0][0][-4:] == ["shell", "pm", "clear", PKG]

    async def test_clear_data_success_output_parsed(self) -> None:
        service, adb = _make_control_service()
        adb._resolve_serial = AsyncMock(return_value=None)
        adb._run = AsyncMock(return_value=(b"Success\n", b""))
        assert (await service.manage_app(PKG, "clear_data")).success

    async def test_clear_data_failure_output_parsed(self) -> None:
        service, adb = _make_control_service()
        adb._resolve_serial = AsyncMock(return_value=None)
        adb._run = AsyncMock(return_value=(b"Failed\n", b""))
        assert not (await service.manage_app(PKG, "clear_data")).success


class TestManageAppClearCache:
    async def test_clear_cache_sends_rm_command(self) -> None:
        service, adb = _make_control_service()
        adb._resolve_serial = AsyncMock(return_value=None)
        adb._run = AsyncMock(return_value=(b"", b""))
        await service.manage_app(PKG, "clear_cache")
        assert adb._run.call_args[0][0][-4:] == ["shell", "rm", "-rf", f"/data/data/{PKG}/cache/*"]

    async def test_clear_cache_success(self) -> None:
        service, adb = _make_control_service()
        adb._resolve_serial = AsyncMock(return_value=None)
        adb._run = AsyncMock(return_value=(b"", b""))
        service._get_root_available = AsyncMock(return_value=True)
        result = await service.manage_app(PKG, "clear_cache")
        assert result.success and result.requires_root is False

    async def test_clear_cache_permission_denied_sets_requires_root(self) -> None:
        service, adb = _make_control_service()
        adb._resolve_serial = AsyncMock(return_value=None)
        err = ADBError(f"rm: /data/data/{PKG}/cache/*: Permission denied")
        adb._run = AsyncMock(side_effect=err)
        result = await service.manage_app(PKG, "clear_cache")
        assert not result.success and result.requires_root is True

    async def test_clear_cache_other_error_does_not_set_requires_root(self) -> None:
        service, adb = _make_control_service()
        adb._resolve_serial = AsyncMock(return_value=None)
        adb._run = AsyncMock(side_effect=ADBError("device offline"))
        result = await service.manage_app(PKG, "clear_cache")
        assert not result.success and result.requires_root is None


class TestManageAppDisable:
    async def test_disable_uses_pm_disable_when_root_available(self) -> None:
        service, adb = _make_control_service()
        adb._resolve_serial = AsyncMock(return_value=None)
        service._get_root_available = AsyncMock(return_value=True)
        adb._run = AsyncMock(return_value=(b"", b""))
        await service.manage_app(PKG, "disable")
        assert adb._run.call_args[0][0][-4:] == ["shell", "pm", "disable", PKG]

    async def test_disable_uses_pm_disable_user_when_no_root(self) -> None:
        service, adb = _make_control_service()
        adb._resolve_serial = AsyncMock(return_value=None)
        service._get_root_available = AsyncMock(return_value=False)
        adb._run = AsyncMock(return_value=(b"", b""))
        await service.manage_app(PKG, "disable")
        cmd = adb._run.call_args[0][0]
        assert "disable-user" in cmd and "--user" in cmd

    async def test_disable_returns_success(self) -> None:
        service, adb = _make_control_service()
        adb._resolve_serial = AsyncMock(return_value=None)
        service._get_root_available = AsyncMock(return_value=False)
        adb._run = AsyncMock(return_value=(b"", b""))
        assert (await service.manage_app(PKG, "disable")).success


class TestManageAppEnable:
    async def test_enable_sends_pm_enable_command(self) -> None:
        service, adb = _make_control_service()
        adb._resolve_serial = AsyncMock(return_value=None)
        adb._run = AsyncMock(return_value=(b"", b""))
        await service.manage_app(PKG, "enable")
        assert adb._run.call_args[0][0][-4:] == ["shell", "pm", "enable", PKG]

    async def test_enable_returns_success(self) -> None:
        service, adb = _make_control_service()
        adb._resolve_serial = AsyncMock(return_value=None)
        adb._run = AsyncMock(return_value=(b"", b""))
        assert (await service.manage_app(PKG, "enable")).success


class TestInjectIntentValidation:
    async def test_invalid_intent_type_returns_error(self) -> None:
        service, _ = _make_control_service()
        result = await service.inject_intent("invalid")
        assert not result.success and result.exit_code == -1
        assert "activity" in result.error

    @pytest.mark.parametrize("intent_type", ["activity", "broadcast", "service"])
    async def test_valid_intent_types_accepted(self, intent_type: str) -> None:
        service, adb = _make_control_service()
        adb._resolve_serial = AsyncMock(return_value=None)
        with patch(_PROC, AsyncMock(return_value=_mock_proc(0, b"Starting: ok", b""))):
            result = await service.inject_intent(intent_type)
        assert result.exit_code != -1


class TestInjectIntentCommandBuilding:
    async def _capture(self, intent_type: str = "activity", **kwargs: object) -> tuple:
        service, adb = _make_control_service()
        adb._resolve_serial = AsyncMock(return_value=None)
        captured: list[tuple] = []

        async def fake_exec(*args: str, **kw: object) -> MagicMock:
            captured.append(args)
            return _mock_proc(0, b"Starting: ok", b"")

        with patch(_PROC, fake_exec):
            await service.inject_intent(intent_type, **kwargs)
        return captured[0]

    async def test_activity_uses_am_start(self) -> None:
        assert "start" in await self._capture("activity")

    async def test_broadcast_uses_am_broadcast(self) -> None:
        assert "broadcast" in await self._capture("broadcast")

    async def test_service_uses_am_startservice(self) -> None:
        assert "startservice" in await self._capture("service")

    async def test_action_flag_included(self) -> None:
        cmd = await self._capture(action="android.intent.action.VIEW")
        assert "-a" in cmd and "android.intent.action.VIEW" in cmd

    async def test_component_flag_included(self) -> None:
        cmd = await self._capture(component=f"{PKG}/.MainActivity")
        assert "-n" in cmd and f"{PKG}/.MainActivity" in cmd

    async def test_package_flag_included_without_component(self) -> None:
        assert "-p" in await self._capture(package=PKG)

    async def test_package_flag_not_included_when_component_present(self) -> None:
        assert "-p" not in await self._capture(package=PKG, component=f"{PKG}/.MainActivity")

    async def test_uri_flag_included(self) -> None:
        cmd = await self._capture(uri="content://com.example/data")
        assert "-d" in cmd and "content://com.example/data" in cmd

    async def test_mime_type_flag_included(self) -> None:
        cmd = await self._capture(mime_type="text/plain")
        assert "-t" in cmd and "text/plain" in cmd

    async def test_extras_included_as_es_flags(self) -> None:
        cmd = await self._capture(extras={"key": "value"})
        assert "--es" in cmd and "key" in cmd and "value" in cmd


class TestInjectIntentFiltering:
    async def _inject(self, stdout: bytes, filter: str | None = None) -> InjectIntentResult:
        service, adb = _make_control_service()
        adb._resolve_serial = AsyncMock(return_value=None)
        with patch(_PROC, AsyncMock(return_value=_mock_proc(0, stdout, b""))):
            return await service.inject_intent("activity", filter=filter)

    async def test_no_filter_returns_all_lines(self) -> None:
        assert len((await self._inject(b"line1\nline2\nline3\n")).output) == 3

    async def test_filter_returns_matching_lines_only(self) -> None:
        result = await self._inject(b"Error: something\nSuccess: ok\n", filter="error")
        assert len(result.output) == 1 and "Error" in result.output[0]

    async def test_filter_is_case_insensitive(self) -> None:
        assert len((await self._inject(b"ERROR: fail\nok line\n", filter="error")).output) == 1

    async def test_empty_lines_excluded(self) -> None:
        assert len((await self._inject(b"line1\n\nline2\n\nline3\n")).output) == 3


class TestInjectIntentSuccessDetermination:
    async def _inject(
        self, returncode: int, stdout: bytes = b"", stderr: bytes = b""
    ) -> InjectIntentResult:
        service, adb = _make_control_service()
        adb._resolve_serial = AsyncMock(return_value=None)
        with patch(_PROC, AsyncMock(return_value=_mock_proc(returncode, stdout, stderr))):
            return await service.inject_intent("activity")

    async def test_exit_code_zero_no_markers_is_success(self) -> None:
        assert (await self._inject(0, b"Starting: Intent { }", b"")).success

    async def test_exit_code_nonzero_is_failure(self) -> None:
        assert not (await self._inject(1)).success

    async def test_error_marker_in_stdout_is_failure(self) -> None:
        assert not (await self._inject(0, b"Error: Activity not found", b"")).success

    async def test_error_marker_case_insensitive(self) -> None:
        assert not (await self._inject(0, b"error: something", b"")).success

    async def test_error_field_uses_stderr_when_available(self) -> None:
        result = await self._inject(1, b"", b"some stderr message")
        assert result.error is not None and "some stderr message" in result.error

    async def test_error_field_falls_back_to_stdout_when_stderr_empty(self) -> None:
        result = await self._inject(0, b"Error: bad intent", b"")
        assert result.error is not None and "Error: bad intent" in result.error


class TestLaunchAppExtraComponentParsing:
    async def _launch(
        self,
        resolve: bytes,
        start: bytes | None = None,
        pidof: bytes = PIDOF_OUTPUT,
    ) -> LaunchAppExtraResult:
        service, adb = _make_control_service()
        adb._resolve_serial = AsyncMock(return_value=None)
        adb._run = AsyncMock(
            side_effect=[
                (resolve, b""),
                (start if start is not None else AM_START_SUCCESS.encode(), b""),
                (pidof, b""),
            ]
        )
        with patch(_SLEEP):
            return await service.launch_app_extra(PKG)

    async def test_component_extracted_from_resolve_output(self) -> None:
        result = await self._launch(PM_RESOLVE_OUTPUT.encode())
        assert result.component == f"{PKG}/.MainActivity"

    async def test_app_name_extracted_from_label(self) -> None:
        assert (await self._launch(PM_RESOLVE_OUTPUT.encode())).app_name == "Example App"

    async def test_inner_class_component_extracted(self) -> None:
        result = await self._launch(PM_RESOLVE_INNER.encode())
        assert result.component is not None and "$" in result.component

    async def test_no_match_returns_error_result(self) -> None:
        service, adb = _make_control_service()
        adb._resolve_serial = AsyncMock(return_value=None)
        adb._run = AsyncMock(return_value=(PM_RESOLVE_NO_MATCH.encode(), b""))
        result = await service.launch_app_extra(PKG)
        assert not result.success and "get_app_info" in result.error

    async def test_am_start_error_returns_failure(self) -> None:
        result = await self._launch(PM_RESOLVE_OUTPUT.encode(), AM_START_ERROR.encode())
        assert not result.success

    async def test_success_returns_component_and_success_true(self) -> None:
        result = await self._launch(PM_RESOLVE_OUTPUT.encode())
        assert result.success and result.component is not None


class TestNewModels:
    def test_launch_app_extra_result_defaults(self) -> None:
        r = LaunchAppExtraResult(success=True)
        assert r.component is None and r.app_name is None and r.pid is None and r.error is None

    def test_launch_app_extra_result_with_pid(self) -> None:
        assert LaunchAppExtraResult(success=True, pid=1234).pid == 1234

    def test_manage_app_result_defaults(self) -> None:
        r = ManageAppResult(success=True, action="stop")
        assert r.requires_root is None and r.error is None

    def test_manage_app_result_requires_root(self) -> None:
        r = ManageAppResult(success=False, action="clear_cache", requires_root=True)
        assert r.requires_root is True

    def test_inject_intent_result_defaults(self) -> None:
        r = InjectIntentResult(success=True, exit_code=0)
        assert r.output == [] and r.error is None

    def test_inject_intent_result_output_list(self) -> None:
        r = InjectIntentResult(success=True, exit_code=0, output=["line1", "line2"])
        assert len(r.output) == 2
