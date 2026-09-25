### gratheon/robotic-beehive
[Gratheon Robotic beehive](https://gratheon.com/about/products/robotic_beehive/) is a project to build a robotic beehive that inspects the colony without harming it.

#### Hive Tower (concept v3)
A weatherproof cabinet around a standard vertical hive. To inspect a box, the robot:
1. peels the stack above it apart one edge at a time and lifts it 400 mm;
2. lifts each frame straight up, photographs both faces straight on at a fixed photo spot, then sets it down in the free gap beside it, like a beekeeper working through a box;
3. closes the hive with a rolling landing so bees are pushed aside, not crushed.

- **Design, bee welfare, weather, BOM, mobile roadmap:** [docs/DESIGN.md](docs/DESIGN.md)
- **Wiring:** [docs/WIRING.md](docs/WIRING.md)
- **3D model:** `model/index.html` (interactive, animated, opens from disk) and `model/hive-tower.glb` (the `inspection` animation clip is baked in)
- **Control code:** `hivebot/` (Python), plus a Klipper config in `firmware/klipper/hivebot.cfg`

#### View the model
Open `model/index.html` directly in a browser. It is self-contained; only three.js and fonts load from a CDN. Point at any part to see what it is and why it is there.

To change the model, edit `model/hive-model.js` (geometry, animation) or `model/viewer.template.html` (page), then rebuild:
```bash
cd model && npm install   # three.js, first time only
npm run build             # regenerates index.html and hive-tower.glb
```

#### Run the controller
```bash
python3 -m pytest                    # sequences + bee-safety rules on the simulator
python3 -m hivebot plan --box 1      # dry run: every move, weights, visit time
python3 -m hivebot inspect --box 1   # real robot (Klipper + Moonraker on the Jetson)
python3 -m hivebot bench-move lift_left 700   # bench rig: DM542 on Jetson GPIO
```
The simulator refuses anything a careful beekeeper would refuse, such as landing the stack too fast or lifting a frame into bees hanging under the raised boxes. A code change that makes the robot rougher fails the tests.

#### Components
- NVIDIA Jetson Orin Nano: inspection, cameras, AI models, Klipper host
- BTT Octopus motion board running Klipper firmware
- 4 × NEMA23 on TR16×4 lead screws with DM542 drivers (2 lift beams, 2 scan beams)
- 2 × NEMA17 belt shuttles, 4 servos (forks, hooks)
- 4 × 12 MP frame cameras facing the comb straight on, 2 rim cameras, varroa sump camera
- ESP32 + LoRa always-on supervisor with load cells and climate sensors
- Jetson Nano as the Entrance Observer
- 24 V power supply, optional solar + LiFePO4
- 22 mm aluminium extrusion skeleton

`main.py` is the original keyboard jog for a single DM542 on Jetson GPIO. The FreeCAD models of earlier concepts are in `CAD-model/`.

![](https://gratheon.com/assets/images/Screenshot%202025-02-25%20at%2021.42.01-e92a46ed6f800420006ff91f3bb34f88.png)
