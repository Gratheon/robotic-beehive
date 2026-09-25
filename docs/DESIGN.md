# Robotic Beehive: design (concept v3)

A static, weatherproof cabinet around a standard vertical hive. The robot inspects one box at a time:

1. It raises everything above that box by 400 mm, cracking the propolis seal one edge at a time.
2. It lifts each frame straight up, carries it to a photo spot in the middle of the box where four cameras shoot both faces straight on, then sets it down in the free gap next to it.
3. It closes the hive again so that contact rolls across the rim.

Everything moving lives outside the bee space. The only changes to the hive itself are steel cleats on the boxes and two steel pins per frame.

- **3D model:** `model/index.html` (interactive, animated) and `model/hive-tower.glb` (with the `inspection` animation clip)
- **Wiring:** [WIRING.md](WIRING.md) and [wiring.svg](wiring.svg)
- **Control code:** `hivebot/` (Python) and `firmware/klipper/hivebot.cfg`

## 1. Why this layout

The hard problem is moving frames without killing bees. Frames are glued with propolis, the queen can be on any frame, and brood chills if it stays open too long. Three decisions follow from that:

| Decision | Why |
|---|---|
| **Lift frames straight up, never out sideways** | Bees that fall off a frame drop straight back into their own box, not onto the ground. The frame never tilts: warm, heavy comb breaks when it is not vertical. |
| **Split the stack instead of reaching in from the side** | Works with standard boxes. Side-opening boxes need custom joinery, and bees propolise every door shut. |
| **Put the hive in a cabinet** | Rain, wind and sun stay out. The air around an open box can be pre-warmed to 25 °C, so inspections are safe on 10–15 °C days. Disturbed bees stay inside instead of bothering neighbours, which matters for urban and corporate hives. The mechanics stay clean, and it can look like furniture instead of a pile of boxes. |

Two further choices do most of the bee-safety work:

- **Independent left/right lift beams.** Raising one edge 6 mm while the other stays down acts like a hive tool. It cracks the propolis seal with a fraction of the force a straight pull needs. Closing in the reverse order (left edge lands first, then right) makes the contact line roll across the rim and push bees aside.
- **The working gap.** Each box runs with one frame's worth of free space: 10 frames at 37.5 mm pitch leave a 25 mm gap. The robot works like a beekeeper:
  1. It pushes the frame next to the gap 10 mm into the gap, which breaks burr comb before lifting.
  2. It lifts the frame and photographs it.
  3. It sets the frame down in the gap. The gap has now moved one frame along.
  
  Lifting a frame straight up out of a full box would roll bees between the combs. That is how queens get killed.

## 2. Mechanism

Coordinates follow the model: X left/right, Y up, Z front (+, entrance) / back (−).

| Part | Specification |
|---|---|
| Skeleton | 4 corner posts of 22 mm aluminium extrusion, plinth ring, crown ring. Footprint 810 × 666 mm, height ≈1.99 m for 3 boxes (+285 mm per extra box). |
| Linear guides | MGN12 rail on the inner face of each post. Each post carries one lift-beam carriage and one scan-beam carriage. V-wheels on V-slot extrusion also work if the extrusion allows it. |
| Lift beams (L, R) | NEMA23 + DM542 + TR16×4 lead screw hung from the crown (the screw works in tension). A servo-turned fork shaft carries two fingers that swing under the box cleats. Bar load cells sit in the fork bearing blocks. |
| Scan beams (L, R) | Same drive as the lift beams. Each carries a belt-driven **shuttle** (NEMA17 + GT2) holding the frame hook and an inductive pin sensor, plus two frame cameras on arms (one in front of the box, one behind). |
| Frame cameras | 4 × 12 MP (IMX477 class, ~6 mm lens), portrait, at z = ±265 mm: in the 40 mm between box and cladding, so they never pass over the hive. Each looks straight at the comb from 240 mm and covers one half of a face (x = ±90 mm). A ring strobe with crossed polarisers removes glare from nectar and capping. See *Seeing into the cells* below. |
| Hook | A servo swings an L-shaped hook over the box wall. Its H-shaped tip plate has two back-to-back slots, so it can push a frame toward the gap in either direction. It slides sideways around the pin neck and never presses down on the top bars. Once the frame hangs, the pin head drops into a 1.5 mm pocket, so a lifted frame can be carried either way without sliding out. |
| Box changes | Stainless 30×30 angle cleat on the left and right walls of every box and the lid, 25 mm above the box bottom. They double as hand grips. |
| Frame changes | Two stainless M5 shoulder screws on each top bar ear (neck 2.5 mm, head 2.5 mm; they fit inside the bee space) and an ArUco tag on the end bar. |
| Bottom board | 150 mm tall screened "varroa sump": white tray, fixed wide-angle camera, no moving parts. |

