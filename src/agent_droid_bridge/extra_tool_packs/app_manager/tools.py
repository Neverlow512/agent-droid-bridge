from __future__ import annotations

from fastmcp import FastMCP

from ...adb import ADBService
from .control_service import AppControlService
from .control_tools import register_control_tools
from .package_tools import register_package_tools
from .service import AppManagerService


def register_tools(mcp: FastMCP, adb: ADBService) -> None:
    manager_service = AppManagerService(adb)
    control_service = AppControlService(adb)
    register_package_tools(mcp, manager_service)
    register_control_tools(mcp, control_service)
