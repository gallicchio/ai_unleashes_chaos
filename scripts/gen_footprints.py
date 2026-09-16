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
    model(f, "${KIPRJMOD}/lib/lorenz.3dshapes/SW_DIP_x06_DSIC06.wrl",
          scale=MM_SCALE)
    return name, f


# ------------------------------------------------------------- RGB lamp ----
def led_rgb():
    """MEIHUA MHPA3528CRGBCT common-anode RGB lamp, PLCC-4 (LCSC C2962095).

    Datasheet LPDS-0001482 Rev.1 page 2: body 3.5 x 2.8 mm, 1.85 mm tall.
    "Recommended solder pad" gives four 1.2 x 0.95 mm pads with 2.0 mm between
    the two columns and 0.5 mm between the two rows, so the pad centres land
    on +/-1.6 mm and +/-0.725 mm.  Pin 1 is bottom left in the top view and
    the numbering runs anticlockwise.  The land pattern is the same for both
    of MEIHUA's 3528 lamps; only what sits on each pad differs.  This board
    fits the common-*anode* MHPA3528CRGBCT: 1 = anode, 2 = blue cathode,
    3 = green cathode, 4 = red cathode.
    """
    name = "LED_RGB_PLCC4_3.5x2.8mm"
    f = fp_header(name,
                  "RGB LED, PLCC-4 3.5x2.8mm, MEIHUA MHPA3528CRGBCT common "
                  "anode (LCSC C2962095); 1=A 2=B- 3=G- 4=R-",
                  "LED RGB PLCC-4 3528 common anode", "smd", 2.9)
    PX, PY, PW, PH = 1.6, 0.725, 1.2, 0.95
    for (num, sx, sy) in (("1", -1, +1), ("2", -1, -1), ("3", +1, -1),
                          ("4", +1, +1)):
        f.add(smd_pad(num, sx * PX, sy * PY, PW, PH, f"{name}/p{num}"))
    bw, bh = 3.5 / 2, 2.8 / 2
    rect_lines(f, -bw, -bh, bw, bh, "F.Fab", FAB_W, f"{name}/fab")
    # Silk only above and below the pads, where there is room for it.
    f.add(line(-bw, -bh, bw, -bh, "F.SilkS", SILK_W, f"{name}/silk/t"),
          line(-bw, bh, bw, bh, "F.SilkS", SILK_W, f"{name}/silk/b"))
    # Pin-1 mark, well clear of pad 1 (which reaches x = -2.2, y = 1.2).
    f.add(circle(-2.45, 1.45, 0.2, "F.SilkS", SILK_W, f"{name}/silk/p1"))
    rect_lines(f, -2.45, -1.6, 2.45, 1.6, "F.CrtYd", CRT_W, f"{name}/crt")
    text_fab(f, "A", -1.6, 1.15, f"{name}/fab1", size=0.6)
    model(f, "${KIPRJMOD}/lib/lorenz.3dshapes/LED_RGB_PLCC4.wrl", scale=MM_SCALE)
    return name, f


# ------------------------------------------------- scope ground anchor ------
def scope_gnd():
    """Two plated 1.1 mm holes on 5.08 mm centres, both on the same net.

    A scope ground clip needs something to grab.  Push a loop of wire -- a
    resistor lead offcut does -- through the two holes and solder it, and the
    clip has a post.  Nothing is fitted at the factory: this is two holes and
    a legend, so it costs two drill hits and nothing else.
    """
    name = "TestPoint_ScopeGnd_Loop_2x1.1mm"
    f = fp_header(name,
                  "Oscilloscope ground anchor: two 1.1mm plated holes on "
                  "5.08mm centres for a hand-fitted wire loop",
                  "test point ground loop scope", "through_hole", 4.2)
    for (num, x) in (("1", -2.54), ("1", 2.54)):
        f.add(tht_pad(num, x, 0, 1.1, 2.2, f"{name}/p{x}"))
    # The loop the wire is meant to make, drawn so it is obvious what to do.
    f.add(line(-2.54, -1.6, 2.54, -1.6, "F.SilkS", SILK_W, f"{name}/silk/arc"))
    f.add(line(-2.54, -1.6, -2.54, -1.3, "F.SilkS", SILK_W, f"{name}/silk/l"),
          line(2.54, -1.6, 2.54, -1.3, "F.SilkS", SILK_W, f"{name}/silk/r"))
    rect_lines(f, -3.9, -2.0, 3.9, 1.4, "F.CrtYd", CRT_W, f"{name}/crt")
    rect_lines(f, -3.7, -1.8, 3.7, 1.2, "F.Fab", FAB_W, f"{name}/fab")
    return name, f


