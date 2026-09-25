"""Simulated robot.

Tracks the physical state of the hive (which cleat the forks are under, how
far each side of the stack is lifted, where every frame is, which frame is
on the hook) and refuses any move that a careful beekeeper would refuse:
beam collisions, forks rotating into a cleat, landing the stack or a frame
faster than the landing speed, lifting a frame into bees hanging under the
lifted stack, sliding a frame into its neighbour.

Used by the tests, by `python -m hivebot plan` for dry runs, and for
estimating how long the hive stays open.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

from ..config import RobotConfig
from .base import ALL_AXES, MotionBackend, MotionError

SIDES = ("left", "right")
EPS = 1e-6


@dataclass
class SimHive:
    box_kg: List[float] = field(default_factory=lambda: [32.0, 28.0, 18.0, 12.0])
    lid_kg: float = 4.0
    propolis_kg: float = 12.0  # extra force until the seam cracks
    # (side, height) — something on the rim at this height under that side
    obstruction: Optional[Tuple[str, float]] = None


class SimBackend(MotionBackend):
    def __init__(self, config: Optional[RobotConfig] = None, hive: Optional[SimHive] = None):
        self.cfg = config or RobotConfig()
        self.g = self.cfg.geometry
        self.hive = hive or SimHive()
        self.axes = self.cfg.axes
        self.pos: Dict[str, float] = {a: self.axes[a].home_pos for a in ALL_AXES}
        self.pos["shuttle_left"] = self.pos["shuttle_right"] = 0.0
        self.servos: Dict[str, float] = {"fork_left": 0.0, "fork_right": 0.0, "hook_left": 0.0, "hook_right": 0.0}
        self.outputs: Dict[str, float] = {}
        self.engaged: Dict[str, Optional[int]] = {"left": None, "right": None}  # cleat index
        self.peeled: Dict[str, bool] = {"left": False, "right": False}
        self.contact: Dict[str, bool] = {"left": False, "right": False}
        self.frames: Dict[int, List[float]] = {k: self.g.frame_z() for k in range(self.g.boxes)}
        self.hooked: Optional[int] = None
        self.hook_dir = 0  # push direction of the hooked frame (-1 / +1)
        self.homed = False
        self.clock = 0.0
        self.log: List[tuple] = []

    # ----- helpers -------------------------------------------------------
    def _fail(self, msg: str) -> None:
        self.log.append(("refused", msg))
        raise MotionError(msg)

    def lifted(self, side: str) -> float:
        e = self.engaged[side]
        if e is None:
            return 0.0
        return max(0.0, self.pos[f"lift_{side}"] - self.g.cleat(e))

    def open_box(self) -> Optional[int]:
        e = self.engaged["left"]
        if e is None or e != self.engaged["right"]:
            return None
        return e - 1

    def _is_open(self, k: int) -> bool:
        return self.open_box() == k and min(self.lifted(s) for s in SIDES) >= self.g.gap - 1

    def _scan(self) -> float:
        return (self.pos["scan_left"] + self.pos["scan_right"]) / 2

    def _hook_on(self) -> bool:
        return all(self.servos[h] > 45 for h in ("hook_left", "hook_right"))

    # ----- MotionBackend ---------------------------------------------------
    def home(self, axes: Iterable[str]) -> None:
        axes = list(axes)
        # scan beams first so the lift beams never home into them
        for a in sorted(axes, key=lambda a: 0 if a.startswith("scan") else 1):
            self.pos[a] = self.axes[a].home_pos
        self.homed = True
        self.clock += 30
        self.log.append(("home", tuple(axes)))

    def position(self, axis: str) -> float:
        return self.pos[axis]

    def servo(self, name: str) -> float:
        return self.servos[name]

    def set_output(self, name: str, value: float) -> None:
        self.outputs[name] = value
        self.log.append(("output", name, value))

    def read_input(self, name: str) -> bool:
        if name in ("door_closed", "estop_ok"):
            return True
        if name.startswith("pin_"):
            k = self.open_box()
            if k is None or not self._is_open(k):
                return False
            s = self._scan()
            if not (self.g.engage(k) - 1 <= s <= self.g.engage(k) + self.g.hook_approach + 30):
                return False
            z = self.pos[f"shuttle_{name[4:]}"] + self.g.pin_sensor_offset
            return any(abs(z - fz) <= 3.0 for i, fz in enumerate(self.frames[k]) if i != self.hooked)
        raise KeyError(name)

    def read_load(self, side: str) -> float:
        k = self.open_box()
        if self.engaged[side] is None:
            return 0.0
        e = self.engaged[side]
        weight = sum(self.hive.box_kg[i] for i in range(e, self.g.boxes)) + self.hive.lid_kg
        d = {s: self.lifted(s) for s in SIDES}
        if self.contact[side]:
            return 0.2 * weight / 2
        if d[side] <= EPS:
            return 0.0 if d[_other(side)] <= EPS else weight / 4  # far edge still on the rim
        load = weight / 2
        if d[_other(side)] <= EPS and not self.peeled[side]:
            load += self.hive.propolis_kg
        return load

    def wait(self, seconds: float) -> None:
        self.clock += seconds
        self.log.append(("wait", seconds))

    def emergency_stop(self) -> None:
        self.log.append(("estop",))

    def set_servo(self, name: str, angle: float) -> None:
        side = name.split("_")[1]
        g = self.g
        if name.startswith("fork"):
            engaging = angle > 45
            if engaging:
                lift = self.pos[f"lift_{side}"]
                for i in range(1, g.boxes + 1):
                    if g.cleat(i) - 15 <= lift <= g.cleat(i) - 3:
                        self.engaged[side] = i
                        break
                else:
                    self._fail(f"{name}: fork would swing into a cleat or into air at lift={lift:.1f}")
            else:
                if self.lifted(side) > EPS or (self.engaged[side] is not None and self.pos[f"lift_{side}"] > g.cleat(self.engaged[side]) - 3):
                    self._fail(f"{name}: cannot stow fork while it carries the stack")
                self.engaged[side] = None
                self.peeled[side] = False
                self.contact[side] = False
        else:
            k = self.open_box()
            if k is None or not self._is_open(k):
                self._fail(f"{name}: hook may only move over an open box")
            if self._scan() < g.engage(k) + g.hook_approach - 0.5:
                self._fail(f"{name}: hook must swing above the rim")
            if angle <= 45 and self.hooked is not None:
                self._fail(f"{name}: frame {self.hooked} is still on the hook")
        self.servos[name] = angle
        self.clock += 0.6
        self.log.append(("servo", name, angle))

    def move(self, targets: Dict[str, float], speed: float, accel: Optional[float] = None) -> None:
        g, sp = self.g, self.cfg.speeds
        if not self.homed:
            self._fail("home first")
        for a, v in targets.items():
            ax = self.axes[a]
            if not ax.min_pos - EPS <= v <= ax.max_pos + EPS:
                self._fail(f"{a}={v:.1f} outside [{ax.min_pos:.1f}, {ax.max_pos:.1f}]")
        start = dict(self.pos)
        end = {**self.pos, **targets}

        for s in SIDES:
            if end[f"lift_{s}"] - end[f"scan_{s}"] < g.beam_clearance - EPS:
                self._fail(f"{s}: scan beam would hit lift beam")

        # --- the stack -----------------------------------------------------
        for s in SIDES:
            e = self.engaged[s]
            if e is None:
                continue
            c = g.cleat(e)
            if end[f"lift_{s}"] < c - 15:
                self._fail(f"lift_{s}: engaged fork would run into the box below")
            if end[f"lift_{s}"] > c + EPS and self.engaged[_other(s)] != e:
                self._fail(f"lift_{s}: both forks must be under the same cleat before lifting")
            d0, d1 = start[f"lift_{s}"] - c, end[f"lift_{s}"] - c
            if d0 > EPS and d1 <= EPS:  # landing
                if d0 > sp.landing_zone + EPS:
                    self._fail(f"lift_{s}: landed from {d0:.0f} mm without a slow approach")
                if speed > sp.landing + EPS:
                    self._fail(f"lift_{s}: landing at {speed} mm/s (max {sp.landing})")
            if d0 <= EPS < d1 and d1 <= sp.peel_height + EPS and self.lifted(_other(s)) <= EPS and speed > sp.peel + EPS:
                self._fail(f"lift_{s}: peel too fast")
        dl = max(0.0, end["lift_left"] - g.cleat(self.engaged["left"])) if self.engaged["left"] else 0.0
        dr = max(0.0, end["lift_right"] - g.cleat(self.engaged["right"])) if self.engaged["right"] else 0.0
        if abs(dl - dr) > g.max_tilt + EPS:
            self._fail(f"stack tilt {abs(dl - dr):.0f} mm exceeds {g.max_tilt:.0f} mm")

        for s in SIDES:
            if end[f"lift_{s}"] > start[f"lift_{s}"]:
                self.contact[s] = False
        # obstruction on the rim: the stack stops where it touches
        if self.hive.obstruction:
            side, h = self.hive.obstruction
            k = self.open_box()
            if k is not None and self.engaged[side] is not None:
                touch = g.cleat(self.engaged[side]) + (h - g.rim(k))
                a = f"lift_{side}"
                if start[a] >= touch > end[a]:
                    end[a] = touch
                    self.contact[side] = True

        # --- the hook and frames -------------------------------------------
        k = self.open_box()
        if abs(end["shuttle_left"] - end["shuttle_right"]) > 1.0:
            self._fail("shuttles out of sync")
        scan0 = (start["scan_left"] + start["scan_right"]) / 2
        scan1 = (end["scan_left"] + end["scan_right"]) / 2
        if abs(end["scan_left"] - end["scan_right"]) > 3.0:
            self._fail("scan beams more than 3 mm apart")
        z1 = end["shuttle_left"]
        start_frame = start
        if k is not None and self._hook_on():
            eng, appr = g.engage(k), g.engage(k) + g.hook_approach
            if scan1 < eng - 0.5:
                self._fail("hook below the pin neck: it would press on the top bars")
            head = eng + 5.0  # plate below this would hit a pin head
            if self.hooked is None and scan1 < head and scan0 >= head:
                if not any(abs(z1 - (fz - d * g.slot_approach)) <= 1.0 for fz in self.frames[k] for d in (-1, 1)):
                    self._fail("hook would land on a pin head")
                if speed > sp.hook_lower + EPS:
                    self._fail(f"hook lowered onto the top bars at {speed} mm/s")
            if self.hooked is None and abs(scan1 - eng) <= 0.5:
                for i, fz in enumerate(self.frames[k]):
                    for d in (-1, 1):
                        if abs(z1 - (fz - d * g.slot_engaged)) <= 0.5 and abs(start["shuttle_left"] - (fz - d * g.slot_approach)) <= 1.0:
                            self.hooked, self.hook_dir = i, d
                    if self.hooked is not None:
                        # the slide that captures the pin does not move the frame
                        start_frame = {**start, "shuttle_left": z1, "shuttle_right": z1}
                        break
            if self.hooked is not None:
                self._check_frame(k, start_frame, end, speed)

        # --- time ---------------------------------------------------------
        dur = 0.0
        for a in targets:
            dist = abs(end[a] - start[a])
            if dist < EPS:
                continue
            ax = self.axes[a]
            v = min(speed, ax.max_speed)
            acc = accel or ax.accel
            dur = max(dur, dist / v + v / acc)
        self.clock += dur
        self.pos.update(end)
        for s in SIDES:
            if self.lifted(s) > EPS and self.lifted(_other(s)) > EPS:
                self.peeled[s] = True
        self.log.append(("move", {a: round(end[a], 2) for a in targets}, speed, round(dur, 2)))

    def _check_frame(self, k: int, start: dict, end: dict, speed: float) -> None:
        g, sp = self.g, self.cfg.speeds
        i = self.hooked
        eng = g.engage(k)
        dy0 = (start["scan_left"] + start["scan_right"]) / 2 - eng
        dy1 = (end["scan_left"] + end["scan_right"]) / 2 - eng
        z0 = self.frames[k][i]
        dz = end["shuttle_left"] - start["shuttle_left"]
        if abs(dz) > EPS and dz * self.hook_dir < 0:
            if max(dy0, dy1) <= g.pocket_depth:
                # at rest height, moving backwards slides the hook off the pin
                if 0.5 < max(dy0, dy1):
                    self._fail(f"frame {i}: hook pulled back while the frame is half lifted")
                if abs(end["shuttle_left"] - (z0 - self.hook_dir * g.slot_engaged)) >= 10:
                    self.hooked, self.hook_dir = None, 0
                return
            if min(dy0, dy1) <= g.pocket_depth:
                self._fail(f"frame {i} pulled backwards before its pin sits in the pocket")
        z1 = z0 + dz
        stack_bottom = min(self.lifted(s) for s in SIDES)  # above rim
        if dy1 - g.frame_top_below_rim > stack_bottom - g.bee_clearance + EPS:
            self._fail(f"frame {i} would be lifted into bees under the raised stack")
        inside = dy1 < g.frame_h + g.frame_top_below_rim + 5
        if inside and abs(z1 - z0) > EPS:
            half = g.box_inner_d / 2 - g.frame_pitch / 2
            if not -half - EPS <= z1 <= half + EPS:
                self._fail(f"frame {i} pushed into the box wall")
            for j, zj in enumerate(self.frames[k]):
                if j != i and abs(z1 - zj) < g.frame_pitch - 0.5:
                    self._fail(f"frame {i} would squeeze frame {j}")
        if dy0 > dy1 and dy1 <= EPS + 0.5:
            if dy0 > sp.frame_landing_zone + EPS:
                self._fail(f"frame {i} set down without a slow approach")
            if speed > sp.frame_landing + EPS:
                self._fail(f"frame {i} set down at {speed} mm/s")
        self.frames[k][i] = z1


def _other(side: str) -> str:
    return "right" if side == "left" else "left"
