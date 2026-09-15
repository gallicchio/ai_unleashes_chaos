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
about 5 mA each of quiescent current against roughly 20 mA of actual load.  That
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

**One label per signal net.**  Paul draws no labels at all.  I place exactly one
per net, at the op-amp output, so the PCB gets readable net names (`x`, `-y`,
`z`, `xz`, `xy`) instead of `Net-(U1A-Pad1)`.  One label per name cannot hide a
wiring error the way a scattered set could, and every signal is still a drawn
wire from end to end.

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

**414 vias, most of them ground stitching.**  More than strictly needed.  They
cost nothing at a standard fab and they are what finally connected the last
island of the front pour, so they stay.

**No test points.**  Rails can be probed at C14 and C15 and the three variables
come out on BNCs, so nothing is unreachable, but a pad on each summing junction
would make this a better teaching board.  A rev B change.

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
