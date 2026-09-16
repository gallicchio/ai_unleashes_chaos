# Lorenz Attractor — Design Notes

Reference: Paul Horowitz, <https://seti.harvard.edu/unusual_stuff/misc/lorenz.htm>

## The equations and how the circuit implements them

    dx/dt = s(y - x)          s = 10
    dy/dt = r*x - y - x*z     r = 21.3 .. 37.0, set by the knob (28 at 56 %)
    dz/dt = x*y - b*z         b = 8/3

Every coefficient is `1 MEG / R`.  Time is scaled by `tau0 = 1M * C`.
Circuit voltages represent the dimensionless variables at **0.1 V per unit**
(`V = 0.1 * var`), which is why the multiplier terms carry a factor of 100.

| Integrator | Op-amp | Feedback | Summing inputs | Yields |
|---|---|---|---|---|
| x  | U1A | C_x | R1 100k from `-y`, R2 100k from `x` | dx/dt = 10(y - x) |
| -y | U1B | C_y | R3 27k + RV1 0..20k from `x`, R4 10k from `-xz/100`, R5 1M from `-y` | dy/dt = r x - y - xz |
| z  | U2A | C_z | R6 10k from `-xy/100`, R7 374k from `z` | dz/dt = xy - 2.674 z |

Coefficient check: 1M/100k = **10** = s; 1M/(27k..47k) = **37.0..21.3** = r;
1M/374k = **2.674** = b (8/3 = 2.6667, 0.3 % high); 1M/1M = 1; 1M/10k = 100
cancels the multipliers' /100.

All three are *lossy* integrators — R2, R5 and R7 are local feedback around
their own op-amp, which is what produces the `-x`, `-y` and `-bz` damping terms.

### Multipliers (MPY634, Vout = A*B/10)
* **U3**: X1 = `x`, X2 = GND, Y1 = GND, Y2 = `z`  ->  (x)(-z)/10 = **-xz/100** (normalised)
* **U4**: X1 = `-y`, X2 = GND, Y1 = `x`, Y2 = GND ->  (-y)(x)/10 = **-xy/100** (normalised)

The sign inversions come free by swapping the differential inputs — no extra
op-amps.  Z1 ties to the output, Z2 to ground, SF (pin 3) left open for the
standard 10 V scale factor.

### Signal levels (k = 0.1 V/unit)
`x` = +/-2.0 V, `y` = +/-2.7 V, `z` = 0..4.8 V, multiplier outputs <= 1.0 V.
Comfortable inside +/-12 V rails.

## Changes from Paul's original, and why

1. **USB-C power instead of a bench +/-15 V supply.**
   5 V in -> `A0515S-2WR2` isolated 2 W module -> +/-15 V -> `78L12`/`79L12`
   -> **+/-12 V**.  The module alone is unregulated and rises toward +/-18 V at
   light load, which is uncomfortably close to the MPY634's +/-18 V absolute
   maximum; the two linear regulators pin the rails at +/-12 V and also strip
   the module's switching ripple.  MPY634 is specified from +/-8 V, so +/-12 V
   is well inside its range and leaves >2x headroom on every signal.

2. **100 ohm series resistors on the three BNC outputs.**  Isolates the
   LF412 outputs from coax capacitance (a JFET-input op-amp driving a metre of
   RG-58 will otherwise ring) and survives a shorted output.  Error into a
   1 Mohm scope input is 0.01 %.  They sit *outside* the feedback/summing
   network, so the equations are untouched.

3. **Speed switching.**  No 3-pole 3-position switch is stocked anywhere, so
   the three values are built up in parallel per integrator:
   `C_fast` 2.2 nF C0G is always fitted; a 6-way DIP switch adds 100 nF (bank A,
   poles 1-3) or 470 nF (bank B, poles 4-6) to all three integrators at once.

   Poles 1-3 carry the 470 nF and poles 4-6 the 100 nF, so the six sliders
   read left to right as a two-digit binary number:

   | setting | poles 1-3 (470 nF) | poles 4-6 (100 nF) | C      | Paul's value |
   |---------|--------------------|--------------------|--------|--------------|
   | fast!   | off                | off                | 2.2 nF | 2000 pF      |
   | nice!   | off                | **on**             | 102 nF | 0.1 uF       |
   | slow!   | **on**             | off                | 472 nF | 0.47 uF      |
   | slower! | **on**             | **on**             | 572 nF | —            |

   `slower!` is the fourth speed both banks on give you for nothing: tau =
   572 ms, a fifth slower again than `slow!`.  It is printed on the silkscreen
   table with the other three.  Contact resistance is
   ~100 mohm in series with C; against a 100 kohm..1 Mohm integrating resistor
   that is a 1-ppm effect.

