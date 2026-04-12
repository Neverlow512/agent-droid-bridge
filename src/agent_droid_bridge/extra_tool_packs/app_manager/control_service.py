from __future__ import annotations

import asyncio
import logging
import re
import time

from ...adb import ADBError, ADBService
from ...recorder import get_session_logger
from .models import InjectIntentResult, LaunchAppExtraResult, ManageAppResult

logger = logging.getLogger(__name__)

_INTENT_SUBCOMMANDS: dict[str, str] = {
    "activity": "start",
    "broadcast": "broadcast",
    "service": "startservice",
}


class AppControlService:
    def __init__(self, adb: ADBService) -> None:
        self._adb = adb

    async def _get_root_available(self, serial: str | None) -> bool:
        cmd = [*self._adb._build_base_cmd(serial), "shell", "su", "-c", "id"]
        try:
            stdout, _ = await self._adb._run(cmd, trusted=True)
            return "uid=0" in stdout.decode("utf-8", errors="replace")
        except ADBError:
            return False

    async def launch_app_extra(
        self,
        package: str,
        device_serial: str | None = None,
    ) -> LaunchAppExtraResult:
        serial = await self._adb._resolve_serial(device_serial)

        resolve_cmd = [
            *self._adb._build_base_cmd(serial),
            "shell",
            "pm",
            "resolve-activity",
            "--brief",
            "-a",
            "android.intent.action.MAIN",
            "-c",
            "android.intent.category.LAUNCHER",
            "-p",
            package,
        ]
        try:
            stdout, _ = await self._adb._run(resolve_cmd, trusted=True)
        except ADBError as e:
            return LaunchAppExtraResult(success=False, error=str(e))

        output = stdout.decode("utf-8", errors="replace")
        match = re.search(r"(" + re.escape(package) + r"/[.\w$]+)", output)
        if not match:
            return LaunchAppExtraResult(
                success=False,
                error=(
                    f"Could not resolve launcher activity for {package}. "
                    "Use get_app_info with sections=['components'] to retrieve the activity list, "
                    "then call launch_app with the explicit component."
                ),
            )

        component = match.group(1)
        name_match = re.search(r"label=(.+)", output)
        app_name = name_match.group(1).strip() if name_match else None

        launch_cmd = [
            *self._adb._build_base_cmd(serial),
            "shell",
            "am",
            "start",
            "-n",
            component,
        ]
        try:
            launch_stdout, _ = await self._adb._run(launch_cmd, trusted=True)
        except ADBError as e:
            return LaunchAppExtraResult(success=False, component=component, error=str(e))

        launch_output = launch_stdout.decode("utf-8", errors="replace")
        if "Error" in launch_output:
            return LaunchAppExtraResult(
                success=False,
                component=component,
                error=launch_output.strip()[:300],
            )

        await asyncio.sleep(0.5)

        pid: int | None = None
        try:
            pidof_cmd = [*self._adb._build_base_cmd(serial), "shell", "pidof", package]
            pidof_stdout, _ = await self._adb._run(pidof_cmd, trusted=True)
            pidof_output = pidof_stdout.decode("utf-8", errors="replace").strip()
            if pidof_output:
                pid = int(pidof_output.split()[0])
        except (ADBError, ValueError, IndexError):
            pid = None

        return LaunchAppExtraResult(
            success=True,
            component=component,
            app_name=app_name,
            pid=pid,
        )

    async def manage_app(
        self,
        package: str,
        action: str,
        device_serial: str | None = None,
    ) -> ManageAppResult:
        if action not in ("stop", "clear_data", "clear_cache", "enable", "disable"):
            return ManageAppResult(
                success=False,
                action=action,
                error=(
                    f"Unknown action '{action}'. "
                    "Must be one of: stop, clear_data, clear_cache, enable, disable"
                ),
            )

        serial = await self._adb._resolve_serial(device_serial)

        if action == "stop":
            try:
                cmd = [
                    *self._adb._build_base_cmd(serial),
                    "shell",
                    "am",
                    "force-stop",
                    package,
                ]
                await self._adb._run(cmd, trusted=True)
                return ManageAppResult(action="stop", success=True)
            except ADBError as e:
                return ManageAppResult(action="stop", success=False, error=str(e))

        if action == "clear_data":
            try:
                cmd = [*self._adb._build_base_cmd(serial), "shell", "pm", "clear", package]
                stdout, _ = await self._adb._run(cmd, trusted=True)
                output = stdout.decode("utf-8", errors="replace")
                if "Success" in output:
                    return ManageAppResult(action="clear_data", success=True)
                return ManageAppResult(
                    action="clear_data",
                    success=False,
                    error=output.strip()[:300],
                )
            except ADBError as e:
                return ManageAppResult(action="clear_data", success=False, error=str(e))

        if action == "clear_cache":
            root_available = await self._get_root_available(serial)
            try:
                cmd = [
                    *self._adb._build_base_cmd(serial),
                    "shell",
                    "rm",
                    "-rf",
                    f"/data/data/{package}/cache/*",
                ]
                await self._adb._run(cmd, trusted=True)
                return ManageAppResult(
                    action="clear_cache",
                    success=True,
                    requires_root=not root_available,
                )
            except ADBError as e:
                if "permission denied" in str(e).lower():
                    return ManageAppResult(
                        action="clear_cache",
                        success=False,
                        requires_root=True,
                        error="Root access required to clear cache",
                    )
                return ManageAppResult(action="clear_cache", success=False, error=str(e))

        if action == "enable":
            try:
                cmd = [*self._adb._build_base_cmd(serial), "shell", "pm", "enable", package]
                await self._adb._run(cmd, trusted=True)
                return ManageAppResult(action="enable", success=True)
            except ADBError as e:
                return ManageAppResult(action="enable", success=False, error=str(e))

        root_available = await self._get_root_available(serial)
        if root_available:
            cmd = [*self._adb._build_base_cmd(serial), "shell", "pm", "disable", package]
        else:
            cmd = [
                *self._adb._build_base_cmd(serial),
                "shell",
                "pm",
                "disable-user",
                "--user",
                "0",
                package,
            ]
        try:
            await self._adb._run(cmd, trusted=True)
            return ManageAppResult(action="disable", success=True)
        except ADBError as e:
            return ManageAppResult(action="disable", success=False, error=str(e))

    async def inject_intent(
        self,
        intent_type: str,
        action: str | None = None,
        package: str | None = None,
        component: str | None = None,
        uri: str | None = None,
        mime_type: str | None = None,
        extras: dict[str, str] | None = None,
        filter: str | None = None,
        device_serial: str | None = None,
    ) -> InjectIntentResult:
        if intent_type not in _INTENT_SUBCOMMANDS:
            return InjectIntentResult(
                success=False,
                exit_code=-1,
                error=(
                    f"Unknown intent_type '{intent_type}'. "
                    "Must be one of: activity, broadcast, service"
                ),
            )

        serial = await self._adb._resolve_serial(device_serial)
        subcommand = _INTENT_SUBCOMMANDS[intent_type]

        cmd_parts: list[str] = ["shell", "am", subcommand]
        if action:
            cmd_parts.extend(["-a", action])
        if package and not component:
            cmd_parts.extend(["-p", package])
        if component:
            cmd_parts.extend(["-n", component])
        if uri:
            cmd_parts.extend(["-d", uri])
        if mime_type:
            cmd_parts.extend(["-t", mime_type])
        if extras:
            for key, value in extras.items():
                cmd_parts.extend(["--es", key, value])

        self._adb._check_security(cmd_parts)
        full_cmd = [*self._adb._build_base_cmd(serial), *cmd_parts]
        _start = time.monotonic()

        # Direct subprocess used here to capture the real numeric exit code —
        # _run raises on non-zero and discards it.
        proc = await asyncio.create_subprocess_exec(
            *full_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(),
                timeout=self._adb._settings.adb.command_timeout,
            )
        except TimeoutError:
            proc.kill()
            await proc.wait()
            try:
                _session_logger = get_session_logger()
                if _session_logger:
                    _session_logger.adb_command(
                        command=full_cmd,
                        exit_code=-1,
                        duration_ms=(time.monotonic() - _start) * 1000,
                        stdout=None,
                        stderr=None,
                    )
            except Exception:
                logger.debug(
                    "Session logger unavailable during inject_intent timeout",
                    exc_info=True,
                )
            return InjectIntentResult(
                success=False,
                exit_code=-1,
                error=(
                    f"Intent command timed out after "
                    f"{self._adb._settings.adb.command_timeout}s"
                ),
            )

        duration_ms = (time.monotonic() - _start) * 1000
        exit_code = proc.returncode

        stdout_text = stdout_bytes.decode("utf-8", errors="replace")
        stderr_text = stderr_bytes.decode("utf-8", errors="replace")
        combined = stdout_text + stderr_text

        lines = [line for line in combined.splitlines() if line.strip()]
        if filter:
            needle = filter.lower()
            lines = [line for line in lines if needle in line.lower()]

        error_markers = ("error", "exception", "securityexception")
        combined_lower = combined.lower()
        has_error = any(m in combined_lower for m in error_markers)
        success = exit_code == 0 and not has_error
        error = (stderr_text.strip() or stdout_text.strip())[:300] if not success else None

        try:
            _session_logger = get_session_logger()
            if _session_logger:
                _session_logger.adb_command(
                    command=full_cmd,
                    exit_code=exit_code,
                    duration_ms=duration_ms,
                    stdout=stdout_text or None,
                    stderr=stderr_text or None,
                )
        except Exception:
            logger.debug("Session logger unavailable during inject_intent", exc_info=True)

        return InjectIntentResult(
            success=success,
            exit_code=exit_code,
            output=lines,
            error=error,
        )
