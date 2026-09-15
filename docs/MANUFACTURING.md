# Manufacturing

Two boards are built from one schematic: `lorenz` on two layers and
`lorenz-4layer` on four.  They are electrically identical and share a
footprint, a BOM and a pick-and-place file; the four-layer version adds
a solid ground plane and a +12 V plane between the outer layers.

Both pass ERC, DRC (with schematic parity) and the circuit checker with
zero violations.  `./make.py` rebuilds and rechecks everything from
scratch in about a minute.

## What to upload

| file | where it goes |
|---|---|
| `out/lorenz/lorenz-gerbers.zip` | the *Add gerber file* box |
| `out/lorenz/lorenz-bom.csv` | the BOM box (JLCPCB column layout) |
| `out/lorenz/lorenz-cpl.csv` | the CPL / pick-and-place box |

For the four-layer build use the matching files in `out/lorenz-4layer/`.

## Board options to pick

| option | value | why |
|---|---|---|
| Layers | 2 (or 4) | matches the gerber set you uploaded |
| Dimensions | 100 x 100 mm | the discounted size at all three houses |
| Thickness | 1.6 mm | the BNC flanges and the USB-C shell expect it |
| Surface finish | HASL or ENIG | either; ENIG is flatter for the 0.5 mm-pitch USB-C |
| Copper weight | 1 oz | the design rules assume it |
| Via covering | Tented | the ground stitching is dense; open vias would ruin the silkscreen |
| Assembly side | Top | every placed part is on the front |
| Parts source | JLCPCB (no consignment) | every line has an LCSC code |

## Cost

The board has **158 SMT joints** and **24 through-hole joints** on
23 BOM lines (10 JLCPCB Basic, 13 Extended).
Parts alone are **$71.69 per board**, of which
$61.17 is the pair of MPY634 multipliers.

**2 boards, two layers, fully assembled including through-hole**

| line | cost |
|---|---|
| bare PCBs | $2.00 |
| parts ($71.69 x 2) | $143.38 |
| assembly: setup $8.00 + stencil $1.50 + 316 SMT joints + 13 extended parts + 48 THT joints | $63.44 |
| shipping (DHL, worldwide) | $22.00 |
| **total** | **$230.82**  ($115.41 each) |

**5 boards, two layers, fully assembled including through-hole**

| line | cost |
|---|---|
| bare PCBs | $2.00 |
| parts ($71.69 x 5) | $358.44 |
| assembly: setup $8.00 + stencil $1.50 + 790 SMT joints + 13 extended parts + 120 THT joints | $85.84 |
| shipping (DHL, worldwide) | $22.00 |
| **total** | **$468.29**  ($93.66 each) |

**10 boards, two layers, fully assembled including through-hole**

| line | cost |
|---|---|
| bare PCBs | $4.00 |
| parts ($71.69 x 10) | $716.89 |
| assembly: setup $8.00 + stencil $1.50 + 1580 SMT joints + 13 extended parts + 240 THT joints | $123.19 |
| shipping (DHL, worldwide) | $22.00 |
| **total** | **$866.08**  ($86.61 each) |

Five **four-layer** boards come to about $491.29 ($98.26 each): the only change is the bare-board price.

Two boards is the sensible order: one for Paul and one to keep.

## The through-hole parts

5 parts are through-hole: **J1, J2, J3, J4, U5** -- the three BNC jacks, the DC/DC module and the USB-C shell tabs.
They are included in the BOM and the CPL, so a fab that offers
through-hole assembly will fit them.  If you would rather not pay for
that, deselect them at checkout and solder them yourself: they are the
four largest, easiest joints on the board and take about ten minutes.
Everything else is 0805, 1206, SOIC or SOT-89 and is hand-workable too.

## Check these orientations in the fab's preview

Rotation in a CPL is the one thing a fab's importer cannot verify for
you: a part whose LCSC drawing points a different way than the KiCad
footprint will be fitted turned.  The symmetric parts (every resistor
and capacitor) cannot go wrong.  These can:

| part | what to look for |
|---|---|
| D1 | cathode band toward the ground end |
| U1, U2 | pin 1 dot at the top-left, toward C16 / C18 |
| U3, U4 | pin 1 dot at the top-left |
| U5 | pin 1 (+Vin) at the left, printed face up |
| U6, U7 | tab toward the board centre; U6 tab is ground, U7 tab is -15 V |
| SW1 | switch 1 at the top, 'ON' toward the left |
| J1 | opening facing off the bottom edge |

## Parts, stock and alternates

Stock was checked at JLCPCB on 2026-09-15, the date on the silkscreen.

