from __future__ import annotations

import base64
import logging
import struct
import sys
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from .adb import ADBError, ADBService
from .config import get_settings
from .models import (
    DeviceInfo,
    ScreenElementsResult,
    ScreenshotResult,
    ScreenTextResult,
    UIChangeResult,
)

logger = logging.getLogger(__name__)

settings = get_settings()
logging.basicConfig(level=settings.server.log_level)

adb = ADBService(settings)
mcp = FastMCP("Agent Droid Bridge")

DeviceSerial = Annotated[
    str | None,
    Field(
        default=None,
        pattern=r"^[a-zA-Z0-9\-:.]+$",
        max_length=64,
        description=(
            "Android device serial (e.g. 'emulator-5554' or '192.168.1.10:5555'). "
            "Omit only when a single device is connected. "
            "If the tool returns a multi-device error: STOP. Present the device list "
            "to the user verbatim and wait for their explicit choice. "
            "Do NOT retry with a guessed or inferred serial — this is a hard "
            "requirement. Once the user provides a serial, use it for every "
            "subsequent call in this session. To switch devices mid-session, "
            "ask the user first."
        ),
    ),
]


@mcp.tool()
async def get_ui_hierarchy(device_serial: DeviceSerial = None) -> str:
    """Returns the current Android screen as an XML UI hierarchy.

    Use this when you need to locate element coordinates, read text, or find resource IDs to
    interact with. Do not call this after every action — only call it when you actually need to
    read screen content. To check if the screen changed after an action, use snapshot_ui before
    the action and detect_ui_change after.
    """
    try:
        return await adb.get_ui_hierarchy(device_serial)
    except ADBError as e:
        raise ToolError(str(e)) from e
    except Exception:
        logger.exception("get_ui_hierarchy failed")
        raise ToolError(
            "Failed to retrieve UI hierarchy"
            " — ensure a device is connected and the screen is unlocked"
        )


@mcp.tool()
async def tap_screen(
    x: Annotated[int, Field(ge=0, le=10000, description="X coordinate in screen pixels")],
    y: Annotated[int, Field(ge=0, le=10000, description="Y coordinate in screen pixels")],
    device_serial: DeviceSerial = None,
) -> str:
    """A tap gesture at the given pixel coordinates on the Android screen."""
    try:
        return await adb.tap_screen(x, y, device_serial)
    except ADBError as e:
        raise ToolError(str(e)) from e
    except Exception:
        logger.exception("tap_screen failed")
        raise ToolError("Failed to tap screen")


@mcp.tool()
async def swipe_screen(
    x1: Annotated[int, Field(ge=0, le=10000, description="Start X coordinate")],
    y1: Annotated[int, Field(ge=0, le=10000, description="Start Y coordinate")],
    x2: Annotated[int, Field(ge=0, le=10000, description="End X coordinate")],
    y2: Annotated[int, Field(ge=0, le=10000, description="End Y coordinate")],
    duration_ms: Annotated[
        int, Field(ge=50, le=10000, description="Swipe duration in milliseconds")
    ] = 300,
    device_serial: DeviceSerial = None,
) -> str:
    """A swipe gesture on the Android screen from (x1,y1) to (x2,y2) over the given duration."""
    try:
        return await adb.swipe_screen(x1, y1, x2, y2, duration_ms, device_serial)
    except ADBError as e:
        raise ToolError(str(e)) from e
    except Exception:
        logger.exception("swipe_screen failed")
        raise ToolError("Failed to swipe screen")


@mcp.tool()
async def type_text(
    text: Annotated[
        str,
        Field(
            min_length=1,
            max_length=1000,
            description="Text to type into the focused input field.",
        ),
    ],
    device_serial: DeviceSerial = None,
) -> str:
    """Text input into the currently focused Android input field.

    Spaces are encoded automatically.
    """
    try:
        return await adb.type_text(text, device_serial)
    except ADBError as e:
        raise ToolError(str(e)) from e
    except Exception:
        logger.exception("type_text failed")
        raise ToolError("Failed to type text")


@mcp.tool()
async def press_key(
    keycode: Annotated[
        int,
        Field(
            ge=0,
            le=999,
            description=(
                "Android keycode integer. Common: BACK=4, HOME=3, ENTER=66,"
                " RECENTS=187, TAB=61, DEL=67."
            ),
        ),
    ],
    device_serial: DeviceSerial = None,
) -> str:
    """A key event sent to the Android device using the given keycode integer."""
    try:
        return await adb.press_key(keycode, device_serial)
    except ADBError as e:
        raise ToolError(str(e)) from e
    except Exception:
        logger.exception("press_key failed")
        raise ToolError("Failed to press key")


