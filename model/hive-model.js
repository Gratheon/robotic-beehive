// Gratheon "Hive Tower" — parametric model of a static robotic beehive.
// Single source of truth for both the browser viewer (index.html) and the
// GLB exporter (export-glb.mjs). All dimensions are in millimetres; the scene
// is built in metres (glTF convention).
//
// Axes: X = left/right (frame length, frame ears sit on the left/right walls)
//       Y = up
//       Z = front(+)/back(-) (frames are stacked along Z, entrance faces +Z)

import * as THREE from 'three';

const MM = 0.001;

export const DEFAULTS = {
  boxes: 3, // hive bodies in the stack
  inspectBox: 1, // 0 = bottom box
  box: { w: 506, d: 450, h: 285, wall: 25 }, // Estonian hive body (outer)
  frame: { topBar: 448, width: 410, height: 279, count: 10, pitch: 37.5, pinX: 200 },
  plinth: 200, // cabinet base, holds PSU / battery / Jetson Nano
  bottomBoard: 150, // screened floor + varroa sump camera
  lid: 80, // insulated inner cover
  cleatUnderside: 25, // cleat lifting face, measured from box bottom
  gap: 400, // how far the upper stack is raised to open a box
  frameLift: 300, // how far a frame is raised above its rest position
  post: { x: 372, z: 302 }, // 22 mm extrusion corner posts (centre)
  crown: 180, // electronics + motor bay on top
};

// ---------------------------------------------------------------------------
// Part descriptions (shown on hover in the viewer, exported as glTF extras)
// ---------------------------------------------------------------------------
export const PARTS = {
  post: ['Corner post', '22 mm aluminium extrusion, 4 corners. Each post carries a linear rail on its inner face for the lift beam and scan beam carriages.'],
  plinth: ['Plinth', 'Base of the cabinet, about 200 mm high. Holds the 24 V PSU, the optional LiFePO4 battery, the MPPT charger and the Jetson Nano entrance-observer computer. Stands on levelling feet over a gravel pad.'],
  feet: ['Levelling feet', 'M12 stainless feet with rubber pads. They decouple the cabinet from the ground and let you level the stack so frames hang plumb.'],
  crown: ['Crown bay', 'Dry service bay on top of the cabinet. Lift motors hang the lead screws from here, so the screws work in tension and cannot buckle. All electronics sit here too, with short antenna runs.'],
  liftBeam: ['Lift beam (×2)', 'Left and right beams on independent NEMA23 + TR16×4 lead screws. The screws are self-locking, so a power loss never drops the stack. Running the two sides at different heights lets the robot peel a propolis-glued box apart one edge at a time.'],
  fork: ['Fork fingers', 'A servo turns a steel shaft 90° to swing two fingers under the box cleats. They stay folded down whenever they are not lifting. Painted yellow as a pinch-hazard colour.'],
  loadcell: ['Load cell', 'A bar load cell in each fork bearing block. It weighs the lifted part of the stack (per-box honey weight for free) and detects collisions: if the load drops before the expected landing height, the robot stops.'],
  cleat: ['Lift cleat', 'Stainless 30×30 angle screwed to both sides of every box and the lid. The forks lift on it. It also works as a hand grip for manual beekeeping.'],
  scanBeam: ['Scan beam (×2)', 'Second pair of beams, also NEMA23 + TR16×4 lead screws (self-locking, so a frame never drops). They raise the selected frame straight up out of its box, so bees that drop off fall back into their own box.'],
  shuttle: ['Frame shuttle', 'Runs front/back along the scan beam on a GT2 belt. It carries the hook, two cameras, the strobe LEDs and an inductive sensor that finds the steel frame pins.'],
  belt: ['Shuttle drive', 'NEMA17 + GT2 belt, TMC2209 in StealthChop mode, so it is nearly silent. Bees feel substrate vibration strongly.'],
  hook: ['Frame hook', 'A servo swings an L-shaped hook over the box wall. The slotted tip slides sideways under the frame pin, so it never presses down onto bees.'],
  camera: ['Frame camera (×4)', 'Two per shuttle, aimed at the frame faces from both ends. Each face is seen by two cameras. The frame is flat, so a homography rectifies the images into one straight-on photo per side.'],
  rimCam: ['Rim camera (×2)', 'Small camera under each lift beam, looking down at the box rim. Before closing, it counts bees on the contact edges and looks for burr comb across the seam.'],
  strobe: ['White strobe', 'A short white LED flash synced to the exposure. It gives true colours for brood and pollen, and there is no motion blur even while bees move.'],
  redLight: ['Red work light', 'Bees barely see light above ~620 nm, so the cabinet interior is lit deep red during the whole inspection.'],
  leadScrew: ['Lead screw', 'TR16×4 trapezoidal lead screw, self-locking (lead angle ≈4.5°). It is hung from a thrust bearing in the crown. Dry PTFE lubrication, no grease to trap debris or bees.'],
  nema23: ['NEMA23 lift motor', 'Driven by a DM542 driver. Four of them: two lift beams and two scan beams. Lifting 80 kg of upper boxes needs ≈0.8 N·m per side with TR16×4.'],
  nema17: ['NEMA17 motor', 'Drives a shuttle belt. TMC2209 driver on the motion board. StallGuard detects jams.'],
  box: ['Hive body', 'A standard wooden hive body. Only change needed: two cleats and steel frame pins. Nothing robotic lives inside the bee space.'],
  lid: ['Insulated inner cover', 'Wood-fibre insulated lid with cleats. The cabinet roof handles rain, so the hive lid stays light.'],
  frame: ['Frame', 'Estonian frame, 448 mm top bar. Frames are kept vertical at all times: warm, heavy comb breaks if it is tilted.'],
  comb: ['Comb', 'Capped brood in the centre, honey arc on top. This is what the cameras capture on every inspection.'],
  pin: ['Robot frame pin', 'A stainless M5 shoulder screw on each ear of the top bar (≈0.20 € per frame). The hook grips it. The inductive sensor locates each frame to ±0.5 mm.'],
  tag: ['Frame ID tag', 'ArUco marker on the end bar. The frame keeps its identity when it moves between boxes, so the web app can track each frame side over time.'],
  bottomBoard: ['Varroa sump', 'Tall screened bottom board. Mites fall through the mesh onto a white tray. A corner camera counts them every day. No moving parts.'],
  varroaCam: ['Varroa camera', 'Wide-angle camera with a ring light inside the sump, looking across the white tray.'],
  entrance: ['Entrance tunnel', 'Carries the bee entrance through the cabinet wall to a landing board. The flight path stays clear of all machinery.'],
  reducer: ['Entrance reducer', 'Servo-driven slide. It narrows the entrance against robbing, hornets or wind, or closes it before transport.'],
  observer: ['Entrance Observer', 'Gratheon entrance camera (runs on the old Jetson Nano). It counts bees in and out and flags hornets and robbing.'],
  cladding: ['Cladding', 'Vertical thermo-treated pine boards. They are weatherproof without chemical preservatives, which can harm bees. Backed by wood-fibre insulation.'],
  plinthClad: ['Charred-wood skirt', 'Yakisugi (charred) boards resist rot and splashing at ground level without any chemicals.'],
  door: ['Service door', 'Full-height front door. Opening it cuts motor power (interlock), and the forks can then be folded away so the hive can be worked by hand.'],
  window: ['Viewing window', 'A polycarbonate slot for visitors. A wooden shutter keeps it dark between inspections.'],
  roof: ['Roof', 'Ventilated double roof with 60 mm overhang and drip edges. The air gap keeps summer heat off the hive.'],
  solar: ['Solar panel', 'About 100 W, south-facing. With the always-on ESP32 at ~0.2 W and the Jetson woken only for inspections, the tower runs off-grid most of the year.'],
  antenna: ['Antenna fin', 'RF-transparent ASA fin on the roof ridge with the LTE, LoRa 868 MHz, Wi-Fi and GNSS antennas. Surge arrestors sit where the cables enter the crown.'],
  vent: ['Hex vent band', 'Hexagon ventilation slots in bronze-anodised aluminium, backed by insect mesh. Crown heat leaves here and does not heat the hive.'],
  estop: ['Emergency stop', 'Latching mushroom switch on the side. It cuts 24 V motor power only; the computers keep running and log the event.'],
  status: ['Status light', 'Honey-yellow ring. Slow pulse = idle, solid = inspecting, red = needs attention.'],
  jetson: ['Jetson Orin Nano', 'Runs inspections, cameras and detection models (bees, queen, varroa, brood). It sends sequences to Klipper over the Moonraker API.'],
  mcu: ['Motion board', 'BTT Octopus-class board running Klipper firmware. It generates step pulses in real time (not Python on the GPIO), handles endstops, servos, fans and the heater.'],
  dm542: ['DM542 drivers', 'External drivers for the four NEMA23 motors. Step/dir signals come from the motion board.'],
  dcdc: ['DC-DC converters', 'Converts 24 V to 19 V for the Orin Nano and 24 V to 5 V for the servos and LEDs. Each output is fused.'],
  modem: ['LTE modem', 'USB LTE modem for sites without Wi-Fi.'],
  lora: ['ESP32 + LoRa', 'Always-on supervisor, about 0.2 W. It reads temperature, humidity and weight, sends LoRa telemetry, wakes the Jetson via a relay and runs the watchdog.'],
  psu: ['24 V PSU', 'Mean Well 24 V ~ 350 W in a sealed box. The motor rail goes through the E-stop and the door interlock.'],
  battery: ['LiFePO4 battery', 'Optional 24 V / 20 Ah pack for solar or off-grid use. Sits low for stability.'],
  nano: ['Jetson Nano', 'The older Jetson Nano, reused as the Entrance Observer computer.'],
  heater: ['Cabinet heater', '24 V PTC fan heater. It pre-warms the cabinet air to about 25 °C before a cold-day inspection, so open brood does not chill.'],
  wheels: ['Mobile base (future)', 'Future variant: the same yoke on a skid-steer base. It drives over a hive dock from behind (away from the flight path) and locks onto three docking cones.'],
  dock: ['Docking cone', 'Kinematic coupling: 3 cones in V-grooves put the robot back within ±0.5 mm of the same hive dock every time.'],
  bee: ['Honey bee', 'The client.'],
};

