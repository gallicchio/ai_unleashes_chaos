#!/usr/bin/env python3
"""Build hardware/lib/lorenz.kicad_sym -- the symbols this project draws itself.

The op-amp and multiplier are shaped the way Paul draws them by hand: the
inverting input on *top*, the multiplier as a right-pointing wedge with the
(x) glyph inside.  Supply pins live on a separate unit so the signal drawing
stays clean and all the bypassing can be grouped in one place, exactly as the
"IC pinouts" box does on the original sheet.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexp import S, q, n, uid, effects

SYM_VERSION = "20251024"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "hardware", "lib", "lorenz.kicad_sym")

W_BODY = 0.254          # symbol outline width, as the stock libraries use


def prop(name, value, x, y, hide=False, justify=None, size=1.27):
    p = S("property", q(name), q(value))
    p.add(S("at", n(x), n(y), "0"), S("show_name", "no"), S("do_not_autoplace", "no"))
    if hide:
        p.add(S("hide", "yes"))
    p.add(effects(size=size, justify=justify))
    return p


def pin(kind, shape, x, y, rot, length, name, number, hide=False, nsize=1.27):
    p = S("pin", kind, shape)
    p.add(S("at", n(x), n(y), n(rot)), S("length", n(length)))
    if hide:
        p.add(S("hide", "yes"))
    p.add(S("name", q(name), effects(size=nsize)),
          S("number", q(number), effects(size=nsize)))
    return p


def poly(points, fill="none", width=W_BODY):
    pts = S("pts")
    for (x, y) in points:
        pts.add(S("xy", n(x), n(y)))
    return S("polyline").add(pts,
                             S("stroke").add(S("width", n(width)), S("type", "default")),
                             S("fill").add(S("type", fill)))


def circ(cx, cy, r, fill="none", width=W_BODY):
    return S("circle").add(S("center", n(cx), n(cy)), S("radius", n(r)),
                           S("stroke").add(S("width", n(width)), S("type", "default")),
                           S("fill").add(S("type", fill)))


def text(txt, x, y, size=1.0, rot=0, justify=None):
    return S("text", q(txt)).add(S("at", n(x), n(y), n(rot)),
                                 effects(size=size, justify=justify))


def symbol(name, ref, value, datasheet, descr, keywords, fp_filters,
           units, pin_offset=0.254, ref_at=(0, 0), val_at=(0, 0)):
    s = S("symbol", q(name))
    s.add(S("pin_names").add(S("offset", n(pin_offset))),
          S("exclude_from_sim", "no"), S("in_bom", "yes"), S("on_board", "yes"))
    s.add(prop("Reference", ref, *ref_at, justify="left"),
          prop("Value", value, *val_at, justify="left"),
          prop("Footprint", "", 0, 0, hide=True),
          prop("Datasheet", datasheet, 0, 0, hide=True),
          prop("Description", descr, 0, 0, hide=True),
          prop("ki_keywords", keywords, 0, 0, hide=True),
          prop("ki_fp_filters", fp_filters, 0, 0, hide=True))
    for unit_no, body in units:
        u = S("symbol", q(f"{name}_{unit_no}_1"))
        for item in body:
            u.add(item)
        s.add(u)
    s.add(S("embedded_fonts", "no"))
    return s


# ------------------------------------------------------------- LF412 -------
def lf412():
    """Dual JFET op-amp.  Inverting input on top, like Paul's sheet."""
    def amp(neg, pos, out):
        return [poly([(-5.08, 5.08), (5.08, 0), (-5.08, -5.08), (-5.08, 5.08)],
                     fill="background"),
                pin("input", "line", -7.62, 2.54, 0, 2.54, "-", neg),
                pin("input", "line", -7.62, -2.54, 0, 2.54, "+", pos),
                pin("output", "line", 7.62, 0, 180, 2.54, "", out)]

    power = [poly([(-2.54, 6.35), (2.54, 6.35), (2.54, -6.35), (-2.54, -6.35),
                   (-2.54, 6.35)], fill="background"),
             pin("power_in", "line", 0, 8.89, 270, 2.54, "V+", "8", nsize=1.0),
             pin("power_in", "line", 0, -8.89, 90, 2.54, "V-", "4", nsize=1.0)]

    return symbol("LF412", "U", "LF412",
                  "https://www.ti.com/lit/ds/symlink/lf412.pdf",
                  "Dual JFET-input operational amplifier, SOIC-8",
                  "dual opamp JFET",
                  "SOIC*3.9x4.9mm*P1.27mm* DIP*W7.62mm*",
                  [(1, amp("2", "3", "1")), (2, amp("6", "5", "7")), (3, power)],
                  ref_at=(0, 7.62), val_at=(0, -7.62))


