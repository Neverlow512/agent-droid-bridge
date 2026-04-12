from __future__ import annotations

from fastmcp import FastMCP

from ...adb import ADBService
from .tools import register_tools

PACK_META = {
    "description": (
        "App management and control — install, uninstall, list, inspect, and extract APKs; "
        "manage runtime permissions; control app state; launch apps by package name; "
        "and fire intents at exported components."
    ),
}


def register(mcp: FastMCP, adb: ADBService) -> None:
    register_tools(mcp, adb)
