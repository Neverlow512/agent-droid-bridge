from __future__ import annotations

from agent_droid_bridge.extra_tool_packs.app_manager.parsers import (
    parse_components,
    parse_metadata,
    parse_permissions,
    parse_version_name_from_dumpsys,
)

DUMPSYS_OUTPUT = """\
Activity Resolver Table:
  Non-Data Actions:
    android.intent.action.MAIN:
        0000abc com.example.testapp/.MainActivity filter 0000abc
        0000def com.example.testapp/.SettingsActivity filter 0000def
        0000ghi com.other.app/.OtherMainActivity filter 0000ghi
Receiver Resolver Table:
  Non-Data Actions:
    android.intent.action.BOOT_COMPLETED:
        1111abc com.example.testapp/.BootReceiver filter 1111abc
Service Resolver Table:
  Non-Data Actions:
    com.example.action.BACKGROUND:
        2222abc com.example.testapp/.BackgroundService filter 2222abc
Provider Resolver Table:
    3333abc com.example.testapp/com.example.testapp.data.AppContentProvider filter 3333abc
Packages:
  Package [com.example.testapp] (abc123):
    userId=10100
    codePath=/data/app/com.example.testapp-abc123
    nativeLibraryDir=/data/app/com.example.testapp-abc123/lib/arm64
    versionCode=210 minSdk=21 targetSdk=33
    versionName=2.1.0
    firstInstallTime=2023-01-15 10:00:00
    lastUpdateTime=2024-03-20 14:30:00
    installerPackageName=com.android.vending
    dataDir=/data/user/0/com.example.testapp
    declared permissions:
      android.permission.CAMERA: prot=dangerous
      android.permission.RECORD_AUDIO: prot=dangerous
    install permissions:
      android.permission.INTERNET: granted=true
      android.permission.RECEIVE_BOOT_COMPLETED: granted=false
    User 0: ceDataInode=12345 installed=true hidden=false
      runtime permissions:
        android.permission.CAMERA: granted=true, flags=[ USER_SET]
        android.permission.RECORD_AUDIO: granted=false, flags=[]
    User 10: ceDataInode=67890 installed=true hidden=false
      runtime permissions:
        android.permission.READ_EXTERNAL_STORAGE: granted=true, flags=[ USER_SET]
  Package [com.other.app] (def456):
    versionCode=990 minSdk=21 targetSdk=33
    versionName=9.9.9
    firstInstallTime=2022-05-01 09:00:00
    lastUpdateTime=2022-05-01 09:00:00
"""

DUMPSYS_LEGACY_NATIVE_LIB = """\
Packages:
  Package [com.example.testapp] (abc123):
    userId=10100
    versionCode=1 minSdk=21 targetSdk=33
    versionName=1.0.0
    legacyNativeLibraryDir=/data/app/com.example.testapp-abc123/lib
    installInitiatingPackageName=com.example.installer
"""

DUMPSYS_INNER_CLASS_COMPONENTS = """\
Activity Resolver Table:
  Non-Data Actions:
      abc12 com.example.testapp/.ui.MainActivity$InnerActivity filter abc12
Service Resolver Table:
  Non-Data Actions:
      def78 com.example.testapp/.service.SyncService$Worker filter def78
Packages:
  Package [com.example.testapp] (abc123):
    userId=10100
    versionCode=1 minSdk=21 targetSdk=33
    versionName=1.0.0
"""

DUMPSYS_PERMISSIONS_SECTION_RESET = """\
Packages:
  Package [com.example.testapp] (abc123):
    userId=10100
    install permissions:
      android.permission.INTERNET: granted=true
    activities:
      com.example.testapp/.MainActivity
      android.permission.FAKE_LATE: granted=true
"""

EMPTY_OUTPUT = ""

MISSING_SECTIONS_OUTPUT = """\
Packages:
  Package [com.example.testapp] (abc123):
    userId=10100
"""