# ------------------------------------------------------------ PTC fuse -----
def ptc():
    """1812 land pattern for the resettable fuse, named so it is a PTC.

    Geometrically the same as KiCad's Fuse_1812_4532Metric -- IPC density
    level B, pads 1.125 x 3.4 mm on 4.275 mm centres -- but the symbol this
    project uses is Device:Polyfuse, whose footprint filters ask for a name
    containing "PTC".  A footprint whose name disagrees with the symbol is a
    DRC warning and, more to the point, an invitation to fit the wrong part.
    """
    name = "PTC_1812_4532Metric"
    f = fp_header(name,
                  "Resettable PTC fuse, 1812 (4532 metric), IPC density B; "
                  "Bourns MF-MSMF050-2 (LCSC C17313)", "PTC fuse resettable "
                  "polyfuse 1812", "smd", 2.8)
    for (num, x) in (("1", -2.1375), ("2", 2.1375)):
        f.add(smd_pad(num, x, 0, 1.125, 3.4, f"{name}/p{num}"))
    rect_lines(f, -2.25, -1.6, 2.25, 1.6, "F.Fab", FAB_W, f"{name}/fab")
    f.add(line(-1.5, -1.85, 1.5, -1.85, "F.SilkS", SILK_W, f"{name}/silk/t"),
          line(-1.5, 1.85, 1.5, 1.85, "F.SilkS", SILK_W, f"{name}/silk/b"))
    rect_lines(f, -2.95, -2.1, 2.95, 2.1, "F.CrtYd", CRT_W, f"{name}/crt")
    model(f, "${KIPRJMOD}/lib/lorenz.3dshapes/Fuse_1812.wrl", scale=MM_SCALE)
    return name, f


# ------------------------------------------------------------- trimmer -----
def trimpot():
    """Bourns 3386P, 3/8 inch square single-turn cermet trimmer, top adjust.

    Bourns 3386 data sheet: a 9.53 mm square body 4.83 mm tall, screw on top,
    and the P pin pattern -- terminal 1 and terminal 3 on a 5.08 mm pitch with
    the wiper 2.54 mm to the side of the midpoint.  Pins are 0.51 mm diameter,
    so 0.8 mm holes.

    KiCad ships this footprint, but the AppImage's reduced 3D set has no model
    for it, and a footprint edited on the board to add one stops matching its
    library.  Drawing it here keeps the board, the library and the render in
    agreement.  Pad 1 is square, which is the other thing KiCad's copy does
    not do and the one that tells an assembler which way round it goes.
    """
    name = "Potentiometer_Bourns_3386P_Vertical"
    f = fp_header(name,
                  "Bourns 3386P, 9.53 mm square single-turn cermet trimmer, "
                  "top adjust (LCSC C116287)",
                  "potentiometer trimmer trimpot Bourns 3386P vertical",
                  "through_hole", 3.6)
    cy = -2.54                       # body centre, relative to terminal 1
    for (num, x, y, shape) in (("1", 0.0, 0.0, "rect"),
                               ("2", 2.54, -2.54, "circle"),
                               ("3", 0.0, -5.08, "circle")):
        f.add(tht_pad(num, x, y, 0.8, 1.6, f"{name}/p{num}", shape=shape))
    rect_lines(f, -4.765, cy - 4.765, 4.765, cy + 4.765, "F.Fab", FAB_W,
               f"{name}/fab")
    f.add(circle(0, cy, 1.6, "F.Fab", FAB_W, f"{name}/screw"))
    rect_lines(f, -4.87, cy - 4.87, 4.87, cy + 4.87, "F.SilkS", SILK_W,
               f"{name}/silk")
    # the corner that says which end terminal 1 is
    f.add(line(-4.87, 1.4, -3.5, 2.33, "F.SilkS", SILK_W, f"{name}/silk/p1"))
    rect_lines(f, -5.12, cy - 5.12, 5.12, cy + 5.12, "F.CrtYd", CRT_W,
               f"{name}/crt")
    text_fab(f, "1", -2.2, 0.0, f"{name}/fab/p1", size=0.9)
    model(f, "${KIPRJMOD}/lib/lorenz.3dshapes/Potentiometer_3386P.wrl",
          scale=MM_SCALE)
    return name, f


def main():
    os.makedirs(OUT, exist_ok=True)
    for maker in (bnc, dcdc, dipsw, led_rgb, scope_gnd, ptc, trimpot):
        name, node = maker()
        path = os.path.join(OUT, name + ".kicad_mod")
        with open(path, "w") as fh:
            fh.write(node.render() + "\n")
        print(f"  wrote {os.path.relpath(path)}")


if __name__ == "__main__":
    main()
