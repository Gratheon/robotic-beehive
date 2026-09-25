"""Bench backend: step/dir straight from the Jetson 40-pin header to DM542s.

This is the setup main.py already uses (PUL=33, DIR=40, ENA=22, BOARD
numbering). It adds trapezoidal ramps, several axes stepped together
(Bresenham), soft limits and endstop homing.

Linux cannot time pulses reliably (expect jitter and a ceiling of a few
kHz), so keep DM542 microstepping low (400-800 pulses/rev) and use this only
on the bench. The robot uses the Klipper backend.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Iterable, Optional

from ..config import RobotConfig
from .base import MotionBackend, MotionError


@dataclass(frozen=True)
class Pins:
    pul: int
    dir: int
    ena: Optional[int] = None
    endstop: Optional[int] = None
    invert_dir: bool = False
    ena_active_low: bool = True  # DM542: ENA+ high = motor free


# The current bench rig: one DM542 on the lift axis.
BENCH_PINS = {"lift_left": Pins(pul=33, dir=40, ena=22)}


class JetsonGPIOBackend(MotionBackend):
    def __init__(self, pins: Dict[str, Pins] = BENCH_PINS, config: Optional[RobotConfig] = None, pulses_per_rev: int = 400):
        import Jetson.GPIO as GPIO  # only on the Jetson

        self.GPIO = GPIO
        self.cfg = config or RobotConfig()
        self.axes = self.cfg.axes
        self.pins = pins
        self.ppr = pulses_per_rev
        self._pos: Dict[str, float] = {a: self.axes[a].home_pos for a in pins}
        GPIO.setmode(GPIO.BOARD)
        for p in pins.values():
            GPIO.setup(p.pul, GPIO.OUT, initial=GPIO.LOW)
            GPIO.setup(p.dir, GPIO.OUT, initial=GPIO.LOW)
            if p.ena is not None:
                GPIO.setup(p.ena, GPIO.OUT, initial=GPIO.LOW if p.ena_active_low else GPIO.HIGH)
            if p.endstop is not None:
                GPIO.setup(p.endstop, GPIO.IN)

    def steps_per_mm(self, axis: str) -> float:
        return self.ppr / self.axes[axis].rotation_distance

    # ----- motion -------------------------------------------------------
    def move(self, targets: Dict[str, float], speed: float, accel: Optional[float] = None) -> None:
        for a, pos in targets.items():
            if a not in self.pins:
                raise MotionError(f"{a} is not wired on the bench rig")
            ax = self.axes[a]
            if not ax.min_pos <= pos <= ax.max_pos:
                raise MotionError(f"{a}={pos:.1f} outside [{ax.min_pos}, {ax.max_pos}]")
        steps = {a: round((targets[a] - self._pos[a]) * self.steps_per_mm(a)) for a in targets}
        lead = max(steps, key=lambda a: abs(steps[a]), default=None)
        if lead is None or steps[lead] == 0:
            return
        v = min(speed, min(self.axes[a].max_speed for a in targets))
        acc = accel or min(self.axes[a].accel for a in targets)
        self._run(steps, lead, v * self.steps_per_mm(lead), acc * self.steps_per_mm(lead))
        for a in targets:
            self._pos[a] += steps[a] / self.steps_per_mm(a)

    def _run(self, steps: Dict[str, int], lead: str, v_max: float, a_max: float, stop_pin: Optional[int] = None) -> int:
        """Step all axes; `lead` sets the timing, others follow by Bresenham.
        Trapezoidal profile in steps/s. Returns steps done on the lead axis."""
        G = self.GPIO
        for a, n in steps.items():
            p = self.pins[a]
            G.output(p.dir, G.HIGH if (n > 0) != p.invert_dir else G.LOW)
        time.sleep(10e-6)  # DM542 direction setup time
        n = abs(steps[lead])
        err = {a: n // 2 for a in steps}
        ramp = int(v_max * v_max / (2 * a_max))
        t = time.perf_counter()
        for i in range(n):
            if stop_pin is not None and G.input(stop_pin):
                return i
            to_go = n - i
            v = min(v_max, (2 * a_max * (i + 1)) ** 0.5, (2 * a_max * to_go) ** 0.5) if ramp else v_max
            period = 1.0 / max(v, 50.0)
            for a in steps:
                err[a] -= abs(steps[a])
                if err[a] < 0:
                    err[a] += n
                    G.output(self.pins[a].pul, G.HIGH)
            t_high = time.perf_counter() + 5e-6
            while time.perf_counter() < t_high:
                pass
            for a in steps:
                G.output(self.pins[a].pul, G.LOW)
            t += period
            while time.perf_counter() < t:  # busy-wait: sleep() is far too coarse
                pass
        return n

    def home(self, axes: Iterable[str]) -> None:
        for a in axes:
            p = self.pins.get(a)
            if p is None or p.endstop is None:
                raise MotionError(f"{a} has no endstop on the bench rig")
            ax = self.axes[a]
            spm = self.steps_per_mm(a)
            far = -round((ax.max_pos - ax.min_pos + 20) * spm)
            done = self._run({a: far}, a, 10 * spm, 50 * spm, stop_pin=p.endstop)
            if done >= abs(far):
                raise MotionError(f"{a}: endstop never triggered")
            self._pos[a] = ax.home_pos

    def position(self, axis: str) -> float:
        return self._pos[axis]

    # ----- not on the bench rig -------------------------------------------
    def set_servo(self, name: str, angle: float) -> None:
        raise MotionError("servos are driven by the motion board, not the Jetson")

    def servo(self, name: str) -> float:
        return 0.0

    def set_output(self, name: str, value: float) -> None:
        pass

    def read_input(self, name: str) -> bool:
        return name in ("door_closed", "estop_ok")

    def read_load(self, side: str) -> float:
        raise MotionError("no load cells on the bench rig")

    def wait(self, seconds: float) -> None:
        time.sleep(seconds)

    def emergency_stop(self) -> None:
        self.disable_motors()

    def disable_motors(self) -> None:
        for p in self.pins.values():
            if p.ena is not None:
                self.GPIO.output(p.ena, self.GPIO.HIGH if p.ena_active_low else self.GPIO.LOW)

    def close(self) -> None:
        self.GPIO.cleanup()