| ref | value | LCSC | JLC | unit | stock then | notes |
|---|---|---|---|---|---|---|
| C1,C4,C7 | 2.2nF | C28260 | basic | $0.0280 | 179,637 | C0G/NP0 50V |
| C10,C12,C13,C14,C15 | 10uF | C15850 | basic | $0.0840 | 6,702,077 | X5R 25V, 0805 - bulk |
| C11,C16,C17,C18,C19,C20,C21,C22,C23 | 100nF | C49678 | basic | $0.0190 | 18,183,154 | X7R 50V, 0805 - bypass |
| C2,C5,C8 | 100nF | C170182 | extended | $0.1870 | 193,311 | C0G/NP0 50V, 1206 |
| C3,C6,C9 | 470nF | C277483 | extended | $0.0320 | 190,079 | X7R 50V, 1206 |
| D1 | green | C2297 | basic | $0.0160 | 1,542,400 | Rails-OK indicator, runs from +12 V |
| F1 | 500mA | C17313 | extended | $0.0680 | 142,624 | Resettable PTC on the USB input |
| J1 | USB-C | C165948 | extended | $0.1860 | 230,097 | USB-C receptacle, power only (16 pin) |
| J2,J3,J4 | BNC | C41416668 | extended | $1.5490 | 410 | 50 ohm BNC jack, right angle, 4 ground posts on 8x8 mm |
| R1,R2 | 100k | C149504 | basic | $0.0060 | 4,893,299 |  |
| R11,R12 | 5.1k | C27834 | basic | $0.0060 | 3,917,491 |  |
| R13 | 4.7k | C17673 | basic | $0.0050 | 5,973,538 |  |
| R3 | 35.7k | C843989 | extended | $0.0150 | 2,783 |  |
| R4,R6 | 10k | C17414 | basic | $0.0040 | 53,835,303 |  |
| R5 | 1M | C17514 | basic | $0.0050 | 2,688,974 |  |
| R7 | 374k | C2933427 | extended | $0.0040 | 18,582 |  |
| R8,R9,R10 | 100R | C17408 | basic | $0.0040 | 10,085,527 |  |
| SW1 | SW_DIP_x06 | C54952 | extended | $0.5710 | 2,140 | 6-way SMD DIP switch, 2.54 mm pitch - integrator speed select |
| U1,U2 | LF412 | C15322 | extended | $0.9060 | 1,037 | Dual JFET-input op-amp (Paul's original part) |
| U3,U4 | MPY634 | C1523457 | extended | $30.5860 | 874 | Four-quadrant analog multiplier, W=(X1-X2)(Y1-Y2)/10 (Paul's part) |
| U5 | A0515S-2WR2 | C19272710 | extended | $1.5950 | 255 | Isolated 5V -> +/-15V 2W DC/DC module |
| U6 | 78L12 | C8615 | extended | $0.0990 | 52,154 | +12 V linear regulator (SOT-89: 1=OUT 2=GND 3=IN) |
| U7 | 79L12 | C8626 | extended | $0.1180 | 11,413 | -12 V linear regulator (SOT-89: 1=GND 2=IN 3=OUT) |

### If something is out of stock

**LF412CDR** (C15322)
  - TL072CDT / C6961 (JLCPCB Basic, $0.16) - same pinout, slightly higher bias current

**MPY634KU/1K** (C1523457)
  - AD633ARZ / C431243 - identical transfer function but SOIC-8, needs a different footprint; zero stock at JLCPCB 2026-09-15

**BNC-KYWE-295-W4-N** (C41416668)
  - HL2-BNC-KYWE / C48606310 (180 in stock)
  - MLD-BNC-KYWE-L29.5 / C52766468 (67 in stock)

**A0515S-2WR2** (C19272710)
  - A0515S-2WR2L / C20622616 (233 in stock)
  - A0515S-1WR3 / C5369388 (920 in stock, 1W) - same footprint and pinout; 1W is enough for this board's ~20 mA/rail but leaves less margin

The three BNC jacks are the thinnest line: about 400 in stock, so
roughly 130 boards' worth.  All three listed alternates are the same
'BNC-KYWE' body -- a 10 x 10 mm flange, four ground posts on an 8 x 8 mm
square and a centre pin -- so the footprint takes any of them, but
measure the drawing before you substitute.

## Bringing the board up

1. Plug in USB-C.  The green LED by the regulators should light: it runs
   from +12 V, so it only comes on once the whole supply chain works.
2. Measure the rails at C14 and C15: +12.0 V and -12.0 V, a few tens of
   millivolts of ripple at most.  The board draws about 20 mA a rail.
3. Set SW1 to *nice!* -- switches 1, 2 and 3 on, 4, 5 and 6 off.
4. Scope on x and z, X-Y mode, about 1 V/div on both.  The owl's face
   should appear within a second or so of power-up; the circuit starts
   itself, because the origin is an unstable fixed point and op-amp
   offset is more than enough to push it off.
5. `-y` is inverted on purpose, exactly as on Paul's original sheet.
6. Try *fast!* (all switches off) and *slow!* (4, 5, 6 only).

If nothing moves, the first thing to check is that both MPY634s are
powered: pin 16 at +12 V and pin 10 at -12 V.

