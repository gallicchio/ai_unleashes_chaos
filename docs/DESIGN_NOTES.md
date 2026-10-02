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
   two LF412s; this board spends the spare half on something useful.  A 15k /
   33k divider from +12 V makes **+3.75 V**, U2B buffers it, and that becomes
   the common *anode* of one RGB lamp.  Holding the anode above the signals is
   what lets signals that swing either side of zero drive an LED at all: a die
   conducts when the voltage at its cathode falls a forward drop below the
   anode.

   In rev B each cathode sees a small resistor network rather than one
   resistor:

   | die | fed from | through | what it is for |
   |---|---|---|---|
   | red | -y | R15 = 1.5k | the main feed: 73 % of what the cathode sees |
   | | x | R22 = 8.2k | blends in about a fifth as much x, which shifts where in each orbit red peaks |
   | | +12 V | R23 = 8.2k | lifts red's cathode 1.6 V, so red lights over the +x wing and fades on the -x wing |
   | green | x | R13 = 24k | lights over most of the orbit, brightest on the -x wing; 24k because green is the most efficient die per milliamp |
   | blue | z | R14 = 2.2k | the bottom of every loop, either wing |
   | | -12 V | R24 = 36k | lowers blue's cathode 0.7 V, which moves its threshold up the z swing |

   R23 and R24 are what make rev B saturated: they move red's and blue's
   thresholds independently of the shared anode, so the dies take turns
   instead of all being on at once.  Simulated with the corrected LED model,
   red is lit 75 % of the time (peak 1.8 mA), green 91 % (peak 0.13 mA) and
   blue 41 % (peak 0.7 mA).  Weighted for how bright each colour looks, the
   three peaks come out within a factor of two of each other.  U2B sources 1.9 mA at the
   peak and 0.6 mA on average, and R23 draws at most 1.5 mA from +12 V.

   What you see at `slow!`: on the +x wing the colour runs violet through
   magenta to red, on the -x wing green through cyan to azure, and through
   the crossings blue to orange.  It is vivid -- neither near white nor near
   black -- about 90 % of the time, and its vivid moments fill 11 of the 12
   30-degree hue sectors about equally.  At `fast!` the eye sees only the
   average, a steady violet.

   **Rev A's lamp was different, and duller than predicted.**  It was option
   038 of `docs/lamp/` -- 12k/33k for +3.20 V, z to red through 470 ohm, x to
   green through 3.9k, -y to blue through 1.5k -- chosen with an LED model the
   boards proved wrong: it came out mostly blue with some green.  See "What the
   rev A boards showed" and "The rev B search" below; rev B is candidate 1 of
   that search.

   The part is **MHPA3528CRGBCT** (LCSC C2962095), common anode: pin 1 is the
   anode, pin 2 blue, pin 3 green, pin 4 red, numbered clockwise from the
   bottom left in the top view.  Its common-*cathode* twin MHPC3528CRGBCT is
   the same dies in the same package with pins 1 and 4 swapped, so the two
   are not interchangeable on this board.  D1's footprint, position and
   rotation are exactly rev A's, which rev A's boards proved right.

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

## Choosing the chaos lamp

The RGB lamp is the one part of this board that is not Paul's.  It is also the
only part whose value could not be derived from the equations, so it was
chosen by building a model of the lamp and looking at every wiring of it.

### Why it is not obvious

An LED is a threshold device and the three signals swing either side of zero,
so "drive the LED from x" has no obvious meaning.  Four things have to be
decided together, and they interact:

1. **common anode or common cathode** -- which end of the dies the reference
   holds, and therefore whether a die lights when its signal goes *up* or
   *down*;
2. **which signal drives which die** -- six permutations of x, -y, z onto red,
   green, blue;
3. **the reference voltage** -- where the threshold sits inside each signal's
   swing;
4. **the three series resistors** -- which set both the peak brightness and,
   because luminous efficiency is nonlinear in current, the *shape* of each
   die's response.

Get these wrong and the lamp is a two-colour lamp with a third die soldered on
for decoration, or a white blur, or dark.

### The model:  `scripts/lamp_model.py`

Rather than guess, the board's colour is computed from the data sheet:

* **I-V per die**, as an ideal diode with a series resistance, back-solved so
  that each die passes exactly its data-sheet 20 mA at its data-sheet forward
  voltage:  `i_s = 0.020 exp(-(Vf20 - 0.020 Rs) / (n VT))`.
