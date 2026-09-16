# Design review

Written after the board passed everything, going back over it looking for what
is wrong rather than what is finished.  Things I changed are marked **fixed**;
things I decided to live with say why.

## The circuit

**MPY634 is end-of-life at TI.**  The datasheet is stamped OBSOLETE, though the
grey shading shows that applies to the AM/BM/SM grades and not to the KP/KU
commercial parts this board uses.  874 MPY634KU were in stock at JLCPCB on
2026-09-15, which is 437 boards' worth, so this is not a problem today and is
a problem eventually.  The honest successor is the AD633 -- same A*B/10
transfer function, so the resistor values would not change at all -- but every
AD633 variant showed **zero** stock at JLCPCB, which fails the "do not wait for
out-of-stock items" requirement outright.  I chose availability now over
longevity, and documented the swap.

**Running the multipliers at +/-12 V rather than +/-15 V.**  The MPY634's
accuracy is specified at +/-15 V; at +/-12 V it is inside its +/-8 V to +/-18 V
operating range but no longer at its rated operating point.  It does not matter
here -- the largest signal on the board is z at 4.8 V and the largest multiplier
output is about 1 V -- and the alternative is worse: the converter is
unregulated, and at this board's light load its +/-15 V output climbs toward
+/-17 V, which is close enough to the +/-18 V absolute maximum that a different
vendor's module could take the part out.  Regulating down to +/-12 V also
removes the converter's 100 kHz ripple, which the op-amps' PSRR would not.

**The 470 nF "slow" capacitor is X7R, not C0G.**  Nobody makes a 470 nF C0G
part in a package you would put on this board.  X7R has a voltage coefficient,
so at the slow setting the integrator's time constant depends a little on the
signal across it, which is a mild nonlinearity fed straight into a nonlinear
system.  The attractor is structurally stable and this only wobbles the time
scale by a few percent, but it is a real compromise: the "nice!" setting uses a
100 nF **C0G** part precisely because that one can be had, and it is the
setting I would trust for anything quantitative.

**Six switch actuators for three speeds.**  I would rather have fitted one
three-position knob.  No supplier stocks a three-pole three-position switch, and
the three integrators have to change together or the attractor distorts, so the
capacitance is built up in parallel behind two banks of three DIP poles.  The
silkscreen carries the table.  This is the part of the design I like least.

**The regulators cost a quarter of the board's current.**  78L12 and 79L12 draw
about 5 mA each of quiescent current against roughly 25 mA of actual load
(op-amps, multipliers, the lamps and the lamp reference).  That
is the price of clean rails and it fits inside the 2 W converter comfortably;
with the 1 W part it would be tight, which is why the 2 W part is the one in
the BOM.

**Checked and fine:** JFET inputs mean bias current through R5 = 1 M contributes
50 microvolts, not millivolts.  The switch sits between the capacitor and the
op-amp *output*, both low-impedance nodes, so contact resistance and leakage do
nothing.  The circuit self-starts, because at r = 28 the origin is a saddle and
op-amp offset is orders of magnitude more than the push it needs.  The LF412
has 3 MHz of gain-bandwidth against about 700 Hz of circuit bandwidth at the
fastest setting.

## The schematic

**U1 does two rows.**  Paul's sheet reads as three integrators stacked down the
page, and so does this one, but one LF412 carries the x and -y integrators, so
the packages do not line up with the rows.  That is inherent in using Paul's
part; the alternative is three separate packages, which is worse.

**A2 rather than A3.**  Spreading out far enough that no label touches anything
else, with the equations, the parameter table and the attractor all on one
sheet, did not fit on A3.  It prints legibly reduced to A3.

**Labels: one readable name per net, and as many drawn notes as help.**  Paul
draws no labels at all.  This sheet has exactly one KiCad label per net -- `x`,
`-y`, `z`, `xz`, `xy`, `SJ_X`, `SJ_Y`, `SJ_Z` -- so that the netlist, the DRC
report and `check_circuit.py` all talk about the circuit in its own vocabulary
rather than in `Net-(U1A-Pad1)`.  That is a different thing from the *drawn*
annotation: the name `x` also appears beside the bus every time it leaves for a
load, exactly the way Paul does it, because that is a comment and not a
connection.  A KiCad label is a wire; a drawn note is not, and the sheet is
allowed to have plenty of the second kind.

