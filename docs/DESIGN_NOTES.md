# Lorenz Attractor — Design Notes

Reference: Paul Horowitz, <https://seti.harvard.edu/unusual_stuff/misc/lorenz.htm>

## The equations and how the circuit implements them

    dx/dt = s(y - x)          s = 10
    dy/dt = r*x - y - x*z     r = 28
    dz/dt = x*y - b*z         b = 8/3

Every coefficient is `1 MEG / R`.  Time is scaled by `tau0 = 1M * C`.
Circuit voltages represent the dimensionless variables at **0.1 V per unit**
(`V = 0.1 * var`), which is why the multiplier terms carry a factor of 100.

| Integrator | Op-amp | Feedback | Summing inputs | Yields |
|---|---|---|---|---|
| x  | U1A | C_x | R1 100k from `-y`, R2 100k from `x` | dx/dt = 10(y - x) |
| -y | U1B | C_y | R3 35.7k from `x`, R4 10k from `-xz/100`, R5 1M from `-y` | dy/dt = 28x - y - xz |
| z  | U2A | C_z | R6 10k from `-xy/100`, R7 374k from `z` | dz/dt = xy - 2.674 z |

Coefficient check: 1M/100k = **10** = s; 1M/35.7k = **28.01** = r;
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

   | setting | poles 1-3 | poles 4-6 | C      | Paul's value |
   |---------|-----------|-----------|--------|--------------|
   | fast!   | off       | off       | 2.2 nF | 2000 pF      |
   | nice!   | **on**    | off       | 102 nF | 0.1 uF       |
   | slow!   | off       | **on**    | 472 nF | 0.47 uF      |

   (Both banks on gives 572 nF — a bonus "very slow".)  Contact resistance is
   ~100 mohm in series with C; against a 100 kohm..1 Mohm integrating resistor
   that is a 1-ppm effect.

4. **The isolation is used.**  The converter's output common is *not* tied to
   the USB ground.  The board has two grounds: `GND` downstream of the
   converter (op-amps, multipliers, BNC shells, everything a scope touches) and
   `GNDU` upstream of it (the USB connector and its shell, the CC pull-downs,
   the input bulk, the +5 V lamp).  They are separate copper pours with a 1 mm
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
   | R21 | 1 M | drains static, so the analog side cannot float up on charge |
   | C25 | 2.2 nF | 720 ohm at the converter's 100 kHz, 1.2 Gohm at 60 Hz |
   | JP1 | solder jumper, open | bridge it to give the isolation up |

5. **U2B drives the chaos lamp's reference.**  Paul also used only 1.5 of his
   two LF412s; this board spends the spare half on something useful.  A 4.7k /
   33k divider from -12 V makes -1.50 V, U2B buffers it, and that becomes the
   common cathode of one RGB LED whose anodes come from x, -y and z through
   1.5k, 6.8k and 4.7k.

   Holding the cathode *below* ground is what makes signals that swing either
   side of zero drive an LED at all.  Each colour then lights above its own
   threshold:

   | colour | from | lights when | peak |
   |---|---|---|---|
   | red | x | x > +0.25 V, i.e. the +x wing | 1.16 mA |
   | green | -y | y < -1.10 V, i.e. the -x wing | 0.23 mA |
   | blue | z | z > +1.10 V, brightness tracking z | 0.79 mA |

   So red and green alternate as the trajectory changes wings -- which is the
   chaos itself -- and blue brightens with z and drops out at the bottom of
   each excursion.  In `slow!` that happens at a few hertz, which is watchable;
   in `fast!` it averages into a colour.  The resistors are sized for roughly
   equal *perceived* brightness from the datasheet's luminous intensities, not
   equal current: green is about five times brighter per milliamp than red and
   sits where the eye is most sensitive.

   The lamp taps the op-amp outputs *before* the 100 ohm series resistors, so
   none of its current flows in the BNC output impedance.

6. **Three rail lamps, one per rail.**  Yellow on +5 V (on the USB side of the
   barrier), green on +12 V, white on -12 V, each named on the silkscreen
   beside it.  A single lamp on one rail cannot tell you the other two are up.

## Part selection (JLCPCB stock checked 2026-09-15)

| Ref | Part | LCSC | Package | Stock | Unit |
|---|---|---|---|---|---|
| U1,U2 | LF412CDR | C15322 | SOIC-8 | 1037 | $0.91 |
| U3,U4 | MPY634KU/1K | C1523457 | SOIC-16-300mil | 874 | $30.59 |
| U5 | A0515S-2WR2 | C19272710 | SIP-7 THT | 255 | $1.60 |
| U6 | CJ78L12 | C8615 | SOT-89 | 52154 | $0.10 |
| U7 | CJ79L12 | C8626 | SOT-89 | 11413 | $0.12 |
| J1 | TYPE-C-31-M-12 | C165948 | SMD | 230097 | $0.19 |
| J2-J4 | BNC-KYWE-295-W4-N | C41416668 | THT right-angle | 410 | $1.55 |
| SW1 | DSIC06LSGET | C54952 | SMD DIP-6 | 2140 | $0.57 |
| D1-D3 | KT-0805Y / G / W | C2296 / C2297 / C34499 | 0805 | >500k each | $0.02 |
| D4 | MHPC3528CRGBCT | C2962096 | PLCC-4 3.5x2.8 | 3789 | $0.05 |

LF412 and MPY634 are Paul's exact parts — both still stocked, both in
hand-solderable wide-body packages, so the circuit stays literally his.

