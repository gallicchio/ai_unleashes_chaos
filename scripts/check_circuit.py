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

    # --- the three integrators -------------------------------------------
    integrators = [("U1", "2", "1"), ("U1", "6", "7"), ("U2", "2", "1")]
    caps_seen = {}
    results = {}
    for (ref, inv, out) in integrators:
        sj, outnet = nl.net(ref, inv), nl.net(ref, out)
        plus = "3" if inv == "2" else "5"
        need(nl.net(ref, plus) == "GND",
             f"{ref} pin {plus} (+ input) at ground -- a true virtual earth")

        expr, terms = {}, []
        cap_total = 0.0
        for (r, p) in sorted(nl.others(sj, exclude_ref=ref)):
            kind = r[0]
            if kind == "R":
                src = nl.other_pin(r, p)
                if src not in meaning:
                    problems.append(f"FAIL  {r} feeds {sj} from unknown net '{src}'")
                    continue
                weight = SCALE / ohms(nl.value[r])
                expr = padd(expr, meaning[src], -weight)
                terms.append(f"{r}={nl.value[r]} (1M/R={weight:.4g}) from {src}")
            elif kind == "C":
                far = nl.other_pin(r, p)
                cap_total += farads(nl.value[r])
                if far != outnet:
                    # the switched branches reach the output through one pole;
                    # on a DIP switch pole k pairs with pin 13-k
                    hop = [(rr, pp) for (rr, pp) in nl.others(far, exclude_ref=r)
                           if rr.startswith("SW")]
                    if not hop:
                        problems.append(f"FAIL  {r} hangs off {far} with no switch")
                        continue
                    sw, swpin = hop[0]
                    mate = str(13 - int(swpin))
                    need(nl.net(sw, mate) == outnet,
                         f"{r} reaches {ref}'s output through {sw} pole "
                         f"{swpin}-{mate}")
            else:
                problems.append(f"FAIL  unexpected {r} on summing node {sj}")
        results[outnet] = expr
        caps_seen[outnet] = cap_total
        notes.append(f"      {ref} ({outnet}): d/dt = {pstr(expr)}")
        for t in terms:
            notes.append(f"         <- {t}")

    # --- compare with Lorenz ---------------------------------------------
    want = {
        "x":  poly(x=-S_TARGET, y=S_TARGET),                       # 10(y-x)
        "-y": poly(x=-R_TARGET, y=1.0, xz=1.0),                    # -(28x - y - xz)
        "z":  poly(xy=1.0, z=-B_TARGET),                           # xy - (8/3)z
    }
    labels = {"x": "dx/dt = s(y - x)",
              "-y": "d(-y)/dt = -(r x - y - x z)",
              "z": "dz/dt = x y - b z"}
    for net, target in want.items():
        got = results.get(net)
        if got is None:
            problems.append(f"FAIL  no integrator produces '{net}'")
            continue
        need(pclose(got, target), f"{labels[net]}   ->   {pstr(got)}")

    # extract the realised constants for the report
    s_got = results.get("x", {}).get("y", 0.0)
    r_got = -results.get("-y", {}).get("x", 0.0)
    b_got = -results.get("z", {}).get("z", 0.0)
    notes.append(f"      realised constants: s = {s_got:.4g}, r = {r_got:.4g}, "
                 f"b = {b_got:.5g}  (8/3 = {B_TARGET:.5g})")
    need(abs(b_got - B_TARGET) / B_TARGET < 0.005,
         f"b within 0.5 % of 8/3 ({100*abs(b_got-B_TARGET)/B_TARGET:.2f} % high)")

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

    # --- the chaos lamp: three signals, one common cathode ---------------
    # There is no separate power lamp.  The lamp needs +12 V (the op-amps),
    # -12 V (the reference), and therefore the converter and the USB input, so
    # it lights only when the whole chain is up -- which three discrete LEDs
    # on three rails told you less well and in three more places.
    vled = nl.net("D1", 4)
    need(vled == nl.net("U2", 7) and vled == nl.net("U2", 6),
         "D1's common cathode is driven by U2B wired as a unity follower")
    ref_node = nl.net("U2", 5)
    top = sorted(r for (r, p) in nl.nets[ref_node] if r.startswith("R"))
    need(top == ["R16", "R17"],
         f"the reference is a two-resistor divider (found {top})")
    r_gnd = ohms(nl.value["R16"]) if "GND" in (nl.other_pin("R16", "1"),
                                               nl.other_pin("R16", "2")) \
        else ohms(nl.value["R17"])
    r_neg = ohms(nl.value["R17"]) if r_gnd == ohms(nl.value["R16"]) \
        else ohms(nl.value["R16"])
    vk = -12.0 * r_gnd / (r_gnd + r_neg)
    need(-2.0 < vk < -1.0,
         f"the cathode sits at {vk:.2f} V -- below ground, so a signal that "
         "goes negative can still switch its colour off")
    caps = {r for (r, p) in nl.nets[ref_node] if r.startswith("C")}
    need(caps == {"C24"}, "C24 filters the reference before the buffer")

    # each colour, its drive resistor, its source and what it means
    colours = [("1", "R13", "x", 1.75, -2.0, 2.0, "red"),
               ("3", "R14", "-y", 2.60, -2.7, 2.7, "green"),
               ("2", "R15", "z", 2.60, 0.0, 4.8, "blue")]
    i_total = 0.0
    for (pin, res, src, vf, vmin, vmax, name) in colours:
        anode = nl.net("D1", pin)
        need(nl.net(res, 1) == src or nl.net(res, 2) == src,
             f"{res} feeds D1's {name} from {src}")
        need(anode in (nl.net(res, 1), nl.net(res, 2)),
             f"{res} lands on D1 pin {pin} ({name})")
        thresh = vk + vf
        i_pk = (vmax - vk - vf) / ohms(nl.value[res]) * 1e3
        i_total += i_pk
        need(-1.0 < thresh < 1.5 and 0.15 < i_pk < 3.0,
             f"{name}: {res} = {nl.value[res]}, lights above {src} = "
             f"{thresh:+.2f} V, {i_pk:.2f} mA at the extreme")
        v_rev = max(0.0, vk - vmin)
        need(v_rev < 5.0,
             f"{name} never sees more than {v_rev:.1f} V in reverse when "
             f"{src} bottoms out at {vmin:+.1f} V (the part is rated 5 V)")
    need(i_total < 8.0,
         f"the lamp draws at most {i_total:.1f} mA, which U2B can sink and "
         "the 2 W converter will not notice")
    # the lamp must tap the output node, not the summing junction and not the
    # far side of the series resistor
    for (res, src, series) in (("R13", "x", "R8"), ("R14", "-y", "R9"),
                               ("R15", "z", "R10")):
        need(nl.net(series, 1) == src,
             f"{res} and {series} share the op-amp output node, so no lamp "
             f"current flows in the 100 ohm going to the BNC")

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