## The PCB

**The BNC footprint is drawn from a vendor drawing, not a part in my hand.**
This is the single biggest risk in the package.  The dimensions come from the
SAMZO drawing's own "PCB LAYOUT" box -- four ground posts on an 8 x 8 mm square,
centre pin in the middle -- and the three listed alternates are all the same
"BNC-KYWE" body, but none of that is the same as offering up a real connector.
`out/lorenz/lorenz-assembly-top.pdf` prints 1:1 for exactly this check.

**The routing wanders.**  A person would have routed this more tidily; the maze
router takes the cheapest path it can find, which is not always the prettiest.
At these frequencies -- the fastest setting puts about 700 Hz through a 1 Mohm
scale of impedances -- trace length and shape are irrelevant, and the ground
plane under every signal matters far more than the route above it, so I left it.

**438 vias, most of them plane stitching.**  More than strictly needed.  They
cost nothing at a standard fab and they are what finally connected the last
island of the front pour, so they stay.  The USB island gets a denser lattice
(3.5 mm rather than 4.5 mm) because it is small enough that a few tracks can
carve it into pieces.

**Thirteen probe pads, and deliberately none on the summing junctions.**  Every
DC rail gets a plated hole with its name beside it -- +5 V, +/-15 V, +/-12 V,
both grounds -- and so do the five interesting signals: the three outputs and
the two multiplier products, `-xz/100` and `-xy/100`.  Three wire loops take a
scope's ground clip.

The summing junctions do not get one, and that is a choice rather than an
oversight.  A summing junction is a virtual earth: its *voltage* is zero by
construction and carries no information, while the quantity the annotation
names -- dx/dt -- exists there only as a current.  Worse, it is the one node on
the board where a scope probe would actually change the answer: 15 pF of probe
capacitance against a 1 Mohm scale of impedances is a 15 microsecond pole
hanging off the integrator's input.  What you can do instead, and what makes
this a good teaching board, is check that each junction really sits at 0 V --
and for that the resistor pads themselves are the right place to put a tip.

**Fixed while reviewing:**

* Four M3 mounting holes.  Three BNCs along one edge means cables lever on the
  board every time they are plugged; it needs standoffs, and there was nowhere
  to put a screw.  D1 and R13 moved to clear the fourth corner.
* The `.gitignore` inherited from the Python template has unanchored `lib/` and
  `parts/` rules.  `hardware/lib/` -- every symbol and footprint this project
  draws itself -- was not in the repository at all.  Anchored them to the root.
* `check_schematic.py` found one note hanging off the left edge of the frame,
  then immediately caught the mounting-hole caption when I dropped it on the
  title block.
* Ground pads were starving the zone's thermal reliefs (an 0805 or SOIC pad is
  too small for two spokes).  Switched to `THT_THERMAL`: solid on SMD, relieved
  on through-hole so the BNCs and the converter stay hand-solderable.

## Four bugs the checks caught that I would not have

Worth recording, because each one produces a board that looks right:

1. **Vias were checked against track clearance, not their own.**  A 0.6 mm via
   needs more room than a 0.3 mm track; the router was dropping them 0.1 mm
   from other nets.
2. **A custom-shaped pad is not centred on its anchor.**  The SOT-89 tab's
   bounding box sits 1.9 mm off its pad position, so the router happily ran the
   -15 V rail straight across U6's ground tab.
3. **A track halo has to include the next track's half width.**  Two 0.3 mm
   tracks were ending up 0.05 mm apart.
4. **A net has to be allowed onto its own copper.**  Clearance does not apply
   between a pad and the track landing on it -- without that rule a 0.3 mm
   USB-C pad, which its neighbours' halos completely cover, is unreachable.

Numbers 1 and 3 are clearance violations DRC would have caught anyway.  Number
2 is a short.  Number 4 just made two nets unroutable.


## Prompt 2: what changed, and what I decided against

