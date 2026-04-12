from __future__ import annotations

import logging
from typing import Annotated, Literal

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from ...adb import ADBError
from ...utils.types import DeviceSerial
from .control_service import AppControlService
from .models import InjectIntentResult, LaunchAppExtraResult, ManageAppResult

logger = logging.getLogger(__name__)


def register_control_tools(mcp: FastMCP, service: AppControlService) -> None:
    @mcp.tool(tags={"app_manager"})
    async def launch_app_extra(
        package: Annotated[str, Field(description="Android package name (e.g. com.example.app).")],
        device_serial: DeviceSerial = None,
    ) -> LaunchAppExtraResult:
        """Launch an app by package name without requiring a component name. Resolves the launcher
        activity automatically using pm resolve-activity. Returns the resolved component, app name,
        and PID when available. PID is best-effort — it may be None on success if the process had
        not registered by the time of the check. If resolution fails, the error message will suggest
        using get_app_info with sections=['components'] followed by launch_app with the explicit
        component."""
        try:
            return await service.launch_app_extra(package=package, device_serial=device_serial)
        except ADBError as e:
            raise ToolError(str(e)) from e
        except Exception:
            logger.exception("launch_app_extra failed")
            raise ToolError("Failed to launch app")

    @mcp.tool(tags={"app_manager"})
    async def manage_app(
        package: Annotated[str, Field(description="Android package name (e.g. com.example.app).")],
        action: Annotated[
            Literal["stop", "clear_data", "clear_cache", "enable", "disable"],
            Field(
                description=(
                    "'stop': force-stops the app process, safe and reversible. "
                    "'clear_data': permanently deletes all app data including databases, "
                    "preferences, and files — irreversible. "
                    "'clear_cache': removes cached files only; requires root — returns "
                    "requires_root=false when root is available, true when root is needed but "
                    "unavailable; null for all other actions. "
                    "'enable': re-enables a disabled app. "
                    "'disable': disables the app for the current user; uses pm disable with "
                    "root, pm disable-user without."
                ),
            ),
        ],
        device_serial: DeviceSerial = None,
    ) -> ManageAppResult:
        """Control app runtime state. Clear_data is irreversible — it permanently removes all
        user data for the app. Clear_cache requires root and reports requires_root=true when
        unavailable."""
        try:
            return await service.manage_app(
                package=package,
                action=action,
                device_serial=device_serial,
            )
        except ADBError as e:
            raise ToolError(str(e)) from e
        except Exception:
            logger.exception("manage_app failed")
            raise ToolError("Failed to manage app")

    @mcp.tool(tags={"app_manager"})
    async def inject_intent(
        intent_type: Annotated[
            Literal["activity", "broadcast", "service"],
            Field(
                description=(
                    "Routes to the corresponding am subcommand: "
                    "'activity' (default) uses am start — use for launching UI components. "
                    "'broadcast' uses am broadcast — use for system or app-wide events. "
                    "'service' uses am startservice — use for background service components. "
                    "Override this default when firing broadcasts or starting services."
                ),
            ),
        ] = "activity",
        action: Annotated[
            str | None,
            Field(
                description=(
                    "Intent action string (e.g. android.intent.action.VIEW or a custom action)."
                ),
            ),
        ] = None,
        package: Annotated[
            str | None,
            Field(
                description=(
                    "Target package. Used with -p when no explicit component is given."
                ),
            ),
        ] = None,
        component: Annotated[
            str | None,
            Field(
                description=(
                    "Component in package/class or .ShortClass format "
                    "(e.g. com.example.app/.MainActivity). "
                    "Use get_app_info to retrieve component names in the correct format."
                ),
            ),
        ] = None,
        uri: Annotated[
            str | None,
            Field(
                description=(
                    "Data URI passed to the intent (e.g. https://example.com or content://...)."
                ),
            ),
        ] = None,
        mime_type: Annotated[
            str | None,
            Field(
                description="MIME type for the intent data (e.g. text/plain, image/*).",
            ),
        ] = None,
        extras: Annotated[
            dict[str, str] | None,
            Field(
                description=(
                    "Key-value string extras passed as --es key value. "
                    "All values are treated as strings."
                ),
            ),
        ] = None,
        filter: Annotated[
            str | None,
            Field(
                description=(
                    "Case-insensitive substring filter applied to output lines. "
                    "Use to extract signal from verbose broadcast output "
                    "(e.g. 'exception', 'denied', 'result'). Omit to return all output lines."
                ),
            ),
        ] = None,
        device_serial: DeviceSerial = None,
    ) -> InjectIntentResult:
        """Fire an intent at a component. Requires intent_type: 'activity', 'broadcast', or
        'service'. Broadcasts can produce verbose output — use filter to extract relevant lines.
        Returns success, exit code, filtered or full output lines, and error if any. For advanced
        intent flags not covered here, use execute_adb_command directly."""
        try:
            return await service.inject_intent(
                intent_type=intent_type,
                action=action,
                package=package,
                component=component,
                uri=uri,
                mime_type=mime_type,
                extras=extras,
                filter=filter,
                device_serial=device_serial,
            )
        except ADBError as e:
            raise ToolError(str(e)) from e
        except Exception:
            logger.exception("inject_intent failed")
            raise ToolError("Failed to inject intent")