**Seeing into the cells.** A cell is 5.4 mm wide and about 11 mm deep, and it slopes up 9–13°. Eggs lie at the bottom, so the camera must look nearly down the cell axis.

- *Before (v3.0).* Cameras hung beside the frame's ends and looked along the face. The far half of the comb was seen up to 77° off-axis, which shows cell walls, not contents.
- *Now.* The cameras face the comb. The worst corner is about 35° off-axis and most of the comb is within 25°, so the camera sees to the bottom of the cell.
- *Low mount.* The cameras sit 10 mm below comb centre. Lower rows, whose cells slope away from the camera, are then seen more nearly along their axis.
- *Same photo spot.* Every frame is photographed at the same place (centred between the cameras). Distance, focus and mm-per-pixel are identical for every frame, which makes cell counts and sizes comparable over time. At 12 MP a cell is about 60 px across and an egg about 18 px long.
- *Cost.* Carrying the frame to the spot and back adds about 5 s per frame.
- *Entrance.* Because the front cameras pass the entrance on their way down, the entrance is two 120 mm tunnels, one either side of the cameras' path.

**Why TR16×4 lead screws everywhere.** Each screw hangs from a thrust bearing in the crown, so the load puts it in tension and it cannot buckle.

- *Self-locking.* The lead angle is about 4.5°, so the stack or a frame stays put on power loss. No brakes needed.
- *Speed.* At 1.5 m length the whip limit is about 1000 rpm, which allows 40 mm/s frame lifts. The first choice, TR10×2, would have needed 1500 rpm, above its whip limit.
- *Torque.* Lifting 80 kg of honey supers needs ≈0.8 N·m per side, within a NEMA23's range at 24 V.

**Load limits.** The software stops a lift above 45 kg per side (90 kg of boxes above the target) and a peel above 60 kg. Heavy honey supers should be harvested before the stack outgrows that.

## 3. Inspection sequence

This is the sequence in `hivebot/sequences.py`. The simulator in `hivebot/motion/sim.py` enforces every rule in brackets.

1. **Pre-flight check** (`safety.evaluate`):
   - Outside ≥15 °C, or ≥10 °C with the cabinet pre-warmed to 25 °C.
   - No rain, wind below 8 m/s, between 10:00 and 16:00 (foragers are out).
   - At least 7 days since the last visit, battery OK, door closed, E-stop released.
2. Red work light on. Bees barely see light above ~620 nm.
3. The lift beams move to 8 mm below the cleats of the box above the target box. The forks swing in. *(A fork may only rotate at that height.)*
4. **Peel.** The left edge rises 6 mm at 1 mm/s, then the right edge. The load cells show the breakaway force and the weight of everything above, so the robot learns the weight of each box for free.
5. The stack rises 400 mm in 50 mm stages, checking the load after each stage. *(The stack may tilt at most 35 mm.)*
6. The scan beams rise to the rim. The pin sensors step across each expected pin position and re-locate every frame to ±1 mm.
7. **Each frame** (about 40 s):
   1. The hook lands 26 mm beside the pin at 8 mm/s. *(It may not land on a pin head.)*
   2. It slides onto the pin neck and pushes the frame 10 mm toward the gap.
   3. It peels the ears 2 mm, one end at a time, then lifts 300 mm at 40 mm/s. *(The frame top must stay 40 mm below the bees hanging under the raised stack.)*
   4. Carry the frame to the photo spot (middle of the box). Strobe and capture: 4 cameras, both faces straight on, each face in two halves.
   5. The frame moves over the gap. It is lowered at 35 mm/s, and the last 20 mm at 3 mm/s. *(Checked.)*
   6. The hook slides off.
8. The scan beams park. The stack lowers to 30 mm above the rim.
9. **Rim check.** A camera counts bees on the contact edges. If it sees any, the robot waits 20 s, up to 3 times, then closes anyway: a slow rolling close beats a chilled box.
10. **Rolling close** in 2 mm steps at 2 mm/s. *(Landing faster is refused.)* If the load cells report contact more than 5 mm above the rim, the robot stops, backs off 20 mm and raises an alarm. That catches fingers, tools and fallen comb.
11. Forks out, beams park, photos upload.

**Timing (simulated):** ≈45 s per frame. A box is open for about 10 minutes. A full visit takes 9.5–12 minutes depending on which box. Run `python3 -m hivebot plan --box 1` to see every move with its duration. Only the target box is ever open; the rest of the stack stays closed and warm.

## 4. Bee welfare checklist

