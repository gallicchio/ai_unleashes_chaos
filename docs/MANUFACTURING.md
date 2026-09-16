# Manufacturing

One board, two layers, 100 x 100 mm.  It passes ERC, DRC (with
schematic parity), the circuit checker and the fab-package checks with
zero violations, and `./make.py` rebuilds and rechecks everything from
scratch in about forty seconds.

The copper is split: the USB input has its own ground plane in the
bottom-left corner, isolated from the analog ground by the converter and
bridged only by R21, C25 and JP1.  Do not scratch across the 1 mm gap.

## What to upload

| file | where it goes |
|---|---|
| `out/lorenz/lorenz-gerbers.zip` | the *Add gerber file* box |
| `out/lorenz/lorenz-bom.csv` | the BOM box (JLCPCB column layout) |
| `out/lorenz/lorenz-cpl.csv` | the CPL / pick-and-place box |

## Board options to pick

| option | value | why |
|---|---|---|
| Layers | 2 | what the gerber set contains |
| Dimensions | 100 x 100 mm | the discounted size at all three houses |
| Thickness | 1.6 mm | the BNC flanges and the USB-C shell expect it |
| Surface finish | HASL or ENIG | either; ENIG is flatter for the 0.5 mm-pitch USB-C |
| Copper weight | 1 oz | the design rules assume it |
| Via covering | Tented | the ground stitching is dense; open vias would ruin the silkscreen |
| Assembly side | Top | every placed part is on the front |
| Parts source | JLCPCB (no consignment) | every line has an LCSC code |

## Cost

The board has **186 SMT joints** and **35 through-hole joints** on
28 BOM lines (14 JLCPCB Basic, 14 Extended).
Parts alone are **$74.31 per board**, of which
$61.17 is the pair of MPY634 multipliers.

**2 boards, two layers, fully assembled including through-hole**

| line | cost |
|---|---|
| bare PCBs | $2.00 |
| parts ($74.31 x 2) | $148.62 |
| assembly: setup $8.00 + stencil $1.50 + 372 SMT joints + 14 extended parts + 70 THT joints | $73.13 |
| shipping (DHL, worldwide) | $22.00 |
| **total** | **$245.75**  ($122.88 each) |

**5 boards, two layers, fully assembled including through-hole**

| line | cost |
|---|---|
| bare PCBs | $2.00 |
| parts ($74.31 x 5) | $371.55 |
| assembly: setup $8.00 + stencil $1.50 + 930 SMT joints + 14 extended parts + 175 THT joints | $105.58 |
| shipping (DHL, worldwide) | $22.00 |
| **total** | **$501.14**  ($100.23 each) |

**10 boards, two layers, fully assembled including through-hole**

| line | cost |
|---|---|
| bare PCBs | $4.00 |
| parts ($74.31 x 10) | $743.11 |
| assembly: setup $8.00 + stencil $1.50 + 1860 SMT joints + 14 extended parts + 350 THT joints | $159.66 |
| shipping (DHL, worldwide) | $22.00 |
| **total** | **$928.77**  ($92.88 each) |

Four layers would cost about $524.14 for five ($104.83 each) -- the only change is the bare-board price --
and buys almost nothing here: tracks cover 1.2 % of the back copper, so
the pour on the two-layer board is already 98.8 % of an unbroken ground
plane.  That is why this project ships one board.

Two boards is the sensible order: one for Paul and one to keep.

## Uploading to JLCPCB

| upload | file |
|---|---|
| gerbers | `lorenz-gerbers.zip` |
| BOM | `lorenz-bom.csv` |
| placements | **`lorenz-cpl_jlc_corrected.csv`** |
| paste into the order notes | `lorenz-assembly-notes.txt` |

Use the *corrected* placement file for JLCPCB, and the plain
`lorenz-cpl.csv` for anyone else.  JLCPCB places from its own model of
each part, and for some parts that model is turned differently from
KiCad's footprint, so a file that is right everywhere else is wrong by
a fixed angle there.  The angle belongs to the part number, not to the
package: it is a property of JLC's drawing of that one LCSC part.

| parts | LCSC | turned by |
|---|---|---|
| U1, U2 | C15322 | 270 deg counter-clockwise |
| U3, U4 | C1523457 | 270 deg counter-clockwise |
| SW1 | C54952 | 270 deg counter-clockwise |
| U6 | C8615 | 180 deg counter-clockwise |
| U7 | C8626 | 180 deg counter-clockwise |
| J2, J3, J4, J5 | C41416668 | 90 deg counter-clockwise |

Everything else -- every resistor, every capacitor -- is symmetric or
already agrees, and is left alone.  `check_outputs.py` proves the two
files differ in nothing but those angles.

### What the preview gets wrong, and why it does not matter