**The isolation is now used.**  The A0515S-2WR2 really is isolated -- 1 kV, no
DC path between input and output -- and the board was throwing that away by
tying COM to the USB ground.  It no longer does.  GND (everything downstream of
the converter: both op-amps, both multipliers, the BNC shells) and GNDU (the
USB connector, its shell, the CC pull-downs, the input bulk, the +5 V lamp) are
two separate copper pours with a 1 mm gap, and U5 straddles the gap with its
own 5.08 mm barrier over it.

Why this is worth doing on *this* board in particular: its entire purpose is to
be looked at on an oscilloscope, and an oscilloscope ground clip is bonded to
mains earth.  With the grounds tied, the loop runs scope earth -> BNC shell ->
board ground -> USB cable -> laptop or charger -> back to earth, and whatever
current that loop carries appears as an offset and a 50/60 Hz wobble on signals
whose full scale is 2 V.  Isolate, and the scope clip is the *only* thing that
decides where analog ground sits.

The barrier is not left completely open: R21 = 1 M drains static so the analog
side cannot float up on charge, and C25 = 2.2 nF gives the converter's ~100 kHz
common-mode current a low-impedance way home without doing anything at all at
60 Hz (1.2 Gohm there).  Both were already in the BOM, so the whole
arrangement costs two 0805s.  JP1 is an open solder jumper: bridge it and the
two grounds are hard-tied again, which is the right thing if you ever want to
drive the board from a supply that shares a ground with your signal source.

The argument against, which I do not find convincing here: a floating section
is a section nobody has defined the potential of, and if you touch it while it
is charged you get a small spark.  At +/-12 V into a 1 M bleeder there is
nothing to discharge.

**The chaos lamp, and how the negative-going problem is solved.**
*(Superseded at prompt 4, which flipped the lamp to a common anode at +3.2 V
and rewired the colours; see the prompt 4 section at the foot of this file.
The argument below is unchanged -- only the sign of it is.)*  One
common-cathode RGB LED, red from x, green from -y, blue from z, with the
*cathode* held at -1.5 V by the half of U2 that Paul never needed.  That single
trick is what makes the negative excursions usable: each colour now lights only
when its own signal rises above -1.5 V plus that colour's forward drop, which
works out at x > +0.25 V, y < -1.1 V and z > +1.1 V.

Red therefore marks the +x wing and green the -x wing, so the lamp alternates
red and green as the trajectory switches wings -- which *is* the chaos -- while
blue brightens with z and drops out at the bottom of each excursion.  In
"slow!" (tau = 472 ms) that happens on a timescale you can watch; in "nice!" it
is a flicker; in "fast!" it averages into a colour.

The nonlinearity Paul worried about is real and, for this purpose, a feature:
an LED with a series resistor is a soft threshold, and a threshold is exactly
what turns a continuous variable into "which wing am I on".  A proportional
current drive would give a smooth fade and lose the switching.  The three
resistors are sized for roughly equal *perceived* brightness from the
datasheet's luminous intensities -- 1.5 k for red, 6.8 k for green (green is
about five times brighter per milliamp and sits where the eye is most
sensitive) and 4.7 k for blue -- so the colour you see is a fair mix rather
than green with hints.  Peak current is 2.2 mA for all three together, which
U2B sinks without noticing.

`check_circuit.py` recomputes the reference, every threshold, every peak
current and the worst-case reverse voltage on each junction from the resistors
that are actually fitted, so none of those numbers can drift away from the
board.

**Three rail lamps instead of one "rails OK".**  The old single green LED hung
off +12 V and claimed to mean "rails OK".  It did not: it said nothing about
-12 V and nothing about the USB input, so it could sit there looking healthy
with half the board dead.  Now there is one lamp per rail -- yellow on +5 V
(on the USB side of the barrier, where it belongs), green on +12 V, white on
-12 V -- each with its own name on the silkscreen next to it.  Three different
colours, all three JLCPCB Basic parts, so a dark one names itself without
anybody reading the legend.  Not red: red reads as "fault" when here it would
mean the rail is up, and red, green and blue are already spoken for by the
chaos lamp.