// ---------------------------------------------------------------------------
// Derived geometry
// ---------------------------------------------------------------------------
export function derive(p) {
  const n = p.boxes;
  const k = Math.min(p.inspectBox, n - 1);
  const h = p.box.h;
  const base = p.plinth + p.bottomBoard;
  const boxBottom = (i) => base + i * h; // i === n → lid
  const cleatY = (i) => boxBottom(i) + p.cleatUnderside;
  const rim = boxBottom(k) + h;
  const frameTop = (rimY) => rimY - 2; // top bar sits 2 mm below the rim
  const engage = frameTop(rim) + 1.25; // hook plate sits on the pin neck
  const liftMax = cleatY(n) + p.gap; // worst case: lifting only the lid
  const postTop = liftMax + 70;
  const inner = p.box.d - 2 * p.box.wall;
  const f = p.frame;
  // Working gap of 25 mm starts at the back wall; frames fill the rest.
  const frameZ = [];
  for (let i = 0; i < f.count; i++) frameZ.push(-inner / 2 + 25 + f.pitch / 2 + i * f.pitch);
  const gapWidth = inner - f.count * f.pitch;
  return {
    n, k, h, base, boxBottom, cleatY, rim, engage, liftMax, postTop, frameZ, gapWidth,
    frameTop: frameTop(rim),
    crownTop: postTop + p.crown,
    stackTop: boxBottom(n) + p.lid,
    liftPark: base + 250,
    scanPark: p.plinth + 220,
  };
}

