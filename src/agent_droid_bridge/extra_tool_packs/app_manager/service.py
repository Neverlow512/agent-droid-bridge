from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil

from ...adb import ADBError, ADBService
from .models import (
    AppComponents,
    AppPermissions,
    GetAppInfoResult,
    InstallAppResult,
    ListPackagesResult,
    ManagePermissionResult,
    PackageInfo,
    PullApkResult,
    PulledFile,
    UninstallAppResult,
)
from .parsers import (
    parse_components,
    parse_metadata,
    parse_permissions,
    parse_version_name_from_dumpsys,
)

logger = logging.getLogger(__name__)
_ALL_SECTIONS: frozenset[str] = frozenset({"metadata", "permissions", "components"})


class AppManagerService:
    def __init__(self, adb: ADBService) -> None:
        self._adb = adb

    async def list_packages(
        self,
        filter: str = "all",
        mode: str = "summary",
        search: str | None = None,
        device_serial: str | None = None,
    ) -> ListPackagesResult:
        serial = await self._adb._resolve_serial(device_serial)

        flags: list[str] = []
        if filter == "user":
            flags = ["-3"]
        elif filter == "system":
            flags = ["-s"]
        elif filter == "disabled":
            flags = ["-d"]

        if mode == "detailed":
            flags.append("-f")

        cmd = self._adb._build_base_cmd(serial) + ["shell", "pm", "list", "packages"] + flags
        stdout, _ = await self._adb._run(cmd, trusted=True)
        output = stdout.decode("utf-8", errors="replace")

        packages: list[tuple[str, str | None]] = []
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue

            if mode == "detailed":
                if line.startswith("package:"):
                    raw = line[len("package:"):]
                    parts = raw.rsplit("=", 1)
                    if len(parts) == 2:
                        apk_path = parts[0].strip()
                        pkg_name = parts[1].strip()
                        packages.append((pkg_name, apk_path))
            else:
                match = re.match(r"^package:(.+)$", line)
                if match:
                    pkg_name = match.group(1).strip()
                    packages.append((pkg_name, None))

        if search:
            needle = search.lower()
            packages = [(name, path) for name, path in packages if needle in name.lower()]

        if mode == "summary":
            package_infos = [PackageInfo(package=name) for name, _ in packages]
            return ListPackagesResult(
                total=len(package_infos),
                filter=filter,
                mode=mode,
                search=search,
                packages=package_infos,
            )

        async def _fetch_detail(pkg_name: str, apk_path: str | None) -> PackageInfo:
            try:
                dumpsys_cmd = self._adb._build_base_cmd(serial) + [
                    "shell",
                    "dumpsys",
                    "package",
                    pkg_name,
                ]
                dumpsys_stdout, _ = await self._adb._run(dumpsys_cmd, trusted=True)
                dumpsys_output = dumpsys_stdout.decode("utf-8", errors="replace")

                version = parse_version_name_from_dumpsys(dumpsys_output)

                install_time = None
                match = re.search(r"firstInstallTime=(.+)", dumpsys_output)
                if match:
                    install_time = match.group(1).strip()

                installer = None
                match = re.search(r"installerPackageName=(.+)", dumpsys_output)
                if match:
                    installer = match.group(1).strip()

                return PackageInfo(
                    package=pkg_name,
                    apk_path=apk_path,
                    version_name=version,
                    install_time=install_time,
                    installer=installer,
                )
            except Exception:
                return PackageInfo(package=pkg_name, apk_path=apk_path)

        results = await asyncio.gather(
            *[_fetch_detail(pkg, path) for pkg, path in packages],
            return_exceptions=True,
        )

        package_infos: list[PackageInfo] = []
        for i, result in enumerate(results):
            pkg_name, apk_path = packages[i]
            if isinstance(result, Exception):
                package_infos.append(PackageInfo(package=pkg_name, apk_path=apk_path))
            else:
                package_infos.append(result)

        return ListPackagesResult(
            total=len(package_infos),
            filter=filter,
            mode=mode,
            search=search,
            packages=package_infos,
        )

    async def get_app_info(
        self,
        package: str,
        sections: list[str] | None = None,
        search: str | None = None,
        device_serial: str | None = None,
    ) -> GetAppInfoResult:
        if sections is None or "all" in sections:
            effective_sections = _ALL_SECTIONS
        else:
            effective_sections = frozenset(s for s in sections if s in _ALL_SECTIONS)

        serial = await self._adb._resolve_serial(device_serial)

        (dumpsys_out, _), (getprop_out, _) = await asyncio.gather(
            self._adb._run(
                self._adb._build_base_cmd(serial) + ["shell", "dumpsys", "package", package],
                trusted=True,
            ),
            self._adb._run(
                self._adb._build_base_cmd(serial) + ["shell", "getprop", "ro.build.version.sdk"],
                trusted=True,
            ),
        )

        dumpsys_output = dumpsys_out.decode("utf-8", errors="replace")
        api_level: int | None = None
        try:
            api_level = int(getprop_out.decode("utf-8", errors="replace").strip())
        except (ValueError, AttributeError):
            pass

        if package not in dumpsys_output or len(dumpsys_output) < 50:
            return GetAppInfoResult(
                package=package,
                error="Package not found or empty dumpsys output",
                raw_snippet=dumpsys_output[:500],
                api_level=api_level,
            )

        metadata = None
        permissions = None
        components = None

        try:
            if "metadata" in effective_sections:
                metadata = parse_metadata(dumpsys_output, package)
            if "permissions" in effective_sections:
                permissions = parse_permissions(dumpsys_output, package)
            if "components" in effective_sections:
                components = parse_components(dumpsys_output, package)
        except Exception:
            logger.exception("Failed to parse package info for %s", package)
            return GetAppInfoResult(
                package=package,
                error="Failed to parse package info — unexpected output format",
                raw_snippet=dumpsys_output[:500],
                api_level=api_level,
            )

        if search:
            needle = search.lower()
            if components is not None:
                components = AppComponents(
                    activities=[a for a in components.activities if needle in a.lower()],
                    services=[s for s in components.services if needle in s.lower()],
                    receivers=[r for r in components.receivers if needle in r.lower()],
                    providers=[p for p in components.providers if needle in p.lower()],
                )
            if permissions is not None:
                permissions = AppPermissions(
                    declared=[p for p in permissions.declared if needle in p.lower()],
                    install_granted=[p for p in permissions.install_granted if needle in p.lower()],
                    runtime_granted=[p for p in permissions.runtime_granted if needle in p.lower()],
                )

        return GetAppInfoResult(
            package=package,
            metadata=metadata,
            permissions=permissions,
            components=components,
            api_level=api_level,
        )

    async def install_app(
        self,
        apk_path: str,
        device_serial: str | None = None,
    ) -> InstallAppResult:
        if not os.path.exists(apk_path):
            raise ADBError(f"APK file not found on host: {apk_path}")

        async def _extract_aapt_meta(path: str) -> tuple[str | None, str | None]:
            if shutil.which("aapt") is None:
                return None, None
            try:
                proc = await asyncio.create_subprocess_exec(
                    "aapt",
                    "dump",
                    "badging",
                    path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    stdin=asyncio.subprocess.DEVNULL,
                )
                try:
                    stdout, _ = await asyncio.wait_for(
                        proc.communicate(),
                        timeout=self._adb._settings.adb.aapt_timeout,
                    )
                except TimeoutError:
                    proc.kill()
                    await proc.wait()
                    return None, None
                text = stdout.decode("utf-8", errors="replace")
                pkg_match = re.search(r"package: name='([^']+)'", text)
                ver_match = re.search(r"versionName='([^']+)'", text)
                return (
                    pkg_match.group(1) if pkg_match else None,
                    ver_match.group(1) if ver_match else None,
                )
            except Exception:
                return None, None

        (aapt_package, aapt_version), serial = await asyncio.gather(
            _extract_aapt_meta(apk_path),
            self._adb._resolve_serial(device_serial),
        )

        cmd = self._adb._build_base_cmd(serial) + ["install", apk_path]
        stdout, _ = await self._adb._run(cmd, trusted=True)
        output = stdout.decode("utf-8", errors="replace")

        if "Success" in output:
            success = True
            error = None
        else:
            match = re.search(r"Failure \[(.+?)\]", output)
            if match:
                success = False
                error = match.group(1)
            else:
                success = False
                error = f"Unexpected install output: {output[:300]}"

        return InstallAppResult(
            success=success,
            package=aapt_package,
            version_installed=aapt_version,
            error=error,
        )

    async def uninstall_app(
        self,
        package: str,
        keep_data: bool = False,
        device_serial: str | None = None,
    ) -> UninstallAppResult:
        serial = await self._adb._resolve_serial(device_serial)

        cmd = self._adb._build_base_cmd(serial) + ["shell", "pm", "uninstall"]
        if keep_data:
            cmd.append("-k")
        cmd.append(package)

        stdout, _ = await self._adb._run(cmd, trusted=True)
        output = stdout.decode("utf-8", errors="replace")

        if "Success" in output:
            success = True
            error = None
        elif "Failure" in output:
            success = False
            match = re.search(r"Failure \[(.+?)\]", output)
            error = match.group(1) if match else "Uninstall failed"
        else:
            success = False
            error = output[:300]

        return UninstallAppResult(success=success, package=package, error=error)

    async def pull_apk(
        self,
        package: str,
        dest: str,
        split: str = "base",
        device_serial: str | None = None,
    ) -> PullApkResult:
        serial = await self._adb._resolve_serial(device_serial)

        cmd = self._adb._build_base_cmd(serial) + ["shell", "pm", "path", package]
        stdout, _ = await self._adb._run(cmd, trusted=True)
        lines = stdout.decode("utf-8", errors="replace").splitlines()
        device_paths = [
            m.group(1).strip()
            for line in lines
            if (m := re.match(r"^package:(.+)$", line))
        ]
        if not device_paths:
            return PullApkResult(success=False, error=f"No APK paths found for {package}")

        if not os.path.isdir(dest):
            raise ADBError(f"Destination directory does not exist: {dest}")

        paths_to_pull = device_paths[:1] if split == "base" else device_paths

        pulled: list[PulledFile] = []
        errors: list[str] = []

        for device_path in paths_to_pull:
            try:
                pull_cmd = self._adb._build_base_cmd(serial) + ["pull", device_path, dest]
                await self._adb._run(pull_cmd, trusted=True)
                local_path = os.path.join(dest, os.path.basename(device_path))
                pulled.append(PulledFile(path=local_path, size_bytes=os.path.getsize(local_path)))
            except (ADBError, OSError) as e:
                errors.append(str(e))

        if not pulled:
            return PullApkResult(success=False, error="All APK pulls failed: " + "; ".join(errors))

        return PullApkResult(
            success=True,
            files=pulled,
            total_size_bytes=sum(f.size_bytes for f in pulled),
            error="; ".join(errors) if errors else None,
        )

    async def manage_permission(
        self,
        package: str,
        action: str,
        permission: str | None = None,
        device_serial: str | None = None,
    ) -> ManagePermissionResult:
        if action not in ("grant", "revoke", "check", "list"):
            return ManagePermissionResult(
                success=False,
                action=action,
                error=f"Unknown action '{action}'. Must be one of: grant, revoke, check, list",
            )

        serial = await self._adb._resolve_serial(device_serial)

        if action == "list":
            cmd = self._adb._build_base_cmd(serial) + ["shell", "dumpsys", "package", package]
            stdout, _ = await self._adb._run(cmd, trusted=True)
            parsed = parse_permissions(stdout.decode("utf-8", errors="replace"), package)
            return ManagePermissionResult(success=True, action="list", permissions=parsed)

        if action == "grant":
            if permission is None:
                return ManagePermissionResult(
                    success=False,
                    action="grant",
                    error="Permission name required for grant action",
                )
            try:
                cmd = self._adb._build_base_cmd(serial) + [
                    "shell",
                    "pm",
                    "grant",
                    package,
                    permission,
                ]
                await self._adb._run(cmd, trusted=True)
                return ManagePermissionResult(success=True, action="grant")
            except ADBError as e:
                return ManagePermissionResult(success=False, action="grant", error=str(e))

        if action == "revoke":
            if permission is None:
                return ManagePermissionResult(
                    success=False,
                    action="revoke",
                    error="Permission name required for revoke action",
                )
            try:
                cmd = self._adb._build_base_cmd(serial) + [
                    "shell",
                    "pm",
                    "revoke",
                    package,
                    permission,
                ]
                await self._adb._run(cmd, trusted=True)
                return ManagePermissionResult(success=True, action="revoke")
            except ADBError as e:
                return ManagePermissionResult(success=False, action="revoke", error=str(e))

        if action == "check":
            if permission is None:
                return ManagePermissionResult(
                    success=False,
                    action="check",
                    error="Permission name required for check action",
                )
            try:
                cmd = self._adb._build_base_cmd(serial) + ["shell", "dumpsys", "package", package]
                stdout, _ = await self._adb._run(cmd, trusted=True)
                parsed = parse_permissions(stdout.decode("utf-8", errors="replace"), package)
                granted = (
                    permission in parsed.install_granted
                    or permission in parsed.runtime_granted
                )
                return ManagePermissionResult(success=True, action="check", granted=granted)
            except ADBError as e:
                return ManagePermissionResult(success=False, action="check", error=str(e))

        return ManagePermissionResult(success=False, action=action, error="Unexpected error")