class TestParseVersionName:
    def test_extracts_version_name(self) -> None:
        result = parse_version_name_from_dumpsys(DUMPSYS_OUTPUT)
        assert result == "2.1.0"

    def test_returns_none_for_empty_string(self) -> None:
        assert parse_version_name_from_dumpsys(EMPTY_OUTPUT) is None

    def test_returns_none_when_not_present(self) -> None:
        output = "Package [com.example.testapp] (abc123):\n  userId=10100\n"
        assert parse_version_name_from_dumpsys(output) is None

    def test_returns_first_match_not_scoped_to_package(self) -> None:
        # This helper is not package-scoped — it returns the first versionName= in the string.
        result = parse_version_name_from_dumpsys(DUMPSYS_OUTPUT)
        assert result == "2.1.0"
        assert result != "9.9.9"


class TestParseMetadata:
    def test_extracts_version_name_and_code(self) -> None:
        result = parse_metadata(DUMPSYS_OUTPUT, "com.example.testapp")
        assert result.version_name == "2.1.0"
        assert result.version_code == 210

    def test_extracts_install_times(self) -> None:
        result = parse_metadata(DUMPSYS_OUTPUT, "com.example.testapp")
        assert result.first_install_time == "2023-01-15 10:00:00"
        assert result.last_update_time == "2024-03-20 14:30:00"

    def test_extracts_data_dir(self) -> None:
        result = parse_metadata(DUMPSYS_OUTPUT, "com.example.testapp")
        assert result.data_dir == "/data/user/0/com.example.testapp"

    def test_extracts_native_lib_dir(self) -> None:
        result = parse_metadata(DUMPSYS_OUTPUT, "com.example.testapp")
        assert result.native_lib_dir is not None
        assert "arm64" in result.native_lib_dir

    def test_extracts_legacy_native_lib_dir_prefix(self) -> None:
        result = parse_metadata(DUMPSYS_LEGACY_NATIVE_LIB, "com.example.testapp")
        assert result.native_lib_dir == "/data/app/com.example.testapp-abc123/lib"

    def test_extracts_installer(self) -> None:
        result = parse_metadata(DUMPSYS_OUTPUT, "com.example.testapp")
        assert result.installer == "com.android.vending"

    def test_install_initiating_package_fallback(self) -> None:
        result = parse_metadata(DUMPSYS_LEGACY_NATIVE_LIB, "com.example.testapp")
        assert result.installer == "com.example.installer"

    def test_apk_paths_from_code_path(self) -> None:
        result = parse_metadata(DUMPSYS_OUTPUT, "com.example.testapp")
        assert len(result.apk_paths) == 1
        assert "/data/app/com.example.testapp-abc123" in result.apk_paths

    def test_scoped_to_package_does_not_bleed(self) -> None:
        result = parse_metadata(DUMPSYS_OUTPUT, "com.example.testapp")
        assert result.version_name == "2.1.0"
        assert result.version_name != "9.9.9"

    def test_returns_empty_metadata_when_package_not_found(self) -> None:
        result = parse_metadata(DUMPSYS_OUTPUT, "com.nonexistent.app")
        assert result.version_name is None
        assert result.version_code is None
        assert result.first_install_time is None
        assert result.last_update_time is None
        assert result.data_dir is None
        assert result.apk_paths == []
        assert result.native_lib_dir is None
        assert result.installer is None

    def test_missing_fields_return_none(self) -> None:
        result = parse_metadata(MISSING_SECTIONS_OUTPUT, "com.example.testapp")
        assert result.version_name is None
        assert result.version_code is None
        assert result.first_install_time is None
        assert result.last_update_time is None
        assert result.data_dir is None
        assert result.apk_paths == []
        assert result.native_lib_dir is None
        assert result.installer is None