JLCPCB draws each part from its own model, and that model has its own
idea of where the middle of the part is.  For some of ours it does not
agree with the middle of the body, so the preview draws the part beside
its pads however the placement file is written.  There is nothing in a
CPL that can say *use your origin, not mine* -- the only lever is the
coordinate itself, and moving that to flatter a preview would put a
wrong number in the file for everybody else.

Three of the parts that look wrong there cannot go in wrong at all:

| part | holes | fits at |
|---|---|---|
| U5, the DC/DC module | 5, with a gap where pin 3 would be | one orientation |
| RV1, RV2, the trimmers | 3 in an L | one orientation |

A hole pattern that does not map onto itself under a quarter turn is
its own key: there is exactly one way the part goes into the board, and
an operator putting legs through holes cannot do anything else with it.
`check_outputs.py` re-derives that from the board file on every build,
so it stays true rather than merely having been true once.

The BNCs are *not* keyed -- four symmetric ground posts and a centre
pin -- which is why their 90 degree correction is in the table above,
and why the barrel pointing off the board edge is worth a glance.

J1, the USB-C receptacle, sits at the board edge deliberately: its body
is flush with the edge so a cable with a moulded body can seat.  A 3D
preview showing it overhang the edge is showing it correctly.

### Still unverified

One rotation has never actually been seen, because JLCPCB has no
drawing of the part to turn:

* **C2962095** -- D1, the RGB lamp -- JLCPCB has no drawing of this part, so it appears as an unknown-part checkerboard and its rotation cannot be read off the preview at all.

It is left uncorrected.  D1 is the one part on this board where a
preview you cannot read costs you something, so it gets its own
paragraph below and its own line in the assembler's notes.

## Check these before you pay

The one thing that cannot be checked from here is how the assembler
turns each part.  Your CPL says which way; their library has its own
idea of zero degrees, and where the two disagree a polarised part goes
in backwards.  JLCPCB renders every part on the board before you
confirm the order.  Compare that rendering with this table and with
`lorenz-assembly-top.pdf`, which prints 1:1.

The lamp, the DIP switch and the two trimmers carry a filled triangle
on the front silkscreen, printed just outside the outline and pointing
at pin 1.  It is drawn from the real pad, so it is right by
construction; use it as the reference when you compare the rendering.
The SOICs and the two SOT-89s are not marked that way because KiCad's
own footprints already print a pin-1 dot or a notched corner on them,
and two marks beside each other are two marks to reconcile.

| part | what to look for | should be |
|---|---|---|
| D1 | the RGB lamp's pin 1, the common anode | bottom left, the corner the triangle points at |
| RV1 | the r trimmer, terminal 1 | the lower pad, the one the triangle points at; the screw is on top |
| RV2 | the sync weight trimmer, terminal 1 | same part, same way up, directly above RV1 |
| J5 | SYNC IN X | barrel pointing off the left edge, in line with the x output on the right |
| U6 | 78L12, SOT-89 | pin 1 (OUT) on the left, tab to ground |
| U7 | 79L12, SOT-89 | pin 1 (GND) on the left; its tab is at -15 V, not ground |
| U1, U2 | LF412 SOIC-8 | pin 1 dot at the top left |
| U3, U4 | MPY634 SOIC-16W | pin 1 dot at the top left |
| J1 | USB-C receptacle | opening facing off the board edge |
| SW1 | 6-way DIP switch | slider 1 at the left, the part's own "ON" printing facing the "ON ->" arrow on the board |
| U5 | the converter, hand-fitted | pin 1 is the square pad, at the left, marked on the silkscreen |
| F1 | PTC fuse | not polarised |

The four BNCs and the converter are through-hole and can be checked
by eye after assembly: the converter's own printed face carries its pin
numbers.

## The through-hole parts

8 parts are through-hole: **J1, J2, J3, J4, J5, RV1, RV2, U5** -- the four BNC jacks, the two trimmers, the DC/DC module and the USB-C shell tabs.
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
| D1 | pin 1, the common anode, at the bottom left -- the die order is red, green, blue anticlockwise from it |
| RV1, RV2 | terminal 1 at the bottom, terminal 3 at the top, wiper to the right |
| J5 | barrel off the left edge, the mirror image of J2, J3 and J4 |
| U1, U2 | pin 1 dot at the top-left, toward C16 / C18 |
| U3, U4 | pin 1 dot at the top-left |
| U5 | pin 1 (+Vin) at the left, printed face up |
| U6, U7 | tab toward the board centre; U6 tab is ground, U7 tab is -15 V |
| SW1 | slider 1 at the left; pin 1 is on the side *away* from the part's "ON" legend, which is where the board's triangle points |
| J1 | opening facing off the bottom edge |

## Parts, stock and alternates

Stock was checked at JLCPCB on 2026-09-15, the date on the silkscreen.