// ---------------------------------------------------------------------------
// Materials
// ---------------------------------------------------------------------------
function makeMaterials() {
  const std = (color, o = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.7, metalness: 0, ...o });
  return {
    alu: std(0xc4c9ce, { metalness: 0.75, roughness: 0.35 }),
    bronze: std(0x7a6247, { metalness: 0.7, roughness: 0.4 }),
    steel: std(0x9aa1a8, { metalness: 0.85, roughness: 0.3 }),
    black: std(0x1f2122, { roughness: 0.55 }),
    rubber: std(0x151515, { roughness: 0.95 }),
    pcbGreen: std(0x1d4d33, { roughness: 0.6 }),
    pcbBlue: std(0x1f3552, { roughness: 0.6 }),
    yellow: std(0xf2b705, { roughness: 0.45 }),
    red: std(0xc8261d, { roughness: 0.4 }),
    white: std(0xf1f0ea, { roughness: 0.8 }),
    woodBox: [std(0xd7b07a, { roughness: 0.85 }), std(0xcfa46b, { roughness: 0.85 }), std(0xdcba88, { roughness: 0.85 }), std(0xc99b61, { roughness: 0.85 })],
    lid: std(0xb98d5a, { roughness: 0.85 }),
    slat: std(0x8b5a3c, { roughness: 0.8 }),
    slatAlt: std(0x7f5236, { roughness: 0.8 }),
    backer: std(0x2c2420, { roughness: 0.9 }),
    charred: std(0x262220, { roughness: 0.95 }),
    topBar: std(0xe0c28f, { roughness: 0.8 }),
    comb: std(0xe2b24a, { roughness: 0.6 }),
    honey: std(0xf3c647, { roughness: 0.35, emissive: 0x3a2800, emissiveIntensity: 0.3 }),
    brood: std(0xa8743c, { roughness: 0.75 }),
    mesh: std(0x6f7478, { metalness: 0.6, roughness: 0.5, transparent: true, opacity: 0.55 }),
    glass: new THREE.MeshPhysicalMaterial({ color: 0xcfe6ee, roughness: 0.05, metalness: 0, transmission: 0.85, transparent: true, opacity: 0.35, thickness: 4 }),
    solar: std(0x14213d, { metalness: 0.4, roughness: 0.25 }),
    fin: std(0xd8d6cf, { roughness: 0.5 }),
    ledWhite: std(0xffffff, { emissive: 0xffffff, emissiveIntensity: 2.5 }),
    ledRed: std(0x550000, { emissive: 0xff1a0a, emissiveIntensity: 2.0 }),
    ledYellow: std(0x6a4a00, { emissive: 0xffc21a, emissiveIntensity: 1.6 }),
    beam: new THREE.MeshBasicMaterial({ color: 0xfff6d8, transparent: true, opacity: 0.12, depthWrite: false }),
    beeBody: std(0x2a1d0e, { roughness: 0.6 }),
    beeStripe: std(0xe3a824, { roughness: 0.6 }),
    beeWing: std(0xe8f2f7, { roughness: 0.2, transparent: true, opacity: 0.45 }),
  };
}

// ---------------------------------------------------------------------------
// Builder helpers (geometry cache keeps the GLB small)
// ---------------------------------------------------------------------------
function helpers() {
  const geoCache = new Map();
  const cached = (key, make) => {
    if (!geoCache.has(key)) geoCache.set(key, make());
    return geoCache.get(key);
  };
  const place = (parent, geo, mat, x, y, z, part) => {
    const m = new THREE.Mesh(geo, mat);
    m.position.set(x * MM, y * MM, z * MM);
    m.castShadow = true;
    m.receiveShadow = true;
    if (part) m.userData.part = part;
    parent.add(m);
    return m;
  };
  const box = (parent, sx, sy, sz, mat, x = 0, y = 0, z = 0, part) =>
    place(parent, cached(`b${sx}|${sy}|${sz}`, () => new THREE.BoxGeometry(sx * MM, sy * MM, sz * MM)), mat, x, y, z, part);
  // Cylinder along an axis ('x' | 'y' | 'z')
  const cyl = (parent, r, len, mat, x = 0, y = 0, z = 0, axis = 'y', part, seg = 20) => {
    const m = place(parent, cached(`c${r}|${len}|${seg}`, () => new THREE.CylinderGeometry(r * MM, r * MM, len * MM, seg)), mat, x, y, z, part);
    if (axis === 'x') m.rotation.z = Math.PI / 2;
    if (axis === 'z') m.rotation.x = Math.PI / 2;
    return m;
  };
  const group = (parent, name, x = 0, y = 0, z = 0, part) => {
    const g = new THREE.Group();
    g.name = name;
    g.position.set(x * MM, y * MM, z * MM);
    if (part) g.userData.part = part;
    parent.add(g);
    return g;
  };
  return { box, cyl, group, place, cached };
}

