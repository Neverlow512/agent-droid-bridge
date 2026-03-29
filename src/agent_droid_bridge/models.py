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
