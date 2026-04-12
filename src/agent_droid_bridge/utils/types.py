from __future__ import annotations

from typing import Annotated

from pydantic import Field

DeviceSerial = Annotated[
    str | None,
    Field(
        default=None,
        pattern=r"^[a-zA-Z0-9\-:.]+$",
        max_length=64,
        description=(
            "Target device serial — pass as device_serial=<serial>. "
            "Android device serial (e.g. 'emulator-5554' or '192.168.1.10:5555'). "
            "Omit only when a single device is connected. "
            "If the tool returns a multi-device error: STOP. Present the device list "
            "to the user verbatim and wait for their explicit choice. "
            "Do NOT retry with a guessed or inferred serial — this is a hard "
            "requirement. Once the user provides a serial, use it for every "
            "subsequent call in this session. To switch devices mid-session, "
            "ask the user first."
        ),
    ),
]
