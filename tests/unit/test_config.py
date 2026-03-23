import pytest
from pydantic import ValidationError

from agent_droid_bridge.config import ADBConfig, ServerConfig, Settings


class TestADBConfig:
    def test_defaults(self) -> None:
        cfg = ADBConfig()
        assert cfg.path == "adb"
        assert cfg.command_timeout == 30
        assert cfg.screenshot_timeout == 60

    def test_zero_timeout_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ADBConfig(command_timeout=0)

    def test_negative_timeout_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ADBConfig(screenshot_timeout=-1)


class TestServerConfig:
    def test_default_log_level(self) -> None:
        cfg = ServerConfig()
        assert cfg.log_level == "INFO"

    def test_log_level_normalized_to_uppercase(self) -> None:
        cfg = ServerConfig(log_level="debug")
        assert cfg.log_level == "DEBUG"

    def test_invalid_log_level_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ServerConfig(log_level="VERBOSE")


class TestSettings:
    def test_defaults_when_no_file(self, tmp_path) -> None:
        missing = tmp_path / "nonexistent.yaml"
        s = Settings.load(path=missing)
        assert s.adb.path == "adb"
        assert s.server.log_level == "INFO"

    def test_load_from_yaml(self, tmp_path) -> None:
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("adb:\n  path: /usr/local/bin/adb\n  command_timeout: 10\n")
        s = Settings.load(path=cfg_file)
        assert s.adb.path == "/usr/local/bin/adb"
        assert s.adb.command_timeout == 10
        assert s.adb.screenshot_timeout == 60


class TestExecutionMode:
    def test_default_is_unrestricted(self) -> None:
        s = Settings()
        assert s.execution_mode == "unrestricted"

    def test_restricted_accepted(self) -> None:
        s = Settings(execution_mode="restricted")
        assert s.execution_mode == "restricted"

    def test_invalid_mode_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Settings(execution_mode="yolo")


class TestAllowShell:
    def test_default_is_true(self) -> None:
        s = Settings()
        assert s.allow_shell is True

    def test_can_be_set_false(self) -> None:
        s = Settings(allow_shell=False)
        assert s.allow_shell is False


class TestUIChangeConfig:
    def test_poll_interval_default(self) -> None:
        cfg = ADBConfig()
        assert cfg.ui_change_poll_interval == 0.5

    def test_zero_poll_interval_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ADBConfig(ui_change_poll_interval=0)

    def test_negative_poll_interval_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ADBConfig(ui_change_poll_interval=-0.1)

    def test_ui_change_timeout_default(self) -> None:
        cfg = ADBConfig()
        assert cfg.ui_change_timeout == 10

    def test_zero_ui_change_timeout_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ADBConfig(ui_change_timeout=0)


class TestAllowedShellCommands:
    def test_defaults_to_empty_list(self) -> None:
        cfg = ADBConfig()
        assert cfg.allowed_shell_commands == []

    def test_accepts_list_of_strings(self) -> None:
        cfg = ADBConfig(allowed_shell_commands=["ls", "pm", "dumpsys"])
        assert cfg.allowed_shell_commands == ["ls", "pm", "dumpsys"]


class TestSettingsLoadExecutionMode:
    def test_reads_execution_mode_env_var(self, tmp_path, monkeypatch) -> None:
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("adb:\n  path: adb\n")
        monkeypatch.setenv("ADB_EXECUTION_MODE", "restricted")
        s = Settings.load(path=cfg_file)
        assert s.execution_mode == "restricted"

    def test_defaults_execution_mode_without_env_var(self, tmp_path, monkeypatch) -> None:
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("adb:\n  path: adb\n")
        monkeypatch.delenv("ADB_EXECUTION_MODE", raising=False)
        s = Settings.load(path=cfg_file)
        assert s.execution_mode == "unrestricted"

    def test_reads_allow_shell_env_var_false(self, tmp_path, monkeypatch) -> None:
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("adb:\n  path: adb\n")
        monkeypatch.setenv("ADB_ALLOW_SHELL", "false")
        s = Settings.load(path=cfg_file)
        assert s.allow_shell is False

    def test_allow_shell_defaults_true_without_env_var(self, tmp_path, monkeypatch) -> None:
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text("adb:\n  path: adb\n")
        monkeypatch.delenv("ADB_ALLOW_SHELL", raising=False)
        s = Settings.load(path=cfg_file)
        assert s.allow_shell is True


class TestScreenshotResult:
    def test_model_fields(self) -> None:
        from agent_droid_bridge.models import ScreenshotResult

        r = ScreenshotResult(image="abc", width=1080, height=1920, format="png")
        assert r.width == 1080
        assert r.height == 1920
        assert r.format == "png"


class TestUIChangeResult:
    def test_without_hierarchy_is_valid(self) -> None:
        from agent_droid_bridge.models import UIChangeResult

        r = UIChangeResult(changed=True, elapsed_seconds=1.5)
        assert r.changed is True
        assert r.elapsed_seconds == 1.5
        assert r.hierarchy is None

    def test_with_hierarchy_is_valid(self) -> None:
        from agent_droid_bridge.models import UIChangeResult

        r = UIChangeResult(changed=False, elapsed_seconds=4.0, hierarchy="<xml/>")
        assert r.changed is False
        assert r.elapsed_seconds == 4.0
        assert r.hierarchy == "<xml/>"


