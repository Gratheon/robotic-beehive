"""Command line.

  python3 -m hivebot plan --box 1            dry run on the simulator, prints every move
  python3 -m hivebot inspect --box 1         real run through Klipper/Moonraker
  python3 -m hivebot home
  python3 -m hivebot bench-move lift_left 700   one axis on the Jetson-GPIO bench rig
"""
from __future__ import annotations

import argparse
import logging
import sys

from .config import RobotConfig
from .motion.base import ALL_AXES
from .sequences import Inspector


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="hivebot")
    sub = ap.add_subparsers(dest="cmd", required=True)
    plan = sub.add_parser("plan", help="simulate an inspection and print the moves")
    plan.add_argument("--box", type=int, default=1)
    plan.add_argument("--quiet", action="store_true")
    ins = sub.add_parser("inspect", help="inspect one box on the real robot")
    ins.add_argument("--box", type=int, default=1)
    ins.add_argument("--moonraker", default="http://127.0.0.1:7125")
    home = sub.add_parser("home")
    home.add_argument("--moonraker", default="http://127.0.0.1:7125")
    bench = sub.add_parser("bench-move", help="move one axis on the Jetson-GPIO bench rig")
    bench.add_argument("axis", choices=ALL_AXES)
    bench.add_argument("position", type=float)
    bench.add_argument("--speed", type=float, default=10.0)
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    cfg = RobotConfig()

    if args.cmd == "plan":
        from .motion.sim import SimBackend

        sim = SimBackend(cfg)
        insp = Inspector(sim, cfg)
        insp.home()
        t0 = sim.clock
        report = insp.inspect(args.box)
        if not args.quiet:
            for entry in sim.log:
                print(*entry)
        print(f"\nbox {args.box}: {len(report.frames)} frames, stack above weighs {report.lifted_kg:.1f} kg, "
              f"visit takes {(sim.clock - t0) / 60:.1f} min (simulated)")
        for w in report.warnings:
            print("warning:", w)
        return 0

    if args.cmd in ("inspect", "home"):
        from .motion.klipper import KlipperBackend

        backend = KlipperBackend(args.moonraker, cfg)
        insp = Inspector(backend, cfg)
        insp.home()
        if args.cmd == "inspect":
            report = insp.inspect(args.box)
            print(f"box {args.box}: {len(report.frames)} frames captured")
        return 0

    if args.cmd == "bench-move":
        from .motion.jetson_gpio import JetsonGPIOBackend

        backend = JetsonGPIOBackend(config=cfg)
        try:
            backend.move({args.axis: args.position}, args.speed)
        finally:
            backend.close()
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
