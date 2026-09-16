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

**The chaos lamp, and how the negative-going problem is solved.**  One
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
