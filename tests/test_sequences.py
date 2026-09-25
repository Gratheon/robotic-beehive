import json
import shutil
import subprocess
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from hivebot.capture import NullCapture
from hivebot.config import RobotConfig
from hivebot.motion.base import MotionError
from hivebot.motion.sim import SimBackend, SimHive
from hivebot.safety import Conditions, evaluate
from hivebot.sequences import InspectionAborted, Inspector

ROOT = Path(__file__).resolve().parents[1]


def make(config=None, hive=None):
    cfg = config or RobotConfig()
    sim = SimBackend(cfg, hive)
    cam = NullCapture()
    insp = Inspector(sim, cfg, capture=cam)
    insp.home()
    return sim, insp, cam


def assert_closed(sim):
    assert sim.engaged == {"left": None, "right": None}
    assert sim.lifted("left") == 0 and sim.lifted("right") == 0
    assert sim.hooked is None


@pytest.mark.parametrize("box", [0, 1, 2])
def test_full_inspection_every_box(box):
    sim, insp, cam = make()
    before = list(sim.frames[box])
    report = insp.inspect(box)
    assert len(report.frames) == 10
    assert len(cam.shots) == 10
    assert_closed(sim)
    assert sim.outputs["red_light"] == 0.0
    # every frame moved one working-gap width toward the back wall
    gap = sim.g.gap_width
    assert sim.frames[box] == pytest.approx([z - gap for z in before])
    # other boxes untouched
    for k in range(sim.g.boxes):
        if k != box:
            assert sim.frames[k] == pytest.approx(sim.g.frame_z())


def test_every_frame_is_photographed_at_the_photo_spot():
    class SpyCapture(NullCapture):
        def __init__(self, sim):
            super().__init__()
            self.sim = sim

        def capture(self, meta):
            k, i = meta["box"], self.sim.hooked
            self.shots.append((self.sim.frames[k][i], self.sim.lifted("left")))
            return []

    cfg = RobotConfig()
    sim = SimBackend(cfg)
    cam = SpyCapture(sim)
    insp = Inspector(sim, cfg, capture=cam)
    insp.home()
    insp.inspect(1)
    assert len(cam.shots) == 10
    assert all(z == pytest.approx(cfg.geometry.photo_z) for z, _ in cam.shots)


def test_second_visit_walks_the_gap_back():
    sim, insp, _ = make()
    insp.inspect(1)
    insp.inspect(1)
    assert sim.frames[1] == pytest.approx(sim.g.frame_z())
    assert_closed(sim)


def test_peel_lifts_one_edge_first():
    sim, insp, _ = make()
    insp.open_box(1)
    c = sim.g.cleat(2)
    lifts = [e for e in sim.log if e[0] == "move" and any(a.startswith("lift") and v > c for a, v in e[1].items())]
    assert set(lifts[0][1]) == {"lift_left"}
    assert set(lifts[1][1]) == {"lift_right"}
    assert lifts[0][2] <= sim.cfg.speeds.peel


def test_reports_weight_above_the_box():
    hive = SimHive(box_kg=[30, 25, 20], lid_kg=5)
    sim, insp, _ = make(hive=hive)
    assert insp.open_box(0) == pytest.approx(25 + 20 + 5)


def test_obstruction_on_the_rim_stops_closing():
    sim, insp, _ = make(hive=SimHive(obstruction=("right", RobotConfig().geometry.rim(1) + 15)))
    insp.open_box(1)
    with pytest.raises(InspectionAborted, match="right edge touched"):
        insp.close_box(1, check_rim=False)
    assert sim.lifted("right") > 15  # backed off, not pressing on it


def test_rim_check_waits_for_bees():
    class Bees:
        def __init__(self):
            self.counts = [4, 1, 0]

        def bees_on_rim(self):
            return self.counts.pop(0)

    cfg = RobotConfig()
    sim = SimBackend(cfg)
    insp = Inspector(sim, cfg, rim_check=Bees())
    insp.home()
    insp.open_box(1)
    assert insp.close_box(1) == []
    assert sum(1 for e in sim.log if e[0] == "wait") == 2


