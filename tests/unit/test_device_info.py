from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from agent_droid_bridge.adb import ADBError
from agent_droid_bridge.device_info import DeviceInfoService

SYNTHETIC_GETPROP = (
    "[ro.product.manufacturer]: [TestCorp]\n"
    "[ro.product.model]: [TestDevice]\n"
    "[ro.product.device]: [testdevice]\n"
    "[ro.build.version.release]: [13]\n"
    "[ro.build.version.sdk]: [33]\n"
    "[ro.kernel.qemu]: [0]\n"
    "[ro.build.characteristics]: [phone]\n"
    "[ro.build.type]: [userdebug]\n"
    "[ro.product.cpu.abi]: [arm64-v8a]\n"
    "[ro.product.cpu.abi2]: [armeabi]\n"
    "[ro.hardware]: [testboard]\n"
    "[ro.product.board]: [testboard]\n"
    "[ro.build.fingerprint]: [google/testdevice/testdevice:13/"
    "TPP1.220624.014/eng.testuser.20220624.100901:userdebug/test-keys]\n"
    "[ro.build.tags]: [test-keys]\n"
    "[ro.build.version.codename]: [REL]\n"
    "[ro.debuggable]: [1]\n"
    "[ro.secure]: [1]\n"
    "[ro.boot.verifiedbootstate]: [green]\n"
    "[persist.sys.usb.config]: [adb]\n"
    "[ro.boot.veritymode]: [enforcing]\n"
    "[ro.crypto.state]: [encrypted]\n"
    "[ro.product.cpu.abilist]: [arm64-v8a,armeabi-v7a,armeabi]\n"
    "[ro.hardware.egl]: [adreno]\n"
    "[ro.board.platform]: [testplatform]\n"
)

_GETPROP_BYTES = SYNTHETIC_GETPROP.encode()
_WM_SIZE_BYTES = b"Physical size: 1080x1920\n"
_WM_DENSITY_BYTES = b"Physical density: 420\n"
_MEMINFO_BYTES = b"MemTotal:        4096000 kB\nMemFree:        2000000 kB\n"
_NPROC_BYTES = b"8\n"
_DF_DATA_BYTES = (
    b"Filesystem       1K-blocks     Used Available Use% Mounted on\n"
    b"/dev/block/dm-9  67108864  15234048  51874816  23% /data\n"
)
_UNAME_BYTES = b"5.15.0-test-generic\n"
_GETENFORCE_BYTES = b"Enforcing\n"
_ID_NON_ROOT_BYTES = b"uid=1000(shell) gid=1000(shell) groups=1000(shell)\n"
_ID_ROOT_BYTES = b"uid=0(root) gid=0(root) groups=0(root)\n"


def _make_adb_mock() -> MagicMock:
    adb = MagicMock()
    adb._build_base_cmd = MagicMock(return_value=["adb"])
    adb._resolve_serial = AsyncMock(return_value=None)
    adb._run = AsyncMock()
    return adb


def _make_service(adb: MagicMock | None = None) -> DeviceInfoService:
    if adb is None:
        adb = MagicMock()
    return DeviceInfoService(adb)


class TestCheckCommand:
    def test_raises_for_command_without_shell_token(self) -> None:
        svc = _make_service()
        with pytest.raises(ADBError, match="Non-shell"):
            svc._check_command(["adb", "devices"])

    def test_raises_for_empty_command_list(self) -> None:
        svc = _make_service()
        with pytest.raises(ADBError, match="Non-shell"):
            svc._check_command([])

    def test_raises_for_untrusted_shell_command(self) -> None:
        svc = _make_service()
        with pytest.raises(ADBError, match="not permitted"):
            svc._check_command(["adb", "shell", "rm", "-rf", "/"])

    def test_passes_for_getprop(self) -> None:
        svc = _make_service()
        svc._check_command(["adb", "shell", "getprop"])

    def test_passes_for_wm(self) -> None:
        svc = _make_service()
        svc._check_command(["adb", "shell", "wm", "size"])

    def test_passes_for_id(self) -> None:
        svc = _make_service()
        svc._check_command(["adb", "shell", "id"])

    def test_passes_for_su(self) -> None:
        svc = _make_service()
        svc._check_command(["adb", "shell", "su", "-c", "id"])

    def test_passes_for_cat(self) -> None:
        svc = _make_service()
        svc._check_command(["adb", "shell", "cat", "/proc/meminfo"])

    def test_passes_for_uname(self) -> None:
        svc = _make_service()
        svc._check_command(["adb", "shell", "uname", "-r"])

    def test_passes_for_getenforce(self) -> None:
        svc = _make_service()
        svc._check_command(["adb", "shell", "getenforce"])

    def test_passes_for_nproc(self) -> None:
        svc = _make_service()
        svc._check_command(["adb", "shell", "nproc"])

    def test_passes_for_df(self) -> None:
        svc = _make_service()
        svc._check_command(["adb", "shell", "df", "/data"])

    def test_raises_for_absolute_path_shell_command(self) -> None:
        svc = _make_service()
        with pytest.raises(ADBError, match="not permitted"):
            svc._check_command(["adb", "shell", "/system/bin/rm"])


