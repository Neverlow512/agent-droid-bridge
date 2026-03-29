from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import shlex
import time
import xml.etree.ElementTree as ET

from .config import DEVICE_SERIAL_PATTERN, Settings
from .models import ScreenElementsResult, ScreenTextResult
from .ui_parser import parse_elements, parse_screen_text

logger = logging.getLogger(__name__)


class ADBError(Exception):
    """Safe-to-display error from ADB operations."""


COMPONENT_PATTERN = re.compile(r"^[a-zA-Z0-9_.$@/]+$")


class ADBService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._snapshots: dict[str, str] = {}

    def _build_base_cmd(self, serial: str | None) -> list[str]:
        cmd = [self._settings.adb.path]
        if serial:
            cmd.extend(["-s", serial])
        return cmd

    async def _get_connected_devices(self) -> list[str]:
        cmd = [self._settings.adb.path, "devices"]
        stdout, _ = await self._run(cmd, skip_serial_check=True, trusted=True)
        lines = stdout.decode("utf-8", errors="replace").strip().splitlines()
        devices = [
            line.split("\t")[0]
            for line in lines[1:]
            if line.strip() and "\t" in line and not line.endswith("offline")
        ]
        return devices

    async def _resolve_serial(self, device_serial: str | None) -> str | None:
        if device_serial is not None:
            if not DEVICE_SERIAL_PATTERN.match(device_serial):
                raise ADBError("Invalid device serial format")
            return device_serial
        devices = await self._get_connected_devices()
        if len(devices) == 1:
            return devices[0]
        if len(devices) == 0:
            raise ADBError("No Android devices connected")
        detailed = await self.list_devices()
        lines = "\n".join(
            f"  {d['serial']}  (model: {d['model'] or 'unknown'}, state: {d['state']})"
            for d in detailed
            if d["state"] != "offline"
        )
        raise ADBError(
            f"Multiple devices connected — cannot proceed without explicit device selection.\n"
            f"Available devices:\n{lines}\n"
            f"Present this list to the user and wait for them to choose a serial. "
            f"Do not retry with a guessed serial."
        )

    async def _run(
        self,
        cmd: list[str],
        timeout: int | None = None,
        skip_serial_check: bool = False,
        trusted: bool = False,
    ) -> tuple[bytes, bytes]:
        effective_timeout = timeout or self._settings.adb.command_timeout
        if not trusted:
            if self._settings.execution_mode == "restricted":
                shell_idx = None
                for i, token in enumerate(cmd):
                    if token == "shell":
                        shell_idx = i
                        break
                if shell_idx is not None and shell_idx + 1 < len(cmd):
                    target_cmd = cmd[shell_idx + 1]
                    allowed = self._settings.adb.allowed_shell_commands
                    if not allowed:
                        raise ADBError(
                            "No commands are permitted in restricted mode"
                            " — allowed_shell_commands is empty"
                        )
                    if target_cmd not in allowed:
                        raise ADBError(
                            f"Command '{target_cmd}' is not permitted in restricted mode"
                        )
                elif shell_idx is None:
                    raise ADBError("Top-level ADB commands are not permitted in restricted mode")
            if not self._settings.allow_shell:
                for token in cmd:
                    if token == "shell":
                        raise ADBError(
                            "Shell commands are disabled — ADB_ALLOW_SHELL is set to false"
                        )
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=effective_timeout)
        except TimeoutError:
            proc.kill()
            await proc.wait()
            raise ADBError(f"ADB command timed out after {effective_timeout}s")

        if proc.returncode != 0:
            logger.error(
                "ADB command failed | cmd=%s | stderr=%s",
                cmd,
                stderr.decode(errors="replace"),
            )
            stderr_snippet = stderr.decode(errors="replace").strip()[:300]
            raise ADBError(f"ADB command failed: {stderr_snippet}")

        return stdout, stderr

    async def list_devices(self) -> list[dict]:
        cmd = [self._settings.adb.path, "devices", "-l"]
        stdout, _ = await self._run(cmd, skip_serial_check=True, trusted=True)
        output = stdout.decode("utf-8", errors="replace").strip()
        lines = output.splitlines()[1:]
        devices = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            tokens = line.split()
            if len(tokens) < 2:
                logger.debug("list_devices: skipping unrecognized line: %r", line)
                continue
            serial = tokens[0]
            state = tokens[1]
            model = ""
            for token in tokens[2:]:
                if token.startswith("model:"):
                    model = token.split(":", 1)[1]
                    break
            devices.append({"serial": serial, "state": state, "model": model})
        return devices

    async def snapshot_ui(self, device_serial: str | None = None) -> str:
        xml = await self.get_ui_hierarchy(device_serial)
        if "<hierarchy" not in xml:
            raise ADBError("UI hierarchy snapshot returned invalid data")
        token = hashlib.sha256(xml.encode()).hexdigest()[:16]
        if len(self._snapshots) >= 100:
            oldest_key = next(iter(self._snapshots))
            del self._snapshots[oldest_key]
        self._snapshots[token] = xml
        return token

    async def get_ui_hierarchy(
        self, device_serial: str | None = None, timeout: int | None = None
    ) -> str:
        serial = await self._resolve_serial(device_serial)
        cmd = self._build_base_cmd(serial) + ["exec-out", "uiautomator", "dump", "/dev/tty"]
        stdout, _ = await self._run(cmd, timeout=timeout, trusted=True)
        output = stdout.decode("utf-8", errors="replace")
        for marker in ("<?xml", "<hierarchy"):
            idx = output.find(marker)
            if idx != -1:
                sliced = output[idx:]
                end = sliced.rfind("</hierarchy>")
                if end != -1:
                    return sliced[: end + len("</hierarchy>")]
                return sliced.strip()
        return output.strip()

    async def tap_screen(self, x: int, y: int, device_serial: str | None = None) -> str:
        serial = await self._resolve_serial(device_serial)
        cmd = self._build_base_cmd(serial) + ["shell", "input", "tap", str(x), str(y)]
        await self._run(cmd, trusted=True)
        return f"Tapped ({x}, {y})"

    async def swipe_screen(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        duration_ms: int = 300,
        device_serial: str | None = None,
    ) -> str:
        serial = await self._resolve_serial(device_serial)
        cmd = self._build_base_cmd(serial) + [
            "shell",
            "input",
            "swipe",
            str(x1),
            str(y1),
            str(x2),
            str(y2),
            str(duration_ms),
        ]
        await self._run(cmd, trusted=True)
        return f"Swiped ({x1},{y1}) -> ({x2},{y2}) over {duration_ms}ms"

    async def type_text(self, text: str, device_serial: str | None = None) -> str:
        serial = await self._resolve_serial(device_serial)
        encoded = text.replace(" ", "%s")
        cmd = self._build_base_cmd(serial) + ["shell", "input", "text", encoded]
        await self._run(cmd, trusted=True)
        return f"Typed {len(text)} characters"

    async def press_key(self, keycode: int, device_serial: str | None = None) -> str:
        serial = await self._resolve_serial(device_serial)
        cmd = self._build_base_cmd(serial) + ["shell", "input", "keyevent", str(keycode)]
        await self._run(cmd, trusted=True)
        return f"Pressed keycode {keycode}"

    async def take_screenshot(self, device_serial: str | None = None) -> bytes:
        serial = await self._resolve_serial(device_serial)
        cmd = self._build_base_cmd(serial) + ["exec-out", "screencap", "-p"]
        stdout, _ = await self._run(
            cmd, timeout=self._settings.adb.screenshot_timeout, trusted=True
        )
        if not stdout:
            raise ADBError("Screenshot returned empty data")
        return stdout

    async def launch_app(self, component: str, device_serial: str | None = None) -> str:
        if not COMPONENT_PATTERN.match(component):
            raise ADBError("Invalid component format — expected 'package/activity'")
        serial = await self._resolve_serial(device_serial)
        cmd = self._build_base_cmd(serial) + ["shell", "am", "start", "-n", component]
        stdout, _ = await self._run(cmd, trusted=True)
        output = stdout.decode("utf-8", errors="replace")
        if "Error" in output:
            raise ADBError("Failed to launch app — component not found or not exported")
        package = component.split("/")[0]
        top_cmd = self._build_base_cmd(serial) + ["shell", "dumpsys", "activity", "top"]
        top_stdout, _ = await self._run(top_cmd, trusted=True)
        top_output = top_stdout.decode("utf-8", errors="replace")
        foreground = any(
            line.strip().startswith("ACTIVITY") and package in line
            for line in top_output.splitlines()
        )
        if not foreground:
            raise ADBError(f"Failed to launch {component}: app did not reach foreground")
        return f"Launched {component}"

    async def execute_adb_command(
        self,
        command: str,
        use_shell: bool = True,
        device_serial: str | None = None,
    ) -> str:
        try:
            parts = shlex.split(command)
        except ValueError as e:
            raise ADBError("Invalid command syntax: unable to parse") from e
        if not parts:
            raise ADBError("Empty command")
        serial = await self._resolve_serial(device_serial)
        base = self._build_base_cmd(serial)
        cmd = base + (["shell"] + parts if use_shell else parts)
        stdout, _ = await self._run(cmd)
        return stdout.decode("utf-8", errors="replace")

    async def get_screen_elements(
        self, device_serial: str | None, mode: str
    ) -> ScreenElementsResult:
        xml = await self.get_ui_hierarchy(device_serial)
        try:
            elements = parse_elements(xml, mode)
        except ValueError as e:
            raise ADBError(str(e)) from e
        except ET.ParseError as e:
            raise ADBError("Failed to parse UI hierarchy XML") from e
        return ScreenElementsResult(mode=mode, total=len(elements), elements=elements)

    async def get_screen_text(self, serial: str | None) -> ScreenTextResult:
        xml = await self.get_ui_hierarchy(serial)
        try:
            return parse_screen_text(xml)
        except ET.ParseError as e:
            raise ADBError("Failed to parse UI hierarchy XML") from e

    async def detect_ui_change(
        self,
        timeout: int | None = None,
        device_serial: str | None = None,
        baseline_token: str | None = None,
        return_hierarchy: bool = False,
    ) -> dict:
        effective_timeout = timeout or self._settings.adb.ui_change_timeout
        poll_interval = self._settings.adb.ui_change_poll_interval
        if baseline_token is not None:
            previous_xml = self._snapshots.pop(baseline_token, None)
            if previous_xml is None:
                raise ADBError(f"Snapshot token '{baseline_token}' not found or already used")
        else:
            previous_xml = await self.get_ui_hierarchy(device_serial)
        previous_hash = hashlib.sha256(previous_xml.encode()).hexdigest()
        start = time.monotonic()
        while True:
            elapsed = time.monotonic() - start
            if elapsed >= effective_timeout:
                result: dict = {"changed": False, "elapsed_seconds": round(elapsed, 2)}
                if return_hierarchy:
                    result["hierarchy"] = await self.get_ui_hierarchy(device_serial)
                return result
            await asyncio.sleep(poll_interval)
            remaining = effective_timeout - (time.monotonic() - start)
            if remaining <= 0:
                result = {
                    "changed": False,
                    "elapsed_seconds": round(time.monotonic() - start, 2),
                }
                if return_hierarchy:
                    result["hierarchy"] = await self.get_ui_hierarchy(device_serial)
                return result
            current_xml = await self.get_ui_hierarchy(device_serial)
            current_hash = hashlib.sha256(current_xml.encode()).hexdigest()
            elapsed = time.monotonic() - start
            if current_hash != previous_hash:
                result = {"changed": True, "elapsed_seconds": round(elapsed, 2)}
                if return_hierarchy:
                    result["hierarchy"] = current_xml
                return result
            previous_xml = current_xml
            previous_hash = current_hash
