"""Generates docs/wiring.svg (block-level wiring of the Hive Tower).

    python3 docs/wiring_diagram.py
"""
from pathlib import Path
from xml.sax.saxutils import escape

W, H = 1200, 800
POWER, MOTOR, SIGNAL, USB, RF = "#c2410c", "#b91c1c", "#1d4ed8", "#7c3aed", "#047857"
out = []


def box(x, y, w, h, title, lines=(), fill="#ffffff", stroke="#374151", dash=False):
    d = ' stroke-dasharray="6 4"' if dash else ""
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="1.4"{d}/>')
    out.append(f'<text x="{x + 10}" y="{y + 19}" class="t">{escape(title)}</text>')
    for i, line in enumerate(lines):
        out.append(f'<text x="{x + 10}" y="{y + 37 + i * 15}" class="s">{escape(line)}</text>')
    return (x, y, w, h)


def wire(points, color, width=2.0, label=None, lx=None, ly=None, dash=False):
    d = " ".join(f"{'M' if i == 0 else 'L'}{x},{y}" for i, (x, y) in enumerate(points))
    da = ' stroke-dasharray="5 4"' if dash else ""
    out.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}"{da} marker-end="url(#a{color[1:]})"/>')
    if label:
        x, y = (lx, ly) if lx is not None else points[len(points) // 2]
        out.append(f'<text x="{x}" y="{y}" class="w" fill="{color}">{escape(label)}</text>')


def section(x, y, text):
    out.append(f'<text x="{x}" y="{y}" class="h">{escape(text)}</text>')


# ---------------------------------------------------------------- columns
section(20, 40, "POWER — PLINTH")
section(300, 40, "DISTRIBUTION — CROWN")
section(590, 40, "CONTROL — CROWN")
section(880, 40, "FIELD DEVICES")

box(20, 60, 240, 58, "Mains 230 V AC", ["RCD 30 mA, IP66 inlet, PE to earth rod"])
box(20, 150, 240, 74, "24 V PSU  ~350 W", ["Mean Well class, sealed box", "feeds the 24 V bus"])
box(20, 256, 240, 90, "Solar option", ["100 W panel → 24 V MPPT", "LiFePO4 24 V 20 Ah", "joins bus via ideal diode"], dash=True)

box(300, 60, 250, 104, "Fuse block (24 V bus)", ["F1  5 A  logic: Jetsons, board, ESP32", "F2 10 A  motor rail (switched)", "F3  5 A  heater  ·  F4 3 A  LEDs, fans", "(F3/F4 via board MOSFETs)"])
box(300, 196, 250, 104, "Safety chain → motor rail", ["E-stop (NC, latching)", "→ door interlock (NC reed)", "→ relay K1, held by ESP32 watchdog", "cuts 24 V motor power only"], fill="#fff7ed", stroke=MOTOR)
box(300, 332, 250, 88, "DC-DC converters", ["24→19 V 5 A  Jetson Orin Nano", "24→5 V 5 A  Jetson Nano, USB hub", "24→6 V 10 A  servos (motor rail)"])

box(590, 60, 250, 72, "Antenna fin (roof)", ["LTE ×2 + GNSS · Wi-Fi · LoRa 868", "surge arrestors at crown entry"], fill="#ecfdf5", stroke=RF)
box(590, 160, 250, 92, "Jetson Orin Nano", ["inspection brain, AI models", "Klipper host + Moonraker, NVMe", "USB: board, LTE modem, cameras"], fill="#f0fdf4")
box(590, 280, 250, 124, "BTT Octopus (Klipper MCU)", ["MOTOR0-3 step/dir → DM542 ×4", "MOTOR4-5 TMC2209 → shuttles", "PG6-PG13 endstops · PG14/15 pins", "PB6 PB7 PE12 PE13 servos", "PA8 strobe · PE5 red · PA2 heater"], fill="#eff6ff")
box(590, 432, 250, 92, "ESP32 + LoRa supervisor", ["always on, ~0.2 W · UART ↔ Orin", "HX711 ×2, BME280 ×2, DS18B20", "relays: Jetson power, K1 watchdog"], fill="#eff6ff")
box(590, 552, 250, 60, "Jetson Nano (old)", ["Entrance Observer · Ethernet ↔ Orin"], fill="#f0fdf4")

box(880, 60, 280, 60, "DM542 ×4 → NEMA23 ×4", ["lift L/R, scan L/R · TR16×4 screws"])
box(880, 138, 280, 48, "NEMA17 ×2", ["shuttle belts (TMC2209 StealthChop)"])
box(880, 204, 280, 48, "Servos ×4 (6 V)", ["fork L/R, hook L/R"])
box(880, 270, 280, 60, "Switches & sensors", ["6 endstops (NC) · 2 inductive M8", "door reed · E-stop monitor"])
box(880, 348, 280, 48, "Light & heat", ["strobe · 660 nm red · PTC heater"])
box(880, 414, 280, 48, "Cameras (USB)", ["4 frame cams · varroa sump cam"])
box(880, 480, 280, 48, "Load cells ×2 + climate", ["fork blocks · inside/outside air"])

# ---------------------------------------------------------------- wires
# mains and 24 V bus
wire([(140, 118), (140, 150)], POWER, 2.5, "230 V", 148, 138)
wire([(260, 187), (300, 112)], POWER, 3, "24 V", 232, 146)
wire([(260, 300), (282, 300), (282, 146), (300, 146)], POWER, 2.5, dash=True)
wire([(425, 164), (425, 196)], MOTOR, 3, "F2", 432, 184)
wire([(300, 90), (290, 90), (290, 376), (300, 376)], POWER, 2, "F1", 272, 240)
wire([(425, 300), (425, 332)], MOTOR, 2.5, "switched", 432, 320)
# logic power into the control column (lane x 560-576)
wire([(550, 350), (564, 350), (564, 206), (590, 206)], POWER, 2, "19 V", 520, 195)
wire([(550, 366), (572, 366), (572, 582), (590, 582)], POWER, 2, "5 V", 540, 600)
wire([(550, 120), (568, 120), (568, 330), (590, 330)], POWER, 2, "24 V", 552, 114)
wire([(550, 136), (576, 136), (576, 470), (590, 470)], POWER, 2)
# switched motor power runs around the outside to the field column
wire([(300, 270), (280, 270), (280, 640), (1172, 640), (1172, 90), (1160, 90)], MOTOR, 3, "24 V motor rail (switched) → DM542 ×4, board motor input", 600, 634)
wire([(425, 420), (425, 660), (1180, 660), (1180, 228), (1160, 228)], MOTOR, 2.2, "6 V servo bus", 600, 676)
# data
wire([(715, 132), (715, 160)], RF, 2, "LTE / GNSS / Wi-Fi", 722, 150)
wire([(590, 110), (584, 110), (584, 500), (590, 500)], RF, 1.8, "LoRa", 540, 454)
wire([(715, 252), (715, 280)], USB, 2, "USB", 722, 270)
wire([(590, 596), (580, 596), (580, 236), (590, 236)], USB, 1.6)
wire([(840, 186), (872, 186), (872, 438), (880, 438)], USB, 2, "USB", 846, 180)
wire([(840, 292), (848, 292), (848, 100), (880, 100)], SIGNAL, 1.6, "step/dir", 846, 274)
wire([(840, 306), (856, 306), (856, 162), (880, 162)], SIGNAL, 1.6)
wire([(840, 320), (862, 320), (862, 228), (880, 228)], SIGNAL, 1.6)
wire([(840, 346), (866, 346), (866, 300), (880, 300)], SIGNAL, 1.6)
wire([(840, 372), (880, 372)], SIGNAL, 1.6)
wire([(840, 500), (880, 504)], SIGNAL, 1.6)
wire([(590, 510), (556, 510), (556, 286), (550, 286)], SIGNAL, 1.4, "K1 hold", 500, 520)

# ---------------------------------------------------------------- legend
ly = 712
out.append(f'<text x="20" y="{ly}" class="h">LEGEND</text>')
for i, (c, name, dash) in enumerate([(POWER, "24 V / mains power", False), (MOTOR, "switched motor power", False), (SIGNAL, "signals (step/dir, I/O, UART)", False), (USB, "USB / Ethernet", False), (RF, "antenna coax", False), ("#374151", "optional", True)]):
    x = 20 + (i % 3) * 300
    y = ly + 22 + (i // 3) * 24
    da = ' stroke-dasharray="5 4"' if dash else ""
    out.append(f'<line x1="{x}" y1="{y - 4}" x2="{x + 34}" y2="{y - 4}" stroke="{c}" stroke-width="3"{da}/>')
    out.append(f'<text x="{x + 44}" y="{y}" class="s">{escape(name)}</text>')
out.append('<text x="20" y="784" class="s">Frame, crown plate and antenna ground bonded to PE and an earth rod. Motor cable shields grounded at the driver end only.</text>')

markers = "".join(
    f'<marker id="a{c[1:]}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>'
    for c in (POWER, MOTOR, SIGNAL, USB, RF)
)
svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Helvetica, Arial, sans-serif">
<defs>{markers}<style>
.t {{ font-size: 14px; font-weight: 700; fill: #111827; }}
.s {{ font-size: 12px; fill: #374151; }}
.h {{ font-size: 12px; font-weight: 700; letter-spacing: 1.5px; fill: #6b7280; }}
.w {{ font-size: 11px; font-weight: 700; }}
</style></defs>
<rect width="{W}" height="{H}" fill="#fafaf7"/>
<text x="20" y="22" style="font-size:16px;font-weight:700;fill:#111827">Hive Tower — electrical block diagram</text>
{chr(10).join(out)}
</svg>
"""
Path(__file__).with_name("wiring.svg").write_text(svg)
print("wrote docs/wiring.svg")