- No smoke. Bees stay calm in darkness and under red light.
- Short white strobe flashes, synced to the exposure, instead of constant bright light.
- Quiet motion: StealthChop on the shuttles, S-curve ramps, rubber pads between the hive and the plinth deck. Bees feel vibration in the wood far more than they hear airborne sound.
- Frames always vertical, gentle accelerations (≤80 mm/s²).
- Every slow zone is enforced in the simulator, so a code change that speeds up a landing fails the tests.
- Only one box open at a time, with open time budgeted and measured.
- Bees that drop fall back into their own box: frames and the stack are only ever directly above it.
- The cabinet keeps robbing bees, wasps and hornets away from the open box.
- The two entrance tunnels keep the flight path clear of every moving part. The robot's service side is the back.

## 5. Weather, materials, ecology

| Area | Choice |
|---|---|
| Cladding | Vertical thermally-modified pine boards over a wood-fibre insulation board. No chemical wood preservatives, which harm bees. The plinth skirt is yakisugi (charred) wood against splash and rot. |
| Roof | Ventilated double roof, 60 mm overhang, drip edges, sloping down to the south. The 100 W solar panel sits on it. The air gap keeps summer heat off the hive. |
| Crown bay | Motors and electronics in a dry bay above the hive. Warm air leaves through the hex vent band (insect mesh behind). A Gore-type breather vent stops condensation. |
| Corrosion | Aluminium, stainless fasteners (nylon washers against aluminium), brass lead-screw nuts, dry PTFE lubrication. No grease, which collects debris and bees. |
| Hive humidity | Box seams stay closed except during a visit, so moist hive air does not reach the mechanics. The cabinet vents passively top and bottom. |
| Winter | The insulated cabinet cuts heat loss and wind chill, which improves overwintering. The robot does not inspect below 10 °C. It keeps logging weight and temperature. |
| End of life | Aluminium, steel, wood and one electronics bay, all separable with screws. No glued composites. |

## 6. Maintenance and human safety

- **Service door** (full height, front). A reed interlock cuts motor power when it opens. Fold the forks and the hive can be worked by hand like any other hive, using the cleats as handles.
- **E-stop** on the right side. It cuts only the 24 V motor rail; the computers keep logging.
- **Watchdog.** The ESP32 supervisor holds relay K1 closed only while the Jetson sends heartbeats, so a hung computer means no motor power.
- **Nothing can drop.** The lead screws are self-locking, so power loss or an E-stop leaves the stack and frames where they are.
- **Pinch points.** Forks and hooks are painted yellow. Contact detection on closing stops on anything firmer than bees.
- **Modular.** Motors connect with GX16 plugs. Each beam unbolts from its carriages. The crown lid lifts off. All boards are standard and replaceable.
- **Service UI.** Klipper's web UI (Mainsail/Fluidd) jogs any axis for maintenance. `main.py` remains as the bench keyboard jog.

## 7. Compute, power, connectivity

| Unit | Role |
|---|---|
| Jetson Orin Nano | Inspection brain: runs `hivebot`, Klipper host and Moonraker, the cameras, and the detection models (bees, queen, brood, varroa). Powered only for inspections. |
| BTT Octopus + Klipper | Real-time step generation, homing, servos, heater and LED outputs. Python on Linux cannot time step pulses reliably, and the pulse jitter in `main.py` is that problem. |
| ESP32 + LoRa (e.g. Heltec V3) | Always-on supervisor at ~0.2 W. Handles weight, temperature, humidity, LoRa telemetry, waking the Jetson and the watchdog. |
| Jetson Nano (old) | Entrance Observer at the entrance tunnel: counts bees in and out, flags hornets and robbing. |

**Energy per day:**

| Load | Energy |
|---|---|
| Supervisor | ≈5 Wh |
| Weekly inspection (Jetson 15 W for 15 min, motors ≈50 W average for 12 min) | ≈15 Wh, plus up to 20 Wh of heater on cool days |
| Entrance Observer running in daylight | 60–120 Wh, the largest consumer |

A 100 W panel gives roughly 300–400 Wh/day in an Estonian summer and far less in winter. So off-grid, the Entrance Observer runs in the season and sleeps in winter.

**Antennas.** All antennas sit in one RF-transparent fin on the roof ridge, above everything metal:

- LTE MIMO and GNSS go to a USB modem.
- LoRa 868 MHz goes to the ESP32.
- Wi-Fi goes to the Orin's M.2 card.

Coax runs are short (crown to roof, under 0.5 m) with surge arrestors where they enter. The frame is bonded to an earth rod.

## 8. From static tower to mobile robot

The skeleton is designed as a separable **yoke**: posts, beams and crown are one unit. The hive side is a **dock**: plinth, bottom board, cleated boxes. Two steps later:

