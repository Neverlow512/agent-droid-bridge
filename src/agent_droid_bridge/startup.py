from __future__ import annotations

import importlib
import logging

from fastmcp import FastMCP

from .config import Settings

logger = logging.getLogger(__name__)


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
        logger.info("Loaded extra tool pack: %s", name)