**The four-layer board is gone.**  The measurement that decided it: on the
routed two-layer board, tracks cover **1.2 % of the back copper** and 2.6 % of
the front.  The back is therefore already 98.8 % of an unbroken ground plane,
and a dedicated plane layer recovers that last one per cent.  Against that,
four layers costs roughly four times the bare-board price, doubles the number
of gerber sets somebody can pick the wrong one of, and -- now that the ground
is split for isolation -- the split would have to be drawn on four layers
instead of two.  The fastest thing on the board is a 100 kHz switching
converter and the signals are DC to about 700 Hz.  It bought nothing worth
having, so it is out; `route.py` and `gen_pcb.py` still take a layer count, and
the history is in git.

**QR codes drawn from scratch.**  Nothing in KiCad draws one and the build must
work from a bare clone, so `scripts/qrcode_gen.py` is a QR encoder: byte mode,
versions 1-6, level L or M, Reed-Solomon over GF(256), all eight masks scored.
Two things made this worth the trouble rather than dangerous:

* It is checked three ways.  Its Reed-Solomon, data placement and format
  information match the `qrcode` package module for module; its mask penalty
  scoring matches segno's on 200 random matrices; and the 32 published format
  words come out of its BCH.  Both reference libraries were installed only to
  check against and are not build dependencies.
* The finished board is decoded back.  `check_outputs.py` reads the rectangles
  out of `lorenz.kicad_pcb`, samples them into a matrix and runs the decoder,
  which verifies the BCH, every Reed-Solomon block's syndromes, and the
  payload.  A QR code is the one thing on this board that can be completely
  wrong while still looking right.

Two details that would each have shipped a broken code.  The modules have to
*touch*: a decoder finds the symbol by the 1:1:3:1:1 run lengths across a
finder pattern, and any gap at all breaks that -- I measured it, a 10 % gap is
already fatal.  And the code has to be mirrored in board coordinates, exactly
like back-layer text, or it reads correctly only through the board; I settled
that by plotting a back-layer legend beside it and seeing which way round the
legend read.

**The switch table.**  Rebuilt on both the sheet and the silkscreen.  On the
board it now sits directly over the switch, with each `off`/`ON` cell centred
on the slider it refers to, a silkscreen bar between the two banks of three,
the speed naming the row, and the capacitance and time constant in their own
columns on the right.  The middle capacitor bank moved 4 mm further from its
row to make the band above the switch wide enough -- that asymmetry is there
for the legend, and it is the right trade.

**Cross-probing.**  It was not working because the footprints carried no link
back to their symbols.  Each footprint now stores the symbol's UUID as its
sheet path, plus `sheetname` and `sheetfile`, and the project file carries the
root sheet in its `sheets` list.  Clicking a part in one editor now highlights
it in the other.

**A fifth bug, found by the reproducibility check.**  Splitting the ground
made the build stop being byte-reproducible: four consecutive builds of an
unchanged design produced four different boards.  The router and the placement
were both deterministic; the zone *filler* was not.  Two zones of equal
priority on one layer are filled in whichever order the filler's threads reach
them, and the two orders differ in the last nanometre of every arc -- about
0.01 % of the copper area, scattered as thousands of sub-micron slivers.
Giving GNDU a higher priority than GND ranks them, and eight consecutive fills
then give one answer instead of four.  The outlines do not overlap, so the
ranking changes nothing about the board.

Worth recording because of how it would have shown up: not as a wrong board,
but as a `git diff` of four thousand lines every time anybody rebuilt, which is
exactly the noise that hides a real change.

**Still not right, and I know it:**

* The routing still wanders.  The maze router takes the cheapest path, not the
  prettiest one, and a person would have done better.
* The board is dense.  100 x 100 mm holds 84 footprints, sixteen of which are
  probe pads, and the front silkscreen is close to full.  Anything else would
  need a bigger board.
* `ON` on a DIP switch is marked on the package, and I have not held one.  The
  silkscreen says so rather than guessing a direction.


# Prompt 3: the full review

Worked through item by item.  Where a check could be made to run every build
rather than once, it was; those are named.