class TestParseGetprop:
    def test_parses_standard_property(self) -> None:
        svc = _make_service()
        result = svc._parse_getprop("[ro.product.manufacturer]: [TestCorp]")
        assert result == {"ro.product.manufacturer": "TestCorp"}

    def test_parses_empty_value(self) -> None:
        svc = _make_service()
        result = svc._parse_getprop("[ro.some.key]: []")
        assert result == {"ro.some.key": ""}

    def test_parses_multiple_properties(self) -> None:
        svc = _make_service()
        raw = "[ro.a]: [alpha]\n[ro.b]: [beta]\n[ro.c]: [gamma]"
        result = svc._parse_getprop(raw)
        assert result == {"ro.a": "alpha", "ro.b": "beta", "ro.c": "gamma"}

    def test_ignores_malformed_lines(self) -> None:
        svc = _make_service()
        raw = (
            "[ro.product.model]: [TestDevice]\n"
            "this is not a property\n"
            "[incomplete:\n"
            "[ro.build.type]: [userdebug]\n"
        )
        result = svc._parse_getprop(raw)
        assert result == {"ro.product.model": "TestDevice", "ro.build.type": "userdebug"}

    def test_returns_empty_dict_for_empty_string(self) -> None:
        svc = _make_service()
        assert svc._parse_getprop("") == {}


class TestCheckDeviceCapabilitiesIdentityMode:
    async def test_identity_fields_populated(self) -> None:
        adb = _make_adb_mock()
        adb._run.side_effect = [
            (_GETPROP_BYTES, b""),
            (_UNAME_BYTES, b""),
            (_GETENFORCE_BYTES, b""),
        ]
        svc = _make_service(adb)
        result = await svc.check_device_capabilities("identity")
        assert result.manufacturer == "TestCorp"
        assert result.model == "TestDevice"
        assert result.codename == "testdevice"
        assert result.android_version == "13"
        assert result.api_level == 33
        assert result.is_emulator is False
        assert result.build_type == "userdebug"
        assert result.cpu_abi == "arm64-v8a"
        assert result.hardware == "testboard"
        assert result.board == "testboard"
        assert result.device_type == "phone"
        assert result.build_fingerprint == (
            "google/testdevice/testdevice:13/"
            "TPP1.220624.014/eng.testuser.20220624.100901:userdebug/test-keys"
        )
        assert result.build_tags == "test-keys"
        assert result.android_version_codename == "REL"
        assert result.kernel_version == "5.15.0-test-generic"
        assert result.selinux_status == "Enforcing"

    async def test_hardware_only_fields_are_none_in_identity_mode(self) -> None:
        adb = _make_adb_mock()
        adb._run.return_value = (_GETPROP_BYTES, b"")
        svc = _make_service(adb)
        result = await svc.check_device_capabilities("identity")
        assert result.cpu_abi2 is None
        assert result.screen_resolution is None
        assert result.total_ram_mb is None

    async def test_security_fields_are_none_in_identity_mode(self) -> None:
        adb = _make_adb_mock()
        adb._run.return_value = (_GETPROP_BYTES, b"")
        svc = _make_service(adb)
        result = await svc.check_device_capabilities("identity")
        assert result.adb_is_root is None
        assert result.root_available is None


