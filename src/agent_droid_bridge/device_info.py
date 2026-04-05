from __future__ import annotations

import logging
import re

from .adb import ADBError, ADBService
from .models import DeviceCapabilities

logger = logging.getLogger(__name__)

_GETPROP_RE = re.compile(r"^\[(.+?)\]: \[(.*)?\]", re.MULTILINE)
_TRUSTED_COMMANDS = frozenset(
    {"getprop", "wm", "id", "su", "cat", "uname", "getenforce", "nproc", "df"}
)


class DeviceInfoService:
    def __init__(self, adb: ADBService) -> None:
        self._adb = adb

    def _check_command(self, cmd: list[str]) -> None:
        for i, token in enumerate(cmd):
            if token == "shell" and i + 1 < len(cmd):
                shell_cmd = cmd[i + 1]
                if shell_cmd not in _TRUSTED_COMMANDS:
                    raise ADBError(f"Command not permitted: {shell_cmd}")
                return
        raise ADBError("Non-shell commands are not permitted in DeviceInfoService")

    def _parse_getprop(self, raw: str) -> dict[str, str]:
        return {m.group(1): m.group(2) for m in _GETPROP_RE.finditer(raw)}

    async def check_device_capabilities(
        self, mode: str, device_serial: str | None = None
    ) -> DeviceCapabilities:
        serial = await self._adb._resolve_serial(device_serial)
        getprop_cmd = self._adb._build_base_cmd(serial) + ["shell", "getprop"]
        self._check_command(getprop_cmd)
        stdout, _ = await self._adb._run(getprop_cmd, trusted=True)
        props = self._parse_getprop(stdout.decode("utf-8", errors="replace"))

        data: dict = {"mode": mode}

        if mode in ("identity", "all"):
            data["manufacturer"] = props.get("ro.product.manufacturer") or None
            data["model"] = props.get("ro.product.model") or None
            data["codename"] = props.get("ro.product.device") or None
            data["android_version"] = props.get("ro.build.version.release") or None
            api_str = props.get("ro.build.version.sdk")
            data["api_level"] = int(api_str) if api_str and api_str.isdigit() else None
            characteristics = props.get("ro.build.characteristics", "")
            is_emulator = props.get("ro.kernel.qemu") == "1" or "emulator" in characteristics
            data["is_emulator"] = is_emulator
            data["build_type"] = props.get("ro.build.type") or None
            data["cpu_abi"] = props.get("ro.product.cpu.abi") or None
            data["hardware"] = props.get("ro.hardware") or None
            data["board"] = props.get("ro.product.board") or None
            if "tablet" in characteristics:
                data["device_type"] = "tablet"
            elif "tv" in characteristics:
                data["device_type"] = "tv"
            elif "watch" in characteristics:
                data["device_type"] = "watch"
            elif is_emulator:
                data["device_type"] = "emulator"
            else:
                data["device_type"] = "phone"
            data["build_fingerprint"] = props.get("ro.build.fingerprint")
            data["build_tags"] = props.get("ro.build.tags")
            data["android_version_codename"] = props.get("ro.build.version.codename")
            try:
                uname_cmd = self._adb._build_base_cmd(serial) + ["shell", "uname", "-r"]
                self._check_command(uname_cmd)
                uname_out, _ = await self._adb._run(uname_cmd, trusted=True)
                data["kernel_version"] = uname_out.decode("utf-8", errors="replace").strip() or None
            except ADBError:
                data["kernel_version"] = None
            try:
                getenforce_cmd = self._adb._build_base_cmd(serial) + ["shell", "getenforce"]
                self._check_command(getenforce_cmd)
                getenforce_out, _ = await self._adb._run(getenforce_cmd, trusted=True)
                data["selinux_status"] = (
                    getenforce_out.decode("utf-8", errors="replace").strip() or None
                )
            except ADBError:
                data["selinux_status"] = None

        if mode in ("hardware", "all"):
            data["cpu_abi"] = props.get("ro.product.cpu.abi") or None
            data["cpu_abi2"] = props.get("ro.product.cpu.abi2") or None
            data["hardware"] = props.get("ro.hardware") or None
            data["board"] = props.get("ro.product.board") or None
            try:
                wm_cmd = self._adb._build_base_cmd(serial) + ["shell", "wm", "size"]
                self._check_command(wm_cmd)
                wm_out, _ = await self._adb._run(wm_cmd, trusted=True)
                wm_str = wm_out.decode("utf-8", errors="replace")
                m = re.search(r"Physical size:\s*(\d+x\d+)", wm_str)
                data["screen_resolution"] = m.group(1) if m else None
            except ADBError:
                data["screen_resolution"] = None
            try:
                mem_cmd = self._adb._build_base_cmd(serial) + ["shell", "cat", "/proc/meminfo"]
                self._check_command(mem_cmd)
                mem_out, _ = await self._adb._run(mem_cmd, trusted=True)
                mem_str = mem_out.decode("utf-8", errors="replace")
                m = re.search(r"MemTotal:\s+(\d+)\s+kB", mem_str)
                data["total_ram_mb"] = int(m.group(1)) // 1024 if m else None
            except ADBError:
                data["total_ram_mb"] = None
            data["supported_abis"] = props.get("ro.product.cpu.abilist")
            gpu_val = props.get("ro.hardware.egl") or props.get("ro.board.platform")
            data["gpu"] = gpu_val if gpu_val else None
            try:
                density_cmd = self._adb._build_base_cmd(serial) + ["shell", "wm", "density"]
                self._check_command(density_cmd)
                density_out, _ = await self._adb._run(density_cmd, trusted=True)
                density_str = density_out.decode("utf-8", errors="replace")
                m = re.search(r"Physical density:\s*(\d+)", density_str)
                data["screen_density"] = m.group(1) if m else None
            except ADBError:
                data["screen_density"] = None
            try:
                nproc_cmd = self._adb._build_base_cmd(serial) + ["shell", "nproc"]
                self._check_command(nproc_cmd)
                nproc_out, _ = await self._adb._run(nproc_cmd, trusted=True)
                data["cpu_cores"] = int(nproc_out.decode("utf-8", errors="replace").strip())
            except (ADBError, ValueError):
                data["cpu_cores"] = None
            try:
                df_cmd = self._adb._build_base_cmd(serial) + ["shell", "df", "/data"]
                self._check_command(df_cmd)
                df_out, _ = await self._adb._run(df_cmd, trusted=True)
                df_str = df_out.decode("utf-8", errors="replace")
                lines = df_str.strip().splitlines()
                if len(lines) >= 2:
                    fields = lines[1].split()
                    kb = int(fields[1])
                    gb = kb / (1024 * 1024)
                    data["storage_total_gb"] = f"{gb:.1f}G"
                else:
                    data["storage_total_gb"] = None
            except (ADBError, ValueError, IndexError):
                data["storage_total_gb"] = None

        if mode in ("security", "all"):
            try:
                id_cmd = self._adb._build_base_cmd(serial) + ["shell", "id"]
                self._check_command(id_cmd)
                id_out, _ = await self._adb._run(id_cmd, trusted=True)
                data["adb_is_root"] = "uid=0" in id_out.decode("utf-8", errors="replace")
            except ADBError:
                data["adb_is_root"] = None
            try:
                su_cmd = self._adb._build_base_cmd(serial) + ["shell", "su", "-c", "id"]
                self._check_command(su_cmd)
                su_out, _ = await self._adb._run(su_cmd, trusted=True)
                data["root_available"] = "uid=0" in su_out.decode("utf-8", errors="replace")
            except ADBError:
                data["root_available"] = False
            data["ro_debuggable"] = props.get("ro.debuggable") == "1"
            data["ro_secure"] = props.get("ro.secure") == "1"
            data["verified_boot_state"] = props.get("ro.boot.verifiedbootstate")
            data["usb_config"] = props.get("persist.sys.usb.config")
            data["dm_verity"] = props.get("ro.boot.veritymode")
            data["encryption_state"] = props.get("ro.crypto.state")
            try:
                getenforce_cmd = self._adb._build_base_cmd(serial) + ["shell", "getenforce"]
                self._check_command(getenforce_cmd)
                getenforce_out, _ = await self._adb._run(getenforce_cmd, trusted=True)
                data["selinux_status"] = (
                    getenforce_out.decode("utf-8", errors="replace").strip() or None
                )
            except ADBError:
                data["selinux_status"] = None

        return DeviceCapabilities(**data)