## Four bugs, in order of how badly they would have hurt

**1. DRC was not reading this project's design rules at all.**  `pcbnew` writes
a `.kicad_pro` next to any board it saves, with a default set of rules, and
`make.py` only regenerated the real one at the very end -- after DRC.  So every
"DRC: 0 violations" this project has ever printed was measured against KiCad's
defaults, not against the rules in `gen_project.py`.  Regenerating the project
file immediately before DRC turned up **203 violations** that had been there
all along.  The zone filler had the same problem from the other side: it works
from the *board's* settings, and a board made by `CreateEmptyBoard()` carries
defaults, so the pour was backing off 0.25 mm from holes while the rule asked
for 0.3.  Both are fixed; `apply_rules()` now sets them on the board before
anything is filled.

This is the worst kind of bug: a check that reports success while checking
nothing.  Everything below was found only because it started working.

**2. Every via violated the annular-ring rule.**  0.6 mm outside diameter on a
0.3 mm drill is 0.15 mm of annulus, against a rule asking for 0.25.  Vias are
now 0.8/0.3 -- 0.25 mm -- and the rule sits at 0.20, because the binding item
turned out to be the four shell tabs of KiCad's own USB-C footprint, which are
0.20.  0.20 is still well above the 0.13-0.15 mm the three fabs quote; the
board's own vias and pads are all 0.25 or better.

**3. Stitching vias were necking the pour beside through-hole pads.**  A via
placed 1.5 mm from a 2.2 mm ground pad leaves a 0.08 mm isthmus of copper
between them -- legal for clearance, since they are the same net, and caught
only by the minimum-connection-width check.  It is also pointless: a
through-hole pad already connects every layer, so it *is* a stitching via.
The router now refuses to place one within 0.35 mm of a drilled pad and skips
the per-pad via for through-hole pads entirely.

**4. Both multipliers had no designator on the silkscreen.**  The legend
placer avoided pads and other legends but not the package body, so `U3` and
`U4` were printed neatly underneath the chips.  It now treats every
footprint's courtyard as occupied, which is the rule that should always have
applied: silk under a part is silk nobody reads.

## Packages, rotations and pin assignments

Checked mechanically: 82 footprints, none flipped, all on `F.Cu`, every
rotation 0 or 90 degrees, no mirrored text on the front.  (Two *symbols* are
mirrored on the sheet -- U2B and the lamp, because the lamp is fed from the
right -- which has no effect on the board.)

`scripts/check_pinout.py` now runs in every build.  It writes out each IC's pin
table from the datasheet named in the code, compares it with the symbol this
project actually uses, and -- where KiCad ships the same part -- compares it
again with KiCad's library, drawn by other people from the same document:

| part | datasheet | second source |
|---|---|---|
| MPY634 SOIC-16 | TI SBFS017A, "PIN CONFIGURATIONS", 'KU' column | `Analog:MPY634KU` |
| LF412 SOIC-8 | TI SLOS091 | `Amplifier_Operational:LM2904` |
| CJ78L12 SOT-89 | Changjiang outline: 1 OUT, 2 GND, 3 IN | `Regulator_Linear:MC78L05_SOT89` |
| CJ79L12 SOT-89 | Changjiang outline: 1 GND, 2 IN, 3 OUT | `Regulator_Linear:L79L05_SOT89` |
| A0515S-2WR2 | YLPTEC pin table, dual-output column | -- |
| MHPC3528CRGBCT | MEIHUA LPDS-0001482 Rev.1 p.2 | -- |

Two of these are worth calling out.  The SOT-89 tab is pin 2, which is *ground*
on the 78L12 and the **input** on the 79L12 -- so U7's tab sits at -15 V, not
at ground, and a footprint drawn for the positive part would have shorted it.
And the A0515S's pins are 1, 2, 4, 5, 6 with no pin 3; the gap is the module's
own isolation barrier, and this board puts the plane split through it.

