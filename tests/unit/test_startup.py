from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from agent_droid_bridge.config import ExtraToolPacksConfig, Settings, ToolsConfig
from agent_droid_bridge.startup import apply_tool_deny_list, load_extra_packs


class TestApplyToolDenyList:
    def test_empty_denied_list_does_nothing(self) -> None:
        mcp = MagicMock()
        settings = Settings(tools=ToolsConfig(denied=[]))
        apply_tool_deny_list(mcp, settings)
        mcp.disable.assert_not_called()

    def test_single_tool_disabled(self) -> None:
        mcp = MagicMock()
        settings = Settings(tools=ToolsConfig(denied=["execute_adb_command"]))
        apply_tool_deny_list(mcp, settings)
        mcp.disable.assert_called_once_with(names={"execute_adb_command"})

    def test_multiple_tools_disabled(self) -> None:
        mcp = MagicMock()
        settings = Settings(tools=ToolsConfig(denied=["tool_a", "tool_b"]))
        apply_tool_deny_list(mcp, settings)
        assert mcp.disable.call_count == 2
        mcp.disable.assert_any_call(names={"tool_a"})
        mcp.disable.assert_any_call(names={"tool_b"})

    def test_unknown_tool_logs_warning_no_crash(self) -> None:
        mcp = MagicMock()
        mcp.disable.side_effect = Exception("tool not found")
        settings = Settings(tools=ToolsConfig(denied=["nonexistent_tool"]))
        apply_tool_deny_list(mcp, settings)


class TestLoadExtraPacks:
    def test_disabled_packs_not_loaded(self) -> None:
        mcp = MagicMock()
        settings = Settings(
            extra_tool_packs=ExtraToolPacksConfig(enabled=False, packs=["some_pack"])
        )
        with patch("importlib.import_module") as mock_import:
            load_extra_packs(mcp, settings)
            mock_import.assert_not_called()

    def test_empty_packs_list_not_loaded(self) -> None:
        mcp = MagicMock()
        settings = Settings(extra_tool_packs=ExtraToolPacksConfig(enabled=True, packs=[]))
        with patch("importlib.import_module") as mock_import:
            load_extra_packs(mcp, settings)
            mock_import.assert_not_called()

    def test_invalid_pack_name_raises_value_error(self) -> None:
        mcp = MagicMock()
        settings = Settings(
            extra_tool_packs=ExtraToolPacksConfig(enabled=True, packs=["nonexistent_pack"])
        )
        with patch("importlib.import_module", side_effect=ImportError("no module")):
            with pytest.raises(ValueError, match="nonexistent_pack"):
                load_extra_packs(mcp, settings)

    def test_missing_register_function_raises_value_error(self) -> None:
        mcp = MagicMock()
        settings = Settings(
            extra_tool_packs=ExtraToolPacksConfig(enabled=True, packs=["test_pack"])
        )
        mock_module = MagicMock()
        mock_module.register = None
        with patch("importlib.import_module", return_value=mock_module):
            with pytest.raises(ValueError, match="register"):
                load_extra_packs(mcp, settings)

    def test_valid_pack_calls_register(self) -> None:
        mcp = MagicMock()
        settings = Settings(
            extra_tool_packs=ExtraToolPacksConfig(enabled=True, packs=["test_pack"])
        )
        mock_register = MagicMock()
        mock_module = MagicMock()
        mock_module.register = mock_register
        with patch("importlib.import_module", return_value=mock_module):
            load_extra_packs(mcp, settings)
            mock_register.assert_called_once_with(mcp)