def test_sim_refuses_fast_landing():
    sim, insp, _ = make()
    insp.open_box(1)
    c = sim.g.cleat(2)
    sim.move({"lift_left": c + 30, "lift_right": c + 30}, 15)
    with pytest.raises(MotionError, match="landing"):
        sim.move({"lift_left": c, "lift_right": c}, 15)


def test_frame_never_lifted_into_hanging_bees():
    cfg = RobotConfig()
    cfg = replace(cfg, geometry=replace(cfg.geometry, bee_clearance=120))
    sim, insp, _ = make(cfg)
    with pytest.raises(InspectionAborted, match="frame stuck"):
        insp.inspect(1)
    assert ("estop",) in sim.log


def test_hook_cannot_swing_into_a_closed_box():
    sim, insp, _ = make()
    with pytest.raises(MotionError):
        sim.set_servo("hook_left", 90)


def test_box_open_time_is_short():
    sim, insp, _ = make()
    insp.open_box(1)
    t0 = sim.clock
    insp.scan_box(1, __import__("hivebot.sequences").sequences.Report(box=1))
    insp.close_box(1)
    open_minutes = (sim.clock - t0) / 60
    print(f"box open for {open_minutes:.1f} min")
    assert open_minutes < 10  # regression guard; see docs/DESIGN.md for the budget


def test_weather_gate():
    noon = datetime(2026, 6, 1, 12)
    assert evaluate(Conditions(noon, outside_c=20, cabinet_c=20)).go
    cold = evaluate(Conditions(noon, outside_c=12, cabinet_c=15))
    assert cold.go and cold.preheat
    assert not evaluate(Conditions(noon, outside_c=8, cabinet_c=15)).go
    assert not evaluate(Conditions(noon, outside_c=20, cabinet_c=20, raining=True)).go
    assert not evaluate(Conditions(noon.replace(hour=19), outside_c=20, cabinet_c=20)).go
    assert not evaluate(Conditions(noon, outside_c=20, cabinet_c=20, last_inspection=noon - timedelta(days=2))).go


def test_inspect_refuses_in_rain():
    sim, insp, _ = make()
    with pytest.raises(InspectionAborted, match="raining"):
        insp.inspect(1, Conditions(datetime(2026, 6, 1, 12), outside_c=20, cabinet_c=20, raining=True))


@pytest.mark.skipif(not shutil.which("node") or not (ROOT / "model/node_modules/three").exists(), reason="needs node + model deps")
def test_model_and_controller_share_geometry():
    script = (
        "import('./hive-model.js').then(m => { const d = m.derive(m.DEFAULTS);"
        "console.log(JSON.stringify({engage: d.engage, cleat2: d.cleatY(2), liftMax: d.liftMax, frameZ: d.frameZ, gap: d.gapWidth,"
        "liftPark: d.liftPark, scanPark: d.scanPark})) })"
    )
    out = subprocess.run(["node", "--input-type=module", "-e", script], cwd=ROOT / "model", capture_output=True, text=True, check=True)
    js = json.loads(out.stdout)
    g = RobotConfig().geometry
    assert js["engage"] == pytest.approx(g.engage(1))
    assert js["cleat2"] == pytest.approx(g.cleat(2))
    assert js["liftMax"] == pytest.approx(g.cleat(g.boxes) + g.gap)
    assert js["frameZ"] == pytest.approx(g.frame_z())
    assert js["gap"] == pytest.approx(g.gap_width)
    assert js["liftPark"] == pytest.approx(g.lift_park)
    assert js["scanPark"] == pytest.approx(g.scan_park)


@pytest.mark.skipif(not shutil.which("node") or not (ROOT / "model/node_modules/esbuild").exists(), reason="needs node + model deps")
def test_viewer_is_rebuilt(tmp_path):
    """index.html is generated; fail if someone edited the sources without `npm run build`."""
    before = (ROOT / "model/index.html").read_text()
    subprocess.run(["node", "build-viewer.mjs"], cwd=ROOT / "model", check=True, capture_output=True)
    assert (ROOT / "model/index.html").read_text() == before, "run `npm run build` in model/"
