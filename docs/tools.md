# Tools

All tools accept an optional `device_serial` parameter. When omitted, the server auto-detects the connected device. When multiple devices are connected and no serial is provided, the tool returns a device list — present it to the user and wait for their choice before proceeding.

## get_ui_hierarchy

Returns the current Android screen as an XML UI hierarchy. Each node includes bounds, resource-id, text, content-desc, and class attributes.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `device_serial` | string | No | auto-detect | Android device serial (pattern: `^[a-zA-Z0-9\-:.]+$`, max 64 chars) |

*Example: "What is currently on the screen?"*

## take_screenshot

Captures the current Android device screen. Returns a structured object with the base64-encoded PNG image, pixel dimensions, and format.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `device_serial` | string | No | auto-detect | Android device serial (pattern: `^[a-zA-Z0-9\-:.]+$`, max 64 chars) |

*Returns: `image` (base64 PNG string), `width` (pixels), `height` (pixels), `format` (`"png"`).*

*Example: "Take a screenshot of the device."*

## tap_screen

Sends a tap gesture at the specified pixel coordinates on the Android screen.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `x` | integer | Yes | — | X coordinate in screen pixels (0–10000) |
| `y` | integer | Yes | — | Y coordinate in screen pixels (0–10000) |
| `device_serial` | string | No | auto-detect | Android device serial (pattern: `^[a-zA-Z0-9\-:.]+$`, max 64 chars) |

*Example: "Tap the OK button at the center of the screen."*

## swipe_screen

Sends a swipe gesture on the Android screen from one point to another over a specified duration.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `x1` | integer | Yes | — | Start X coordinate (0–10000) |
| `y1` | integer | Yes | — | Start Y coordinate (0–10000) |
| `x2` | integer | Yes | — | End X coordinate (0–10000) |
| `y2` | integer | Yes | — | End Y coordinate (0–10000) |
| `duration_ms` | integer | No | `300` | Swipe duration in milliseconds (50–10000) |
| `device_serial` | string | No | auto-detect | Android device serial (pattern: `^[a-zA-Z0-9\-:.]+$`, max 64 chars) |

*Example: "Scroll down the page slowly."*

## type_text

Types text into the currently focused Android input field. Spaces are encoded automatically.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `text` | string | Yes | — | Text to type (1–1000 characters) |
| `device_serial` | string | No | auto-detect | Android device serial (pattern: `^[a-zA-Z0-9\-:.]+$`, max 64 chars) |

*Example: "Type 'hello world' into the search box."*

## press_key

Sends an Android keycode event to the device.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `keycode` | integer | Yes | — | Android keycode (0–999). Common values: HOME=3, BACK=4, ENTER=66, DEL=67, TAB=61, RECENTS=187 |
| `device_serial` | string | No | auto-detect | Android device serial (pattern: `^[a-zA-Z0-9\-:.]+$`, max 64 chars) |

*Example: "Press the back button."*

## launch_app

Launches an Android app by its component name in `package/activity` format.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `component` | string | Yes | — | Component in `package/activity` format, e.g. `com.android.settings/.Settings` (3–500 chars) |
| `device_serial` | string | No | auto-detect | Android device serial (pattern: `^[a-zA-Z0-9\-:.]+$`, max 64 chars) |

The tool verifies that the app reached the foreground after launch. An error is returned if the component is not found or the app does not become active.

*Example: "Open the Settings app."*

## execute_adb_command

Runs an ADB command and returns its output. The command string is parsed via `shlex` — it is never passed to a system shell, so shell injection is not possible.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `command` | string | Yes | — | The command to run (1–2000 characters) |
| `use_shell` | boolean | No | `true` | When `true`, prepends `adb shell` — use for on-device commands like `pm list packages`. When `false`, runs as a top-level ADB command — use for `adb devices`, `adb install`, etc. |
| `device_serial` | string | No | auto-detect | Android device serial (pattern: `^[a-zA-Z0-9\-:.]+$`, max 64 chars) |

Behavior is controlled by two environment variables set in your MCP client config: `ADB_EXECUTION_MODE` (`unrestricted` / `restricted`) and `ADB_ALLOW_SHELL` (`true` / `false`). See [configuration.md](configuration.md) for details.

*Example: "List all installed packages on the device."*

## list_devices

Returns all Android devices currently visible to ADB.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| *(none)* | — | — | — | This tool takes no parameters |

*Returns: a list of objects, each with `serial` (string), `state` (string), and `model` (string).*

*Call this first when multiple devices may be connected to get the serials needed for other tools.*

*Example: "Which devices are connected right now?"*

## snapshot_ui

Takes a lightweight snapshot of the current UI state and returns a short token. Use this before performing an action when you only need to confirm the screen changed afterward — not read its content. Pass the token to `detect_ui_change` as `baseline_token`. Do not use this when you need to read or interact with screen elements — use `get_ui_hierarchy` for that.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `device_serial` | string | No | auto-detect | Android device serial (pattern: `^[a-zA-Z0-9\-:.]+$`, max 64 chars) |

*Returns: a 16-character hex token representing the current UI state.*

Tokens are scoped to the server process lifetime. If the server restarts between `snapshot_ui` and `detect_ui_change`, the token will not be recognised and `detect_ui_change` will capture a fresh baseline instead.

*Example: "Capture a baseline before tapping a button."*

## detect_ui_change

Polls the UI hierarchy after an action and returns when the screen content changes or the timeout is reached. For reliable detection of fast transitions, call `snapshot_ui` before the action and pass the token as `baseline_token`. Returns hierarchy only when `return_hierarchy` is set to `true`.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `timeout_seconds` | integer | No | `10` | Maximum seconds to poll for a UI change (1–300) |
| `baseline_token` | string | No | — | Token from `snapshot_ui`, captured before the action. When provided, compares current UI against that snapshot. When omitted, captures a fresh baseline at call time. |
| `return_hierarchy` | boolean | No | `false` | When `true`, includes the full XML hierarchy in the response. When `false`, returns only `changed` and `elapsed_seconds`. |
| `device_serial` | string | No | auto-detect | Android device serial (pattern: `^[a-zA-Z0-9\-:.]+$`, max 64 chars) |

*Returns: `changed` (bool), `elapsed_seconds` (float), `hierarchy` (XML string, only when `return_hierarchy` is `true`).*

*Example: "Tap the button and wait for the screen to change."*
