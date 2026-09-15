#!/usr/bin/env python3
"""Generate the project-specific footprints that the stock KiCad libraries lack.

Every dimension below is taken from the manufacturer drawing named in the
footprint's description, so the numbers can be re-checked against the PDF.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexp import S, q, n, uid, effects, stroke, at

FP_VERSION = "20260206"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "hardware", "lib", "lorenz.pretty")

SILK_W = 0.15
FAB_W = 0.10
CRT_W = 0.05


MM_SCALE = 1.0 / 2.54       # KiCad VRML unit is 2.54 mm; models are drawn in mm


def model(f, path, scale=1.0, rot=(0, 0, 0), offset=(0, 0, 0)):
    m = S("model", q(path))
    m.add(S("offset").add(S("xyz", n(offset[0]), n(offset[1]), n(offset[2]))),
          S("scale").add(S("xyz", n(scale), n(scale), n(scale))),
          S("rotate").add(S("xyz", n(rot[0]), n(rot[1]), n(rot[2]))))
    f.add(m)


def fp_header(name, descr, tags, attr, ref_y):
    f = S("footprint", q(name))
    f.add(S("version", FP_VERSION),
          S("generator", q("lorenz-gen")),
          S("generator_version", q("10.0")),
          S("layer", q("F.Cu")),
          S("descr", q(descr)),
          S("tags", q(tags)),
          S("attr", attr))
    for pname, val, layer, hide in (("Reference", "REF**", "F.SilkS", False),
                                    ("Value", name, "F.Fab", False),
                                    ("Datasheet", "", "F.Fab", True),
                                    ("Description", descr, "F.Fab", True)):
        y = ref_y if pname == "Reference" else -ref_y
        p = S("property", q(pname), q(val))
        p.add(at(0, y), S("unlocked", "yes"), S("layer", q(layer)))
        if hide:
            p.add(S("hide", "yes"))
        p.add(S("uuid", q(uid(f"{name}/prop/{pname}"))),
              effects(size=1.0, thickness=0.15))
        f.add(p)
    return f


def line(x1, y1, x2, y2, layer, width, key):
    return S("fp_line").add(
        S("start", n(x1), n(y1)), S("end", n(x2), n(y2)),
        stroke(width), S("layer", q(layer)), S("uuid", q(uid(key))))


def rect_lines(f, x1, y1, x2, y2, layer, width, key):
    f.add(line(x1, y1, x2, y1, layer, width, key + "/t"),
          line(x2, y1, x2, y2, layer, width, key + "/r"),
          line(x2, y2, x1, y2, layer, width, key + "/b"),
          line(x1, y2, x1, y1, layer, width, key + "/l"))


def circle(cx, cy, r, layer, width, key):
    return S("fp_circle").add(
        S("center", n(cx), n(cy)), S("end", n(cx + r), n(cy)),
        stroke(width), S("fill", "no"), S("layer", q(layer)), S("uuid", q(uid(key))))


def tht_pad(num, x, y, drill, dia, key, shape="circle"):
    p = S("pad", q(num), "thru_hole", shape)
    p.add(at(x, y), S("size", n(dia), n(dia)), S("drill", n(drill)),
          S("layers", q("*.Cu"), q("*.Mask")),
          S("remove_unused_layers", "no"), S("uuid", q(uid(key))))
    return p


def smd_pad(num, x, y, w, h, key):
    p = S("pad", q(num), "smd", "roundrect")
    p.add(at(x, y), S("size", n(w), n(h)),
          S("layers", q("F.Cu"), q("F.Paste"), q("F.Mask")),
          S("roundrect_rratio", "0.25"), S("uuid", q(uid(key))))
    return p


def text_fab(f, txt, x, y, key, size=0.8):
    f.add(S("fp_text", "user", q(txt)).add(
        at(x, y, 0), S("layer", q("F.Fab")), S("uuid", q(uid(key))),
        effects(size=size, thickness=0.12)))


# ----------------------------------------------------------------- BNC ------
def bnc():
    """SAMZO BNC-KYWE-295-W4-N right-angle PCB BNC jack.

    Drawing BNCKYWE-P03900 (LCSC C41416668): 10 x 10 mm body on the board,
    four ground pins O1.14 on an 8 x 8 mm square, centre pin O1.0 at the
    middle, barrel on the +X axis, 29.5 mm overall, axis 6.1 mm above board.
    The datasheet's own "PCB LAYOUT" box calls for a O1.2 hole on the centre
    pin; the ground holes follow the same 0.2 mm clearance on O1.14 pins.
    """
    name = "BNC_KYWE_RightAngle"
    f = fp_header(name,
                  "BNC jack, right angle, 4 ground pins on 8x8mm + centre pin, "
                  "SAMZO BNC-KYWE-295-W4-N / HenryTech HL2-BNC-KYWE (LCSC C41416668)",
                  "BNC coaxial jack right-angle 50ohm", "through_hole", 7.4)
    BODY, PIN, BARREL_END, BARREL_R = 10.0, 4.0, 24.5, 4.8

    # Centre pin is pad 1 (signal); the four flange posts are all pad 2 (shield).
    f.add(tht_pad("1", 0, 0, 1.3, 2.4, f"{name}/p1", "circle"))
    for i, (sx, sy) in enumerate([(-1, -1), (1, -1), (-1, 1), (1, 1)]):
        f.add(tht_pad("2", sx * PIN, sy * PIN, 1.4, 2.6, f"{name}/p2/{i}"))

    h = BODY / 2
    rect_lines(f, -h, -h, h, h, "F.Fab", FAB_W, f"{name}/fab/body")
    f.add(line(h, -BARREL_R, BARREL_END, -BARREL_R, "F.Fab", FAB_W, f"{name}/fab/bt"),
          line(h, BARREL_R, BARREL_END, BARREL_R, "F.Fab", FAB_W, f"{name}/fab/bb"),
          line(BARREL_END, -BARREL_R, BARREL_END, BARREL_R, "F.Fab", FAB_W, f"{name}/fab/be"))

    # Silkscreen: body outline, broken at the pads, plus a stub showing where
    # the barrel points so the assembler cannot fit it backwards.
    # The four ground posts sit 2.7 to 5.3 mm out along each axis, so the
    # outline is drawn only across the middle of each edge -- a continuous
    # square would run straight through the pads.
    m = 2.4
    for key, (x1, y1, x2, y2) in {
        "t": (-m, -h, m, -h), "b": (-m, h, m, h),
        "l": (-h, -m, -h, m), "r": (h, -m, h, m),
    }.items():
        f.add(line(x1, y1, x2, y2, "F.SilkS", SILK_W, f"{name}/silk/{key}"))
    # the barrel overhangs the board edge, so it is shown on F.Fab only;
    # a silk line there would be clipped by the edge and flagged by DRC
    f.add(line(h, -BARREL_R, h + 1.5, -BARREL_R, "F.Fab", FAB_W, f"{name}/fab/bt2"),
          line(h, BARREL_R, h + 1.5, BARREL_R, "F.Fab", FAB_W, f"{name}/fab/bb2"))

    rect_lines(f, -h - 0.25, -h - 0.25, BARREL_END + 0.25, h + 0.25,
               "F.CrtYd", CRT_W, f"{name}/crt")
    text_fab(f, "BNC", 0, 0, f"{name}/fabtxt")
    model(f, "${KIPRJMOD}/lib/lorenz.3dshapes/BNC_KYWE_RightAngle.wrl",
          scale=MM_SCALE)
    return name, f


# ---------------------------------------------------------------- DC-DC -----
def dcdc():
    """YLPTEC / EVISUN A05xxS-1WR3 and -2WR2 isolated SIP modules.

    Both share pins on a 2.54 mm grid at positions 1, 2, (3 absent), 4, 5, 6 --
    span 12.70 mm -- so one footprint takes the 1 W and the 2 W part.  Body is
    19.5 x 6.0 mm (1 W) or 19.65 x 7.0 mm (2 W); the outline drawn here is the
    larger of the two.  Recommended hole diameter 1.0 mm.
    """
    name = "DCDC_SIP_A05xxS_1W_2W"
    f = fp_header(name,
                  "Isolated dual-output DC/DC SIP module, 5 pins on 2.54mm grid "
                  "(pos 1,2,4,5,6), fits A0515S-2WR2 and A0515S-1WR3",
                  "DC-DC isolated SIP dual-output", "through_hole", 5.6)
    PITCH, X0 = 2.54, 0.0
    positions = {1: 0, 2: 1, 4: 3, 5: 4, 6: 5}
    for pin, slot in positions.items():
        x = X0 + slot * PITCH
        shape = "rect" if pin == 1 else "circle"
        f.add(tht_pad(str(pin), x, 0, 1.0, 1.8, f"{name}/p{pin}", shape))

    # Body: 19.65 long, pin 1 sits 2.21 mm in from the left end (2 W drawing);
    # 7.0 mm deep with the pin row 0.9 mm from the front edge.
    bx1, bx2 = -2.21, -2.21 + 19.65
    by1, by2 = -6.1, 0.9
    rect_lines(f, bx1, by1, bx2, by2, "F.Fab", FAB_W, f"{name}/fab")
    # Silk stops 1.3 mm above the pin row: the body really does reach y=+0.9,
    # but an outline there crosses the pads.
    rect_lines(f, bx1, by1, bx2, -1.3, "F.SilkS", SILK_W, f"{name}/silk")
    f.add(circle(X0, -2.2, 0.3, "F.SilkS", SILK_W, f"{name}/silk/p1dot"))
    rect_lines(f, bx1 - 0.25, by1 - 0.25, bx2 + 0.25, 1.5,
               "F.CrtYd", CRT_W, f"{name}/crt")
    text_fab(f, "+/-15V", (bx1 + bx2) / 2, -2.6, f"{name}/fabtxt")
    model(f, "${KIPRJMOD}/lib/lorenz.3dshapes/DCDC_SIP_A05xxS.wrl",
          scale=MM_SCALE)
    return name, f


# ------------------------------------------------------------ DIP switch ----
def dipsw():
    """KingTek DSIC06LSGET, 6-way SMD DIP switch, 2.54 mm pitch (LCSC C54952).

    Drawing DSIC06LSGET-A "RECOMMENDED P.C.B. LAYOUT": pads 2.20 x 1.44 mm,
    6.60 mm between the inner pad edges and 11.00 mm across the outer edges,
    giving 8.80 mm between pad centres; switch pitch 2.54 mm.  Pad sizes here
    are grown slightly for a visible hand-solder fillet.
    """
    name = "SW_DIP_SPSTx06_KingTek_DSIC06_P2.54mm"
    f = fp_header(name,
                  "6-way SMD DIP switch, 2.54mm pitch, 8.8mm row spacing, "
                  "KingTek DSIC06LSGET (LCSC C54952)",
                  "DIP switch SPST x6 SMD 2.54mm", "smd", 8.4)
    PITCH, ROW, PW, PH = 2.54, 4.40, 2.40, 1.50
    y0 = -PITCH * 2.5           # six positions centred on the origin
    for i in range(6):
        y = y0 + i * PITCH
        f.add(smd_pad(str(i + 1), -ROW, y, PW, PH, f"{name}/p{i+1}"),
              smd_pad(str(12 - i), ROW, y, PW, PH, f"{name}/p{12-i}"))

    bw, bl = 6.00 / 2, 15.24 / 2        # body 15.24 x 6.00 mm
    rect_lines(f, -bw, -bl, bw, bl, "F.Fab", FAB_W, f"{name}/fab")
    # Silk runs down the two open sides only, clear of every pad.
    f.add(line(-bw, -bl, bw, -bl, "F.SilkS", SILK_W, f"{name}/silk/t"),
          line(-bw, bl, bw, bl, "F.SilkS", SILK_W, f"{name}/silk/b"),
          line(-bw, -bl, -bw, -bl + 1.2, "F.SilkS", SILK_W, f"{name}/silk/l1"),
          line(bw, -bl, bw, -bl + 1.2, "F.SilkS", SILK_W, f"{name}/silk/r1"),
          line(-bw, bl - 1.2, -bw, bl, "F.SilkS", SILK_W, f"{name}/silk/l2"),
          line(bw, bl - 1.2, bw, bl, "F.SilkS", SILK_W, f"{name}/silk/r2"))
    f.add(circle(-bw + 0.8, -bl + 0.8, 0.3, "F.SilkS", SILK_W, f"{name}/silk/p1dot"))
    rect_lines(f, -(ROW + PW / 2 + 0.25), -bl - 0.25, ROW + PW / 2 + 0.25, bl + 0.25,
               "F.CrtYd", CRT_W, f"{name}/crt")
    text_fab(f, "ON ->", 0, -bl + 1.2, f"{name}/fabtxt", size=0.7)
    # close enough to the real DSIC06 to be worth showing: same six positions,
    # 2.54 mm pitch, 8.61 mm rather than 8.8 mm between the rows
    model(f, "${KICAD10_3DMODEL_DIR}/Button_Switch_SMD.3dshapes/"
             "SW_DIP_SPSTx06_Slide_9.78x17.42mm_W8.61mm_P2.54mm.step")
    return name, f


def main():
    os.makedirs(OUT, exist_ok=True)
    for maker in (bnc, dcdc, dipsw):
        name, node = maker()
        path = os.path.join(OUT, name + ".kicad_mod")
        with open(path, "w") as fh:
            fh.write(node.render() + "\n")
        print(f"  wrote {os.path.relpath(path)}")


if __name__ == "__main__":
    main()