# ------------------------------------------------------------ MPY634 -------
def mpy634():
    """Four-quadrant multiplier, drawn as Paul's right-pointing wedge."""
    body = [
        poly([(-7.62, 12.7), (-2.54, 12.7), (5.08, 6.35), (5.08, -6.35),
              (-2.54, -12.7), (-7.62, -12.7), (-7.62, 12.7)], fill="background"),
        # the two differential input stages
        poly([(-5.08, 10.16), (-5.08, 5.08), (-1.27, 7.62), (-5.08, 10.16)]),
        poly([(-5.08, -5.08), (-5.08, -10.16), (-1.27, -7.62), (-5.08, -5.08)]),
        poly([(-1.27, 7.62), (0.0, 7.62), (0.0, 1.905)]),
        poly([(-1.27, -7.62), (0.0, -7.62), (0.0, -1.905)]),
        # the (x) glyph
        circ(0.0, 0, 1.905),
        poly([(-1.347, 1.347), (1.347, -1.347)]),
        poly([(-1.347, -1.347), (1.347, 1.347)]),
        poly([(1.905, 0), (3.048, 0)]),
        pin("input", "line", -10.16, 8.89, 0, 2.54, "X1", "1"),
        pin("input", "line", -10.16, 6.35, 0, 2.54, "X2", "2"),
        pin("input", "line", -10.16, -6.35, 0, 2.54, "Y1", "6"),
        pin("input", "line", -10.16, -8.89, 0, 2.54, "Y2", "7"),
        pin("input", "line", -10.16, -11.43, 0, 2.54, "SF", "4"),
        pin("input", "line", 7.62, 2.54, 180, 2.54, "Z1", "13"),
        pin("output", "line", 7.62, 0, 180, 2.54, "W", "14"),
        pin("input", "line", 7.62, -2.54, 180, 2.54, "Z2", "12"),
    ]
    for nc in ("3", "5", "8", "9", "11", "15"):
        body.append(pin("no_connect", "line", -10.16, 13.97, 0, 2.54, "NC", nc, hide=True))

    power = [poly([(-2.54, 2.54), (2.54, 2.54), (2.54, -2.54), (-2.54, -2.54),
                   (-2.54, 2.54)], fill="background"),
             pin("power_in", "line", 0, 5.08, 270, 2.54, "V+", "16"),
             pin("power_in", "line", 0, -5.08, 90, 2.54, "V-", "10")]

    return symbol("MPY634", "U", "MPY634",
                  "https://www.ti.com/lit/ds/symlink/mpy634.pdf",
                  "Wide-bandwidth precision four-quadrant analog multiplier, "
                  "W = (X1-X2)(Y1-Y2)/10 + Z, SOIC-16 wide",
                  "multiplier four-quadrant analog",
                  "SOIC*7.5x10.3mm*P1.27mm* DIP*W7.62mm*",
                  [(1, body), (2, power)],
                  ref_at=(-7.62, 15.24), val_at=(-7.62, -15.24))


# ------------------------------------------------------------- DC-DC -------
def dcdc():
    body = [
        poly([(-10.16, 7.62), (10.16, 7.62), (10.16, -7.62), (-10.16, -7.62),
              (-10.16, 7.62)], fill="background"),
        poly([(0, 7.62), (0, -7.62)], width=0.127),
        text("isolated", 0, -6.1, size=0.9),
        pin("power_in", "line", -12.7, 2.54, 0, 2.54, "+Vin", "1", nsize=1.0),
        pin("power_in", "line", -12.7, -2.54, 0, 2.54, "-Vin", "2", nsize=1.0),
        pin("power_out", "line", 12.7, 3.81, 180, 2.54, "+Vout", "6", nsize=1.0),
        pin("power_out", "line", 12.7, 0, 180, 2.54, "COM", "5", nsize=1.0),
        pin("power_out", "line", 12.7, -3.81, 180, 2.54, "-Vout", "4", nsize=1.0),
    ]
    return symbol("DCDC_A0515S", "U", "A0515S-2WR2",
                  "https://www.lcsc.com/product-detail/C19272710.html",
                  "Isolated 5V to +/-15V dual-output DC/DC converter module, SIP",
                  "DC-DC isolated dual output converter",
                  "DCDC_SIP*",
                  [(1, body)], ref_at=(-10.16, 10.16), val_at=(-10.16, -12.7))


def main():
    lib = S("kicad_symbol_lib")
    lib.add(S("version", SYM_VERSION),
            S("generator", q("lorenz-gen")),
            S("generator_version", q("10.0")))
    for maker in (lf412, mpy634, dcdc):
        lib.add(maker())
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        fh.write(lib.render() + "\n")
    print(f"  wrote {os.path.relpath(OUT)}")


if __name__ == "__main__":
    main()