1. **Shared yoke on a trolley.** The yoke unbolts from one dock and bolts onto the next. Three docking cones in V-grooves set it back within ±0.5 mm, so frame positions and cleat heights stay valid.
2. **Wheeled yoke (robotic apiary).** The same yoke on a skid-steer base, open at the back. It drives over a dock from behind, away from the flight path, lowers onto the cones and runs the same `hivebot` sequence. Each dock then needs only a light weather hood with a rear door. The expensive part (yoke, motors, compute) is shared across about 10 hives.

This is why the model keeps all motors and electronics on the yoke, and why frame positions are stored per hive and re-checked by the pin sensors on every visit.

## 9. Bill of materials (new parts, EUR, rough 2026 prices)

Parts you already have (Jetsons, 24 V PSU, extrusions, NEMA23s, DM542s) are counted at €0 where noted.

| Group | Items | € |
|---|---|---|
| Motion | MGN12 rails ×4 with carriages 120 · TR16×4 screws ×4 with brass nuts 90 · BK/BF12 bearing sets ×4 60 · couplings 20 · NEMA17 ×2 + GT2 belts and pulleys 40 · servos ×4 (waterproof metal gear) 60 · fork shafts, bearings, 2 load cells + HX711 35 · extra NEMA23/DM542 if short 0–130 · brackets, T-nuts, stainless fasteners 40 | 465–595 |
| Hive kit | Stainless cleats for 4 boxes + lid 30 · frame pins (80) 20 · ArUco tags 5 | 55 |
| Electronics | BTT Octopus 70 · NVMe 256 GB 30 · 12 MP cameras ×4 (IMX477 class, USB or CSI mux) 240 · polariser film 15 · varroa camera 25 · LED ring strobes + red strip 30 · ESP32 LoRa 25 · LTE modem 45 · antennas, bulkheads, surge arrestors 50 · DC-DC ×3 35 · E-stop, reed switch, relays, fuses, GX16, glands 60 · endstops + inductive sensors 20 · climate sensors 15 · cable chains and cable 40 · PTC heater 20 · sealed PSU box 20 | 780 |
| Cabinet | Thermo-pine cladding ~6 m² 120 · wood-fibre board 40 · plywood backers, roof board 60 · charred skirt 25 · polycarbonate window 15 · hinges, lock, EPDM seals, insect mesh, hex vent panel 60 · levelling feet 20 · roof flashing 20 | 360 |
| **Total** | | **≈1,660–1,790** |
| Solar option | 100 W panel 70 · 24 V MPPT 50 · LiFePO4 24 V 20 Ah 200 | 320 |

Ways to cut cost:
- One centred camera per face instead of two (−€120; the comb edges are then seen at up to ~40°, still far better than v3.0).
- V-wheels instead of rails (−€90).
- Painted plywood instead of thermo-pine (−€60).
- Skip the heater and inspect only on warm days (−€20).

## 10. Risks and open questions to test first

1. **Propolis breakaway force** between boxes after a full season. Measure it with a luggage scale on real hives. The 60 kg peel limit is a guess.
2. **Burr comb between boxes.** Bees build comb across the seam, and lifting tears it. The rim camera should detect it; the robot may need a heated wire or a thin blade swept along the seam before the peel.
3. **Pin fit.** A 6 mm slot on a 5 mm neck needs frames positioned to ±1 mm. The sensor search gives that, but swollen or warped frames need testing.
4. **Bees festooning under the raised stack.** The 40 mm clearance above a lifted frame should be checked against real clusters.
5. **Condensation** in the cabinet in autumn. Log humidity in the crown and near the rails.
6. **Mice and wax moths** in the plinth and cabinet. Use mesh on every vent and a mouse guard at the entrance tunnel.

## 11. More ideas for bees and beekeepers

- **Per-box weight for free.** Lifting at different seams tells the robot how heavy each box is. It can report honey flow and time the harvest.
- **Frame identity over time.** ArUco tags plus the Gratheon web app's frame-side history give a time-lapse of each comb face: brood pattern, queen laying rate, honey arc.
- **Queen-safe mode.** If the detector sees the queen on a frame, set that frame down slower and skip the nudge.
- **Motorised entrance reducer** (already in the model): closes against robbing or hornets, narrows in wind and winter, closes for transport.
- **Varroa sump camera:** a daily mite-drop count with no drawer to pull. Combined with frame photos it gives a treatment trigger.
- **Heating and ventilation hooks.** The cabinet heater and crown fan are already on the motion board, ready for the Hive heating and Ventilation control ideas.
- **Visitor window with shutter** for school groups and corporate sponsorship programmes, closed by default so the hive stays dark.
- **Feeder port** through the lid for a syrup line, filled from outside the cabinet.
