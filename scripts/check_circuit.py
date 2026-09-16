#!/usr/bin/env python3
"""Read the exported netlist back and prove the board solves Lorenz.

This does not trust the drawing.  It walks the real netlist, works out what
every integrator actually computes from the resistors that are really attached
to it, and compares the result with

    dx/dt = s(y-x),  dy/dt = rx - y - xz,  dz/dt = xy - bz.

It also checks the housekeeping that makes those equations true: the op-amps'
non-inverting inputs at ground, the multipliers wired for A*B/10 with the sign
inversions Paul gets by swapping inputs, matched capacitors across the three
integrators, and every supply pin on the right rail.
"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexp_parse import parse_file

S_TARGET, R_TARGET, B_TARGET = 10.0, 28.0, 8.0 / 3.0
R_BISTABLE = 24.06       # below this the trace falls into a wing and stays
POT = "RV1"              # the r knob, a rheostat in series with R3
SYNC_POT = "RV2"         # the sync weight knob, a divider across the input
POT_TRAVEL = 310.0       # degrees, Bourns 3386 "Mechanical Angle"
SCALE = 1.0e6            # every coefficient is 1 MEG / R
TOL = 0.01               # 1 % on the resistor ratios


# ------------------------------------------------------------ polynomials --
def poly(**terms):
    return {k: float(v) for k, v in terms.items() if v}


def padd(a, b, k=1.0):
    out = dict(a)
    for mono, c in b.items():
        out[mono] = out.get(mono, 0.0) + k * c
        if abs(out[mono]) < 1e-12:
            del out[mono]
    return out


def pmul(a, b):
    out = {}
    for m1, c1 in a.items():
        for m2, c2 in b.items():
            mono = "".join(sorted(m1 + m2))
            out[mono] = out.get(mono, 0.0) + c1 * c2
    return {k: v for k, v in out.items() if abs(v) > 1e-12}


def pstr(p):
    if not p:
        return "0"
    bits = []
    for mono in sorted(p, key=lambda m: (len(m), m)):
        c = p[mono]
        bits.append(f"{c:+.4g} {mono or '1'}")
    return " ".join(bits)


def pclose(a, b, tol=TOL):
    keys = set(a) | set(b)
    for k in keys:
        va, vb = a.get(k, 0.0), b.get(k, 0.0)
        scale = max(abs(va), abs(vb), 1.0)
        if abs(va - vb) / scale > tol:
            return False
    return True


# ----------------------------------------------------------------- values --
def ohms(text):
    t = text.strip().upper().replace("OHM", "").replace("R", "" if text[-1] in "Rr" else "R")
    t = text.strip().upper().rstrip("R")
    mult = 1.0
    if t.endswith("M"):
        mult, t = 1e6, t[:-1]
    elif t.endswith("K"):
        mult, t = 1e3, t[:-1]
    return float(t) * mult


def farads(text):
    t = text.strip().lower()
    for suffix, mult in (("uf", 1e-6), ("nf", 1e-9), ("pf", 1e-12)):
        if t.endswith(suffix):
            return float(t[:-len(suffix)]) * mult
    return float(t)


# ---------------------------------------------------------------- netlist --
class Net:
    def __init__(self, path):
        root = parse_file(path)
        self.value, self.footprint = {}, {}
        for c in root.first("components").kids("comp"):
            ref = c.first("ref").atom(0)
            self.value[ref] = c.first("value").atom(0)
            f = c.first("footprint")
            self.footprint[ref] = f.atom(0) if f is not None else ""
        self.nets = {}
        for n in root.first("nets").kids("net"):
            name = n.first("name").atom(0).lstrip("/")
            self.nets[name] = {(x.first("ref").atom(0), x.first("pin").atom(0))
                               for x in n.kids("node")}
        self.of = {}
        for name, nodes in self.nets.items():
            for node in nodes:
                self.of[node] = name

    def net(self, ref, pin):
        return self.of.get((ref, str(pin)))

    def others(self, name, exclude_ref=None):
        return {(r, p) for (r, p) in self.nets.get(name, ())
                if r != exclude_ref}

    def other_pin(self, ref, pin):
        """For a 2-pin part, the net on the opposite pin."""
        pins = sorted(p for (r, p) in self.of if r == ref)
        assert len(pins) == 2, f"{ref} is not a 2-pin part ({pins})"
        other = pins[0] if str(pin) == pins[1] else pins[1]
        return self.net(ref, other)


def upstream(nl, ref, pin, knob, meaning):
    """Follow a summing resistor outward until it reaches a named signal.

    Returns (total ohms, net).  Almost every branch is one resistor, but the
    r branch is R3 in series with the trimmer, so this walks a chain rather
    than assuming a single part.  `knob` is the trimmer setting: 0.0 at the
    clockwise stop, where the wiper is on terminal 3 and nothing of the track
    is in circuit, and 1.0 at the counter-clockwise stop, where all of it is.
    If the walk ends somewhere that is not a signal it returns (None, net),
    and the caller decides whether that net is a mistake or the sync input.
    """
    total = 0.0
    for _ in range(4):
        total += (ohms(nl.value[ref]) * knob if ref == POT
                  else ohms(nl.value[ref]))
        pins = sorted(p for (r, p) in nl.of if r == ref)
        far = {nl.net(ref, p) for p in pins if p != pin}
        if len(far) != 1:
            return None, f"{ref} bridges {sorted(far)}"
        net = far.pop()
        if net in meaning:
            return total, net
        onward = sorted(nl.others(net, exclude_ref=ref))
        if len(onward) != 1 or not onward[0][0].startswith("R"):
            return None, net
        ref, pin = onward[0]
    return None, "chain too long"


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "out/lorenz.net"
    nl = Net(path)
    problems, notes = [], []

    def need(cond, msg):
        (notes if cond else problems).append(("ok " if cond else "FAIL") + "  " + msg)

    # --- what each signal net means, in normalised variables --------------
    meaning = {"x": poly(x=1), "-y": poly(y=-1), "z": poly(z=1), "GND": {}}

    # --- multipliers: W = (X1-X2)(Y1-Y2)/10 volts = ab/100 normalised ------
    for ref in ("U3", "U4"):
        x1, x2 = nl.net(ref, 1), nl.net(ref, 2)
        y1, y2 = nl.net(ref, 6), nl.net(ref, 7)
        w, z1, z2 = nl.net(ref, 14), nl.net(ref, 13), nl.net(ref, 12)
        need(z1 == w, f"{ref} Z1 tied to its output (unity scale)")
        need(z2 == "GND", f"{ref} Z2 to ground")
        sf = nl.net(ref, 4)
        need(sf is None or len(nl.nets.get(sf, ())) == 1,
             f"{ref} SF left open -> x10 V scale factor")
        need(nl.net(ref, 16) == "+12V" and nl.net(ref, 10) == "-12V",
             f"{ref} powered from +/-12 V")
        for nm in (x1, x2, y1, y2):
            need(nm in meaning, f"{ref} input net '{nm}' is a known signal")
        a = padd(meaning.get(x1, {}), meaning.get(x2, {}), -1)
        b = padd(meaning.get(y1, {}), meaning.get(y2, {}), -1)
        meaning[w] = {k: v / 100.0 for k, v in pmul(a, b).items()}
        notes.append(f"      {ref}: W = ({pstr(a)}) x ({pstr(b)}) / 100 "
                     f"= {pstr(meaning[w])}")

    # --- the three integrators, solved at both ends of the r knob ---------
    # RV1 makes one coefficient adjustable, so the netlist is walked twice:
    # once with the trimmer at its clockwise stop, where none of the track is
    # in circuit, and once at the counter-clockwise stop, where all of it is.
    # Every other coefficient has to come out identical both times.
    integrators = [("U1", "2", "1"), ("U1", "6", "7"), ("U2", "2", "1")]
    caps_seen = {}
    injected = []

    def solve(knob, record):
        results = {}
        for (ref, inv, out) in integrators:
            sj, outnet = nl.net(ref, inv), nl.net(ref, out)
            plus = "3" if inv == "2" else "5"
            if record:
                need(nl.net(ref, plus) == "GND",
                     f"{ref} pin {plus} (+ input) at ground -- a true virtual earth")

            expr, terms = {}, []
            cap_total = 0.0
            for (r, p) in sorted(nl.others(sj, exclude_ref=ref)):
                kind = r[0]
                if kind == "R":
                    rtot, src = upstream(nl, r, p, knob, meaning)
                    if rtot is None:
                        # Not a signal.  The one branch allowed to end
                        # somewhere else is the sync input, which ends on the
                        # wiper of the weight knob.
                        wipers = sorted(rr for (rr, _) in nl.nets.get(src, ())
                                        if rr.startswith("RV"))
                        if not wipers:
                            problems.append(
                                f"FAIL  {r} feeds {sj} from unknown net '{src}'")
                        elif record:
                            injected.append((r, sj, ohms(nl.value[r]),
                                             wipers[0], src))
                        continue
                    weight = SCALE / rtot
                    expr = padd(expr, meaning[src], -weight)
                    terms.append(f"{r} -> {src}: {rtot / 1e3:g}k, "
                                 f"1M/R = {weight:.4g}")
                elif kind == "C":
                    far = nl.other_pin(r, p)
                    cap_total += farads(nl.value[r])
                    if far != outnet:
                        # the switched branches reach the output through one
                        # pole; on a DIP switch pole k pairs with pin 13-k
                        hop = [(rr, pp) for (rr, pp)
                               in nl.others(far, exclude_ref=r)
                               if rr.startswith("SW")]
                        if not hop:
                            if record:
                                problems.append(
                                    f"FAIL  {r} hangs off {far} with no switch")
                            continue
                        sw, swpin = hop[0]
                        mate = str(13 - int(swpin))
                        if record:
                            need(nl.net(sw, mate) == outnet,
                                 f"{r} reaches {ref}'s output through {sw} pole "
                                 f"{swpin}-{mate}")
                else:
                    problems.append(f"FAIL  unexpected {r} on summing node {sj}")
            results[outnet] = expr
            if record:
                caps_seen[outnet] = cap_total
                notes.append(f"      {ref} ({outnet}): d/dt = {pstr(expr)}")
                for t in terms:
                    notes.append(f"         <- {t}")
        return results

    cw = solve(0.0, True)      # trimmer shorted out: the least R, the most r
    ccw = solve(1.0, False)    # the whole track in circuit: the least r

    # --- compare with Lorenz ---------------------------------------------
    # r is the knob's, so it is left out of the fixed comparison and checked
    # by the span it covers.
    want = {
        "x":  poly(x=-S_TARGET, y=S_TARGET),                       # 10(y-x)
        "-y": poly(y=1.0, xz=1.0),                                 # -(-y - xz)
        "z":  poly(xy=1.0, z=-B_TARGET),                           # xy - (8/3)z
    }
    labels = {"x": "dx/dt = s(y - x)",
              "-y": "d(-y)/dt = -(r x - y - x z), r term excluded",
              "z": "dz/dt = x y - b z"}
    for net, target in want.items():
        for (tag, res) in (("clockwise", cw), ("counter-clockwise", ccw)):
            got = res.get(net)
            if got is None:
                problems.append(f"FAIL  no integrator produces '{net}'")
                continue
            fixed = {k: v for k, v in got.items()
                     if not (net == "-y" and k == "x")}
            need(pclose(fixed, target),
                 f"knob {tag:17s}  {labels[net]}   ->   {pstr(got)}")

    # extract the realised constants for the report
    s_got = cw.get("x", {}).get("y", 0.0)
    b_got = -cw.get("z", {}).get("z", 0.0)
    r_hi = -cw.get("-y", {}).get("x", 0.0)
    r_lo = -ccw.get("-y", {}).get("x", 0.0)
    notes.append(f"      realised constants: s = {s_got:.4g}, "
                 f"b = {b_got:.5g}  (8/3 = {B_TARGET:.5g}), "
                 f"r = {r_lo:.4g} .. {r_hi:.4g}")
    need(abs(b_got - B_TARGET) / B_TARGET < 0.005,
         f"b within 0.5 % of 8/3 ({100*abs(b_got-B_TARGET)/B_TARGET:.2f} % high)")

    # --- the r knob -------------------------------------------------------
    # Clockwise has to be the end that raises r: terminal 1 is tied to the
    # wiper, so the section in circuit is wiper-to-3 and shrinks as the screw
    # turns clockwise.  Everything else here is about whether the knob is
    # worth fitting: does it reach the interesting values, and can a person
    # hold a setting?
    pot_pins = sorted(p for (r, p) in nl.of if r == POT)
    need(pot_pins == ["1", "2", "3"], f"{POT} has three terminals")
    need(nl.net(POT, "1") == nl.net(POT, "2"),
         f"{POT} terminal 1 is tied to the wiper, so grit under the wiper "
         f"means maximum resistance -- the lowest r -- and never an open")
    need(nl.net(POT, "3") == nl.net("R3", 1) or nl.net(POT, "3") == nl.net("R3", 2),
         f"{POT} terminal 3 goes to R3, and R3 to the summing junction")
    need(r_lo < R_TARGET < r_hi,
         f"the knob sweeps r = {r_lo:.2f} to {r_hi:.2f}, across Lorenz's 28")
    r_hopf = s_got * (s_got + b_got + 3.0) / (s_got - b_got - 1.0)
    for (rc, what) in ((R_BISTABLE, "where the wings stop being an attractor"),
                       (r_hopf, "the Hopf bifurcation, where the fixed "
                                "points let go")):
        need(r_lo < rc < r_hi, f"...and across r = {rc:.2f}, {what}")
    # dr/dtheta is steepest at the clockwise stop, where R is smallest
    span = r_hi - r_lo
    steepest = (SCALE * ohms(nl.value[POT]) / ohms(nl.value["R3"]) ** 2
                / POT_TRAVEL)
    need(steepest < 0.15,
         f"one degree of screw never moves r by more than {steepest:.3f}, so "
         f"a setting can be found again by hand")
    need(span > 10.0,
         f"the sweep is {span:.1f} wide -- more than the 10 that the sync "
         f"input adds, so a receiving board can be turned down to match")

    # --- the three time constants must match ------------------------------
    vals = sorted(caps_seen.values())
    need(abs(vals[0] - vals[-1]) < 1e-15,
         f"all three integrators carry the same capacitance ({vals[0]*1e9:.1f} nF fitted)")

    # --- outputs ----------------------------------------------------------
    for (net, res, jack) in (("x", "R8", "J2"), ("-y", "R9", "J3"), ("z", "R10", "J4")):
        need(nl.net(res, 1) == net, f"{res} takes {net} to {jack}")
        need(nl.net(res, 2) == nl.net(jack, 1), f"{res} drives {jack} centre pin")
        need(nl.net(jack, 2) == "GND", f"{jack} shell grounded")

    # --- supplies ---------------------------------------------------------
    for ref, vp, vn in (("U1", 8, 4), ("U2", 8, 4)):
        need(nl.net(ref, vp) == "+12V" and nl.net(ref, vn) == "-12V",
             f"{ref} powered from +/-12 V")
    need(nl.net("U6", 3) == "+15V" and nl.net("U6", 1) == "+12V"
         and nl.net("U6", 2) == "GND", "U6 78L12: +15 V in, +12 V out, tab to ground")
    need(nl.net("U7", 2) == "-15V" and nl.net("U7", 3) == "-12V"
         and nl.net("U7", 1) == "GND", "U7 79L12: -15 V in, -12 V out")
    # the datasheets are characterised with 0.33 uF in and 0.1 uF out, "located
    # as close as possible": the 10 uF bulk is not close, so each pin gets its
    # own 100 nF as well
    for (ureg, ipin, opin, cin, cout) in (("U6", 3, 1, "C26", "C27"),
                                          ("U7", 2, 3, "C28", "C29")):
        for (cref, pin) in ((cin, ipin), (cout, opin)):
            net = nl.net(ureg, pin)
            need(net in (nl.net(cref, 1), nl.net(cref, 2))
                 and "GND" in (nl.other_pin(cref, "1"), nl.other_pin(cref, "2"))
                 and nl.value[cref] == "100nF",
                 f"{cref} is 100 nF from {ureg} pin {pin} ({net}) to ground")
    need(nl.net("U5", 1) == "+5V" and nl.net("U5", 2) == "GNDU"
         and nl.net("U5", 6) == "+15V" and nl.net("U5", 5) == "GND"
         and nl.net("U5", 4) == "-15V",
         "U5 converter: 5 V in on GNDU, +/-15 V out on GND")
    need(nl.net("R11", 2) == "GNDU" and nl.net("R12", 2) == "GNDU",
         "both CC lines pulled down, so a USB-C source will turn 5 V on")

    # --- the isolation barrier -------------------------------------------
    # The two grounds must meet at R21, C25 and JP1 and nowhere else; a single
    # stray symbol would quietly undo the isolation and nothing would look
    # wrong on the drawing.
    bridges = set()
    for (ref, _) in nl.nets.get("GNDU", ()):
        if ref.startswith("#") or ref == "U5":   # U5 *is* the barrier
            continue
        pins = sorted(p for (r, p) in nl.of if r == ref)
        if any(nl.net(ref, p) == "GND" for p in pins):
            bridges.add(ref)
    need(bridges == {"R18", "C25", "JP1"},
         f"apart from the converter itself, GND and GNDU meet only at "
         f"R18, C25 and JP1 (found {sorted(bridges)})")
    need(nl.value.get("R18") == "1M" and nl.value.get("C25") == "2.2nF",
         "the barrier is 1 M in parallel with 2.2 nF: static drains, "
         "100 kHz common-mode current gets home, 60 Hz does not")
    usb_side = {r for (r, _) in nl.nets.get("GNDU", ())
                if not r.startswith("#") and not r.startswith("TP")}
    need(usb_side == {"J1", "R11", "R12", "C10", "C11", "U5", "R18",
                      "C25", "JP1"},
         f"only the USB input sits on GNDU (found {sorted(usb_side)})")
    need(nl.net("J1", "SH") == "GNDU",
         "the USB shell stays on the USB side, where the cable screen belongs")

    # --- the chaos lamp: three signals, one common anode -----------------
    # There is no separate power lamp.  The lamp needs +12 V (the op-amps and
    # the reference), and therefore the converter and the USB input, so it
    # lights only when the whole chain is up -- which three discrete LEDs on
    # three rails told you less well and in three more places.
    vled = nl.net("D1", 1)
    need(vled == nl.net("U2", 7) and vled == nl.net("U2", 6),
         "D1's common anode is driven by U2B wired as a unity follower")
    ref_node = nl.net("U2", 5)
    top = sorted(r for (r, p) in nl.nets[ref_node] if r.startswith("R"))
    need(top == ["R16", "R17"],
         f"the reference is a two-resistor divider (found {top})")
    legs = {}
    for r in top:
        ends = [nl.net(r, "1"), nl.net(r, "2")]
        legs[ends[1] if ends[0] == ref_node else ends[0]] = ohms(nl.value[r])
    need(set(legs) == {"GND", "+12V"},
         f"the divider hangs between +12 V and ground (found {sorted(legs)})")
    va = 12.0 * legs.get("GND", 0.0) / sum(legs.values())
    need(2.9 < va < 3.5,
         f"the anode sits at {va:.2f} V: above the red die's forward drop at "
         "every z, and below the peak of every signal, so each colour has a "
         "threshold inside its own swing")
    caps = {r for (r, p) in nl.nets[ref_node] if r.startswith("C")}
    need(caps == {"C24"}, "C24 filters the reference before the buffer")

    # Each colour, its drive resistor, its source, and the range that source
    # covers over the whole sweep of the r knob (r = 21.3 measured at the
    # bottom, r = 37.0 at the top).  A die conducts when its cathode -- the
    # signal -- falls a forward drop below the anode, so the peak current is
    # set by the signal's *minimum*, and the reverse voltage by its maximum.
    colours = [("4", "R15", "z", 1.75, 0.28, 6.00, "red"),
               ("3", "R13", "x", 2.60, -2.10, 2.20, "green"),
               ("2", "R14", "-y", 2.60, -2.95, 3.15, "blue")]
    i_total = 0.0
    for (pin, res, src, vf, vmin, vmax, name) in colours:
        cath = nl.net("D1", pin)
        need(nl.net(res, 1) == src or nl.net(res, 2) == src,
             f"{res} feeds D1's {name} die from {src}")
        need(cath in (nl.net(res, 1), nl.net(res, 2)),
             f"{res} lands on D1 pin {pin} ({name})")
        thresh = va - vf
        i_pk = (va - vmin - vf) / ohms(nl.value[res]) * 1e3
        i_total += i_pk
        need(vmin < thresh < vmax and 0.15 < i_pk < 3.0,
             f"{name}: {res} = {nl.value[res]}, lights below {src} = "
             f"{thresh:+.2f} V, {i_pk:.2f} mA at the extreme")
        v_rev = max(0.0, vmax - va)
        need(v_rev < 5.0,
             f"{name} never sees more than {v_rev:.1f} V in reverse when "
             f"{src} tops out at {vmax:+.1f} V (the part is rated 5 V)")
    need(i_total < 8.0,
         f"the lamp draws at most {i_total:.1f} mA, which U2B can source and "
         "the 2 W converter will not notice")
    # the lamp must tap the output node, not the summing junction and not the
    # far side of the series resistor
    for (res, src, series) in (("R13", "x", "R8"), ("R14", "-y", "R9"),
                               ("R15", "z", "R10")):
        need(nl.net(series, 1) == src,
             f"{res} and {series} share the op-amp output node, so no lamp "
             f"current flows in the 100 ohm going to the BNC")

    # --- the synchronisation input ---------------------------------------
    # A BNC, a weight knob and one resistor into the dy/dt summing junction.
    # It has to land on the r x term: the junction inverts, so an injected
    # voltage always arrives with a minus sign, and diffusive coupling
    # k(x1 - x2) is only available where the local term already carries a
    # plus.  The knob is a divider across the incoming signal rather than a
    # rheostat in series, which makes the weight linear in the knob and lets
    # it reach zero -- the same thing as unplugging the cable.
    need(len(injected) == 1, f"exactly one branch comes in from outside "
                             f"(found {[i[0] for i in injected]})")
    for (res, sj, rval, pot, node) in injected:
        need(sj == nl.net("U1", "6"),
             f"{res} injects into the dy/dt summing junction, the one node "
             f"where an inverted input still adds to a + r x term")
        need(sj == nl.net("R3", 1) or sj == nl.net("R3", 2),
             f"{res} and R3 meet on the same node, so the sync input adds to "
             f"the x term and to nothing else")
        gain = SCALE / rval
        need(5.0 < gain < 15.0,
             f"{res} = {nl.value[res]} sets the *maximum* coupling to "
             f"{gain:.1f}, which also adds up to {gain:.1f} to the receiving "
             f"board's r -- inside the {span:.1f} the knob can take back")
        need(gain <= span,
             f"...and {gain:.1f} is no more than the r knob's {span:.1f}, so "
             f"every weight setting can be compensated")
        # the knob: terminal 3 to the connector, terminal 1 to ground, wiper
        # to the series resistor.  Turning it clockwise moves the wiper toward
        # terminal 3, which is the signal end, so clockwise raises the weight.
        need(nl.net(pot, "2") == node,
             f"{pot}'s wiper drives {res}")
        need(nl.net(pot, "1") == "GND",
             f"{pot} terminal 1 is grounded, so the knob reaches zero weight "
             f"-- which is the same as unplugging the cable")
        top = nl.net(pot, "3")
        jacks = sorted(rr for (rr, _) in nl.nets.get(top, ())
                       if rr.startswith("J"))
        need(len(jacks) == 1,
             f"{pot} terminal 3 is fed straight from a jack (found {jacks})")
        for j in jacks:
            need(nl.net(j, 2) == "GND", f"{j} shell grounded")
        need(ohms(nl.value[pot]) * 0.25 < 0.1 * rval,
             f"{pot} = {nl.value[pot]} adds at most "
             f"{ohms(nl.value[pot]) * 0.25 / 1e3:.1f}k of wiper impedance to "
             f"{res}'s {rval / 1e3:.0f}k, so the weight stays within 5 % of "
             f"linear in the knob")
        holds = [r for (r, _) in nl.nets[node]
                 if r.startswith("R") and r != res and not r.startswith("RV")]
        need(len(holds) == 1 and "GND" in (nl.other_pin(holds[0], "1"),
                                           nl.other_pin(holds[0], "2")),
             f"the wiper node is held at ground by {holds} if the wiper ever "
             f"lifts off the track")
        if holds:
            leak = ohms(nl.value[holds[0]])
            need(leak >= 10.0 * ohms(nl.value[pot]),
                 f"{holds[0]} = {nl.value[holds[0]]} is "
                 f"{leak / ohms(nl.value[pot]):.0f}x the track, so it costs "
                 f"under {100 * ohms(nl.value[pot]) / leak:.0f} % of the "
                 f"divider's setting")

    # --- probe points -----------------------------------------------------
    # Every rail and every interesting node gets a pad, and nothing gets two.
    # The designators are assigned in drawing order, so check the set of nets
    # that are probed rather than which number landed where.
    got_tp = {r: nl.net(r, "1") for r in nl.value if r.startswith("TP")}
    want = {"x", "-y", "z", "xz", "xy", vled,
            "+5V", "+15V", "-15V", "+12V", "-12V", "GNDU"}
    probed = sorted(got_tp.values())
    for netname in sorted(want):
        need(probed.count(netname) == 1,
             f"exactly one probe pad on {netname}")
    grounds = [r for r, n in got_tp.items() if n == "GND"]
    need(len(grounds) == 4,
         f"one GND probe pad and three scope-ground loops ({len(grounds)} found)")
    need(set(probed) == want | {"GND"},
         f"nothing else is probed (extra: {sorted(set(probed) - want - {'GND'})})")
    loops = [r for r in grounds
             if "Loop" in (nl.footprint.get(r) or "")]
    need(len(loops) == 3,
         f"three of them are wire loops for a ground clip ({sorted(loops)})")
    vbus = nl.net("J1", "A4")
    need(nl.net("F1", 1) == vbus and nl.net("F1", 2) == "+5V",
         "F1 in series between the USB-C VBUS pins and +5 V")
    need(all(nl.net("J1", p) == vbus for p in ("A9", "B4", "B9")),
         "all four VBUS pins tied together")

    for (ref, vp, vn) in (("U1", 8, 4), ("U2", 8, 4),
                          ("U3", 16, 10), ("U4", 16, 10)):
        for (pin, rail) in ((vp, "+12V"), (vn, "-12V")):
            caps = [r for (r, _) in nl.others(rail) if r.startswith("C")]
            local = [c for c in caps
                     if nl.other_pin(c, "1") == "GND"
                     or nl.other_pin(c, "2") == "GND"]
            need(bool(local), f"{rail} has bypass capacitors to ground")
    bypass = sum(1 for (r, p) in nl.nets.get("GND", ())
                 if r.startswith("C") and nl.value.get(r) == "100nF")
    need(bypass >= 8, f"{bypass} x 100 nF from a rail to ground "
                      "(one per supply pin, plus the input)")

    # --- the series output resistors are the value the design intends ------
    for res in ("R8", "R9", "R10"):
        need(nl.value[res] == "100R",
             f"{res} is 100 ohm -- enough to isolate coax capacitance, "
             "0.01 % error into a 1 Mohm scope")

    # --- nothing left dangling -------------------------------------------
    # KiCad gives every deliberately-unconnected pin its own "unconnected-(...)"
    # net; anything else with one pin is a wiring mistake.
    singles = [n for n, nodes in nl.nets.items()
               if len(nodes) < 2 and not n.startswith("unconnected-")]
    need(not singles, f"no accidental single-pin nets"
         + ("" if not singles else ": " + str(singles)))
    nc = sorted(n for n in nl.nets if n.startswith("unconnected-"))
    expect_nc = 6 + 2 * 7            # USB D+/D-/SBU, then NC x6 + SF on each MPY634
    need(len(nc) == expect_nc,
         f"{len(nc)} deliberately unconnected pins (USB data lines, "
         f"MPY634 NC pins and both SF pins)")

    # --- report -----------------------------------------------------------
    print("\n".join(notes))
    print()
    if problems:
        print("\n".join(problems))
        print(f"\n{len(problems)} circuit check(s) FAILED")
        return 1
    print(f"all circuit checks passed ({len(notes)} verified)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
