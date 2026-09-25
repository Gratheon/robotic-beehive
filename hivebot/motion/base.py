"""Motion backend interface.

Sequences talk to hardware only through this interface, so the same
inspection logic runs against the simulator (tests, dry runs), Klipper
(production) or bare Jetson GPIO (bench rig).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Iterable, Optional

LIFT = ("lift_left", "lift_right")
SCAN = ("scan_left", "scan_right")
SHUTTLE = ("shuttle_left", "shuttle_right")
FORKS = ("fork_left", "fork_right")
HOOKS = ("hook_left", "hook_right")
ALL_AXES = LIFT + SCAN + SHUTTLE


class MotionError(RuntimeError):
    """A move was refused or failed. The robot is stopped when this is raised."""


class MotionBackend(ABC):
    @abstractmethod
    def move(self, targets: Dict[str, float], speed: float, accel: Optional[float] = None) -> None:
        """Move the given axes to absolute positions (mm). All axes start together,
        run at `speed` and the call returns when every axis has arrived."""

    @abstractmethod
    def home(self, axes: Iterable[str]) -> None:
        """Run the axes onto their endstops and set their positions."""

    @abstractmethod
    def position(self, axis: str) -> float:
        """Last commanded position of an axis (mm)."""

    @abstractmethod
    def set_servo(self, name: str, angle: float) -> None:
        """Set a servo angle (degrees) and wait for it to settle."""

    @abstractmethod
    def servo(self, name: str) -> float:
        """Last commanded servo angle."""

    @abstractmethod
    def set_output(self, name: str, value: float) -> None:
        """Set a switched output: 'red_light', 'strobe', 'heater' (0..1)."""

    @abstractmethod
    def read_input(self, name: str) -> bool:
        """Read a digital input: 'pin_left' / 'pin_right' (inductive frame-pin
        sensors on the shuttles), 'door', 'estop'."""

    @abstractmethod
    def read_load(self, side: str) -> float:
        """Load on one fork pair in kg ('left' or 'right')."""

    @abstractmethod
    def wait(self, seconds: float) -> None:
        """Dwell (the simulator only records it)."""

    @abstractmethod
    def emergency_stop(self) -> None:
        """Cut motion immediately."""

    def disable_motors(self) -> None:  # optional: self-locking screws hold position
        pass