| ref | value | LCSC | JLC | unit | stock then | notes |
|---|---|---|---|---|---|---|
| C1,C4,C7,C25 | 2.2nF | C28260 | basic | $0.0280 | 179,637 | C0G/NP0 50V |
| C10,C12,C13,C14,C15 | 10uF | C15850 | basic | $0.0840 | 6,702,077 | X5R 25V, 0805 - bulk |
| C11,C16,C17,C18,C19,C20,C21,C22,C23,C24,C26,C27,C28,C29 | 100nF | C49678 | basic | $0.0190 | 18,183,154 | X7R 50V, 0805 - bypass |
| C2,C5,C8 | 100nF | C170182 | extended | $0.1870 | 193,311 | C0G/NP0 50V, 1206 |
| C3,C6,C9 | 470nF | C277483 | extended | $0.0320 | 190,079 | X7R 50V, 1206 |
| D1 | RGB | C2962095 | extended | $0.0650 | 9,796 | Common-anode RGB lamp, PLCC-4: red = z, green = x, blue = -y |
| F1 | 500mA | C17313 | extended | $0.0680 | 142,624 | Resettable PTC on the USB input |
| J1 | USB-C | C165948 | extended | $0.1860 | 230,097 | USB-C receptacle, power only (16 pin) |
| J2,J3,J4,J5 | BNC | C41416668 | extended | $1.5490 | 410 | 50 ohm BNC jack, right angle, 4 ground posts on 8x8 mm |
| R1,R2,R19 | 100k | C149504 | basic | $0.0060 | 4,893,299 |  |
| R11,R12 | 5.1k | C27834 | basic | $0.0060 | 3,917,491 |  |
| R13 | 3.9k | C17614 | basic | $0.0015 | 296,958 |  |
| R14 | 1.5k | C4310 | basic | $0.0015 | 585,325 |  |
| R15 | 470R | C17710 | basic | $0.0025 | 3,140,647 |  |
| R16 | 12k | C17444 | basic | $0.0021 | 456,483 |  |
| R17 | 33k | C17633 | basic | $0.0028 | 570,100 |  |
| R3 | 27k | C17593 | basic | $0.0013 | 238,446 |  |
| R4,R6 | 10k | C17414 | basic | $0.0040 | 53,835,303 |  |
| R5,R18,R20 | 1M | C17514 | basic | $0.0050 | 2,688,974 |  |
| R7 | 374k | C2933427 | extended | $0.0040 | 18,582 |  |
| R8,R9,R10 | 100R | C17408 | basic | $0.0040 | 10,085,527 |  |
| RV1,RV2 | 20k | C116287 | extended | $0.4458 | 767 | 20k single-turn cermet trimmer, 9.5 mm square, top adjust.  Two are fitted: RV1 sets r, as a rheostat with terminal 1 tied to the wiper so grit means maximum resistance and never an open; RV2 sets the sync weight, as a plain divider across the incoming signal so the weight is linear in the knob and reaches zero |
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

**MHPA3528CRGBCT** (C2962095)
  - MHPC3528CRGBCT / C2962096 is the same part with a common *cathode*: same footprint, same dies, but pins 1 and 4 swap roles, so the board would have to change with it

**3386P-1-203LF** (C116287)
  - 3386P-1-103LF / C116281 (10k, 1700 in stock) with R3 raised to 33k gives r = 23 to 30 -- a narrower sweep that never leaves the chaotic region

The BNC jacks are the thinnest line: about 400 in stock and four per
board, so roughly 100 boards' worth.  All three listed alternates are the same
'BNC-KYWE' body -- a 10 x 10 mm flange, four ground posts on an 8 x 8 mm
square and a centre pin -- so the footprint takes any of them, but
measure the drawing before you substitute.

## Bringing the board up

1. Plug in USB-C.  The chaos lamp should light within a second: it
   hangs on +12 V through U2B and on all three integrator outputs, so
   it only comes on once the whole board works.
2. Measure the rails at C14 and C15: +12.0 V and -12.0 V, a few tens of
   millivolts of ripple at most.  The board draws about 20 mA a rail.
3. Set SW1 to *nice!* -- switches 4, 5 and 6 on, 1, 2 and 3 off.
4. Scope on x and z, X-Y mode, about 1 V/div on both.  The owl's face
   should appear within a second or so of power-up; the circuit starts
   itself, because the origin is an unstable fixed point and op-amp
   offset is more than enough to push it off.
5. `-y` is inverted on purpose, exactly as on Paul's original sheet.
6. Try *fast!* (all switches off), *slow!* (1, 2, 3 only) and
   *slower!* (all six on).  Poles 1-3 switch in the 470 nF and poles
   4-6 the 100 nF, so the six sliders read left to right as a
   two-digit binary number: 00, 01, 10, 11.
7. Turn RV1 clockwise to raise r and anticlockwise to lower it.  About
   a third of the way round from the anticlockwise stop the attractor
   collapses into one wing and the lamp settles on a colour; back the
   other way and it starts wandering again.

If nothing moves, the first thing to check is that both MPY634s are
powered: pin 16 at +12 V and pin 10 at -12 V.