class TestCheckDeviceCapabilitiesSecurityMode:
    async def test_security_fields_populated(self) -> None:
        adb = _make_adb_mock()
        adb._run.side_effect = [
            (_GETPROP_BYTES, b""),
            (_ID_NON_ROOT_BYTES, b""),
            (_ID_ROOT_BYTES, b""),
            (_GETENFORCE_BYTES, b""),
        ]
        svc = _make_service(adb)
        result = await svc.check_device_capabilities("security")
        assert result.adb_is_root is False
        assert result.root_available is True
        assert result.ro_debuggable is True
        assert result.ro_secure is True
        assert result.verified_boot_state == "green"
        assert result.usb_config == "adb"
        assert result.dm_verity == "enforcing"
        assert result.encryption_state == "encrypted"
        assert result.selinux_status == "Enforcing"

    async def test_identity_and_hardware_fields_are_none_in_security_mode(self) -> None:
        adb = _make_adb_mock()
        adb._run.side_effect = [
            (_GETPROP_BYTES, b""),
            (_ID_NON_ROOT_BYTES, b""),
            (_ID_ROOT_BYTES, b""),
            (_GETENFORCE_BYTES, b""),
        ]
        svc = _make_service(adb)
        result = await svc.check_device_capabilities("security")
        assert result.manufacturer is None
        assert result.model is None
        assert result.cpu_abi is None
        assert result.screen_resolution is None
        assert result.total_ram_mb is None


class TestCheckDeviceCapabilitiesHardwareMode:
    async def test_hardware_fields_populated(self) -> None:
        adb = _make_adb_mock()
        adb._run.side_effect = [
            (_GETPROP_BYTES, b""),
            (_WM_SIZE_BYTES, b""),
            (_MEMINFO_BYTES, b""),
            (_WM_DENSITY_BYTES, b""),
            (_NPROC_BYTES, b""),
            (_DF_DATA_BYTES, b""),
        ]
        svc = _make_service(adb)
        result = await svc.check_device_capabilities("hardware")
        assert result.cpu_abi == "arm64-v8a"
        assert result.cpu_abi2 == "armeabi"
        assert result.hardware == "testboard"
        assert result.board == "testboard"
        assert result.screen_resolution == "1080x1920"
        assert result.total_ram_mb == 4000
        assert result.supported_abis == "arm64-v8a,armeabi-v7a,armeabi"
        assert result.gpu == "adreno"
        assert result.screen_density == "420"
        assert result.cpu_cores == 8
        assert result.storage_total_gb == "64.0G"

    async def test_identity_fields_are_none_in_hardware_mode(self) -> None:
        adb = _make_adb_mock()
        adb._run.side_effect = [
            (_GETPROP_BYTES, b""),
            (_WM_SIZE_BYTES, b""),
            (_MEMINFO_BYTES, b""),
            (_WM_DENSITY_BYTES, b""),
            (_NPROC_BYTES, b""),
            (_DF_DATA_BYTES, b""),
        ]
        svc = _make_service(adb)
        result = await svc.check_device_capabilities("hardware")
        assert result.manufacturer is None
        assert result.model is None
        assert result.android_version is None
        assert result.is_emulator is None

    async def test_security_fields_are_none_in_hardware_mode(self) -> None:
        adb = _make_adb_mock()
        adb._run.side_effect = [
            (_GETPROP_BYTES, b""),
            (_WM_SIZE_BYTES, b""),
            (_MEMINFO_BYTES, b""),
            (_WM_DENSITY_BYTES, b""),
            (_NPROC_BYTES, b""),
            (_DF_DATA_BYTES, b""),
        ]
        svc = _make_service(adb)
        result = await svc.check_device_capabilities("hardware")
        assert result.adb_is_root is None
        assert result.root_available is None


