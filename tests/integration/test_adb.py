import pytest

from src.agent_droid_bridge.adb import ADBError, ADBService
from src.agent_droid_bridge.config import Settings
from src.agent_droid_bridge.models import ScreenTextResult


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings.load()


@pytest.fixture(scope="session")
async def adb_service(settings: Settings) -> ADBService:
    svc = ADBService(settings)
    try:
        devices = await svc._get_connected_devices()
    except Exception:
        pytest.skip("ADB not available")
    if not devices:
        pytest.skip("No Android devices connected — skipping integration tests")
    return svc


class TestGetUIHierarchy:
    async def test_returns_xml(self, adb_service: ADBService) -> None:
        result = await adb_service.get_ui_hierarchy()
        assert "<hierarchy" in result or "<?xml" in result
        assert "node" in result

    async def test_get_ui_hierarchy_with_explicit_timeout(self, adb_service: ADBService) -> None:
        result = await adb_service.get_ui_hierarchy(timeout=15)
        assert "<hierarchy" in result or "<?xml" in result


class TestTapScreen:
    async def test_tap_returns_confirmation(self, adb_service: ADBService) -> None:
        result = await adb_service.tap_screen(100, 100)
        assert "Tapped" in result


class TestSwipeScreen:
    async def test_swipe_returns_confirmation(self, adb_service: ADBService) -> None:
        result = await adb_service.swipe_screen(100, 500, 100, 100, 300)
        assert "Swiped" in result


class TestTypeText:
    async def test_type_simple_text(self, adb_service: ADBService) -> None:
        result = await adb_service.type_text("hello")
        assert "5 characters" in result

    async def test_type_text_with_spaces(self, adb_service: ADBService) -> None:
        result = await adb_service.type_text("hello world")
        assert "11 characters" in result


class TestPressKey:
    async def test_press_home(self, adb_service: ADBService) -> None:
        result = await adb_service.press_key(3)
        assert "keycode 3" in result


class TestTakeScreenshot:
    async def test_returns_valid_png(self, adb_service: ADBService) -> None:
        raw = await adb_service.take_screenshot()
        assert raw[:4] == b"\x89PNG"

    async def test_screenshot_has_valid_png_size(self, adb_service: ADBService) -> None:
        raw = await adb_service.take_screenshot()
        assert len(raw) >= 24, "Screenshot data too small for PNG header"
        assert raw[:4] == b"\x89PNG"


class TestLaunchApp:
    async def test_launch_settings(self, adb_service: ADBService) -> None:
        result = await adb_service.launch_app("com.android.settings/com.android.settings.Settings")
        assert "Launched" in result


class TestExecuteADBCommand:
    async def test_shell_command(self, adb_service: ADBService) -> None:
        result = await adb_service.execute_adb_command("ls /sdcard")
        assert isinstance(result, str)

    async def test_toplevel_adb_command(self, adb_service: ADBService) -> None:
        result = await adb_service.execute_adb_command("devices", use_shell=False)
        assert "List of devices" in result

    async def test_invalid_syntax_raises(self, adb_service: ADBService) -> None:
        with pytest.raises(ADBError):
            await adb_service.execute_adb_command("echo 'unterminated")


class TestSerialValidation:
    async def test_injection_attempt_rejected(self, adb_service: ADBService) -> None:
        with pytest.raises(ADBError):
            await adb_service.tap_screen(100, 100, device_serial="'; rm -rf /")

    async def test_nonexistent_serial_raises_adb_error(self, adb_service: ADBService) -> None:
        with pytest.raises(ADBError):
            await adb_service.tap_screen(100, 100, device_serial="nonexistent-0000")

    async def test_invalid_serial_raises(self, settings: Settings) -> None:
        svc = ADBService(settings)
        with pytest.raises(ADBError, match="Invalid device serial"):
            await svc.get_ui_hierarchy(device_serial="bad serial!")


class TestListDevices:
    async def test_returns_list(self, adb_service: ADBService) -> None:
        result = await adb_service.list_devices()
        assert isinstance(result, list)
        assert len(result) >= 1

    async def test_device_has_required_keys(self, adb_service: ADBService) -> None:
        result = await adb_service.list_devices()
        device = result[0]
        assert "serial" in device
        assert "state" in device
        assert "model" in device
        assert device["state"] == "device"


class TestDetectUIChange:
    async def test_returns_dict_shape(self, adb_service: ADBService) -> None:
        result = await adb_service.detect_ui_change(timeout=2)
        assert "changed" in result
        assert "elapsed_seconds" in result
        assert "hierarchy" not in result
        assert isinstance(result["changed"], bool)
        assert isinstance(result["elapsed_seconds"], float)

    async def test_returns_hierarchy_when_requested(self, adb_service: ADBService) -> None:
        result = await adb_service.detect_ui_change(timeout=2, return_hierarchy=True)
        assert "hierarchy" in result
        assert isinstance(result["hierarchy"], str)

    async def test_stable_screen_returns_false(self, adb_service: ADBService) -> None:
        result = await adb_service.detect_ui_change(timeout=2)
        assert result["changed"] is False

    async def test_timeout_with_return_hierarchy_fetches_fresh(
        self, adb_service: ADBService
    ) -> None:
        result = await adb_service.detect_ui_change(timeout=3, return_hierarchy=True)
        assert result["changed"] is False
        assert "hierarchy" in result
        assert "<hierarchy" in result["hierarchy"]
        assert result["elapsed_seconds"] >= 3.0


