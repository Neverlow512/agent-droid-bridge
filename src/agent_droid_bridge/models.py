from __future__ import annotations

from pydantic import BaseModel


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
