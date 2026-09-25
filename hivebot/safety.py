"""When is it OK to open the hive?

The robot decides on its own, so it must be at least as conservative as a
good beekeeper: warm, dry, calm, around midday when foragers are out, and
not too often.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class Conditions:
    now: datetime
    outside_c: float
    cabinet_c: float
    raining: bool = False
    wind_ms: float = 0.0
    last_inspection: Optional[datetime] = None
    door_closed: bool = True
    estop_ok: bool = True
    battery_pct: float = 100.0


@dataclass(frozen=True)
class Policy:
    min_outside_c: float = 15.0  # open without help above this
    min_outside_with_heater_c: float = 10.0  # open only after pre-warming the cabinet
    cabinet_target_c: float = 25.0
    max_wind_ms: float = 8.0
    hours: Tuple[int, int] = (10, 16)
    min_days_between: float = 7.0
    min_battery_pct: float = 40.0
    heater: bool = True


@dataclass
class Decision:
    go: bool
    preheat: bool = False
    reasons: List[str] = field(default_factory=list)


def evaluate(c: Conditions, p: Policy = Policy()) -> Decision:
    reasons = []
    if not c.estop_ok:
        reasons.append("emergency stop is pressed")
    if not c.door_closed:
        reasons.append("service door is open")
    if c.raining:
        reasons.append("raining")
    if c.wind_ms > p.max_wind_ms:
        reasons.append(f"wind {c.wind_ms:.0f} m/s > {p.max_wind_ms:.0f} m/s")
    if not p.hours[0] <= c.now.hour < p.hours[1]:
        reasons.append(f"outside the {p.hours[0]}:00–{p.hours[1]}:00 window")
    if c.last_inspection and c.now - c.last_inspection < timedelta(days=p.min_days_between):
        reasons.append(f"last inspection less than {p.min_days_between:.0f} days ago")
    if c.battery_pct < p.min_battery_pct:
        reasons.append(f"battery {c.battery_pct:.0f}% < {p.min_battery_pct:.0f}%")

    preheat = False
    if c.outside_c < p.min_outside_c:
        if p.heater and c.outside_c >= p.min_outside_with_heater_c:
            preheat = c.cabinet_c < p.cabinet_target_c
        else:
            reasons.append(f"too cold outside ({c.outside_c:.0f} °C)")
    return Decision(go=not reasons, preheat=preheat, reasons=reasons)
