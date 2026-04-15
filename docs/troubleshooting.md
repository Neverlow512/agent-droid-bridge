# Troubleshooting

| Problem | Quick fix |
|---|---|
| No devices listed | Enable USB debugging; try `adb kill-server && adb start-server` |
| Device shows as `unauthorized` | Tap "Allow" on the device prompt; revoke and re-pair if dismissed |
| `adb: command not found` | Set `ADB_PATH` to the full binary path in your MCP client config |
| Multiple devices connected | Specify a device serial in your agent prompt |
| Permission denied on Linux | Add a udev rule or add your user to the `plugdev` group |
| Emulator not detected | Start the emulator before the server; restart ADB server if needed |
| No tools appear in the client | Restart the MCP client; verify JSON config syntax |
| `app_manager` tools missing | Set `ADB_EXTRA_TOOL_PACKS=app_manager` and restart |

---

## No devices listed

USB debugging is likely not enabled, or the ADB server needs a reset.

1. Go to **Settings > About phone** and tap **Build number** seven times to unlock Developer options.
2. Go to **Settings > Developer options** and enable **USB debugging**.
3. Try a different USB cable or port.
4. Restart the ADB server:

```bash
adb kill-server && adb start-server
```

## Device shows as `unauthorized`

The device displayed a prompt asking whether to trust this computer. Tap **Allow**.

If you already dismissed it:

1. Disconnect the device.
2. Go to **Developer options** and tap **Revoke USB debugging authorizations**.
3. Reconnect and tap **Allow** when the prompt appears.

## `adb: command not found`

ADB is not on your system PATH. Set `ADB_PATH` in your MCP client config to the full path of the `adb` binary:

```json
"env": {
  "ADB_PATH": "/usr/local/bin/adb"
}
```

Common locations:

- macOS (Homebrew): `/usr/local/bin/adb`
- Linux: `/usr/bin/adb`
- Windows: `C:\platform-tools\adb.exe`

To verify, run `<path> devices` in your terminal.

## Multiple devices connected

The server lists all connected devices and expects the agent to specify which one to use. If you always want a specific device, specify its serial in your agent prompt or disconnect the others.

## Permission denied on Linux

Your user does not have permission to access USB devices. Choose one of the following options.

**Option 1 — Add a udev rule**

Create `/etc/udev/rules.d/51-android.rules` with:

```
SUBSYSTEM=="usb", ATTR{idVendor}=="<vendor_id>", MODE="0666", GROUP="plugdev"
```

Replace `<vendor_id>` with your device's USB vendor ID. Then reload:

```bash
sudo udevadm control --reload-rules
```

**Option 2 — Add your user to the plugdev group**

```bash
sudo usermod -aG plugdev $USER
```

Log out and back in for the change to take effect.

## Emulator not detected

Start the emulator before starting the server.

1. Launch the emulator from Android Studio or the command line.
2. Run `adb devices` and confirm the emulator appears as `emulator-XXXX device`.
3. If it does not appear, run `adb kill-server && adb start-server` and restart the emulator.

## No tools appear in the client

1. Restart the MCP client after adding the server config.
   - Cursor: `Ctrl+Shift+P` → **Reload Window**
   - Claude Desktop: quit and reopen the application
   - VS Code: `Ctrl+Shift+P` → **Reload Window**
2. Verify the config block is valid JSON — trailing commas will silently break parsing.
3. Confirm `uvx` is installed and on your PATH: `uvx --version`.
4. Try running the server manually: `uvx agent-droid-bridge --help`.

## `app_manager` tools missing

`ADB_EXTRA_TOOL_PACKS` must be set in your MCP client's `env` block:

```json
"env": {
  "ADB_EXTRA_TOOL_PACKS": "app_manager"
}
```

Restart the server after changing the env block.

- Cursor: `Ctrl+Shift+P` → **Reload Window**
- Claude Desktop: quit and reopen the application
- VS Code: `Ctrl+Shift+P` → **Reload Window**