## Power, traced from the connector

    J1 VBUS x4 -> F1 500 mA PTC -> +5V -> C10 10uF + C11 100nF -> U5 pin 1
    J1 GND x4 + shell ------------------------------------------> U5 pin 2
    U5 pin 6 +15V -> C12 + C26 -> U6 pin 3 -> U6 pin 1 +12V -> C27 + C14
    U5 pin 4 -15V -> C13 + C28 -> U7 pin 2 -> U7 pin 3 -12V -> C29 + C15
    U5 pin 5 COM  -> GND
    +12V -> U1.8  U2.8  U3.16  U4.16     each with its own 100 nF
    -12V -> U1.4  U2.4  U3.10  U4.10     each with its own 100 nF

| rail | load | headroom |
|---|---|---|
| +12 V | 20.0 mA | 78L12 rated 100 mA |
| -12 V | 19.5 mA | 79L12 rated 100 mA |
| +15 V | 25.0 mA | module rated 67 mA; minimum load 7 mA, so 3.5x over it |
| -15 V | 24.5 mA | as above |
| USB 5 V | 186 mA at 80 % efficiency | 500 mA PTC |

Regulator dissipation is (15 - 12) x 25 mA = 75 mW each in a SOT-89, which is
a seventh of what the package will take.  The converter delivers 743 mW of its
2 W.  Nothing here is close to a limit, and the one number that could have
been -- the module's **minimum** load of 7 mA per rail, below which its output
climbs -- is met 3.5 times over, which is why the rails sit near 15 V and the
regulators keep their dropout margin.

**Decoupling** was the one place the review actually changed the circuit.  The
78L12 and 79L12 datasheets are characterised with 0.33 uF in and 0.1 uF out,
"located as close as possible", and the 10 uF bulk capacitors were 15 mm away.
Four 100 nF parts, C26 to C29, now sit at the regulators' own pins.

## Impedances, and what drives what

| source | impedance | load | error |
|---|---|---|---|
| LF412 output | ~0.01 ohm closed loop | 100 ohm to a 1 Mohm scope | 0.01 % |
| LF412 output | " | summing resistors 10k..1M into a virtual earth | none |
| LF412 output | " | MPY634 X/Y input, 10 Mohm | none |
| MPY634 output | 1 ohm, +/-10 mA | 10k summing resistor | none |
| U2B output | ~0.01 ohm | three LEDs, 2.2 mA peak | none |
| 4.7k/33k divider | 4.1k Thevenin | LF412 JFET input, 50 pA | 0.2 uV |

The one thing to say out loud: the BNC outputs are meant for a **1 Mohm**
scope input.  Into a 50 ohm termination the 100 ohm series resistor divides the
signal by three.  That is the right trade for a circuit whose output is a slow
voltage and whose op-amp does not want a metre of coax hanging directly off it.

## Input ranges against the datasheets

| part | limit | worst case here |
|---|---|---|
| MPY634 X, Y, Z inputs | +/-10 V linear, +/-Vs absolute | 2.6 V |
| MPY634 output | about +/-9 V at +/-12 V rails | 1.2 V |
| LF412 common mode | about +/-8 V at +/-12 V rails | 0 V, and -1.5 V at U2B |
| LED reverse | 5 V | 1.2 V, computed per colour from the netlist |
| converter input | 4.5 - 5.5 V | 5 V USB |
| 78L12 / 79L12 input | 35 V max, ~14.2 V min for 12 V out | 15 - 15.5 V |
| C0G 2.2 nF, 50 V | 50 V | 5 V |

JFET-input op-amps invert their output if the common mode goes below the
negative limit; both inverting inputs are virtual earths at 0 V and U2B's
non-inverting input is at -1.5 V, so nothing goes near it.

## Configuration pins

`SF` on both multipliers is left open, which selects the 10 V scale factor --
the one the whole resistor network is sized for; a resistor to -Vs there would
change it to 3 V and multiply every product by 3.3.  Both multipliers' six NC
pins are unconnected.  On the USB-C receptacle, CC1 and CC2 get **one 5.1k
each, not a shared one**, which is what tells a source to turn 5 V on; D+, D-,
SBU1 and SBU2 are unconnected; all four VBUS and all four GND pins are tied.
The DIP switch has no configuration pins.  `check_circuit.py` asserts all of
this from the netlist.