// ---------------------------------------------------------------------------
// Scene
// ---------------------------------------------------------------------------
export function buildHiveTower(options = {}) {
  const p = { ...DEFAULTS, ...options, box: { ...DEFAULTS.box, ...(options.box || {}) }, frame: { ...DEFAULTS.frame, ...(options.frame || {}) } };
  const d = derive(p);
  const M = makeMaterials();
  const { box, cyl, group, place, cached } = helpers();
  const W = p.box.w, D = p.box.d, H = p.box.h, T = p.box.wall;
  const PX = p.post.x, PZ = p.post.z;
  const E = 22; // extrusion size

  const root = new THREE.Group();
  root.name = 'HiveTower';
  const nodes = { root };

  // ----- structure: plinth frame, posts, crown frame ------------------------
  const structure = group(root, 'structure');
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) {
    box(structure, E, d.crownTop - 40, E, M.alu, sx * PX, 40 + (d.crownTop - 40) / 2, sz * PZ, 'post');
  }
  const ring = (y, part) => {
    box(structure, 2 * PX + E, E, E, M.alu, 0, y, PZ, part);
    box(structure, 2 * PX + E, E, E, M.alu, 0, y, -PZ, part);
    box(structure, E, E, 2 * PZ - E, M.alu, PX, y, 0, part);
    box(structure, E, E, 2 * PZ - E, M.alu, -PX, y, 0, part);
  };
  ring(51, 'plinth');
  ring(p.plinth - 11, 'plinth');
  ring(d.postTop - 11, 'crown');
  ring(d.crownTop - 11, 'crown');
  // hive deck cross members + rubber pads
  for (const z of [-150, 150]) box(structure, 2 * PX, E, E, M.alu, 0, p.plinth - 11, z, 'plinth');
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) box(structure, 40, 6, 40, M.rubber, sx * 200, p.plinth + 3, sz * 150, 'feet');
  // motor plate in the crown
  box(structure, 2 * PX + E, 6, 2 * PZ + E, M.alu, 0, d.postTop + 3, 0, 'crown');
  // levelling feet
  const feet = group(structure, 'feet');
  for (const sx of [-1, 1]) for (const sz of [-1, 1]) {
    cyl(feet, 6, 30, M.steel, sx * PX, 25, sz * PZ, 'y', 'feet');
    cyl(feet, 22, 10, M.rubber, sx * PX, 5, sz * PZ, 'y', 'feet', 24);
  }
  nodes.feet = feet;

  // ----- hive stack --------------------------------------------------------
  const hive = group(root, 'hive');
  nodes.hive = hive;
  const boxMaterials = [];

  // bottom board / varroa sump
  const bb = group(hive, 'bottomBoard', 0, p.plinth, 0);
  const bbH = p.bottomBoard;
  const bbMat = M.woodBox[3].clone();
  boxMaterials.push(bbMat);
  box(bb, W, bbH, T, bbMat, 0, bbH / 2, -D / 2 + T / 2, 'bottomBoard');
  box(bb, T, bbH, D - 2 * T, bbMat, W / 2 - T / 2, bbH / 2, 0, 'bottomBoard');
  box(bb, T, bbH, D - 2 * T, bbMat, -W / 2 + T / 2, bbH / 2, 0, 'bottomBoard');
  box(bb, W, 12, D, bbMat, 0, 6, 0, 'bottomBoard');
  // front wall with a 300 × 15 entrance slot at the top
  box(bb, W, bbH - 15, T, bbMat, 0, (bbH - 15) / 2, D / 2 - T / 2, 'bottomBoard');
  box(bb, (W - 300) / 2, 15, T, bbMat, -(W + 300) / 4, bbH - 7.5, D / 2 - T / 2, 'bottomBoard');
  box(bb, (W - 300) / 2, 15, T, bbMat, (W + 300) / 4, bbH - 7.5, D / 2 - T / 2, 'bottomBoard');
  box(bb, W - 2 * T, 2, D - 2 * T, M.mesh, 0, bbH - 18, 0, 'bottomBoard');
  box(bb, W - 2 * T - 10, 3, D - 2 * T - 10, M.white, 0, 16, 0, 'bottomBoard');
  const vcam = group(bb, 'varroaCam', -W / 2 + T + 25, 60, -D / 2 + T + 25, 'varroaCam');
  box(vcam, 30, 30, 30, M.black, 0, 0, 0, 'varroaCam');
  cyl(vcam, 8, 6, M.ledWhite, 12, -6, 12, 'y', 'varroaCam');

  // entrance tunnel, landing board, reducer, entrance observer
  const ent = group(root, 'entrance', 0, p.plinth + bbH - 15, 0);
  const tunnelLen = PZ + 40 - D / 2;
  const tz = D / 2 + tunnelLen / 2;
  box(ent, 320, 4, tunnelLen, M.woodBox[3], 0, -2, tz, 'entrance');
  box(ent, 320, 4, tunnelLen, M.woodBox[3], 0, 17, tz, 'entrance');
  box(ent, 4, 15, tunnelLen, M.woodBox[3], -158, 7.5, tz, 'entrance');
  box(ent, 4, 15, tunnelLen, M.woodBox[3], 158, 7.5, tz, 'entrance');
  box(ent, 360, 10, 90, M.woodBox[3], 0, -9, PZ + 32 + 45, 'entrance');
  box(ent, 150, 4, 10, M.yellow, 60, 28, PZ + 38, 'reducer');
  const obs = group(ent, 'observer', 0, 80, PZ + 70, 'observer');
  box(obs, 180, 70, 70, M.black, 0, 0, 0, 'observer');
  box(obs, 200, 6, 90, M.black, 0, 38, 8, 'observer');
  cyl(obs, 12, 10, M.glass, 0, -38, 10, 'y', 'observer');

  // bees on the landing board
  const bees = group(root, 'bees');
  const beeGeo = cached('bee', () => new THREE.SphereGeometry(1, 12, 8));
  const addBee = (x, y, z, rotY, flying = false) => {
    const b = group(bees, `bee_${bees.children.length}`, x, y, z, 'bee');
    b.rotation.y = rotY;
    const body = place(b, beeGeo, M.beeBody, 0, 0, 0, 'bee'); body.scale.set(4 * MM, 3.5 * MM, 7 * MM);
    const stripe = place(b, beeGeo, M.beeStripe, 0, 0.3, -2, 'bee'); stripe.scale.set(4.1 * MM, 3.6 * MM, 3 * MM);
    for (const s of [-1, 1]) {
      const wing = place(b, beeGeo, M.beeWing, s * 4, 3, 1, 'bee');
      wing.scale.set(4 * MM, 0.4 * MM, 6 * MM);
      wing.rotation.y = s * 0.4;
    }
    b.userData.flying = flying;
    return b;
  };
  const landingY = p.plinth + bbH - 15 - 4 + 4;
  addBee(-60, landingY, PZ + 60, 0.3);
  addBee(40, landingY, PZ + 90, -2.4);
  addBee(110, landingY, PZ + 50, 1.9);
  addBee(-120, landingY + 140, PZ + 260, 2.8, true);
  addBee(90, landingY + 220, PZ + 420, -0.6, true);
  addBee(-10, landingY + 90, PZ + 180, 3.1, true);

  // one hive body (hollow walls + cleats + frames)
  const frameParts = (parent, name) => {
    const f = p.frame;
    const g = group(parent, name, 0, 0, 0, 'frame');
    box(g, f.topBar, 20, 25, M.topBar, 0, -10, 0, 'frame');
    for (const s of [-1, 1]) box(g, 10, f.height - 30, 30, M.topBar, s * (f.width / 2 - 5), -20 - (f.height - 30) / 2, 0, 'frame');
    box(g, f.width, 10, 20, M.topBar, 0, -f.height + 5, 0, 'frame');
    box(g, f.width - 20, f.height - 40, 22, M.comb, 0, -20 - (f.height - 40) / 2, 0, 'comb');
    box(g, f.width - 24, 50, 23, M.honey, 0, -50, 0, 'comb');
    const brood = place(g, cached('brood', () => new THREE.CylinderGeometry(1, 1, 24 * MM, 32)), M.brood, 0, -f.height / 2 - 20, 0, 'comb');
    brood.rotation.x = Math.PI / 2;
    brood.scale.set(135 * MM, 1, 85 * MM);
    for (const s of [-1, 1]) {
      cyl(g, 2.5, 2.5, M.steel, s * f.pinX, 1.25, 0, 'y', 'pin', 12);
      cyl(g, 4.5, 2.5, M.steel, s * f.pinX, 3.75, 0, 'y', 'pin', 16);
    }
    box(g, 2, 18, 18, M.white, f.width / 2 + 1, -40, 0, 'tag');
    box(g, 2.2, 10, 10, M.black, f.width / 2 + 1, -40, 0, 'tag');
    return g;
  };

  const hiveBody = (parent, name, i, x, y, z) => {
    const g = group(parent, name, x, y, z, 'box');
    const mat = M.woodBox[i % M.woodBox.length].clone();
    boxMaterials.push(mat);
    box(g, W, H, T, mat, 0, H / 2, D / 2 - T / 2, 'box');
    box(g, W, H, T, mat, 0, H / 2, -D / 2 + T / 2, 'box');
    box(g, T, H, D - 2 * T, mat, W / 2 - T / 2, H / 2, 0, 'box');
    box(g, T, H, D - 2 * T, mat, -W / 2 + T / 2, H / 2, 0, 'box');
    addCleats(g, p.cleatUnderside);
    const frames = [];
    d.frameZ.forEach((fz, fi) => {
      const fg = frameParts(g, `${name}_frame${fi}`);
      fg.position.set(0, (H - 2) * MM, fz * MM);
      frames.push(fg);
    });
    return { g, frames };
  };
  const addCleats = (g, underside) => {
    for (const s of [-1, 1]) {
      box(g, 3, 30, 320, M.steel, s * (W / 2 + 1.5), underside + 15, 0, 'cleat');
      box(g, 30, 3, 320, M.steel, s * (W / 2 + 15), underside + 1.5, 0, 'cleat');
    }
  };

  // Boxes above the inspected box ride in the lifted group, pivoting at the
  // centre of the fork contact line so left/right peel shows up as a tilt.
  const pivotY = d.cleatY(d.k + 1);
  const lifted = group(hive, 'liftedStack', 0, pivotY, 0);
  nodes.lifted = lifted;
  const bodies = [];
  for (let i = 0; i < d.n; i++) {
    const y = d.boxBottom(i);
    const parent = i > d.k ? lifted : hive;
    const b = hiveBody(parent, `box${i}`, i, 0, i > d.k ? y - pivotY : y, 0);
    bodies.push(b);
  }
  const lidG = group(lifted, 'lid', 0, d.boxBottom(d.n) - pivotY, 0, 'lid');
  box(lidG, W, p.lid, D, M.lid, 0, p.lid / 2, 0, 'lid');
  addCleats(lidG, p.cleatUnderside);
  nodes.frames = bodies[d.k].frames;
  nodes.boxMaterials = boxMaterials;

  // ----- lead screws & motors (hang from the crown) -------------------------
  const drive = group(root, 'drives');
  const screwBottom = p.plinth + 20;
  const screwLen = d.postTop - screwBottom;
  for (const s of [-1, 1]) {
    // lift: TR12, z = -60 ; scan: TR10, z = +60
    for (const z of [-60, 60]) { // lift screw at -60, scan screw at +60, both TR16×4
      cyl(drive, 8, screwLen, M.steel, s * PX, screwBottom + screwLen / 2, z, 'y', 'leadScrew', 12);
      box(drive, 57, 76, 57, M.black, s * PX, d.postTop + 6 + 38, z, 'nema23');
      box(drive, 58, 10, 58, M.alu, s * PX, d.postTop + 6 + 76, z, 'nema23');
    }
  }

  // ----- lift beams --------------------------------------------------------
  const beamLen = 2 * PZ - E;
  const makeBeamBase = (g, s, yOff, part, screwZ) => {
    box(g, E, 44, beamLen, M.alu, s * 340, yOff, 0, part);
    for (const sz of [-1, 1]) box(g, 14, 50, 30, M.steel, s * 355, yOff, sz * PZ, part);
    box(g, 44, 30, 30, M.bronze, s * (PX - 1), yOff, screwZ, part);
  };
  nodes.liftBeams = {};
  nodes.forks = {};
  for (const s of [-1, 1]) {
    const side = s < 0 ? 'L' : 'R';
    const g = group(root, `liftBeam${side}`, 0, d.liftPark, 0, 'liftBeam');
    makeBeamBase(g, s, -30, 'liftBeam', -60);
    cyl(g, 6, 380, M.steel, s * 305, -5, 0, 'z', 'fork');
    for (const z of [-150, 150]) {
      box(g, 26, 22, 22, M.alu, s * 318, -12, z, 'fork');
      box(g, 8, 8, 40, M.steel, s * 318, -26, z, 'loadcell');
    }
    box(g, 40, 22, 40, M.black, s * 318, -10, 205, 'fork');
    const rc = group(g, `rimCam${side}`, s * 318, -30, -205, 'rimCam');
    rc.rotation.z = s * 0.6;
    box(rc, 26, 20, 26, M.black, 0, 0, 0, 'rimCam');
    cyl(rc, 6, 4, M.glass, -s * 10, -8, 0, 'y', 'rimCam');
    const forks = [];
    for (const z of [-120, 120]) {
      const pivot = group(g, `fork${side}_${z > 0 ? 'F' : 'B'}`, s * 305, -5, z, 'fork');
      box(pivot, 10, 45, 20, M.yellow, 0, -22.5, 0, 'fork');
      forks.push(pivot);
    }
    nodes.liftBeams[side] = g;
    nodes.forks[side] = forks;
  }

  // ----- scan beams + shuttles --------------------------------------------
  nodes.scanBeams = {};
  nodes.shuttles = {};
  nodes.hooks = {};
  nodes.strobes = [];
  for (const s of [-1, 1]) {
    const side = s < 0 ? 'L' : 'R';
    const g = group(root, `scanBeam${side}`, 0, d.scanPark, 0, 'scanBeam');
    makeBeamBase(g, s, 40, 'scanBeam', 60);
    box(g, 42, 42, 40, M.black, s * 340, 40 + 22 + 21, 250, 'belt');
    box(g, 3, 6, beamLen - 60, M.black, s * 328, 55, 0, 'belt');
    box(g, 4, 6, beamLen - 40, M.ledRed, s * 328, 22, 0, 'redLight');

    const sh = group(g, `shuttle${side}`, 0, 0, 0, 'shuttle');
    box(sh, 22, 60, 56, M.bronze, s * 318, 34, 0, 'shuttle');
    box(sh, 14, 14, 14, M.black, s * 312, 2, -22, 'shuttle'); // inductive sensor
    // hook: pivot 18 mm above the plate, arm → leg → slotted plate
    const hk = group(sh, `hook${side}`, s * 300, 18, 0, 'hook');
    box(hk, 88, 4, 16, M.yellow, -s * 44, 0, 0, 'hook');
    box(hk, 4, 18, 16, M.yellow, -s * 88, -9, 0, 'hook');
    // H-plate: two back-to-back slots so it can push a frame either way
    box(hk, 22, 2.5, 4, M.yellow, -s * 99, -18, 0, 'hook');
    for (const px of [94.5, 105.5]) box(hk, 5, 2.5, 36, M.yellow, -s * px, -18, 0, 'hook');
    // camera rig hanging to frame-centre height
    const camY = -142;
    cyl(sh, 5, 150, M.alu, s * 318, camY / 2 + 5, 0, 'y', 'camera', 12);
    box(sh, 12, 12, 250, M.alu, s * 318, camY, 0, 'camera');
    for (const cz of [-120, 120]) {
      const cam = group(sh, `camera${side}${cz > 0 ? 'F' : 'B'}`, s * 318, camY, cz, 'camera');
      cam.rotation.y = Math.atan2(-s * 318, -cz);
      box(cam, 32, 32, 36, M.black, 0, 0, 0, 'camera');
      cyl(cam, 8, 6, M.glass, 0, 0, 20, 'z', 'camera');
      const led = box(cam, 44, 6, 6, M.ledWhite, 0, 22, 14, 'strobe');
      const reach = Math.hypot(318, cz);
      const cone = place(cam, cached(`cone${Math.round(reach)}`, () => {
        const c = new THREE.ConeGeometry(0.22, reach * MM, 24, 1, true);
        c.rotateX(-Math.PI / 2);
        c.translate(0, 0, (reach * MM) / 2);
        return c;
      }), M.beam, 0, 0, 0, 'strobe');
      cone.castShadow = false;
      cone.receiveShadow = false;
      led.name = `${cam.name}_strobe`;
      cone.name = `${cam.name}_light`;
      nodes.strobes.push(led, cone);
    }
    nodes.scanBeams[side] = g;
    nodes.shuttles[side] = sh;
    nodes.hooks[side] = hk;
  }

  // ----- crown electronics ---------------------------------------------------
  const elec = group(root, 'electronics', 0, d.postTop + 6, 0);
  box(elec, 100, 30, 79, M.pcbGreen, -180, 15, 180, 'jetson');
  box(elec, 60, 28, 60, M.black, -180, 44, 180, 'jetson');
  box(elec, 160, 20, 100, M.pcbBlue, -20, 10, 200, 'mcu');
  for (const x of [110, 150, 190, 230]) box(elec, 34, 75, 118, M.black, x, 37.5, 190, 'dm542');
  box(elec, 60, 30, 40, M.alu, -40, 15, -200, 'dcdc');
  box(elec, 60, 30, 40, M.alu, 40, 15, -200, 'dcdc');
  box(elec, 90, 18, 55, M.black, -170, 9, -200, 'modem');
  box(elec, 50, 12, 28, M.pcbGreen, 170, 6, -200, 'lora');
  box(elec, 70, 60, 70, M.black, 250, 30, -170, 'heater');
  nodes.electronics = elec;
  const base = group(root, 'plinthGear', 0, 60, 0);
  box(base, 215, 50, 115, M.alu, -150, 25, -100, 'psu');
  box(base, 260, 120, 170, M.pcbBlue, 150, 60, 50, 'battery');
  box(base, 100, 30, 80, M.pcbGreen, -180, 15, 150, 'nano');

  // ----- cladding, crown shell, roof --------------------------------------
  const clad = group(root, 'cladding');
  nodes.cladding = clad;
  const OX = PX + 11, OZ = PZ + 11; // outer skeleton faces
  const top = d.postTop;
  const bodyH = top - p.plinth;
  const cy = p.plinth + bodyH / 2;
  const slatW = 68, slatGap = 6;
  // side & back walls: backer + vertical slats
  const slatRun = (width, fn) => {
    const count = Math.floor((width + slatGap) / (slatW + slatGap));
    const used = count * slatW + (count - 1) * slatGap;
    for (let i = 0; i < count; i++) fn(-used / 2 + slatW / 2 + i * (slatW + slatGap), i);
  };
  for (const s of [-1, 1]) {
    box(clad, 8, bodyH, 2 * OZ, M.backer, s * (OX + 4), cy, 0, 'cladding');
    slatRun(2 * OZ + 30, (z, i) => box(clad, 18, bodyH, slatW, i % 2 ? M.slatAlt : M.slat, s * (OX + 17), cy, z, 'cladding'));
  }
  box(clad, 2 * OX + 16, bodyH, 8, M.backer, 0, cy, -(OZ + 4), 'cladding');
  slatRun(2 * OX + 52, (x, i) => box(clad, slatW, bodyH, 18, i % 2 ? M.slatAlt : M.slat, x, cy, -(OZ + 17), 'cladding'));
  // front door with viewing window and entrance cut-out
  const door = group(clad, 'door', 0, 0, 0, 'door');
  const win = { x0: -70, x1: 70, y0: 1000, y1: 1450 };
  const entTop = p.plinth + bbH + 20;
  box(door, 2 * OX + 16, top - entTop, 8, M.backer, 0, (top + entTop) / 2, OZ + 4, 'door');
  slatRun(2 * OX + 52, (x, i) => {
    const mat = i % 2 ? M.slatAlt : M.slat;
    const crossesWin = x + slatW / 2 > win.x0 && x - slatW / 2 < win.x1;
    const crossesEnt = Math.abs(x) - slatW / 2 < 160;
    const y0 = crossesEnt ? entTop : p.plinth;
    const segs = crossesWin ? [[y0, win.y0], [win.y1, top]] : [[y0, top]];
    for (const [a, b] of segs) box(door, slatW, b - a, 18, mat, x, (a + b) / 2, OZ + 17, 'door');
  });
  box(door, win.x1 - win.x0 + 60, win.y1 - win.y0, 6, M.glass, 0, (win.y0 + win.y1) / 2, OZ + 22, 'window');
  box(door, win.x1 - win.x0 + 60, 12, 26, M.bronze, 0, win.y0 - 6, OZ + 17, 'window');
  box(door, win.x1 - win.x0 + 60, 12, 26, M.bronze, 0, win.y1 + 6, OZ + 17, 'window');
  box(door, 16, 220, 22, M.bronze, 2 * OX / 2 - 30, 1150, OZ + 34, 'door'); // handle
  const status = place(door, cached('ring', () => new THREE.TorusGeometry(24 * MM, 4 * MM, 12, 40)), M.ledYellow, 0, top - 90, OZ + 28, 'status');
  nodes.status = status;
  // e-stop on the right side
  box(clad, 20, 90, 90, M.yellow, OX + 36, 1250, 180, 'estop');
  cyl(clad, 22, 24, M.red, OX + 58, 1250, 180, 'x', 'estop', 24);
  // plinth skirt (charred wood)
  for (const s of [-1, 1]) {
    box(clad, 20, p.plinth - 30, 2 * OZ + 40, M.charred, s * (OX + 17), 30 + (p.plinth - 30) / 2, 0, 'plinthClad');
    box(clad, 2 * OX + 54, p.plinth - 30, 20, M.charred, 0, 30 + (p.plinth - 30) / 2, s * (OZ + 17), 'plinthClad');
  }
  // crown shell with hex vent band
  const crownH = p.crown;
  const ccy = top + crownH / 2;
  for (const s of [-1, 1]) {
    box(clad, 20, crownH, 2 * OZ + 40, M.bronze, s * (OX + 17), ccy, 0, 'crown');
    box(clad, 2 * OX + 54, crownH, 20, M.bronze, 0, ccy, s * (OZ + 17), 'crown');
  }
  const hexGeo = cached('hex', () => new THREE.CylinderGeometry(14 * MM, 14 * MM, 4 * MM, 6));
  for (let i = -9; i <= 9; i++) for (let r = 0; r < 2; r++) {
    const x = i * 38 + (r ? 19 : 0);
    if (Math.abs(x) > OX - 10) continue;
    const hx = place(clad, hexGeo, M.backer, x, ccy + (r ? -16 : 16), OZ + 27.5, 'vent');
    hx.rotation.x = Math.PI / 2;
    hx.rotation.y = Math.PI / 6;
  }
  // mono-pitch roof sloping down to the front (south)
  const roof = group(clad, 'roof', 0, d.crownTop + 20, 0, 'roof');
  roof.rotation.x = 0.1;
  box(roof, 2 * OX + 120, 30, 2 * OZ + 150, M.charred, 0, 0, 0, 'roof');
  box(roof, 2 * OX + 40, 36, 2 * OZ + 60, M.alu, 0, 30, 0, 'solar');
  box(roof, 2 * OX + 24, 38, 2 * OZ + 44, M.solar, 0, 31, 0, 'solar');
  for (let i = 1; i < 6; i++) box(roof, 2, 39, 2 * OZ + 44, M.alu, -OX - 12 + (i * (2 * OX + 24)) / 6, 31, 0, 'solar');
  const finShape = new THREE.Shape();
  finShape.moveTo(0, 0);
  finShape.lineTo(220, 0);
  finShape.quadraticCurveTo(60, 20, 0, 120);
  finShape.lineTo(0, 0);
  const finGeo = new THREE.ExtrudeGeometry(finShape, { depth: 26, bevelEnabled: true, bevelSize: 4, bevelThickness: 4, bevelSegments: 2 });
  finGeo.scale(MM, MM, MM);
  finGeo.translate(0, 0, -13 * MM);
  const fin = place(roof, finGeo, M.fin, 0, 48, -OZ - 40, 'antenna');
  fin.rotation.y = -Math.PI / 2;

  // ----- mobile variant (hidden by default) --------------------------------
  const mobile = group(root, 'mobileBase');
  mobile.visible = false;
  for (const sx of [-1, 1]) {
    box(mobile, 60, 80, 2 * PZ + 300, M.black, sx * (PX + 90), 110, 0, 'wheels');
    for (const sz of [-1, 1]) {
      cyl(mobile, 120, 70, M.rubber, sx * (PX + 170), 120, sz * (PZ + 40), 'x', 'wheels', 32);
      cyl(mobile, 60, 74, M.alu, sx * (PX + 170), 120, sz * (PZ + 40), 'x', 'wheels', 24);
      box(mobile, 90, 90, 110, M.bronze, sx * (PX + 85), 120, sz * (PZ + 40), 'wheels');
    }
  }
  for (const [x, z] of [[-PX + 60, PZ - 60], [PX - 60, PZ - 60], [0, -PZ + 60]]) {
    const c = place(mobile, cached('dock', () => new THREE.ConeGeometry(28 * MM, 50 * MM, 24)), M.yellow, x, 25, z, 'dock');
    c.rotation.x = Math.PI;
  }
  nodes.mobile = mobile;
  nodes.bees = bees;

  // ----- animation --------------------------------------------------------
  const timeline = buildTimeline(p, d);
  const applyState = (st) => {
    for (const s of [-1, 1]) {
      const side = s < 0 ? 'L' : 'R';
      nodes.liftBeams[side].position.y = st[`lift${side}`] * MM;
      for (const f of nodes.forks[side]) f.rotation.z = -s * (Math.PI / 2) * st[`fork${side}`];
      nodes.scanBeams[side].position.y = st.scan * MM;
      nodes.shuttles[side].position.z = st.shuttle * MM;
      nodes.hooks[side].rotation.z = -s * (Math.PI / 2) * (1 - st.hook);
    }
    const cleat = d.cleatY(d.k + 1);
    const dL = st.forkL > 0.98 ? Math.max(0, st.liftL - cleat) : 0;
    const dR = st.forkR > 0.98 ? Math.max(0, st.liftR - cleat) : 0;
    lifted.position.y = (cleat + (dL + dR) / 2) * MM;
    lifted.rotation.z = Math.atan2(dR - dL, 2 * (W / 2 + 15));
    nodes.frames.forEach((fg, i) => {
      fg.position.z = st[`f${i}z`] * MM;
      fg.position.y = (H - 2 + st[`f${i}y`]) * MM;
    });
    const on = st.strobe > 0.5 ? 1 : 1e-4;
    for (const m of nodes.strobes) m.scale.setScalar(on);
    return st;
  };
  const animated = [
    ...Object.values(nodes.liftBeams), ...Object.values(nodes.forks).flat(),
    ...Object.values(nodes.scanBeams), ...Object.values(nodes.shuttles), ...Object.values(nodes.hooks),
    lifted, ...nodes.frames, ...nodes.strobes,
  ];
  applyState(timeline.stateAt(0));

  return { root, nodes, params: p, derived: d, timeline, applyState, animated, MM };
}