class TestParsePermissions:
    def test_declared_permissions_extracted(self) -> None:
        result = parse_permissions(DUMPSYS_OUTPUT, "com.example.testapp")
        assert "android.permission.CAMERA" in result.declared
        assert "android.permission.RECORD_AUDIO" in result.declared
        assert "install" not in result.declared
        assert "runtime" not in result.declared

    def test_install_granted_only_true(self) -> None:
        result = parse_permissions(DUMPSYS_OUTPUT, "com.example.testapp")
        assert "android.permission.INTERNET" in result.install_granted
        assert "android.permission.RECEIVE_BOOT_COMPLETED" not in result.install_granted

    def test_runtime_granted_from_all_user_blocks(self) -> None:
        result = parse_permissions(DUMPSYS_OUTPUT, "com.example.testapp")
        assert "android.permission.CAMERA" in result.runtime_granted
        assert "android.permission.READ_EXTERNAL_STORAGE" in result.runtime_granted

    def test_install_and_runtime_are_distinct(self) -> None:
        result = parse_permissions(DUMPSYS_OUTPUT, "com.example.testapp")
        assert set(result.install_granted).isdisjoint(set(result.runtime_granted))

    def test_section_reset_stops_collection_after_component_header(self) -> None:
        # "activities:" at indent <= 4 resets the state machine; permissions after it are ignored.
        result = parse_permissions(DUMPSYS_PERMISSIONS_SECTION_RESET, "com.example.testapp")
        assert "android.permission.INTERNET" in result.install_granted
        assert "android.permission.FAKE_LATE" not in result.install_granted

    def test_permissions_do_not_bleed_from_adjacent_package(self) -> None:
        output = """\
Packages:
  Package [com.example.testapp] (abc123):
    install permissions:
      android.permission.INTERNET: granted=true
  Package [com.other.app] (def456):
    install permissions:
      android.permission.READ_CONTACTS: granted=true
"""
        result = parse_permissions(output, "com.example.testapp")
        assert "android.permission.INTERNET" in result.install_granted
        assert "android.permission.READ_CONTACTS" not in result.install_granted

    def test_missing_sections_return_empty_lists(self) -> None:
        result = parse_permissions(MISSING_SECTIONS_OUTPUT, "com.example.testapp")
        assert result.declared == []
        assert result.install_granted == []
        assert result.runtime_granted == []

    def test_empty_output_returns_empty(self) -> None:
        result = parse_permissions(EMPTY_OUTPUT, "com.example.testapp")
        assert result.declared == []
        assert result.install_granted == []
        assert result.runtime_granted == []


class TestParseComponents:
    def test_activities_extracted(self) -> None:
        result = parse_components(DUMPSYS_OUTPUT, "com.example.testapp")
        assert len(result.activities) == 2

    def test_services_extracted(self) -> None:
        result = parse_components(DUMPSYS_OUTPUT, "com.example.testapp")
        assert len(result.services) == 1

    def test_receivers_extracted(self) -> None:
        result = parse_components(DUMPSYS_OUTPUT, "com.example.testapp")
        assert len(result.receivers) == 1

    def test_providers_extracted(self) -> None:
        result = parse_components(DUMPSYS_OUTPUT, "com.example.testapp")
        assert len(result.providers) == 1
        assert result.providers[0] == "com.example.testapp/com.example.testapp.data.AppContentProvider"

    def test_inner_class_names_with_dollar_sign(self) -> None:
        result = parse_components(DUMPSYS_INNER_CLASS_COMPONENTS, "com.example.testapp")
        assert any("$" in name for name in result.activities)
        assert any("$" in name for name in result.services)

    def test_empty_receivers_section(self) -> None:
        result = parse_components(DUMPSYS_INNER_CLASS_COMPONENTS, "com.example.testapp")
        assert result.receivers == []

    def test_no_bleed_from_adjacent_package(self) -> None:
        result = parse_components(DUMPSYS_OUTPUT, "com.example.testapp")
        assert len(result.activities) == 2
        assert ".OtherMainActivity" not in result.activities

    def test_package_not_found_returns_empty(self) -> None:
        result = parse_components(DUMPSYS_OUTPUT, "com.nonexistent.app")
        assert result.activities == []
        assert result.services == []
        assert result.receivers == []
        assert result.providers == []

    def test_component_names_are_strings(self) -> None:
        result = parse_components(DUMPSYS_OUTPUT, "com.example.testapp")
        all_components = (
            result.activities + result.services + result.receivers + result.providers
        )
        assert all(isinstance(c, str) for c in all_components)
