"""Inspection sequences: open a box, walk its frames past the cameras, close it.

The order of operations follows how a careful beekeeper works a hive:
crack the seam at one edge, lift, work frames one at a time into the free
space at the side of the box, look at the rim before closing, and close by
letting contact roll across the rim so bees are pushed aside rather than
crushed.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .capture import CaptureRig, NoRimCheck, NullCapture, RimCheck
from .config import RobotConfig
from .motion.base import FORKS, HOOKS, LIFT, SCAN, SHUTTLE, MotionBackend, MotionError
from .safety import Conditions, Policy, evaluate

log = logging.getLogger("hivebot")
SIDES = ("left", "right")


class InspectionAborted(RuntimeError):
    pass


@dataclass
class FrameRecord:
    box: int
    index: int
    z_before: float
    z_after: float
    images: List[str] = field(default_factory=list)


@dataclass
class Report:
    box: int
    lifted_kg: float = 0.0
    frames: List[FrameRecord] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def both(axes, value) -> Dict[str, float]:
    return {a: value for a in axes}


class Inspector:
    def __init__(
        self,
        backend: MotionBackend,
        config: Optional[RobotConfig] = None,
        capture: Optional[CaptureRig] = None,
        rim_check: Optional[RimCheck] = None,
        frame_state: Optional[Dict[int, List[float]]] = None,
    ):
        self.m = backend
        self.cfg = config or RobotConfig()
        self.g = self.cfg.geometry
        self.sp = self.cfg.speeds
        self.capture = capture or NullCapture()
        self.rim = rim_check or NoRimCheck()
        # Where every frame hangs (Z, mm). Persist this between runs; the pin
        # sensors re-check it every time a box is opened.
        self.frames: Dict[int, List[float]] = frame_state or {k: self.g.frame_z() for k in range(self.g.boxes)}
        self.holding = False

    # ----- basics -------------------------------------------------------
    def guard(self) -> None:
        if not self.m.read_input("estop_ok"):
            raise InspectionAborted("emergency stop pressed")
        if not self.m.read_input("door_closed"):
            raise InspectionAborted("service door opened")

    def home(self) -> None:
        self.guard()
        self.m.home(SCAN)  # scan beams first: they live below the lift beams
        self.m.home(LIFT)
        self.m.home(SHUTTLE)
        self.park()

    def park(self) -> None:
        # Order the two moves so the beams never close in on each other.
        scan = {**both(SCAN, self.g.scan_park), **both(SHUTTLE, 0.0)}
        lift = both(LIFT, self.g.lift_park)
        raising = self.g.lift_park >= min(self.m.position(a) for a in LIFT)
        for targets in ((lift, scan) if raising else (scan, lift)):
            self.m.move(targets, self.sp.travel)

    # ----- the stack ----------------------------------------------------
    def open_box(self, k: int) -> float:
        """Raise everything above box k by `gap`. Returns the lifted weight (kg)."""
        g, sp, lim = self.g, self.sp, self.cfg.limits
        if not 0 <= k < g.boxes:
            raise ValueError(f"box {k} does not exist")
        c = g.cleat(k + 1)
        self.guard()
        self.m.move({**both(SCAN, g.scan_park), **both(SHUTTLE, 0.0)}, sp.travel)
        self.m.move(both(LIFT, c - 8), sp.travel)
        for f in FORKS:
            self.m.set_servo(f, self.cfg.servos.fork_engaged)
        self.m.move(both(LIFT, c - 1), sp.landing)
        # Peel: one edge at a time. The other side is the hinge.
        for side in SIDES:
            self.m.move({f"lift_{side}": c + sp.peel_height}, sp.peel)
            load = self.m.read_load(side)
            if load > lim.peel_breakaway_kg:
                self._abort_lift(k, f"{side} peel needs {load:.0f} kg, stack may be strapped or wedged")
        weight = sum(self.m.read_load(s) for s in SIDES)
        log.info("stack above box %d weighs %.1f kg", k, weight)
        pos = c + sp.peel_height
        while pos < c + g.gap:
            pos = min(c + g.gap, pos + 50)
            self.guard()
            self.m.move(both(LIFT, pos), sp.travel)
            for side in SIDES:
                if self.m.read_load(side) > lim.max_load_per_side_kg:
                    self._abort_lift(k, f"{side} load above {lim.max_load_per_side_kg:.0f} kg")
        return weight

    def _abort_lift(self, k: int, why: str) -> None:
        log.error("lift aborted: %s", why)
        self.close_box(k, check_rim=False)
        raise InspectionAborted(why)

    def close_box(self, k: int, check_rim: bool = True) -> List[str]:
        g, sp, lim = self.g, self.sp, self.cfg.limits
        c = g.cleat(k + 1)
        warnings = []
        if self.holding:
            raise InspectionAborted("a frame is still on the hook: manual help needed")
        self.m.move({**both(SCAN, g.scan_park), **both(SHUTTLE, 0.0)}, sp.travel)
        top = max(self.m.position(a) for a in LIFT)
        if top > c + sp.landing_zone:
            self.m.move(both(LIFT, c + sp.landing_zone), sp.travel)
        if check_rim:
            for attempt in range(lim.rim_check_retries):
                bees = self.rim.bees_on_rim()
                if not bees:
                    break
                log.info("%d bees on the rim, waiting", bees)
                self.m.wait(lim.rim_check_wait_s)
            else:
                warnings.append("bees still on the rim after retries; closed with rolling contact")
        expected = {s: self.m.read_load(s) for s in SIDES}
        for side in SIDES:  # rolling close: left edge lands first, then right
            self._land(side, c, expected[side])
        for f in FORKS:
            self.m.move({f"lift_{f.split('_')[1]}": c - 8}, sp.landing)
            self.m.set_servo(f, self.cfg.servos.fork_stowed)
        self.park()
        return warnings

    def _land(self, side: str, c: float, expected_kg: float) -> None:
        sp, lim = self.sp, self.cfg.limits
        axis = f"lift_{side}"
        pos = self.m.position(axis)
        while pos > c:
            pos = max(c, pos - 2.0)
            self.m.move({axis: pos}, sp.landing)
            actual = self.m.position(axis)
            d = actual - c
            if d > 5 and self.m.read_load(side) < lim.contact_drop_ratio * expected_kg:
                self.m.move({axis: actual + 20}, sp.landing)
                raise InspectionAborted(f"{side} edge touched something {d:.0f} mm above the rim")

    # ----- frames -------------------------------------------------------
    def locate_frames(self, k: int) -> List[float]:
        """Find each frame's pin with the inductive sensors (2 mm steps)."""
        g, sp = self.g, self.sp
        self.m.move(both(SCAN, g.engage(k) + g.hook_approach), sp.travel)
        found = []
        for z in self.frames[k]:
            hits = self._probe_pin(z, 4) or self._probe_pin(z, 12)
            if hits:
                found.append(sum(hits) / len(hits))
            else:
                log.warning("box %d: no pin near z=%.1f, frame skipped", k, z)
        self.frames[k] = found
        return found

    def _probe_pin(self, z: float, reach: int) -> List[float]:
        """Step the pin sensor across z±reach in 2 mm steps; return positions
        where both sensors see the pin (sensing radius is about 3 mm)."""
        hits = []
        for dz in range(-reach, reach + 1, 2):
            self.m.move(both(SHUTTLE, z + dz - self.g.pin_sensor_offset), self.sp.shuttle)
            if self.m.read_input("pin_left") and self.m.read_input("pin_right"):
                hits.append(z + dz)
        return hits

    def scan_box(self, k: int, report: Report) -> None:
        g = self.g
        zs = sorted(self.locate_frames(k))
        if not zs:
            return
        back_space = zs[0] - g.frame_pitch / 2 + g.box_inner_d / 2
        push = -1 if back_space > g.gap_width / 2 else 1  # toward the working gap
        order = range(len(zs)) if push < 0 else range(len(zs) - 1, -1, -1)
        e = g.engage(k)
        self.m.move(both(SHUTTLE, zs[order[0]] - push * g.slot_approach), self.sp.shuttle)
        for h in HOOKS:  # swing in once per box, then travel just above the pin heads
            self.m.set_servo(h, self.cfg.servos.hook_engaged)
        self.m.move(both(SCAN, e + g.hook_travel), self.sp.hook_lower)
        for i in order:
            self.guard()
            rec = self._lift_frame(k, i, zs[i], push, e)
            zs[i] = rec.z_after
            report.frames.append(rec)
        self.m.move(both(SCAN, e + g.hook_approach), self.sp.hook_lower)
        for h in HOOKS:
            self.m.set_servo(h, self.cfg.servos.hook_stowed)
        self.frames[k] = zs

    def _lift_frame(self, k: int, i: int, z: float, push: int, e: float) -> FrameRecord:
        g, sp = self.g, self.sp
        target = z + push * g.gap_width
        self.m.move(both(SHUTTLE, z - push * g.slot_approach), sp.shuttle)
        self.m.move(both(SCAN, e), sp.hook_lower)  # plate lands beside the pin
        self.m.move(both(SHUTTLE, z - push * g.slot_engaged), sp.shuttle_fine)  # pin enters slot
        self.holding = True
        self.m.move(both(SHUTTLE, z - push * g.slot_engaged + push * sp.frame_nudge), sp.shuttle_fine)
        for s in SCAN:  # peel the ear propolis one end at a time
            self.m.move({s: e + 2}, sp.frame_peel)
        self.m.move(both(SCAN, e + g.frame_lift), sp.frame_up)
        # Same photo spot for every frame: centred between the cameras, so
        # distance, focus and mm-per-pixel never change.
        self.m.move(both(SHUTTLE, g.photo_z - push * g.slot_engaged), sp.shuttle)
        images = self.capture.capture({"box": k, "frame": i, "z": round(z, 1), "side": "both"})
        self.m.move(both(SHUTTLE, target - push * g.slot_engaged), sp.shuttle)
        self.m.move(both(SCAN, e + sp.frame_landing_zone), sp.frame_down)
        self.m.move(both(SCAN, e), sp.frame_landing)
        self.m.move(both(SHUTTLE, target - push * g.slot_approach), sp.shuttle_fine)  # release
        self.holding = False
        self.m.move(both(SCAN, e + g.hook_travel), sp.hook_lower)
        return FrameRecord(k, i, z, target, images)

    # ----- the whole visit ------------------------------------------------
    def inspect(self, k: int, conditions: Optional[Conditions] = None, policy: Policy = Policy()) -> Report:
        if conditions is not None:
            decision = evaluate(conditions, policy)
            if not decision.go:
                raise InspectionAborted("; ".join(decision.reasons))
            if decision.preheat:
                self.m.set_output("heater", 1.0)
                self.m.wait(600)  # the supervisor also watches cabinet temperature
                self.m.set_output("heater", 0.0)
        report = Report(box=k)
        self.m.set_output("red_light", 1.0)
        try:
            report.lifted_kg = self.open_box(k)
            try:
                self.scan_box(k, report)
            except MotionError as err:
                report.warnings.append(f"scan stopped: {err}")
                if self.holding:
                    self.m.emergency_stop()
                    raise InspectionAborted(f"frame stuck on hook: {err}") from err
            report.warnings += self.close_box(k)
        finally:
            self.m.set_output("red_light", 0.0)
        return report
