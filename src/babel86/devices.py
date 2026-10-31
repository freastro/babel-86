"""Audio devices. Milestone 2 has no audio library yet, so this is a fixed mock list.

Milestone 3 replaces `list_outputs` with the OS device list; the shape (a stable ID, a
display name and a channel count) stays the same. Pure, with no Tk.
"""

from __future__ import annotations

from dataclasses import dataclass

DISCONNECTED = " (disconnected)"


@dataclass(frozen=True)
class OutputDevice:
    id: str
    name: str
    channels: int


_MOCK_OUTPUTS = (
    OutputDevice("mock:speakers", "Speakers", 2),
    OutputDevice("mock:interpreter-desk", "Interpreter Desk", 8),
)

# The input unit's device, until the Input Setup dialog and real devices exist.
DEFAULT_INPUT_ID = "mock:microphone"
DEFAULT_INPUT_NAME = "Microphone"


def list_outputs() -> list[OutputDevice]:
    return list(_MOCK_OUTPUTS)


def find(device_id: str) -> OutputDevice | None:
    return next((d for d in list_outputs() if d.id == device_id), None)


def route_name(device_id: str, last_name: str) -> str:
    """The device's current name, or its last-seen name marked disconnected."""
    device = find(device_id)
    if device is None:
        return f"{last_name or device_id}{DISCONNECTED}"
    return device.name