// ---------------------------------------------------------------------------
// Inspection sequence as a timeline of tweens.
// Durations are compressed for the preview; `real` is the estimated
// real-world time at the planned speeds.
// ---------------------------------------------------------------------------
export function buildTimeline(p, d) {
  const INSTANT = new Set(['strobe']);
  const state = {
    liftL: d.liftPark, liftR: d.liftPark, forkL: 0, forkR: 0,
    scan: d.scanPark, shuttle: 0, hook: 0, strobe: 0,
  };
  d.frameZ.forEach((z, i) => { state[`f${i}z`] = z; state[`f${i}y`] = 0; });
  const initial = { ...state };
  const segments = [];
  const steps = [];
  let t = 0;
  let current = null; // index of the frame on the hook
  const SLOT_APPROACH = 26, SLOT_ENGAGED = 8; // gap is at -Z, so push toward -Z

  const tween = (dur, to) => {
    if (current !== null) {
      if ('shuttle' in to) to[`f${current}z`] = to.shuttle - SLOT_ENGAGED;
      if ('scan' in to) to[`f${current}y`] = to.scan - d.engage;
    }
    const from = { ...state };
    Object.assign(state, to);
    segments.push({ t0: t, t1: t + dur, from, to: { ...state } });
    t += dur;
  };
  const step = (label, real, detail, fn) => {
    const start = t;
    fn();
    steps.push({ label, real, detail, t0: start, t1: t });
  };
  const hold = (dur) => tween(dur, {});

  const cleat = d.cleatY(d.k + 1);
  const box = d.k + 1;
  const up = cleat + p.gap;
  const approach = d.engage + 25;

  step('Idle', 'most of the week', 'Supervisor MCU logs temperature, humidity and weight. The Jetson is powered off.', () => hold(1.2));
  step('Pre-flight check', '~1 min', 'Outside ≥ 15 °C, no rain, wind < 8 m/s, 10:00–16:00, last visit > 7 days ago. On a cool day the cabinet is pre-warmed to 25 °C first. Red work light on.', () => hold(1.2));
  step(`Forks to seam above box ${box}`, '~40 s', 'Both lift beams climb to 8 mm below the cleats of the box above the target box.', () => tween(2.2, { liftL: cleat - 8, liftR: cleat - 8 }));
  step('Forks swing in', '2 s', 'Servos turn the fork shafts 90° under the cleats.', () => tween(0.9, { forkL: 1, forkR: 1 }));
  step('Peel: left edge first', '~5 s', 'The left side rises 6 mm while the right side acts as a hinge. Propolis cracks along one edge at a fraction of the force.', () => tween(1.3, { liftL: cleat + 6 }));
  step('Peel: right edge', '~5 s', 'The right side follows. The load cells confirm the stack has come free before the full lift.', () => tween(1.3, { liftR: cleat + 6 }));
  step(`Lift upper stack ${p.gap} mm`, '~30 s', 'Lifts at 15 mm/s, starting slowly. Bees that fall drop straight back into the open box below.', () => tween(2.6, { liftL: up, liftR: up }));
  step('Scan beams to the rim', '~20 s', 'The shuttles pass over the top bars. Inductive sensors find the steel pins and the working gap.', () => tween(2.0, { scan: approach, shuttle: state.f0z + SLOT_APPROACH }));

  const pickFrame = (i, fast) => {
    const s = fast ? 0.55 : 1;
    const z0 = state[`f${i}z`];
    const target = z0 - d.gapWidth;
    tween(0.7 * s, { hook: 1 });
    tween(0.7 * s, { scan: d.engage });
    tween(0.5 * s, { shuttle: z0 + SLOT_ENGAGED });
    current = i;
    tween(0.7 * s, { shuttle: z0 + SLOT_ENGAGED - 10 });
    tween(0.3 * s, { scan: d.engage + 3 });
    tween(2.4 * s, { scan: d.engage + p.frameLift });
    for (let k = 0; k < 3; k++) { tween(0.12, { strobe: 1 }); tween(0.25, { strobe: 0 }); }
    tween(0.5 * s, { shuttle: target + SLOT_ENGAGED });
    tween(2.2 * s, { scan: d.engage + 30 });
    tween(0.9 * s, { scan: d.engage });
    current = null;
    tween(0.5 * s, { shuttle: target + SLOT_APPROACH });
    tween(0.6 * s, { scan: approach });
    tween(0.5 * s, { hook: 0 });
  };
  step('Frame 1: hook, nudge, lift', '~40 s', 'The hook swings in, its H-shaped plate slides around the pin neck and nudges the frame 10 mm into the gap to break burr comb. A 2 mm peel breaks the ear propolis, then the frame rises 300 mm, always vertical.', () => pickFrame(0, false));
  steps[steps.length - 1].captureNote = true;
  step('Frames 2–3', '~40 s each', 'Each frame is lowered into the gap left by the previous one, like a beekeeper working through a box. The last 20 mm go down at 3 mm/s.', () => { tween(0.8, { shuttle: state.f1z + SLOT_APPROACH }); pickFrame(1, true); tween(0.8, { shuttle: state.f2z + SLOT_APPROACH }); pickFrame(2, true); });
  step('…remaining frames', '≈9 min / box', 'The preview skips frames 4–10. In simulation the box stays open about 9 minutes; the rest of the stack stays closed.', () => hold(1.0));
  step('Scan beams park', '~20 s', 'Hooks fold up and the shuttles go back to the middle.', () => tween(1.8, { hook: 0, scan: d.scanPark, shuttle: 0 }));
  step('Rim check', '~10 s', 'The stack stops 30 mm above the box. A camera checks the contact edges for bees; if any are found, the robot waits and retries.', () => tween(2.2, { liftL: cleat + 30, liftR: cleat + 30 }));
  step('Rolling close', '~20 s', 'The left edge lands first at 2 mm/s, then the right. Contact moves across the rim so bees are pushed aside, not crushed.', () => { tween(1.4, { liftL: cleat - 8 }); tween(1.4, { liftR: cleat - 8 }); });
  step('Park & upload', '~1 min', 'Forks fold, beams park, red light off. Photos go to the Gratheon web app over Wi-Fi or LTE, and are stored locally too.', () => { tween(0.8, { forkL: 0, forkR: 0 }); tween(2.0, { liftL: d.liftPark, liftR: d.liftPark }); });
  // hidden reset so the loop is seamless (frames are inside the closed box)
  const reset = {};
  d.frameZ.forEach((z, i) => { reset[`f${i}z`] = z; reset[`f${i}y`] = 0; });
  tween(0.3, reset);

  const duration = t;
  const ease = (x) => x * x * (3 - 2 * x);
  const stateAt = (time) => {
    const tt = Math.max(0, Math.min(duration, time));
    let seg = segments[segments.length - 1];
    for (const s of segments) if (tt <= s.t1) { seg = s; break; }
    const span = seg.t1 - seg.t0;
    const u = span > 0 ? (tt - seg.t0) / span : 1;
    const e = ease(u);
    const out = {};
    for (const key of Object.keys(seg.to)) {
      const a = seg.from[key] ?? initial[key];
      const b = seg.to[key];
      out[key] = INSTANT.has(key) ? (u > 0 ? b : a) : a + (b - a) * e;
    }
    return out;
  };
  return { steps, duration, stateAt, initial };
}
