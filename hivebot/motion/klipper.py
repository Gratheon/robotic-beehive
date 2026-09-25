"""Klipper backend (production).

Klipper runs on a 3D-printer class motion board (BTT Octopus) and generates
step pulses in real time. The Jetson sends G-code through Moonraker's HTTP API.
See firmware/klipper/hivebot.cfg for the matching configuration.

Axes are Klipper `manual_stepper`s. To run several at once, every move but the
longest is sent with SYNC=0 (it does not block the G-code queue). The longest
goes last with the default sync, then M400 waits for all of them.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Callable, Dict, Iterable, Optional

from ..config import RobotConfig
from .base import MotionBackend, MotionError

SERVO_SETTLE_S = 0.6


class KlipperBackend(MotionBackend):
    def __init__(
        self,
        url: str = "http://127.0.0.1:7125",
        config: Optional[RobotConfig] = None,
        load_reader: Optional[Callable[[str], float]] = None,
        timeout: float = 600.0,
    ):
        self.url = url.rstrip("/")
        self.cfg = config or RobotConfig()
        self.axes = self.cfg.axes
        self.timeout = timeout
        self._pos: Dict[str, float] = {}
        self._servo: Dict[str, float] = {}
        # Load cells hang off the ESP32 supervisor (HX711); pass a reader.
        self._load_reader = load_reader

    # ----- transport ------------------------------------------------------
    def _post(self, path: str, body: Optional[dict] = None) -> dict:
        req = urllib.request.Request(
            self.url + path,
            data=json.dumps(body or {}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return json.loads(r.read() or b"{}")
        except Exception as err:  # noqa: BLE001 - any transport error stops motion
            raise MotionError(f"klipper: {err}") from err

    def _get(self, path: str) -> dict:
        try:
            with urllib.request.urlopen(self.url + path, timeout=10) as r:
                return json.loads(r.read())
        except Exception as err:  # noqa: BLE001
            raise MotionError(f"klipper: {err}") from err

    def gcode(self, script: str) -> None:
        self._post("/printer/gcode/script", {"script": script})

    # ----- MotionBackend ------------------------------------------------------
    def move(self, targets: Dict[str, float], speed: float, accel: Optional[float] = None) -> None:
        durations = {}
        for a, pos in targets.items():
            ax = self.axes[a]
            if not ax.min_pos <= pos <= ax.max_pos:
                raise MotionError(f"{a}={pos:.1f} outside [{ax.min_pos}, {ax.max_pos}]")
            v = min(speed, ax.max_speed)
            durations[a] = abs(pos - self._pos.get(a, pos)) / v
        order = sorted(targets, key=lambda a: durations[a])
        lines = []
        for i, a in enumerate(order):
            ax = self.axes[a]
            v = min(speed, ax.max_speed)
            acc = accel or ax.accel
            sync = "" if i == len(order) - 1 else " SYNC=0"
            lines.append(f"MANUAL_STEPPER STEPPER={a} SPEED={v:.3f} ACCEL={acc:.1f} MOVE={targets[a]:.3f}{sync}")
        lines.append("M400")
        self.gcode("\n".join(lines))
        self._pos.update(targets)

    def home(self, axes: Iterable[str]) -> None:
        for a in axes:
            ax = self.axes[a]
            travel = ax.max_pos - ax.min_pos + 20
            # Pretend we are at the top, run down onto the endstop, then set the real height.
            self.gcode(
                f"MANUAL_STEPPER STEPPER={a} ENABLE=1\n"
                f"MANUAL_STEPPER STEPPER={a} SET_POSITION={travel:.1f}\n"
                f"MANUAL_STEPPER STEPPER={a} SPEED={min(10.0, ax.max_speed)} MOVE=0 STOP_ON_ENDSTOP=1\n"
                f"MANUAL_STEPPER STEPPER={a} SET_POSITION={ax.home_pos:.3f}"
            )
            self._pos[a] = ax.home_pos

    def position(self, axis: str) -> float:
        return self._pos[axis]

    def set_servo(self, name: str, angle: float) -> None:
        self.gcode(f"SET_SERVO SERVO={name} ANGLE={angle:.1f}\nG4 P{int(SERVO_SETTLE_S * 1000)}")
        self._servo[name] = angle

    def servo(self, name: str) -> float:
        return self._servo.get(name, 0.0)

    def set_output(self, name: str, value: float) -> None:
        if name == "heater":
            self.gcode(f"SET_HEATER_TEMPERATURE HEATER=cabinet TARGET={25 if value else 0}")
        else:
            self.gcode(f"SET_PIN PIN={name} VALUE={value:.2f}")

    def read_input(self, name: str) -> bool:
        obj = f"gcode_button {name}"
        status = self._get(f"/printer/objects/query?{urllib.parse.quote(obj)}")["result"]["status"]
        pressed = status[obj]["state"] == "PRESSED"
        # door_closed and estop_ok are wired normally-closed: PRESSED = OK
        return pressed

    def read_load(self, side: str) -> float:
        if self._load_reader is None:
            raise MotionError("no load cell reader configured")
        return self._load_reader(side)

    def wait(self, seconds: float) -> None:
        self.gcode(f"G4 P{int(seconds * 1000)}")

    def emergency_stop(self) -> None:
        try:
            self._post("/printer/emergency_stop")
        finally:
            self._pos.clear()  # positions are unknown until homed again

    def disable_motors(self) -> None:
        # Safe: TR16x4 screws are self-locking, beams stay where they are.
        self.gcode("M84")