@mcp.tool()
async def take_screenshot(device_serial: DeviceSerial = None) -> ScreenshotResult:
    """A PNG screenshot of the current Android device screen with width, height,
    and base64-encoded image data."""
    try:
        raw = await adb.take_screenshot(device_serial)
        if len(raw) < 24:
            raise ADBError("Screenshot data too small to extract dimensions")
        width, height = struct.unpack(">II", raw[16:24])
        return ScreenshotResult(
            image=base64.b64encode(raw).decode("ascii"),
            width=width,
            height=height,
            format="png",
        )
    except ADBError as e:
        raise ToolError(str(e)) from e
    except Exception:
        logger.exception("take_screenshot failed")
        raise ToolError("Failed to capture screenshot")


@mcp.tool()
async def list_devices() -> list[DeviceInfo]:
    """All Android devices currently visible to ADB, with their serial numbers,
    connection state, and model names."""
    try:
        raw_devices = await adb.list_devices()
        return [DeviceInfo(**d) for d in raw_devices]
    except ADBError as e:
        raise ToolError(str(e)) from e
    except Exception:
        logger.exception("list_devices failed")
        raise ToolError("Failed to list devices — ensure ADB is installed and on PATH")


@mcp.tool()
async def launch_app(
    component: Annotated[
        str,
        Field(
            min_length=3,
            max_length=500,
            pattern=r"^[a-zA-Z0-9_.$@/]+$",
            description=(
                "Android component in 'package/activity' format,"
                " e.g. 'com.android.settings/.Settings'."
            ),
        ),
    ],
    device_serial: DeviceSerial = None,
) -> str:
    """An Android app launched by its component name (package/activity)."""
    try:
        return await adb.launch_app(component, device_serial)
    except ADBError as e:
        raise ToolError(str(e)) from e
    except Exception:
        logger.exception("launch_app failed")
        raise ToolError("Failed to launch app")


@mcp.tool()
async def execute_adb_command(
    command: Annotated[
        str,
        Field(
            min_length=1,
            max_length=2000,
            description="ADB command to execute. Parsed safely — no shell injection possible.",
        ),
    ],
    use_shell: Annotated[
        bool,
        Field(
            default=True,
            description=(
                "When True, runs as an Android shell command (adb shell ...)."
                " When False, runs as a top-level ADB command (adb devices, adb install, etc.)."
            ),
        ),
    ] = True,
    device_serial: DeviceSerial = None,
) -> str:
    """The output of an ADB command. Parsed safely via shlex and never passed to a system shell."""
    try:
        return await adb.execute_adb_command(command, use_shell, device_serial)
    except ADBError as e:
        raise ToolError(str(e)) from e
    except Exception:
        logger.exception("execute_adb_command failed")
        raise ToolError("Failed to execute ADB command")


@mcp.tool()
async def snapshot_ui(device_serial: DeviceSerial = None) -> str:
    """Takes a lightweight snapshot of the current UI state and returns a short token.

    Use this before performing an action (tap, swipe, launch, key press) when you only need to
    confirm the screen changed afterward — not read its content. Pass the returned token to
    detect_ui_change as baseline_token. This avoids loading the full XML hierarchy into context
    unnecessarily. Do not use this when you need to read or interact with screen elements — use
    get_ui_hierarchy for that.
    """
    try:
        token = await adb.snapshot_ui(device_serial)
        return token
    except ADBError as e:
        raise ToolError(str(e)) from e
    except Exception:
        logger.exception("snapshot_ui failed")
        raise ToolError("Failed to take UI snapshot")