class TestCheckDeviceCapabilitiesAllMode:
    async def test_all_fields_populated_and_mode_is_all(self) -> None:
        adb = _make_adb_mock()
        adb._run.side_effect = [
            (_GETPROP_BYTES, b""),
            (_UNAME_BYTES, b""),
            (_GETENFORCE_BYTES, b""),
            (_WM_SIZE_BYTES, b""),
            (_MEMINFO_BYTES, b""),
            (_WM_DENSITY_BYTES, b""),
            (_NPROC_BYTES, b""),
            (_DF_DATA_BYTES, b""),
            (_ID_NON_ROOT_BYTES, b""),
            (_ID_ROOT_BYTES, b""),
            (_GETENFORCE_BYTES, b""),
        ]
        svc = _make_service(adb)
        result = await svc.check_device_capabilities("all")
        assert result.mode == "all"
        assert result.manufacturer == "TestCorp"
        assert result.model == "TestDevice"
        assert result.kernel_version == "5.15.0-test-generic"
        assert result.cpu_abi == "arm64-v8a"
        assert result.cpu_abi2 == "armeabi"
        assert result.screen_resolution == "1080x1920"
        assert result.screen_density == "420"
        assert result.total_ram_mb == 4000
        assert result.cpu_cores == 8
        assert result.storage_total_gb == "64.0G"
        assert result.adb_is_root is False
        assert result.root_available is True
        assert result.selinux_status == "Enforcing"


class TestApiLevelParsing:
    async def test_api_level_is_none_for_non_numeric_sdk(self) -> None:
        getprop = SYNTHETIC_GETPROP.replace(
            "[ro.build.version.sdk]: [33]",
            "[ro.build.version.sdk]: [not-a-number]",
        )
        adb = _make_adb_mock()
        adb._run.return_value = (getprop.encode(), b"")
        svc = _make_service(adb)
        result = await svc.check_device_capabilities("identity")
        assert result.api_level is None


class TestEmulatorDetection:
    async def test_is_emulator_true_when_qemu_is_1(self) -> None:
        getprop = SYNTHETIC_GETPROP.replace("[ro.kernel.qemu]: [0]", "[ro.kernel.qemu]: [1]")
        adb = _make_adb_mock()
        adb._run.return_value = (getprop.encode(), b"")
        svc = _make_service(adb)
        result = await svc.check_device_capabilities("identity")
        assert result.is_emulator is True

    async def test_is_emulator_true_when_characteristics_contains_emulator(self) -> None:
        getprop = SYNTHETIC_GETPROP.replace(
            "[ro.build.characteristics]: [phone]",
            "[ro.build.characteristics]: [emulator]",
        )
        adb = _make_adb_mock()
        adb._run.return_value = (getprop.encode(), b"")
        svc = _make_service(adb)
        result = await svc.check_device_capabilities("identity")
        assert result.is_emulator is True


class TestDeviceTypeDetection:
    async def test_device_type_is_tablet_when_characteristics_contains_tablet(self) -> None:
        getprop = SYNTHETIC_GETPROP.replace(
            "[ro.build.characteristics]: [phone]",
            "[ro.build.characteristics]: [tablet]",
        )
        adb = _make_adb_mock()
        adb._run.return_value = (getprop.encode(), b"")
        svc = _make_service(adb)
        result = await svc.check_device_capabilities("identity")
        assert result.device_type == "tablet"

    async def test_device_type_is_phone_when_characteristics_is_phone(self) -> None:
        adb = _make_adb_mock()
        adb._run.return_value = (_GETPROP_BYTES, b"")
        svc = _make_service(adb)
        result = await svc.check_device_capabilities("identity")
        assert result.device_type == "phone"

    async def test_device_type_is_phone_when_characteristics_is_empty(self) -> None:
        getprop = SYNTHETIC_GETPROP.replace(
            "[ro.build.characteristics]: [phone]",
            "[ro.build.characteristics]: []",
        )
        adb = _make_adb_mock()
        adb._run.return_value = (getprop.encode(), b"")
        svc = _make_service(adb)
        result = await svc.check_device_capabilities("identity")
        assert result.device_type == "phone"

    async def test_device_type_is_emulator_when_is_emulator_is_true(self) -> None:
        # qemu=1 with non-tablet/non-tv/non-watch characteristics forces device_type to "emulator"
        getprop = SYNTHETIC_GETPROP.replace("[ro.kernel.qemu]: [0]", "[ro.kernel.qemu]: [1]")
        adb = _make_adb_mock()
        adb._run.return_value = (getprop.encode(), b"")
        svc = _make_service(adb)
        result = await svc.check_device_capabilities("identity")
        assert result.device_type == "emulator"


