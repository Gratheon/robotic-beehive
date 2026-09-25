"""Geometry and axis configuration.

Numbers mirror model/hive-model.js (DEFAULTS / derive). All heights are
absolute millimetres above the ground; Z is front(+)/back(-) from the hive
centre.

Axis coordinates:
  lift_*    height of the fork's lifting face
  scan_*    height of the hook plate (the pin-neck level when engaged)
  shuttle_* Z position of the hook slot centre
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class HiveGeometry:
    boxes: int = 3
    box_h: float = 285.0
    box_inner_d: float = 400.0
    plinth: float = 200.0
    bottom_board: float = 150.0
    lid: float = 80.0
    cleat_underside: float = 25.0
    gap: float = 400.0  # how far the upper stack is raised
    frame_lift: float = 300.0  # how far a frame is raised
    frame_count: int = 10
    frame_pitch: float = 37.5
    frame_h: float = 279.0
    working_gap_start: float = 25.0  # empty space at the back wall
    frame_top_below_rim: float = 2.0
    pin_neck: float = 2.5
    hook_approach: float = 25.0  # hook swings in this far above engage level
    hook_travel: float = 8.0  # plate clears the pin heads (top at +3.75) between frames
    # H-shaped hook plate: two back-to-back slots around a centre bar. The hook
    # lands `slot_approach` behind the pin (opposite the push direction), slides
    # until the pin sits `slot_engaged` in front of the centre bar, then pushes.
    slot_approach: float = 26.0
    slot_engaged: float = 8.0
    beam_clearance: float = 119.0  # min lift - scan (beam bodies + 5 mm margin)
    bee_clearance: float = 40.0  # frame top to lifted stack bottom
    max_tilt: float = 35.0  # max left/right height difference of the lifted stack
    pin_sensor_offset: float = -22.0  # inductive sensor Z relative to the hook slot

    @property
    def base(self) -> float:
        return self.plinth + self.bottom_board

    def box_bottom(self, i: int) -> float:
        """Bottom of box i (i == boxes is the lid)."""
        return self.base + i * self.box_h

    def rim(self, k: int) -> float:
        return self.box_bottom(k) + self.box_h

    def cleat(self, i: int) -> float:
        """Underside of the lifting cleat on box i (i == boxes is the lid)."""
        return self.box_bottom(i) + self.cleat_underside

    def engage(self, k: int) -> float:
        """Hook plate height when it is on the pin neck of a frame in box k."""
        return self.rim(k) - self.frame_top_below_rim + self.pin_neck / 2

    def frame_z(self) -> List[float]:
        z0 = -self.box_inner_d / 2 + self.working_gap_start + self.frame_pitch / 2
        return [z0 + i * self.frame_pitch for i in range(self.frame_count)]

    @property
    def gap_width(self) -> float:
        return self.box_inner_d - self.frame_count * self.frame_pitch

    @property
    def lift_park(self) -> float:
        return self.base + 250

    @property
    def scan_park(self) -> float:
        return self.plinth + 220


@dataclass(frozen=True)
class AxisConfig:
    name: str
    min_pos: float
    max_pos: float
    home_pos: float  # position reported when the endstop triggers
    max_speed: float  # mm/s
    accel: float  # mm/s^2
    rotation_distance: float  # mm per motor revolution
    steps_per_rev: int  # full steps * microsteps


def default_axes(g: HiveGeometry) -> Dict[str, AxisConfig]:
    top = g.cleat(g.boxes) + g.gap
    axes = {}
    for side in ("left", "right"):
        # All vertical axes: NEMA23 + DM542 (8 microsteps) + TR16x4 lead screw.
        # TR16x4 is self-locking (lead angle ~4.5 deg), so nothing drops on power
        # loss, and its whip limit at 1.5 m (~1000 rpm) allows 40 mm/s.
        # Lift min/home keeps the lift beam above a parked scan beam.
        axes[f"lift_{side}"] = AxisConfig(f"lift_{side}", g.base + 160, top, g.base + 160, 15.0, 40.0, 4.0, 1600)
        axes[f"scan_{side}"] = AxisConfig(f"scan_{side}", g.plinth + 180, top - g.beam_clearance, g.plinth + 180, 40.0, 80.0, 4.0, 1600)
        # NEMA17 + GT2 20T belt
        axes[f"shuttle_{side}"] = AxisConfig(f"shuttle_{side}", -235.0, 235.0, -235.0, 80.0, 400.0, 40.0, 3200)
    return axes


@dataclass(frozen=True)
class Speeds:
    """Motion speeds in mm/s. The slow ones are what keeps bees alive."""

    travel: float = 15.0
    peel: float = 1.0
    peel_height: float = 6.0
    landing: float = 2.0  # last 30 mm before the stack lands on the rim
    landing_zone: float = 30.0
    frame_up: float = 40.0  # after the nudge there is space on one side
    frame_down: float = 35.0
    frame_landing: float = 3.0  # last 20 mm before a frame's ears touch the rests
    frame_landing_zone: float = 20.0
    hook_lower: float = 8.0  # hook plate descending to just above the top bars
    shuttle: float = 40.0
    shuttle_fine: float = 10.0
    frame_nudge: float = 10.0  # push toward the working gap before lifting
    frame_peel: float = 2.0


@dataclass(frozen=True)
class Servos:
    """Servo angles in degrees."""

    fork_stowed: float = 0.0
    fork_engaged: float = 90.0
    hook_stowed: float = 0.0
    hook_engaged: float = 90.0


@dataclass(frozen=True)
class Limits:
    max_load_per_side_kg: float = 45.0  # stop lifting above this
    peel_breakaway_kg: float = 60.0  # peak allowed while cracking propolis
    contact_drop_ratio: float = 0.7  # load falling below this share of the lifted weight = contact
    rim_check_retries: int = 3
    rim_check_wait_s: float = 20.0


@dataclass(frozen=True)
class RobotConfig:
    geometry: HiveGeometry = field(default_factory=HiveGeometry)
    speeds: Speeds = field(default_factory=Speeds)
    servos: Servos = field(default_factory=Servos)
    limits: Limits = field(default_factory=Limits)

    @property
    def axes(self) -> Dict[str, AxisConfig]:
        return default_axes(self.geometry)
