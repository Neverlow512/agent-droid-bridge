from __future__ import annotations

import importlib
import logging
import re
from collections.abc import Sequence

from fastmcp import FastMCP
from fastmcp.tools.tool import Tool

from .config import Settings

logger = logging.getLogger(__name__)

_pack_meta: dict[str, str] = {}


def build_server_instructions(
    tools: Sequence[Tool],
    pack_meta: dict[str, str] | None = None,
    header: str = "Agent Droid Bridge — Android device control via ADB.",
) -> str:
    _meta = pack_meta or {}

    def _first_sentence(desc: str | None) -> str:
        if not desc or not desc.strip():
            return "(no description)"
        cleaned = re.sub(r"\s*\n\s*", " ", desc.strip())
        sentence = re.split(r"(?<=[.!?])\s+(?=[A-Z])", cleaned)[0]
        if sentence[-1] not in ".!?":
            sentence += "."
        return sentence

    core: list[Tool] = []
    packs: dict[str, list[Tool]] = {}

    for tool in tools:
        pack_tags = sorted(tool.tags or set())
        if not pack_tags:
            core.append(tool)
        else:
            packs.setdefault(pack_tags[0], []).append(tool)

    parts: list[str] = [header]

    core_sorted = sorted(core, key=lambda t: t.name)
    core_lines = [f"## Core ({len(core_sorted)} tools)"]
    if _meta.get("core"):
        core_lines.append(_meta["core"])
    for tool in core_sorted:
        core_lines.append(f"- {tool.name}: {_first_sentence(tool.description)}")
    parts.append("\n".join(core_lines))

    for pack_name in sorted(packs.keys()):
        pack_tools = sorted(packs[pack_name], key=lambda t: t.name)
        pack_lines = [f"## {pack_name} ({len(pack_tools)} tools)"]
        if _meta.get(pack_name):
            pack_lines.append(_meta[pack_name])
        for tool in pack_tools:
            pack_lines.append(f"- {tool.name}: {_first_sentence(tool.description)}")
        parts.append("\n".join(pack_lines))

    return "\n\n".join(parts)


def apply_tool_deny_list(mcp: FastMCP, settings: Settings) -> None:
    denied = settings.tools.denied
    if not denied:
        return
    for tool_name in denied:
        try:
            mcp.disable(names={tool_name})
            logger.info("Disabled denied tool: %s", tool_name)
        except Exception:
            logger.warning("Tool '%s' in tools.denied not found — skipping", tool_name)


def load_extra_packs(mcp: FastMCP, settings: Settings) -> None:
    if not settings.extra_tool_packs.enabled or not settings.extra_tool_packs.packs:
        return
    for name in settings.extra_tool_packs.packs:
        module_path = f"agent_droid_bridge.extra_tool_packs.{name}"
        try:
            module = importlib.import_module(module_path)
        except ImportError as e:
            raise ValueError(f"Extra tool pack '{name}' not found at {module_path}") from e
        register = getattr(module, "register", None)
        if register is None:
            raise ValueError(f"Extra tool pack '{name}' has no register() function")
        register(mcp)
        meta = getattr(module, "PACK_META", None)
        if meta and "description" in meta:
            _pack_meta[name] = meta["description"]
        logger.info("Loaded extra tool pack: %s", name)
