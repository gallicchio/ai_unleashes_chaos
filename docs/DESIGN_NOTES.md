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
   5 V in -> `A0515S-1WR3` isolated 1 W module -> +/-15 V -> `78L12`/`79L12`
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

4. **U2B is spare** (Paul also used only 1.5 of his two LF412s).  Wired as a
   grounded unity-gain follower, which is the correct way to park an unused
   op-amp, and labelled as such on the schematic.

## Part selection (JLCPCB stock checked 2026-09-15)

| Ref | Part | LCSC | Package | Stock | Unit |
|---|---|---|---|---|---|
| U1,U2 | LF412CDR | C15322 | SOIC-8 | 1037 | $0.91 |
| U3,U4 | MPY634KU/1K | C1523457 | SOIC-16-300mil | 874 | $30.59 |
| U5 | A0515S-1WR3 | C5369388 | SIP-7 THT | 920 | $1.88 |
| U6 | CJ78L12 | C8615 | SOT-89 | 52154 | $0.10 |
| U7 | CJ79L12 | C8626 | SOT-89 | 11413 | $0.12 |
| J1 | TYPE-C-31-M-12 | C165948 | SMD | 230097 | $0.19 |
| J2-J4 | BNC-KYWE-295-W4-N | C41416668 | THT right-angle | 410 | $1.55 |
| SW1 | DSIC06LSGET | C54952 | SMD DIP-6 | 2140 | $0.57 |

LF412 and MPY634 are Paul's exact parts — both still stocked, both in
hand-solderable wide-body packages, so the circuit stays literally his.