* **Luminous intensity**, `mcd = Iv20 (i / 20 mA)^gamma`, with gamma = 1.05
  for red and 1.15 for green and blue.  *(Corrected after the boards came
  back: this section said gamma came from the data sheet's own
  relative-intensity curve.  It did not.  That curve is a straight line,
  gamma = 1, and it stops at 1 mA.  Worse, gamma > 1 for green and blue is
  the wrong direction for InGaN.  See "What the rev A boards showed".)*
* **Spectrum**, a Gaussian from each die's peak wavelength and FWHM.
* **Colour**, by integrating that spectrum against the **CIE 1931 2-degree
  observer** (the real table, embedded at 5 nm) to get XYZ, then the D65 sRGB
  matrix to get a screen colour.
* **Adaptation**, a luminance compression before the sRGB gamma, because a
  dark-adapted eye looking at a small lamp does the same thing.  Without it
  the picture is a hard on/off and every shade in between is lost.

The model is self-checked, 13 assertions, run by `./make.py` before anything
else: equal-energy white must land on x = y = 1/3; the luminosity function
must peak at 555 nm; four published monochromatic chromaticities must come
back right; each die's computed dominant wavelength must be within 5 nm of the
data sheet's; the I-V must return 20 mA at the quoted Vf; and D65 must map to
neutral sRGB.  A colour model that cannot reproduce those is not worth
pointing at a circuit.

### The search:  `scripts/lamp_gallery.py`

The Lorenz system is integrated for real -- the same RK4 trajectory that draws
the owl on the back of the board -- and the three node voltages are fed into
the model sample by sample.  The result is rendered as a strip of time: left
to right, wrapping at the end of each row, about four minutes of the lamp at
the `slow!` setting in one picture.

**660 wirings** were rendered: 2 lamp parts x 6 permutations x 11 reference
voltages x 5 resistor rules.  Options that came out black, white or one flat
colour were dropped, and the rest thinned by a greedy max-min pass to the
**100 most different from each other**, written to `docs/lamp/` with an index
page to flip through.

### The pick, and what it has in common

Option **038** was chosen by eye from that gallery.  Measuring the nine
favourites against the other ninety-one afterwards showed what the eye had
been doing:

| | the nine | the other 91 |
|---|---|---|
| hue coverage (of a 24-segment wheel) | **0.71** | 0.42 |
| brightness balance (dimmest peak / brightest) | **0.375** | 0.056 |
| mean saturation | **0.269** | 0.347 |
| fraction of the time the lamp is lit | **1.00** | 0.91 |
| fraction of the time the *dimmest* die is lit | **0.19** | 0.00 |

The last row is the whole story: in **47 of the 100**, one of the three dies
never comes on at all.  None of the nine favourites was one of those.  The two
resistor rules that aim for equal *perceived* brightness rather than equal
current are 26 of the 100 options but 7 of the 9 favourites.  Ranked by
`hue coverage x sqrt(balance) x lit`, the nine come in at 1, 4, 5, 7, 11, 16,
22, 25 and 42 out of 100 -- and 038 comes first.

### What that settled, for rev A

* **Common anode**, MHPA3528CRGBCT, held at **+3.20 V** by the spare half of
  U2 -- so each die lights on the way *down*, and the lamp is never dark.
* **z to red through 470 ohm, x to green through 3.9k, -y to blue through
  1.5k.**
* Peak brightnesses of 38.1, 36.3 and 38.9 mcd -- within 8 % of each other,
  which is what makes the colour a mix rather than one die with hints of the
  others.

What the model said you would see: mostly deep blue, with a fast swirl
through the colour wheel every time the trajectory changes wings, and a red
flash at the bottom of each z excursion.  Turning the r knob changes it -- at
the counter-clockwise stop the lamp stops changing colour altogether, because
the attractor has collapsed to a fixed point.

### What the rev A boards showed

The rev A boards were built exactly as option 038 -- netlist, part and orientation all
check out, and a lamp fitted any other way could not show blue and green at
all.  But the lamp is mostly blue with some green, and anything else is rare.
The model was wrong at two links of the chain, and `scripts/lamp_model.py`
now carries both the model rev A was chosen with (`REVA`) and a corrected one
(`MHPA3528`):