4. **The isolation is used.**  The converter's output common is *not* tied to
   the USB ground.  The board has two grounds: `GND` downstream of the
   converter (op-amps, multipliers, BNC shells, everything a scope touches) and
   `GNDU` upstream of it (the USB connector and its shell, the CC pull-downs,
   the input bulk).  They are separate copper pours with a 1 mm
   gap, and the converter straddles it.

   The reason is specific to this board: its whole purpose is to be watched on
   an oscilloscope, whose ground clip is bonded to mains earth.  Tie the
   grounds and the loop runs scope earth -> BNC shell -> board ground -> USB
   cable -> laptop -> earth, and whatever that loop picks up lands on signals
   whose full scale is 2 V.  Isolated, the scope clip is the only thing that
   decides where analog ground sits.

   Three parts bridge the barrier, all of them already in the BOM:

   | part | value | what it does |
   |---|---|---|
   | R18 | 1 M | drains static, so the analog side cannot float up on charge |
   | C25 | 2.2 nF | 720 ohm at the converter's 100 kHz, 1.2 Gohm at 60 Hz |
   | JP1 | solder jumper, open | bridge it to give the isolation up |

5. **U2B drives the chaos lamp's reference.**  Paul also used only 1.5 of his
   two LF412s; this board spends the spare half on something useful.  A 12k /
   33k divider from +12 V makes **+3.20 V**, U2B buffers it, and that becomes
   the common *anode* of one RGB lamp whose three cathodes are driven from z,
   x and -y through 470 ohm, 3.9k and 1.5k.

   Holding the anode above every signal's maximum is what makes signals that
   swing either side of zero drive an LED at all: each die conducts when its
   own signal falls a forward drop *below* +3.2 V, so the lamp is brightest
   where the signal is most negative.

   | die | from | lights when | peak | lit |
   |---|---|---|---|---|
   | red | z | z < +1.4 V, the bottom of each excursion | 2.5 mA, 38 mcd | 28 % of the time |
   | green | x | x < +0.6 V, most of the -x wing | 0.7 mA, 36 mcd | 87 % |
   | blue | -y | -y < +0.6 V, most of the +x wing | 2.2 mA, 39 mcd | 84 % |

   The three peak brightnesses are within 8 % of each other, so no single
   colour dominates: blue and green mix through the wings and red flashes in
   at the bottom of each excursion.  That is option 038 of the hundred wirings
   rendered in `docs/lamp/` -- mostly deep blue, with a fast swirl through the
   colour wheel whenever the trajectory changes wings.  U2B sources 3.7 mA at
   the peak and 1.2 mA on average.

   The part is **MHPA3528CRGBCT** (LCSC C2962095), common anode: pin 1 is the
   anode, pin 2 blue, pin 3 green, pin 4 red.  Its common-*cathode* twin
   MHPC3528CRGBCT is the same dies in the same package with pins 1 and 4
   swapped, so the two are not interchangeable on this board.

   The lamp taps the op-amp outputs *before* the 100 ohm series resistors, so
   none of its current flows in the BNC output impedance.

6. **An r knob.**  R3 is split into a fixed 27k and RV1, a Bourns 3386P 20k
   single-turn cermet trimmer, which sweeps `r = 1M / (27k + RV1)` from 21.3
   to 37.0.  That covers the whole interesting range: r = 24.06 where the
   wings stop being an attractor, r = 24.74 where the two fixed points let go,
   Lorenz's 28 at 56 % of rotation, and up to 37 where the orbit tightens and
   speeds up.  About 0.05 in r per degree of screw at r = 28, so a setting can
   be found again by hand.

   RV1 is wired as a rheostat -- terminal 3 and the wiper -- with **terminal 1
   tied to the wiper**.  That short is deliberate: it takes the unused section
   of track out of circuit, and if grit ever lifts the wiper the full 20k
   track still bridges the branch, so r falls to its minimum instead of the
   `r x` term vanishing altogether.  A worn wiper fails open; this wiring does
   not let it.

