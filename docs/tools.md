# Tools

All tools accept an optional `device_serial` parameter. When omitted, the server auto-detects the connected device. When multiple devices are connected and no serial is provided, the tool returns a device list — select the target serial and include it in subsequent calls.

## Choosing the right tool

| Goal | Tool |
|---|---|
| Read labels, values, or messages visible on screen | `get_screen_text` |
| Find tap targets or get coordinates to interact with elements | `get_screen_elements` |
| Inspect the full raw XML structure | `get_ui_hierarchy` |
| Confirm a screen transition happened after an action | `snapshot_ui` + `detect_ui_change` |

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

Useful when multiple devices are connected and you need to identify the target serial before calling other tools.

*Example: "Which devices are connected right now?"*

## snapshot_ui

Takes a lightweight snapshot of the current UI state and returns a short token. The token can be passed to `detect_ui_change` as `baseline_token` to detect changes relative to a known point — for example, immediately before triggering an action. This tool is intended for change detection only; it does not return screen content. To read or interact with screen elements, use `get_screen_text` or `get_screen_elements`. For the raw XML structure, use `get_ui_hierarchy`.

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

## get_screen_elements

Returns a structured list of UI elements currently visible on the Android screen. Elements are filtered and shaped by the chosen mode. `tappable` is the right choice for most navigation tasks. Use `interactive` when XPath or bounds are needed for precise ADB commands. `all` returns every node and can produce large responses — use it only when the other modes do not include the element you need.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `mode` | string | No | `tappable` | Controls which elements are returned and how much detail each carries. Options: `tappable`, `interactive`, `input`, `all` (see below) |
| `device_serial` | string | No | auto-detect | Android device serial (pattern: `^[a-zA-Z0-9\-:.]+$`, max 64 chars) |

**Mode options:**

| Mode | Elements returned | Detail level |
|---|---|---|
| `tappable` | Clickable or long-clickable enabled elements (apps, buttons, list items) | Minimal: `resource_id`, `text`, `content_desc`, `center_x`, `center_y` |
| `interactive` | All focusable, scrollable, or input-capable elements | Full: XPath, bounds, class name, all boolean state flags |
| `input` | EditText and SearchView fields only | Full (same as `interactive`). On Compose-based apps, use `interactive` instead — input fields may not be detected |
| `all` | Every element in the UI hierarchy | Full |

*Returns: `mode` (string), `total` (int), `elements` (list). In `tappable` mode, each element has `resource_id`, `text`, `content_desc`, `center_x`, `center_y`. In all other modes, each element additionally has `xpath`, `class_name`, `bounds` (4-tuple), `clickable`, `focusable`, `scrollable`, `long_clickable`, `checkable`, `checked`, `enabled`, `selected`.*

*Example: "Find all tappable elements on the current screen."*

## get_screen_text

Returns all visible text on the current Android screen, sorted top-to-bottom. This tool is for reading screen content only — it does not include coordinates or element metadata. To interact with elements, use `get_screen_elements`.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `device_serial` | string | No | auto-detect | Android device serial (pattern: `^[a-zA-Z0-9\-:.]+$`, max 64 chars) |

*Returns: `plain` (string — all visible text, newline-separated, sorted top-to-bottom), `total` (int — number of text nodes).*

*Example: "Read all visible text on the screen."*

## check_device_capabilities

Returns structured information about the connected Android device in a single call. The `mode` parameter controls which fields are populated — use a specific mode to keep the response minimal, or `all` to get everything at once.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `mode` | string | No | `all` | Controls which fields are returned. Options: `identity`, `security`, `hardware`, `all` (see below) |
| `device_serial` | string | No | auto-detect | Android device serial (pattern: `^[a-zA-Z0-9\-:.]+$`, max 64 chars) |

**Mode options:**

| Mode | Fields returned |
|---|---|
| `identity` | manufacturer, model, codename, device_type, android_version, api_level, is_emulator, build_type, cpu_abi, cpu_abi2, hardware, board, build_fingerprint, build_tags, android_version_codename, kernel_version, selinux_status |
| `security` | root_available, adb_is_root, selinux_status, ro_debuggable, ro_secure, verified_boot_state, usb_config, dm_verity, encryption_state |
| `hardware` | total_ram_mb, screen_resolution, screen_density, supported_abis, cpu_cores, storage_total_gb, gpu |
| `all` | All fields from all three modes combined |

*Example: "What device is connected and is it rooted?"*