class TestAllowlistEnforcement:
    async def test_restricted_blocks_unlisted_command(self, settings: Settings) -> None:
        settings.execution_mode = "restricted"
        settings.security.shell_command_allowlist = ["ls"]
        try:
            svc = ADBService(settings)
            with pytest.raises(ADBError, match="not permitted"):
                await svc.execute_adb_command("pm list packages")
        finally:
            settings.execution_mode = "unrestricted"
            settings.security.shell_command_allowlist = []

    async def test_restricted_permits_listed_command(self, settings: Settings) -> None:
        settings.execution_mode = "restricted"
        settings.security.shell_command_allowlist = ["ls"]
        try:
            svc = ADBService(settings)
            result = await svc.execute_adb_command("ls /sdcard")
            assert isinstance(result, str)
        finally:
            settings.execution_mode = "unrestricted"
            settings.security.shell_command_allowlist = []

    async def test_restricted_empty_list_blocks_all(self, settings: Settings) -> None:
        settings.execution_mode = "restricted"
        settings.security.shell_command_allowlist = []
        try:
            svc = ADBService(settings)
            with pytest.raises(ADBError, match="shell_command_allowlist is empty"):
                await svc.execute_adb_command("ls /sdcard")
        finally:
            settings.execution_mode = "unrestricted"

    async def test_restricted_blocks_toplevel_commands(self, settings: Settings) -> None:
        settings.execution_mode = "restricted"
        settings.security.shell_command_allowlist = ["ls"]
        try:
            svc = ADBService(settings)
            with pytest.raises(ADBError, match="Top-level ADB commands are not permitted"):
                await svc.execute_adb_command("devices", use_shell=False)
        finally:
            settings.execution_mode = "unrestricted"
            settings.security.shell_command_allowlist = []

    async def test_allow_shell_false_blocks_shell_commands(self, settings: Settings) -> None:
        settings.allow_shell = False
        try:
            svc = ADBService(settings)
            with pytest.raises(ADBError, match="ADB_ALLOW_SHELL"):
                await svc.execute_adb_command("ls /sdcard", use_shell=True)
        finally:
            settings.allow_shell = True

    async def test_unrestricted_allows_all(self, settings: Settings) -> None:
        settings.execution_mode = "unrestricted"
        svc = ADBService(settings)
        result = await svc.execute_adb_command("ls /sdcard")
        assert isinstance(result, str)

    async def test_unrestricted_ignores_allowlist(self, settings: Settings) -> None:
        settings.execution_mode = "unrestricted"
        settings.security.shell_command_allowlist = []
        svc = ADBService(settings)
        result = await svc.execute_adb_command("ls /sdcard")
        assert isinstance(result, str)


class TestGetScreenElements:
    async def test_tappable_returns_result(self, adb_service: ADBService) -> None:
        result = await adb_service.get_screen_elements(device_serial=None, mode="tappable")
        assert result.mode == "tappable"
        assert result.total == len(result.elements)

    async def test_interactive_has_xpath(self, adb_service: ADBService) -> None:
        result = await adb_service.get_screen_elements(device_serial=None, mode="interactive")
        if result.elements:
            from src.agent_droid_bridge.models import ScreenElement

            first = result.elements[0]
            assert isinstance(first, ScreenElement)
            assert first.xpath

    async def test_all_gte_tappable(self, adb_service: ADBService) -> None:
        tappable = await adb_service.get_screen_elements(device_serial=None, mode="tappable")
        all_result = await adb_service.get_screen_elements(device_serial=None, mode="all")
        assert all_result.total >= tappable.total

    async def test_invalid_mode_raises(self, adb_service: ADBService) -> None:
        with pytest.raises(ADBError):
            await adb_service.get_screen_elements(device_serial=None, mode="bogus")


class TestSnapshotUI:
    async def test_snapshot_returns_16_char_token(self, adb_service: ADBService) -> None:
        token = await adb_service.snapshot_ui()
        assert isinstance(token, str)
        assert len(token) == 16
        assert token in adb_service._snapshots

    async def test_snapshot_stores_valid_xml(self, adb_service: ADBService) -> None:
        token = await adb_service.snapshot_ui()
        xml = adb_service._snapshots[token]
        assert "<hierarchy" in xml

    async def test_reused_token_raises_error(self, adb_service: ADBService) -> None:
        token = await adb_service.snapshot_ui()
        await adb_service.detect_ui_change(baseline_token=token)
        with pytest.raises(ADBError, match="not found or already used"):
            await adb_service.detect_ui_change(baseline_token=token)

    async def test_invalid_token_raises_error(self, adb_service: ADBService) -> None:
        with pytest.raises(ADBError, match="not found or already used"):
            await adb_service.detect_ui_change(baseline_token="nonexistent0000x")

    async def test_snapshot_cap_evicts_oldest(self, adb_service: ADBService) -> None:
        adb_service._snapshots.clear()
        for i in range(100):
            adb_service._snapshots[f"fake_token_{i:04d}"] = "<hierarchy/>"
        assert len(adb_service._snapshots) == 100
        await adb_service.snapshot_ui()
        assert len(adb_service._snapshots) == 100
        assert "fake_token_0000" not in adb_service._snapshots


class TestGetScreenText:
    async def test_returns_result(self, adb_service: ADBService) -> None:
        result = await adb_service.get_screen_text(serial=None)
        assert isinstance(result, ScreenTextResult)
        assert result.total > 0

    async def test_plain_non_empty(self, adb_service: ADBService) -> None:
        result = await adb_service.get_screen_text(serial=None)
        assert len(result.plain) > 0