7. **A synchronisation input, on its own BNC.**  `SYNC IN X` is a fourth BNC
   on the left edge of the board, in line with the x output on the right,
   because another board's x output is what you plug into it.  From there:
   RV2 as a plain voltage divider across the incoming signal, then R19 = 100k
   into the dy/dt summing junction, where it meets the x branch before the
   two of them reach the summing node.  R20 = 1M holds the wiper node at
   ground if the wiper ever lifts.

   It has to be that junction and it has to be x.  The junction inverts, so
   an injected voltage always arrives with a minus sign, and diffusive
   coupling `g(x1 - x2)` is only available where the local term already
   carries a plus -- which is the `+ r x` term of dy/dt and, through R1, the
   `+ s y` term of dx/dt.  dz/dt has no such term: an injected z arrives as
   `-g z1`, which is anti-diffusive, and simulated, the error grows with g
   rather than shrinking.  Sign-correct coupling on z *does* lock, so this is
   not a conditional-Lyapunov obstruction -- it just needs a `-z` output this
   circuit does not make.

   **The weight knob.**  RV2 is a divider, not a rheostat in series with R19,
   and that is the whole trick: the weight is then

       g  =  1M / 100k  x  (fraction turned)  =  0 .. 10

   which is *linear* in the knob, within 5 % -- the wiper's own source
   impedance peaks at a quarter of the 20k track against R19's 100k.  A
   rheostat would have made g go as 1/R and crammed everything interesting
   into the first tenth of the rotation.  At the counter-clockwise stop the
   wiper sits on ground and the branch contributes exactly nothing, which is
   the same thing as unplugging the cable; at the clockwise stop it is the
   g = 10 the board was already sized for.

   Simulated (two boards, b = 1M/374k, 20 mV of initial mismatch, the
   receiver's r knob turned down by g so both solve the same equations):

   | knob | g | what happens |
   |---|---|---|
   | 0 %   | 0    | nothing at all; the two boards ignore each other |
   | 20 %  | 2    | no lock, ever |
   | 50 %  | 5    | still no lock: close approaches, then bursts apart |
   | ~70 % | ~7   | threshold, measured at r = 32 |
   | 80 %  | 8    | locks in about 5 time units -- 2.2 s at `slow!` |
   | 100 % | 10   | locks in about 3 time units -- 1.5 s at `slow!` |

   So the bottom seven tenths of the knob is "influence you can see but
   never enough", and the top three tenths is "locked", which is the range
   the demonstration wants.

   Because the coupling lands on the `r x` term it also adds g to the
   receiving board's own r.  Drive at r = 32 and the receiver's r knob then
   reads 32 down to 22 as the sync knob goes 0 to full -- the two knobs track
   each other one for one across their whole travel, which is why the r knob
   was sized to sweep more than 10.

   Both boards float on purpose, so they also need a ground in common before
   any of this works: a coax from a BNC splitter carries board 1's ground on
   its screen and does both jobs at once, or run a second wire between a
   SCOPE GND loop on each board.  The 20k divider loads an output that drives
   through 100 ohm by 0.5 %, so the scope on the other leg of the splitter
   sees no difference.

## Part selection (JLCPCB stock checked 2026-09-15)

| Ref | Part | LCSC | Package | Stock | Unit |
|---|---|---|---|---|---|
| U1,U2 | LF412CDR | C15322 | SOIC-8 | 1037 | $0.91 |
| U3,U4 | MPY634KU/1K | C1523457 | SOIC-16-300mil | 874 | $30.59 |
| U5 | A0515S-2WR2 | C19272710 | SIP-7 THT | 255 | $1.60 |
| U6 | CJ78L12 | C8615 | SOT-89 | 52154 | $0.10 |
| U7 | CJ79L12 | C8626 | SOT-89 | 11413 | $0.12 |
| J1 | TYPE-C-31-M-12 | C165948 | SMD | 230097 | $0.19 |
| J2-J5 | BNC-KYWE-295-W4-N | C41416668 | THT right-angle | 410 | $1.55 |
| SW1 | DSIC06LSGET | C54952 | SMD DIP-6 | 2140 | $0.57 |
| D1 | MHPA3528CRGBCT | C2962095 | PLCC-4 3.5x2.8 | 9796 | $0.07 |
| RV1,RV2 | 3386P-1-203LF | C116287 | 9.5 mm square THT | 767 | $0.45 |

LF412 and MPY634 are Paul's exact parts — both still stocked, both in
hand-solderable wide-body packages, so the circuit stays literally his.

