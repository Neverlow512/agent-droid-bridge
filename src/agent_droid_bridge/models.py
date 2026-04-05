from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field


class ScreenshotResult(BaseModel):
    image: str
    width: int
    height: int
    format: str


class DeviceInfo(BaseModel):
    serial: str
    state: str
    model: str


class UIChangeResult(BaseModel):
    changed: bool
    elapsed_seconds: float
    hierarchy: str | None = None


class TappableElement(BaseModel):
    element_type: Literal["tappable"] = "tappable"
    resource_id: str
    text: str
    content_desc: str
    center_x: int
    center_y: int


class ScreenElement(BaseModel):
    element_type: Literal["screen_element"] = "screen_element"
    xpath: str
    resource_id: str
    text: str
    content_desc: str
    class_name: str
    bounds: tuple[int, int, int, int]
    center_x: int
    center_y: int
    clickable: bool
    focusable: bool
    scrollable: bool
    long_clickable: bool
    checkable: bool
    checked: bool
    enabled: bool
    selected: bool


class ScreenElementsResult(BaseModel):
    mode: str
    total: int
    elements: list[Annotated[TappableElement | ScreenElement, Field(discriminator="element_type")]]


class ScreenTextResult(BaseModel):
    plain: str
    total: int


class DeviceCapabilities(BaseModel):
    manufacturer: str | None = None
    model: str | None = None
    codename: str | None = None
    device_type: str | None = None
    android_version: str | None = None
    api_level: int | None = None
    is_emulator: bool | None = None
    build_type: str | None = None
    cpu_abi: str | None = None
    cpu_abi2: str | None = None
    hardware: str | None = None
    board: str | None = None
    root_available: bool | None = None
    adb_is_root: bool | None = None
    total_ram_mb: int | None = None
    screen_resolution: str | None = None
    build_fingerprint: str | None = None
    build_tags: str | None = None
    android_version_codename: str | None = None
    kernel_version: str | None = None
    selinux_status: str | None = None
    ro_debuggable: bool | None = None
    ro_secure: bool | None = None
    verified_boot_state: str | None = None
    usb_config: str | None = None
    dm_verity: str | None = None
    encryption_state: str | None = None
    screen_density: str | None = None
    supported_abis: str | None = None
    cpu_cores: int | None = None
    storage_total_gb: str | None = None
    gpu: str | None = None
    mode: Literal["identity", "security", "hardware", "all"]
