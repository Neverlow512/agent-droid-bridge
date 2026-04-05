from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_droid_bridge.config import ExtraToolPacksConfig, Settings, ToolsConfig
from agent_droid_bridge.server import _lifespan
from agent_droid_bridge.startup import _pack_meta, apply_tool_deny_list, build_server_instructions, load_extra_packs


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


@dataclass
class _FakeTool:
    name: str
    description: str | None
    tags: set[str]


class TestBuildServerInstructions:
    def test_core_tools_grouped_under_core_section(self) -> None:
        tools = [_FakeTool("tap", "Taps the screen.", set())]
        result = build_server_instructions(tools)
        assert "## Core" in result
        assert "tap" in result

    def test_pack_tools_grouped_under_pack_section(self) -> None:
        tools = [_FakeTool("launch_app", "Launches an app.", {"app_manager"})]
        result = build_server_instructions(tools)
        assert "## app_manager" in result
        assert "launch_app" in result

    def test_core_section_before_pack_sections(self) -> None:
        tools = [
            _FakeTool("tap", "Taps the screen.", set()),
            _FakeTool("launch_app", "Launches an app.", {"app_manager"}),
        ]
        result = build_server_instructions(tools)
        assert result.index("## Core") < result.index("## app_manager")

    def test_tools_sorted_alphabetically_within_section(self) -> None:
        tools = [
            _FakeTool("zoom", "Zooms in.", set()),
            _FakeTool("alpha", "Does alpha.", set()),
        ]
        result = build_server_instructions(tools)
        assert result.index("alpha") < result.index("zoom")

    def test_pack_sections_sorted_alphabetically(self) -> None:
        tools = [
            _FakeTool("z_tool", "Z tool.", {"zebra"}),
            _FakeTool("a_tool", "A tool.", {"alpha"}),
        ]
        result = build_server_instructions(tools)
        assert result.index("## alpha") < result.index("## zebra")

    def test_core_description_rendered_from_pack_meta(self) -> None:
        tools = [_FakeTool("tap", "Taps the screen.", set())]
        result = build_server_instructions(tools, pack_meta={"core": "Core controls."})
        assert result.index("Core controls.") > result.index("## Core")

    def test_pack_description_rendered_from_pack_meta(self) -> None:
        tools = [_FakeTool("launch_app", "Launches an app.", {"app_manager"})]
        result = build_server_instructions(tools, pack_meta={"app_manager": "App management."})
        assert result.index("App management.") > result.index("## app_manager")

    def test_custom_header_used(self) -> None:
        result = build_server_instructions([], header="Custom header text.")
        assert result.startswith("Custom header text.")

    def test_default_header_used_when_not_provided(self) -> None:
        result = build_server_instructions([])
        assert result.startswith("Agent Droid Bridge — Android device control via ADB.")

    def test_first_sentence_strips_newlines(self) -> None:
        tools = [_FakeTool("tap", "Taps the screen.\n\nMore detail.", set())]
        result = build_server_instructions(tools)
        assert "- tap: Taps the screen." in result

    def test_first_sentence_preserves_question_mark(self) -> None:
        tools = [_FakeTool("query", "Is the device ready?", set())]
        result = build_server_instructions(tools)
        assert "Is the device ready?" in result
        assert "Is the device ready?." not in result

    def test_first_sentence_preserves_exclamation_mark(self) -> None:
        tools = [_FakeTool("alert", "Sound the alarm!", set())]
        result = build_server_instructions(tools)
        assert "Sound the alarm!" in result
        assert "Sound the alarm!." not in result

    def test_first_sentence_extracts_from_multi_sentence(self) -> None:
        tools = [_FakeTool("tap", "Taps the screen. Returns tap result.", set())]
        result = build_server_instructions(tools)
        assert "- tap: Taps the screen." in result
        assert "Returns tap result." not in result

    def test_first_sentence_adds_period_when_missing(self) -> None:
        tools = [_FakeTool("tap", "Taps the screen", set())]
        result = build_server_instructions(tools)
        assert "- tap: Taps the screen." in result

    def test_none_description_produces_fallback(self) -> None:
        tools = [_FakeTool("mystery", None, set())]
        result = build_server_instructions(tools)
        assert "(no description)" in result

    def test_empty_tool_list_produces_empty_core_section(self) -> None:
        result = build_server_instructions([])
        assert "## Core (0 tools)" in result

    def test_tool_with_multiple_tags_uses_first_alphabetical(self) -> None:
        tools = [_FakeTool("launch_app", "Launches an app.", {"beta", "app_manager"})]
        result = build_server_instructions(tools)
        assert "## app_manager" in result
        assert "## beta" not in result


class TestLoadExtraPacksMetadata:
    def setup_method(self) -> None:
        _pack_meta.clear()

    def test_pack_with_pack_meta_description_stored(self) -> None:
        mcp = MagicMock()
        settings = Settings(
            extra_tool_packs=ExtraToolPacksConfig(enabled=True, packs=["my_pack"])
        )
        mock_module = MagicMock()
        mock_module.PACK_META = {"description": "Some description"}
        with patch("importlib.import_module", return_value=mock_module):
            load_extra_packs(mcp, settings)
        assert _pack_meta["my_pack"] == "Some description"

    def test_pack_without_pack_meta_not_stored(self) -> None:
        mcp = MagicMock()
        settings = Settings(
            extra_tool_packs=ExtraToolPacksConfig(enabled=True, packs=["bare_pack"])
        )
        mock_module = MagicMock(spec=["register"])
        with patch("importlib.import_module", return_value=mock_module):
            load_extra_packs(mcp, settings)
        assert "bare_pack" not in _pack_meta

    def test_pack_with_pack_meta_missing_description_key_not_stored(self) -> None:
        mcp = MagicMock()
        settings = Settings(
            extra_tool_packs=ExtraToolPacksConfig(enabled=True, packs=["partial_pack"])
        )
        mock_module = MagicMock()
        mock_module.PACK_META = {"other_key": "value"}
        with patch("importlib.import_module", return_value=mock_module):
            load_extra_packs(mcp, settings)
        assert "partial_pack" not in _pack_meta

    def test_multiple_packs_each_stored_independently(self) -> None:
        mcp = MagicMock()
        settings = Settings(
            extra_tool_packs=ExtraToolPacksConfig(enabled=True, packs=["pack_a", "pack_b"])
        )

        def fake_import(path: str):
            mod = MagicMock()
            if path.endswith("pack_a"):
                mod.PACK_META = {"description": "Pack A desc"}
            elif path.endswith("pack_b"):
                mod.PACK_META = {"description": "Pack B desc"}
            return mod

        with patch("importlib.import_module", side_effect=fake_import):
            load_extra_packs(mcp, settings)
        assert _pack_meta["pack_a"] == "Pack A desc"
        assert _pack_meta["pack_b"] == "Pack B desc"


class TestLifespanWiring:
    async def test_lifespan_sets_server_instructions(self) -> None:
        mock_server = MagicMock()
        mock_server.list_tools = AsyncMock(
            return_value=[
                _FakeTool("tap", "Taps the screen.", set()),
                _FakeTool("swipe", "Swipes the screen.", set()),
                _FakeTool("launch_app", "Launches an app.", {"app_manager"}),
            ]
        )
        async with _lifespan(mock_server):
            pass
        assert mock_server.instructions is not None
        assert isinstance(mock_server.instructions, str)
        assert len(mock_server.instructions) > 0
        assert "## Core" in mock_server.instructions