## The split ground, re-examined

Still the right call, and now checked rather than asserted.  `gen_pcb.py`
refuses to build if any net has pads on both sides of the gap, apart from the
converter and the three bridge parts, and refuses if any track or via strays
across.  The consequences that matter:

* The only analog-side connection to anything mains-referenced is the scope's
  own ground clip, which is the point.
* No return current crosses the split, because no net does.
* The converter's common-mode current has a 2.2 nF path home (720 ohm at
  100 kHz) that does not run through the analog ground plane.
* With nothing plugged in, the analog side sits within a millivolt of USB
  ground through R18 = 1 M rather than floating on accumulated charge.

**Converter noise, with numbers.**  The module's output ripple is of order
100 mVpp at about 100 kHz.  The linear regulators give perhaps 25 dB there and
the op-amps' own supply rejection another 30 dB, which puts roughly 200 uV of
switching residue at an output whose full scale is 2 V.  That is -80 dB, and
it is a hundred times *below* the MPY634's own output feedthrough of around
30 mV.  An RC between the converter and the regulators would buy another 36 dB
for two resistors; it is not worth the dropout margin it costs, because the
multiplier would still be the limit.  Physically the switcher, its input
capacitors and its 6 mm switching loop are all inside the island in the
bottom-left corner, behind a 1 mm gap, as far from the multipliers as the board
allows.

## What I would bet on if these came back not working

In order:

1. **Part rotation in assembly.**  The CPL says which way each part is turned,
   but the fab's library has its own idea of zero degrees, and for polarised
   parts -- D1, the two regulators, the USB-C receptacle, the DIP switch --
   a disagreement fits the part backwards.  This is the one failure I cannot
   check from here, and it is the most common first-article failure there is.
   `docs/MANUFACTURING.md` now carries a table of every polarised part and
   which way it faces, to check against the fab's own rendering before paying.
2. **The BNC footprint**, still drawn from SAMZO's drawing rather than from a
   connector in my hand.  It is through-hole: if it is wrong it will not fit,
   which is at least loud.  `lorenz-assembly-top.pdf` prints 1:1.
3. **A substituted MPY634.**  It is the one part on the board with no real
   second source, and an "equivalent" would not be.
4. Everything else -- values, nets, equations, ranges, decoupling -- is either
   proved from the netlist on every build or checked against a datasheet here.


# Prompt 4: a knob, a second board, and the lamp as it is actually built

## The lamp, settled

Option 038 of the hundred renderings, chosen by the person the board is for.
**MHPA3528CRGBCT**, common *anode*, held at **+3.20 V** by U2B from a 12k/33k
divider off +12 V; **z -> red through 470 ohm, x -> green through 3.9 k, -y ->
blue through 1.5 k**.  Every die now lights on the way *down*: it conducts when
its own signal falls a forward drop below +3.2 V.

| die | from | conducts below | peak | lit |
|---|---|---|---|---|
| red | z | +1.45 V | 2.5 mA, 38.1 mcd | 28 % of the time |
| green | x | +0.60 V | 0.7 mA, 36.3 mcd | 87 % |
| blue | -y | +0.60 V | 2.2 mA, 38.9 mcd | 84 % |

Three peaks within 8 % of one another, so the colour is a mix rather than one
die with hints of the others; the lamp is never fully dark; and U2B sources
3.7 mA at the peak.  Worst-case reverse on any junction is 2.8 V of the 5 V
rating, at the top of z with the knob fully clockwise.

The part matters: MHPC3528CRGBCT is the same dies in the same package with
pins 1 and 4 swapped, and fitting it here would put the red die's cathode on
the anode rail.  `check_pinout.py` transcribes the polarity drawing from the
data sheet (LPDS-0001481 rev 1 p.2) and compares it against the drawn symbol.

## The knob

R3 splits into 27 k fixed plus **RV1**, a Bourns 3386P 20 k single-turn cermet
trimmer, giving `r = 1M/(27k + RV1)` from **21.3 to 37.0**.

The two questions worth answering before fitting a potentiometer to a circuit
whose author dislikes them:

*Is it controllable?*  310 degrees of mechanical travel for 15.8 in r.  The
slope is steepest at the clockwise stop and even there it is 0.088 in r per
degree; at r = 28 it is 0.05.  Seventeen degrees of screw moves r by one.

*Is there anything at the end of it?*  At the counter-clockwise stop the
attractor is gone -- the trace spirals into a fixed point and the lamp stops
changing colour, which is the most visible thing on this board.  27 % of the
way round the wings become an attractor again; 33 % the fixed points lose
stability; 56 % is Lorenz's 28; and from there to the stop the red flashes
thin from two in five to one in seventeen as the orbit tightens.

*What happens when the wiper wears?*  Terminal 1 is tied to the wiper, so the
section in circuit is wiper-to-3 and the unused section is shorted out.  A
speck of grit that lifts the wiper leaves the whole 20 k track bridging
terminal 1 to terminal 3: r goes to its minimum and the attractor collapses,
which is a symptom you can see and recover from, rather than an open circuit
that deletes the `r x` term.  `check_circuit.py` asserts the tie.

The wiper carries no current that matters: it is in series with 27 k into a
virtual earth, so a wiper resistance that ages from 0.1 ohm to 1 kohm changes
r by 0.05 %.

## The synchronisation input

R19, 100 k from a pad marked SYNC IN into the dy/dt summing junction, with
R20 = 1 M holding the pad at ground when nothing is connected.

The junction inverts, so an injected voltage always arrives negative, and
diffusive coupling `g(u1 - u2)` is only available where the local term already
carries a plus.  In these three equations that is `+r x` in dy/dt and `+s y`
in dx/dt -- and no term at all in dz/dt.

Simulated, two boards at b = 1M/374k with 20 mV of initial mismatch, RK4 over
60 time units:

| channel | locks | threshold | what else must change |
|---|---|---|---|
| x into `+r x` | yes | g ~ 7 | nothing: turn the receiver's knob down by g |
| -y into `+s y` | yes | g ~ 4 | R1 -> 1M/(10-g), and g < 10 always |
| z | no | -- | impossible: the sign is wrong and there is no -z |

x gets the pad because the knob absorbs the offset the coupling adds to r.
At g = 1M/100k = 10 the error falls below a millivolt in 5 time units: 2.4 s
at `slow!`.  Drive at r = 32, receive at r = 22.

z is worth stating carefully.  It is *not* a conditional-Lyapunov obstruction:
sign-correct diffusive coupling `+g(z1 - z2)` synchronises in simulation at
quite modest g.  What blocks it here is that the inverting junction turns an
injected z1 into `-g z1`, which is anti-diffusive -- the error grows with g --
and producing `+g z1` would need a -z output this circuit does not have.

## Pin 1, and the rotation problem

Every part that can be fitted turned -- U1 through U7, D1, SW1, RV1 -- carries
a filled triangle on the front silkscreen, outside its outline, pointing at
pin 1.  `add_pin1_marks()` reads the real pad position and the real courtyard
from the placed footprint and picks the edge pad 1 is nearest, so the mark
cannot disagree with the footprint; a mark with nowhere to go is a build
failure, not a silent omission.

## The USB-C setback, which was wrong

The HRO receptacle's mating face is 3.65 mm in front of its footprint origin.
The origin was 6 mm from the board edge, so the opening sat 2.35 mm inside the
laminate -- far enough that a cable with a large moulded body would foul the
edge before the plug seated.  J1 moved to y = 95.85: the body is half a
millimetre inside the edge, and its printed outline lands exactly on the
0.15 mm silk-to-edge rule, which is as far out as the silkscreen allows
without being clipped.

## Rotations, corrected

For a KiCad chip footprint **rot = 0 is horizontal** and rot = 90 is vertical;
this project had it backwards, and had described vertical parts as horizontal.
Series resistors are now rot = 0 and lie along the signal flow -- R1-R7 into
the summing junctions, R8/R9/R10 into the BNCs, R13-R15 into the lamp, F1 in
the +5 V line -- and shunts are rot = 90 and stand across it.  Every one now
matches the way it is drawn on the schematic.
