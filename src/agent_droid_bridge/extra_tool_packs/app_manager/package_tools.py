from __future__ import annotations

import logging
from typing import Annotated, Literal

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from ...adb import ADBError
from ...utils.types import DeviceSerial
from .models import (
    GetAppInfoResult,
    InstallAppResult,
    ListPackagesResult,
    ManagePermissionResult,
    PullApkResult,
    UninstallAppResult,
)
from .service import AppManagerService

logger = logging.getLogger(__name__)


def register_package_tools(mcp: FastMCP, service: AppManagerService) -> None:
    @mcp.tool(tags={"app_manager"})
    async def list_packages(
        filter: Annotated[
            Literal["all", "user", "system", "disabled"],
            Field(
                description=(
                    "'all': every installed package. "
                    "'user': user-installed (third-party) apps only. "
                    "'system': system packages only. "
                    "'disabled': disabled packages only."
                ),
            ),
        ] = "all",
        mode: Annotated[
            Literal["summary", "detailed"],
            Field(
                description=(
                    "'summary' (default): package names only, fast. "
                    "'detailed': adds version, install time, APK path — runs dumpsys per package, "
                    "expensive on large lists. Use search to narrow first. "
                    "Only 'summary' and 'detailed' are valid — "
                    "'brief' and other values are not accepted."
                ),
            ),
        ] = "summary",
        search: Annotated[
            str | None,
            Field(
                description=(
                    "Substring filter applied to package names before results are returned; "
                    "use this to narrow results before requesting detailed mode or when "
                    "looking for a specific app."
                ),
            ),
        ] = None,
        limit: Annotated[
            int,
            Field(
                description=(
                    "Cap the number of returned packages; default 0 returns all results; "
                    "use as a safety valve when search alone produces more results than needed."
                ),
            ),
        ] = 0,
        device_serial: DeviceSerial = None,
    ) -> ListPackagesResult:
        """List installed packages on the device. Use search to narrow results before requesting
        detailed mode — detailed runs a separate dumpsys call per package and is expensive on
        large lists."""
        try:
            result = await service.list_packages(
                filter=filter,
                mode=mode,
                search=search,
                device_serial=device_serial,
            )
            if limit > 0:
                result.packages = result.packages[:limit]
                result.total = len(result.packages)
            return result
        except ADBError as e:
            raise ToolError(str(e)) from e
        except Exception:
            logger.exception("list_packages failed")
            raise ToolError("Failed to list packages")

    @mcp.tool(tags={"app_manager"})
    async def get_app_info(
        package: Annotated[
            str,
            Field(
                description="Pass as package=<name>. Android package name (e.g. com.example.app).",
            ),
        ],
        sections: Annotated[
            list[str] | None,
            Field(
                description=(
                    "List of sections to fetch: 'metadata' (version, install time, data dir, "
                    "APK paths, native lib dir), 'permissions' (declared, install-granted, "
                    "runtime-granted), 'components' (activities, services, receivers, providers); "
                    "pass ['all'] or omit to fetch everything; request only what you need."
                ),
            ),
        ] = None,
        search: Annotated[
            str | None,
            Field(
                description=(
                    "Substring filter applied to component names and permission strings in the "
                    "result; use to find a specific activity, receiver, or permission without "
                    "reading the full lists."
                ),
            ),
        ] = None,
        device_serial: DeviceSerial = None,
    ) -> GetAppInfoResult:
        """Full static metadata for a single installed app. Request only the sections you need.
        Use search to filter components or permissions by name."""
        try:
            return await service.get_app_info(
                package=package,
                sections=sections,
                search=search,
                device_serial=device_serial,
            )
        except ADBError as e:
            raise ToolError(str(e)) from e
        except Exception:
            logger.exception("get_app_info failed")
            raise ToolError("Failed to retrieve app info")

    @mcp.tool(tags={"app_manager"})
    async def install_app(
        apk_path: Annotated[
            str,
            Field(
                min_length=1,
                description="Absolute path to the APK file on the host machine.",
            ),
        ],
        device_serial: DeviceSerial = None,
    ) -> InstallAppResult:
        """Install an APK from a host path onto the device. Returns the package name and version
        if aapt is available, or None for those fields if not. Returns the package manager error
        string on failure."""
        try:
            return await service.install_app(apk_path=apk_path, device_serial=device_serial)
        except ADBError as e:
            raise ToolError(str(e)) from e
        except Exception:
            logger.exception("install_app failed")
            raise ToolError("Failed to install APK")

    @mcp.tool(tags={"app_manager"})
    async def uninstall_app(
        package: Annotated[str, Field(description="Android package name (e.g. com.example.app).")],
        keep_data: Annotated[
            bool,
            Field(
                description=(
                    "When true, preserves app data and cache on device after removal. "
                    "Useful for testing reinstall flows without losing state."
                ),
            ),
        ] = False,
        device_serial: DeviceSerial = None,
    ) -> UninstallAppResult:
        """Remove an installed app by package name."""
        try:
            return await service.uninstall_app(
                package=package,
                keep_data=keep_data,
                device_serial=device_serial,
            )
        except ADBError as e:
            raise ToolError(str(e)) from e
        except Exception:
            logger.exception("uninstall_app failed")
            raise ToolError("Failed to uninstall app")

    @mcp.tool(tags={"app_manager"})
    async def pull_apk(
        package: Annotated[str, Field(description="Android package name (e.g. com.example.app).")],
        destination: Annotated[
            str,
            Field(
                min_length=1,
                description=(
                    "Pass as destination=<path>. "
                    "Absolute path to an existing directory on the host where the APK "
                    "will be written."
                ),
            ),
        ],
        split: Annotated[
            Literal["base", "all"],
            Field(
                description=(
                    "'base' (default): pulls only the main base APK. "
                    "'all': pulls all APK splits — use for split APK installs where the full "
                    "app is spread across multiple files."
                ),
            ),
        ] = "base",
        device_serial: DeviceSerial = None,
    ) -> PullApkResult:
        """Extract the installed APK from the device by package name. Returns the written file
        path(s) and sizes."""
        try:
            return await service.pull_apk(
                package=package,
                dest=destination,
                split=split,
                device_serial=device_serial,
            )
        except ADBError as e:
            raise ToolError(str(e)) from e
        except Exception:
            logger.exception("pull_apk failed")
            raise ToolError("Failed to pull APK")

    @mcp.tool(tags={"app_manager"})
    async def manage_permission(
        package: Annotated[str, Field(description="Android package name (e.g. com.example.app).")],
        action: Annotated[
            Literal["grant", "revoke", "check", "list"],
            Field(
                description=(
                    "'list': returns all declared, install-granted, and runtime-granted "
                    "permissions — no permission argument needed. "
                    "'grant': grants a runtime permission to the app. "
                    "'revoke': revokes a previously granted runtime permission. "
                    "'check': returns whether a specific permission is currently granted."
                ),
            ),
        ],
        permission: Annotated[
            str | None,
            Field(
                description=(
                    "Full permission string required for grant, revoke, and check "
                    "(e.g. android.permission.CAMERA). Omit for list."
                ),
            ),
        ] = None,
        device_serial: DeviceSerial = None,
    ) -> ManagePermissionResult:
        """Grant, revoke, check, or list runtime permissions for an app. Use list to see all
        permissions without specifying one. Use check to verify grant status before acting."""
        try:
            return await service.manage_permission(
                package=package,
                action=action,
                permission=permission,
                device_serial=device_serial,
            )
        except ADBError as e:
            raise ToolError(str(e)) from e
        except Exception:
            logger.exception("manage_permission failed")
            raise ToolError("Failed to manage permission")