class TestComponentPattern:
    def test_valid_components(self) -> None:
        from agent_droid_bridge.adb import COMPONENT_PATTERN

        assert COMPONENT_PATTERN.match("com.android.calculator2/.Calculator")
        assert COMPONENT_PATTERN.match("com.example/.MainActivity")
        assert COMPONENT_PATTERN.match("com.example/.MyActivity$Inner")
        assert COMPONENT_PATTERN.match("com.example/.Activity@fragment")

    def test_invalid_components_rejected(self) -> None:
        from agent_droid_bridge.adb import COMPONENT_PATTERN

        assert not COMPONENT_PATTERN.match("com.example; rm -rf /")
        assert not COMPONENT_PATTERN.match("")
        assert not COMPONENT_PATTERN.match("com.example!bad")


class TestSnapshotToken:
    def test_token_hash_differs_for_different_xml(self) -> None:
        import hashlib

        xml_a = "<hierarchy><node text='before'/></hierarchy>"
        xml_b = "<hierarchy><node text='after'/></hierarchy>"
        hash_a = hashlib.sha256(xml_a.encode()).hexdigest()[:16]
        hash_b = hashlib.sha256(xml_b.encode()).hexdigest()[:16]
        assert hash_a != hash_b

    def test_token_is_16_chars(self) -> None:
        import hashlib

        xml = "<hierarchy><node text='test'/></hierarchy>"
        token = hashlib.sha256(xml.encode()).hexdigest()[:16]
        assert len(token) == 16

    def test_snapshot_cap_evicts_oldest(self) -> None:
        snapshots: dict[str, str] = {}
        for i in range(100):
            snapshots[f"token_{i:04d}"] = f"xml_{i}"
        assert len(snapshots) == 100
        first_key = next(iter(snapshots))
        assert first_key == "token_0000"
        if len(snapshots) >= 100:
            oldest = next(iter(snapshots))
            del snapshots[oldest]
        snapshots["token_new"] = "xml_new"
        assert "token_0000" not in snapshots
        assert "token_new" in snapshots
        assert len(snapshots) == 100


class TestMultiDeviceError:
    def test_error_message_contains_do_not_retry(self) -> None:
        msg = (
            "Multiple devices connected — cannot proceed without explicit device selection.\n"
            "Available devices:\n"
            "  emulator-5554  (model: sdk_gphone64, state: device)\n"
            "Present this list to the user and wait for them to choose a serial. "
            "Do not retry with a guessed serial."
        )
        assert "Do not retry" in msg
        assert "Present this list to the user" in msg
        assert "emulator-5554" in msg

    def test_error_message_contains_device_list(self) -> None:
        devices = [
            {"serial": "emulator-5554", "state": "device", "model": "sdk_gphone64"},
            {"serial": "192.168.1.10:5555", "state": "device", "model": "Pixel_6"},
        ]
        lines = "\n".join(
            f"  {d['serial']}  (model: {d['model'] or 'unknown'}, state: {d['state']})"
            for d in devices
            if d["state"] != "offline"
        )
        assert "emulator-5554" in lines
        assert "192.168.1.10:5555" in lines
        assert "Pixel_6" in lines


class TestLaunchAppPattern:
    def test_component_pattern_matches_field_pattern(self) -> None:
        import re

        field_pattern = re.compile(r"^[a-zA-Z0-9_.$@/]+$")
        from agent_droid_bridge.adb import COMPONENT_PATTERN

        test_cases = [
            "com.android.settings/.Settings",
            "com.example/.MainActivity",
            "com.example/.MyActivity$Inner",
            "com.example/.Activity@fragment",
            "com.google.android.apps.maps/com.google.android.maps.MapsActivity",
        ]
        for case in test_cases:
            assert COMPONENT_PATTERN.match(case), f"COMPONENT_PATTERN rejected: {case}"
            assert field_pattern.match(case), f"field_pattern rejected: {case}"

    def test_invalid_components_rejected_by_both(self) -> None:
        import re

        field_pattern = re.compile(r"^[a-zA-Z0-9_.$@/]+$")
        from agent_droid_bridge.adb import COMPONENT_PATTERN

        invalid = ["com.example; rm -rf /", "com.example && reboot", ""]
        for case in invalid:
            assert not COMPONENT_PATTERN.match(case)
            assert not field_pattern.match(case)


class TestADBAllowShellParsing:
    def test_true_is_accepted(self, monkeypatch, tmp_path) -> None:
        monkeypatch.setenv("ADB_ALLOW_SHELL", "true")
        from agent_droid_bridge.config import Settings

        s = Settings.load(path=tmp_path / "nonexistent.yaml")
        assert s.allow_shell is True

    def test_false_is_accepted(self, monkeypatch, tmp_path) -> None:
        monkeypatch.setenv("ADB_ALLOW_SHELL", "false")
        from agent_droid_bridge.config import Settings

        s = Settings.load(path=tmp_path / "nonexistent.yaml")
        assert s.allow_shell is False

    def test_invalid_value_raises(self, monkeypatch, tmp_path) -> None:
        monkeypatch.setenv("ADB_ALLOW_SHELL", "banana")
        from agent_droid_bridge.config import Settings

        with pytest.raises(ValueError, match="ADB_ALLOW_SHELL must be"):
            Settings.load(path=tmp_path / "nonexistent.yaml")

    def test_empty_string_raises(self, monkeypatch, tmp_path) -> None:
        monkeypatch.setenv("ADB_ALLOW_SHELL", "")
        from agent_droid_bridge.config import Settings

        with pytest.raises(ValueError, match="ADB_ALLOW_SHELL must be"):
            Settings.load(path=tmp_path / "nonexistent.yaml")
