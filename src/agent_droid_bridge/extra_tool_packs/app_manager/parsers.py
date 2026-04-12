from __future__ import annotations

import re

from .models import AppComponents, AppMetadata, AppPermissions


def parse_metadata(dumpsys_output: str, package: str) -> AppMetadata:
    start = dumpsys_output.find(f"Package [{package}]")
    if start == -1:
        return AppMetadata()
    next_pkg = dumpsys_output.find("Package [", start + 1)
    scoped = dumpsys_output[start:next_pkg] if next_pkg != -1 else dumpsys_output[start:]

    result: dict[str, object] = {
        "version_name": None,
        "version_code": None,
        "first_install_time": None,
        "last_update_time": None,
        "data_dir": None,
        "apk_paths": [],
        "native_lib_dir": None,
        "installer": None,
    }

    try:
        match = re.search(r"versionName=(.+)", scoped)
        if match:
            result["version_name"] = match.group(1).strip()
    except Exception:
        pass

    try:
        match = re.search(r"versionCode=(\d+)", scoped)
        if match:
            result["version_code"] = int(match.group(1))
    except Exception:
        pass

    try:
        match = re.search(r"firstInstallTime=(.+)", scoped)
        if match:
            result["first_install_time"] = match.group(1).strip()
    except Exception:
        pass

    try:
        match = re.search(r"lastUpdateTime=(.+)", scoped)
        if match:
            result["last_update_time"] = match.group(1).strip()
    except Exception:
        pass

    try:
        match = re.search(r"dataDir=(.+)", scoped)
        if match:
            result["data_dir"] = match.group(1).strip()
    except Exception:
        pass

    try:
        apk_paths: list[str] = []
        match = re.search(r"codePath=(.+)", scoped)
        if match:
            apk_paths.append(match.group(1).strip())
        result["apk_paths"] = apk_paths
    except Exception:
        result["apk_paths"] = []

    try:
        match = re.search(r"(?:legacyN|n)ativeLibraryDir=(.+)", scoped)
        if match:
            result["native_lib_dir"] = match.group(1).strip()
    except Exception:
        pass

    try:
        match = re.search(r"installerPackageName=(.+)", scoped)
        if match:
            result["installer"] = match.group(1).strip()
        else:
            match = re.search(r"installInitiatingPackageName=(.+)", scoped)
            if match:
                result["installer"] = match.group(1).strip()
    except Exception:
        pass

    return AppMetadata(**result)


def parse_permissions(dumpsys_output: str, package: str) -> AppPermissions:
    start = dumpsys_output.find(f"Package [{package}]")
    if start == -1:
        return AppPermissions()
    next_pkg = dumpsys_output.find("Package [", start + 1)
    scoped = dumpsys_output[start:next_pkg] if next_pkg != -1 else dumpsys_output[start:]

    declared: list[str] = []
    install_granted: list[str] = []
    runtime_granted: list[str] = []

    DECLARED_HEADER = "declared permissions:"
    INSTALL_HEADER = "install permissions:"
    RUNTIME_HEADER = "runtime permissions:"

    current_section: str | None = None

    for line in scoped.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        if stripped == DECLARED_HEADER:
            current_section = "declared"
            continue
        if stripped == INSTALL_HEADER:
            current_section = "install"
            continue
        if stripped == RUNTIME_HEADER:
            current_section = "runtime"
            continue

        # Any other section-level header resets the state
        if stripped.endswith(":") and not stripped.startswith("android.") and current_section:
            indent = len(line) - len(line.lstrip())
            if indent <= 4:
                current_section = None

        if current_section == "declared":
            name = stripped.split()[0].rstrip(":")
            if name and "." in name:
                declared.append(name)
        elif current_section == "install":
            m = re.match(r"([\w.]+):\s*granted=true", stripped)
            if m:
                install_granted.append(m.group(1))
        elif current_section == "runtime":
            m = re.match(r"([\w.]+):\s*granted=true", stripped)
            if m:
                runtime_granted.append(m.group(1))

    return AppPermissions(
        declared=declared,
        install_granted=install_granted,
        runtime_granted=runtime_granted,
    )


def _normalize_component(name: str, package: str) -> str:
    if "/" in name:
        return name
    return f"{package}/{name}"


def parse_components(dumpsys_output: str, package: str) -> AppComponents:
    activities: list[str] = []
    services: list[str] = []
    receivers: list[str] = []
    providers: list[str] = []

    component_pattern = re.compile(re.escape(package) + r"/([.\w$]+)")

    pkg_block_start = dumpsys_output.find(f"Package [{package}]")
    resolver_section = dumpsys_output[:pkg_block_start] if pkg_block_start != -1 else dumpsys_output

    section_headers = [
        "Activity Resolver Table:",
        "Receiver Resolver Table:",
        "Service Resolver Table:",
        "Provider Resolver Table:",
    ]

    section_bounds: list[tuple[str, int, int]] = []
    for i, header in enumerate(section_headers):
        start = resolver_section.find(header)
        if start == -1:
            continue
        end = len(resolver_section)
        for other_header in section_headers[i + 1:]:
            other_start = resolver_section.find(other_header, start + 1)
            if other_start != -1 and other_start < end:
                end = other_start
        section_bounds.append((header, start, end))

    for header, start, end in section_bounds:
        section_content = resolver_section[start:end]
        matches = component_pattern.findall(section_content)
        seen: set[str] = set()
        unique = [
            _normalize_component(m, package)
            for m in matches
            if not (m in seen or seen.add(m))
        ]

        if "Activity" in header:
            activities.extend(unique)
        elif "Receiver" in header:
            receivers.extend(unique)
        elif "Service" in header:
            services.extend(unique)
        elif "Provider" in header:
            providers.extend(unique)

    if not providers:
        provider_pattern = re.compile(r"Provider\{[^}]+ " + re.escape(package) + r"/([.\w$]+)\}")
        for m in provider_pattern.finditer(resolver_section):
            name = _normalize_component(m.group(1), package)
            if name not in providers:
                providers.append(name)

    return AppComponents(
        activities=activities,
        services=services,
        receivers=receivers,
        providers=providers,
    )


def parse_version_name_from_dumpsys(dumpsys_output: str) -> str | None:
    try:
        match = re.search(r"versionName=(.+)", dumpsys_output)
        if match:
            return match.group(1).strip()
    except Exception:
        pass
    return None
