from __future__ import annotations

from pydantic import BaseModel, Field


class AppMetadata(BaseModel):
    version_name: str | None = None
    version_code: int | None = None
    first_install_time: str | None = None
    last_update_time: str | None = None
    data_dir: str | None = None
    apk_paths: list[str] = Field(default_factory=list)
    native_lib_dir: str | None = None
    installer: str | None = None


class AppPermissions(BaseModel):
    declared: list[str] = Field(default_factory=list)
    install_granted: list[str] = Field(default_factory=list)
    runtime_granted: list[str] = Field(default_factory=list)


class AppComponents(BaseModel):
    activities: list[str] = Field(default_factory=list)
    services: list[str] = Field(default_factory=list)
    receivers: list[str] = Field(default_factory=list)
    providers: list[str] = Field(default_factory=list)


class PackageInfo(BaseModel):
    package: str
    apk_path: str | None = None
    version_name: str | None = None
    install_time: str | None = None
    installer: str | None = None


class ListPackagesResult(BaseModel):
    total: int = 0
    filter: str = "all"
    mode: str = "summary"
    search: str | None = None
    packages: list[PackageInfo] = Field(default_factory=list)


class GetAppInfoResult(BaseModel):
    package: str
    metadata: AppMetadata | None = None
    permissions: AppPermissions | None = None
    components: AppComponents | None = None
    error: str | None = None
    raw_snippet: str | None = None
    api_level: int | None = None


class InstallAppResult(BaseModel):
    success: bool
    package: str | None = None
    version_installed: str | None = None
    error: str | None = None


class UninstallAppResult(BaseModel):
    success: bool
    package: str
    error: str | None = None


class PulledFile(BaseModel):
    path: str
    size_bytes: int


class PullApkResult(BaseModel):
    success: bool
    files: list[PulledFile] = Field(default_factory=list)
    total_size_bytes: int = 0
    error: str | None = None


class ManagePermissionResult(BaseModel):
    success: bool
    action: str
    permissions: AppPermissions | None = None
    granted: bool | None = None
    error: str | None = None


class LaunchAppExtraResult(BaseModel):
    component: str | None = None
    app_name: str | None = None
    pid: int | None = None
    success: bool
    error: str | None = None


class ManageAppResult(BaseModel):
    action: str
    success: bool
    requires_root: bool | None = None
    error: str | None = None


class InjectIntentResult(BaseModel):
    success: bool
    exit_code: int
    output: list[str] = Field(default_factory=list)
    error: str | None = None