class TestHardwareFailureHandling:
    async def test_screen_resolution_is_none_when_wm_fails(self) -> None:
        adb = _make_adb_mock()
        adb._run.side_effect = [
            (_GETPROP_BYTES, b""),
            ADBError("wm command failed"),
            (_MEMINFO_BYTES, b""),
            (_WM_DENSITY_BYTES, b""),
            (_NPROC_BYTES, b""),
            (_DF_DATA_BYTES, b""),
        ]
        svc = _make_service(adb)
        result = await svc.check_device_capabilities("hardware")
        assert result.screen_resolution is None
        assert result.cpu_abi == "arm64-v8a"
        assert result.total_ram_mb == 4000

    async def test_total_ram_mb_is_none_when_meminfo_fails(self) -> None:
        adb = _make_adb_mock()
        adb._run.side_effect = [
            (_GETPROP_BYTES, b""),
            (_WM_SIZE_BYTES, b""),
            ADBError("cat command failed"),
            (_WM_DENSITY_BYTES, b""),
            (_NPROC_BYTES, b""),
            (_DF_DATA_BYTES, b""),
        ]
        svc = _make_service(adb)
        result = await svc.check_device_capabilities("hardware")
        assert result.total_ram_mb is None
        assert result.screen_resolution == "1080x1920"
        assert result.cpu_abi == "arm64-v8a"

    async def test_cpu_cores_is_none_when_nproc_fails(self) -> None:
        adb = _make_adb_mock()
        adb._run.side_effect = [
            (_GETPROP_BYTES, b""),
            (_WM_SIZE_BYTES, b""),
            (_MEMINFO_BYTES, b""),
            (_WM_DENSITY_BYTES, b""),
            ADBError("nproc failed"),
            (_DF_DATA_BYTES, b""),
        ]
        svc = _make_service(adb)
        result = await svc.check_device_capabilities("hardware")
        assert result.cpu_cores is None
        assert result.screen_resolution == "1080x1920"
        assert result.screen_density == "420"
        assert result.storage_total_gb == "64.0G"


class TestSecurityFailureHandling:
    async def test_adb_is_root_is_none_when_id_command_fails(self) -> None:
        adb = _make_adb_mock()
        adb._run.side_effect = [
            (_GETPROP_BYTES, b""),
            ADBError("id command failed"),
            (_ID_ROOT_BYTES, b""),
            (_GETENFORCE_BYTES, b""),
        ]
        svc = _make_service(adb)
        result = await svc.check_device_capabilities("security")
        assert result.adb_is_root is None

    async def test_root_available_is_false_when_su_command_fails(self) -> None:
        adb = _make_adb_mock()
        adb._run.side_effect = [
            (_GETPROP_BYTES, b""),
            (_ID_NON_ROOT_BYTES, b""),
            ADBError("su command failed"),
            (_GETENFORCE_BYTES, b""),
        ]
        svc = _make_service(adb)
        result = await svc.check_device_capabilities("security")
        assert result.root_available is False

    async def test_selinux_status_is_none_when_getenforce_fails(self) -> None:
        adb = _make_adb_mock()
        adb._run.side_effect = [
            (_GETPROP_BYTES, b""),
            (_ID_NON_ROOT_BYTES, b""),
            (_ID_ROOT_BYTES, b""),
            ADBError("getenforce failed"),
        ]
        svc = _make_service(adb)
        result = await svc.check_device_capabilities("security")
        assert result.selinux_status is None
        assert result.adb_is_root is False
        assert result.root_available is True


class TestGetpropErrorPropagation:
    async def test_adb_error_from_getprop_propagates(self) -> None:
        adb = _make_adb_mock()
        adb._run.side_effect = ADBError("getprop failed")
        svc = _make_service(adb)
        with pytest.raises(ADBError):
            await svc.check_device_capabilities("identity")


class TestBuildType:
    async def test_build_type_is_none_when_prop_is_absent(self) -> None:
        getprop = "\n".join(
            line for line in SYNTHETIC_GETPROP.splitlines() if "ro.build.type" not in line
        )
        adb = _make_adb_mock()
        adb._run.return_value = (getprop.encode(), b"")
        svc = _make_service(adb)
        result = await svc.check_device_capabilities("identity")
        assert result.build_type is None