@mcp.tool()
async def detect_ui_change(
    timeout_seconds: Annotated[
        int,
        Field(default=10, ge=1, le=300, description="Maximum seconds to poll for a UI change."),
    ] = 10,
    baseline_token: Annotated[
        str | None,
        Field(
            default=None,
            description=(
                "Token returned by snapshot_ui, captured before the action. "
                "When provided, compares current UI against that snapshot — "
                "use this for reliable change detection without loading XML into context. "
                "When omitted, captures a fresh baseline at call time."
            ),
        ),
    ] = None,
    return_hierarchy: Annotated[
        bool,
        Field(
            default=False,
            description=(
                "When False (default), returns only changed and elapsed_seconds — no XML. "
                "Set to True to include the full UI hierarchy in the response. "
                "Only set True when you need to read element data immediately after the change."
            ),
        ),
    ] = False,
    device_serial: DeviceSerial = None,
) -> UIChangeResult:
    """Polls the UI hierarchy after an action and returns when the screen content changes or the
    timeout is reached. Returns changed status and elapsed time. By default, omits the XML
    hierarchy for efficiency — set return_hierarchy=True to receive the full hierarchy.

    For efficient change detection: call snapshot_ui before the action, perform the action, then
    call detect_ui_change with baseline_token. Only use without baseline_token when you need to
    wait for a slow transition (loading screens, animations). Do not use to read the current
    screen state — use get_ui_hierarchy for that.
    """
    try:
        result = await adb.detect_ui_change(
            timeout=timeout_seconds,
            device_serial=device_serial,
            baseline_token=baseline_token,
            return_hierarchy=return_hierarchy,
        )
        return UIChangeResult(**result)
    except ADBError as e:
        raise ToolError(str(e)) from e
    except Exception:
        logger.exception("detect_ui_change failed")
        raise ToolError("Failed to detect UI change")


@mcp.tool()
async def get_screen_elements(
    mode: Annotated[
        str,
        Field(
            default="tappable",
            pattern=r"^(tappable|interactive|input|all)$",
            description=(
                "Controls which elements are returned and how much detail each carries. "
                "'tappable' (default): only clickable, focusable, or scrollable elements "
                "with minimal fields (resource ID, text, content description, centre "
                "coordinates) — best for quick navigation when you need tap targets, "
                "lowest token cost. "
                "'interactive': same element filter as tappable but returns full detail "
                "including XPath, bounds, class name, and all boolean state flags — use "
                "when you need to construct precise ADB commands or distinguish elements "
                "by type. "
                "'input': only editable text fields (EditText and similar) with full "
                "detail — use when you need to find fields to type into. "
                "On Compose-based apps, input fields may not be detected; "
                "use 'interactive' mode instead and look for focusable elements. "
                "'all': every element in the UI tree with full detail — use only for "
                "security analysis or when other modes miss what you need, as output "
                "can be large."
            ),
        ),
    ] = "tappable",
    device_serial: DeviceSerial = None,
) -> ScreenElementsResult:
    """Structured list of UI elements currently visible on the Android screen.

    Returns elements filtered and shaped by the chosen mode. Prefer 'tappable' for
    navigation and 'interactive' when you need XPath or bounds for ADB commands.
    Only use 'all' as a last resort — it returns every node and can be large.
    """
    try:
        return await adb.get_screen_elements(device_serial, mode)
    except ADBError as e:
        raise ToolError(str(e)) from e
    except Exception:
        logger.exception("get_screen_elements failed")
        raise ToolError(
            "Failed to retrieve screen elements"
            " — ensure a device is connected and the screen is unlocked"
        )


@mcp.tool()
async def get_screen_text(
    device_serial: DeviceSerial = None,
) -> ScreenTextResult:
    """Returns all visible text on the current Android screen, sorted top-to-bottom.

    Use this when you need to read what is on screen. Does not include coordinates
    or element info — for tapping or interacting, use `get_screen_elements`.
    """
    try:
        return await adb.get_screen_text(device_serial)
    except ADBError as e:
        raise ToolError(str(e)) from e
    except Exception:
        logger.exception("get_screen_text failed")
        raise ToolError(
            "Failed to extract screen text"
            " — ensure a device is connected and the screen is unlocked"
        )


_HELP = """\
Agent Droid Bridge - MCP server for Android device control via ADB

Usage:
  uvx agent-droid-bridge          Start the MCP server (stdio transport)
  agent-droid-bridge --help       Show this message and exit

Environment variables:
  ADB_EXECUTION_MODE    unrestricted (default) | restricted
  ADB_ALLOW_SHELL       true (default) | false
  ADB_CONFIG_PATH       Path to a custom adb_config.yaml

Documentation:
  https://github.com/Neverlow512/agent-droid-bridge
"""


def main() -> None:
    if "--help" in sys.argv or "-h" in sys.argv:
        print(_HELP, end="")
        sys.exit(0)
    mcp.run()


if __name__ == "__main__":
    main()