| | rev A's model | corrected |
|---|---|---|
| red at 0.1 mA | 1.36 V | 1.64 V |
| green at 0.1 mA | 2.02 V | 2.40 V |
| blue at 0.1 mA | 2.07 V | 2.52 V |
| red light per mA at 1 mA, against 20 mA | 0.86x | 0.71x |
| green, the same | 0.64x | 1.52x |
| blue, the same | 0.64x | 1.28x |

* **Voltage to current.**  Ideality factors of 3.2 and 5 had every die
  conducting 0.3-0.45 V too early.  The corrected curves are typical of the
  two materials at 0.1 mA, and still land each die's 20 mA voltage inside
  the datasheet's min-max column.
* **Current to light.**  InGaN (green, blue) peaks in efficiency at a few
  A/cm^2 -- about a milliamp for a die this size -- and droops above it, so
  at the lamp's currents it is *more* efficient than at 20 mA.  AlGaInP
  (red) is still gaining efficiency at 20 mA and loses it below a few mA.
  The corrected model uses the ABC model for InGaN and SRH-plus-radiative for
  AlGaInP.  Of all the corrections this one matters most: on its own it
  takes red from 10 % of rev A's light to 4 %.
* **Light to brightness.**  A saturated blue looks about 1.7 times brighter
  than its luminance says, red 1.5, green 1.2 (the Helmholtz-Kohlrausch
  effect, Ware and Cowan's formula).  The judge now uses that.
* **Brightness in time.**  The eye averages colour over a few tens of
  milliseconds.  The corrected red flashes last about 20 ms, so they are
  averaged away; the rev A pictures, which drew every 4.7 ms sample as a
  pixel, showed them all.

Together: red went from 9.7 % of rev A's light to 2.7 %, and its warm flashes
from 38 a minute at about 50 ms each to 9 a minute at about 20 ms.  Under
the corrected model rev A's lamp spends its vivid moments 43 % azure, 23 %
blue, 33 % green-to-cyan and 1 % anything else -- which is what the boards
do.

The colour science itself held up: each die's computed dominant wavelength
is within 3 nm of its datasheet.  What also has to change is the goal.  The
rule that chose rev A rewarded all three dies contributing, which is the
recipe for mixtures -- cyan and white -- and not for saturated hues.

### The rev B search

`scripts/lamp_search.py`, `lamp_search_mix.py` and `lamp_search_reva.py`
search again under the corrected model, and `scripts/lamp_gallery2.py`
writes the finalists to `docs/lamp2/index.html`.  Each wiring is judged on:

* **vivid**: the fraction of the time the lamp is neither near black
  (perceived brightness under a sixth of its own bright end) nor near white
  (under three quarters of the way to the most saturated colour the dies
  can make in that hue, a limit reached exactly when no more than two dies
  are lit);
* **hues**: how evenly those vivid moments spread over the twelve 30-degree
  sectors of the OKLab hue circle, as exp(entropy) / 12;
* **score** = vivid x hues, after the eye's 20 ms two-stage filter at
  `slow!`.

About 6.7 million wirings were judged: every rev-A-style wiring
(3.3 million, exhaustively, on E6 resistors, then polished on E12), rev A
plus one resistor (1.7 million, a grid), and dies with thresholds of their
own or blends of two signals (1.8 million, by evolutionary search).  Every
finalist was then re-judged against 24 LEDs drawn from what the datasheet
allows -- brightness bins, forward voltage, and the uncertainty in the
efficiency curves -- at r = 26, 28 and 31, and ranked on the median.
Designs that stand more than 2 mA in an offset resistor or run a die above
5 mA were set aside.

Rev A scores 0.33 on that test.  The best rev B candidates score 0.77-0.78,
and one of them is rev A's own wiring with one more resistor.  See
`docs/lamp2/` for all ten finalists, playing in real time.

Rev B is built with **candidate 1**, the top scorer.  Re-judged against 96
fresh LEDs at five settings of the r knob it scores 0.805 (90 % interval
0.801-0.809), statistically tied with candidate 2 at 0.804 and clear of the
rest.  `check_circuit.py` now reads the lamp back out of the netlist, checks
it is that wiring, and simulates it -- the build fails if the board's own
lamp scores below 0.70.

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

