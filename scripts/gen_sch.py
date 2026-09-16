#!/usr/bin/env python3
"""Draw the Lorenz attractor schematic, laid out the way Paul draws it.

Three integrator rows stacked down the sheet, the two multipliers in the gaps
on the left feeding the middle of rows 2 and 3, and the three outputs returning
along lanes on the left to feed everything back.  Every signal is a drawn wire;
only the supply rails use labels.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kienv, parts
from schlib import Sheet
from lorenz_curve import owl_xz

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "..", "hardware", "lib", "lorenz.kicad_sym")
OUT = os.path.join(HERE, "..", "hardware", "lorenz.kicad_sch")

# ------------------------------------------------------------ geometry -----
BUS_Z, BUS_NY, BUS_X = 19.05, 30.48, 41.91
GNDCOL   = 60.96          # where the multipliers' grounded inputs turn down
MULT_CX  = 80.01          # multiplier body centre
ZJOG     = 101.6          # column for the multipliers' Z2-to-ground stub
JOG_X    = 135.89         # column the multiplier outputs drop down
RES_CX   = 146.05         # summing resistors  (pins 142.24 / 149.86)
SJ_X     = 168.91         # summing-junction rail
OPA_X    = 187.96         # op-amp body        (-in 180.34, out 195.58)
OUT_X    = 215.9          # output node
RS_CX    = 228.6          # 100 ohm series resistor
BNC_X    = 248.92         # BNC jack           (signal pin at 243.84)
C_FAST, C_NICE, C_SLOW = 173.99, 187.96, 201.93  # capacitor-bank branches

ROW_Y = (63.5, 152.4, 241.3)
RET_DY = 21.59            # output return lane, below each row
BANK_LO, BANK_HI = 13.97, 41.91   # capacitor bank rails, above each row

MULT_Y = (114.3, 203.2)   # U3, U4 body centres -- in the gaps between rows

# the chaos lamp, in the band below the third row
RGB_R, RGB_G, RGB_B = 269.24, 274.32, 279.4
LED_CX, BUF_CX = 114.3, 160.02


def fp(key):
    return parts.PARTS[key]["footprint"]


def rfp():
    return parts.PARTS["R_0805"]["footprint"]


def passive_fields(value):
    p = parts.PASSIVES.get(value)
    return {"LCSC": p["lcsc"], "MPN": p["mpn"]} if p else {}


def part_fields(key):
    p = parts.PARTS[key]
    return {"LCSC": p["lcsc"], "MPN": p["mpn"]}


def build():
    s = Sheet(kienv.share_dir(), paper="A2",
              title="AI Unleashes Chaos -- Lorenz Attractor",
              date=parts.BOARD_DATE, rev=parts.REV,
              company="Circuit by Paul Horowitz  |  PCB by Jason Gallicchio and Claude",
              comments=["dx/dt = s(y-x)   dy/dt = rx - y - xz   dz/dt = xy - bz",
                        "s = 10,  r = 28,  b = 8/3",
                        "Every coefficient is 1 MEG / R;  signals are 0.1 V per unit",
                        "Open source -- https://github.com/gallicchio/ai_unleashes_chaos"])
    s.add_local_lib(LIB, "lorenz")

    pwr_n = [0]

    def pwr_ref():
        pwr_n[0] += 1
        return f"#PWR{pwr_n[0]:02d}"

    def gnd(x, y, key="", up=False, net="GND"):
        """Drop a ground symbol; `up` flips it for a wire arriving from below.

        Two grounds exist on this board.  GND is everything downstream of the
        isolated converter -- the analog circuit, the BNC shells, the scope's
        ground.  GNDU is the USB side.  They meet only at R21/C25/JP1.
        """
        lib = "power:GND" if net == "GND" else "lorenz:GNDU"
        s.place(lib, pwr_ref(), net, x, y, rot=180 if up else 0,
                in_bom=False, on_board=False, hide_ref=True, hide_value=True)

    tp_n = [0]

    def testpoint(x, y, name, rot=180, dx=2.54, dy=0.6, justify="left",
                  loop=False):
        """A probe pad on the board, carrying the name of what it probes.

        The name is the symbol's value, so it reaches the board as a legend
        beside the pad: a probe pad nobody can identify is not a probe pad.
        """
        tp_n[0] += 1
        ref = f"TP{tp_n[0]}"
        s.place("Connector:TestPoint", ref, name, x, y, rot=rot,
                footprint=parts.PARTS["SCOPE_GND" if loop else "TESTPOINT"]
                ["footprint"],
                in_bom=False, hide_ref=True,
                val_off=(dx, dy), val_justify=justify)
        return ref

    def rail(name, x, y, rot=0, to=None):
        s.place(f"power:{name}", pwr_ref(),
                name, x, y, rot=rot, in_bom=False, on_board=False,
                hide_ref=True, val_off=(0, -3.81) if rot == 0 else (0, 3.81))
        if to is not None:
            s.wire((x, y), (x, to))

    # =================================================== the three rows =====
    rows = [
        dict(  # dx/dt = 10(y - x)
            opa=("U1", 1), out="x", y=ROW_Y[0],
            res=[("R1", "100k", -6.35, "-y"), ("R2", "100k", +6.35, "x")],
            caps=("C1", "C2", "C3"), poles=(1, 4), outres="R8", bnc="J2",
            label="x", sj="SJ_X", note="dx/dt = 10 (y - x)"),
        dict(  # dy/dt = 28x - y - xz
            opa=("U1", 2), out="-y", y=ROW_Y[1],
            res=[("R4", "10k", -12.7, "xz"), ("R3", "35.7k", 0.0, "x"),
                 ("R5", "1M", +12.7, "-y")],
            caps=("C4", "C5", "C6"), poles=(2, 5), outres="R9", bnc="J3",
            label="-y", sj="SJ_Y", note="dy/dt = 28 x - y - x z"),
        dict(  # dz/dt = xy - (8/3) z
            opa=("U2", 1), out="z", y=ROW_Y[2],
            res=[("R6", "10k", -6.35, "xy"), ("R7", "374k", +6.35, "z")],
            caps=("C7", "C8", "C9"), poles=(3, 6), outres="R10", bnc="J4",
            label="z", sj="SJ_Z", note="dz/dt = x y - 2.674 z"),
    ]

    feeds = {"x": [], "-y": [], "z": []}      # (x_start, y) horizontal bus taps

    for row in rows:
        y = row["y"]
        uref, uunit = row["opa"]
        y_neg, y_pos, y_out = y - 2.54, y + 2.54, y
        s.place("lorenz:LF412", uref, "LF412", OPA_X, y, unit=uunit,
                footprint=fp("LF412"), fields=part_fields("LF412"),
                ref_off=(1.27, 7.62), val_off=(1.27, 10.8), hide_value=True,
                ref_justify="left")
        s.text("1/2 LF412", OPA_X + 1.27, y + 10.8, size=1.7)

        # --- summing resistors, fanning into the summing-junction rail -----
        ys = [y + dy for (_, _, dy, _) in row["res"]]
        for (ref, val, dy, src) in row["res"]:
            ry = y + dy
            s.place("Device:R_US", ref, val, RES_CX, ry, rot=90,
                    footprint=rfp(), fields=passive_fields(val),
                    ref_off=(0, -7.0), val_off=(0, -3.7))
            s.wire((149.86, ry), (SJ_X, ry))
            if src in feeds:
                feeds[src].append((142.24, ry))
        s.wire((SJ_X, min(ys)), (SJ_X, max(ys)))
        for ry in ys:
            s.junction(SJ_X, ry)
        # rail up into the capacitor bank, and across to the op-amp
        s.wire((SJ_X, min(ys)), (SJ_X, y - BANK_LO))
        s.wire((SJ_X, y_neg), (180.34, y_neg))
        if y_neg not in ys:
            s.junction(SJ_X, y_neg)
        # The summing junction is the one node with no drawn name, and every
        # check that reads the netlist back has to talk about it, so name it.
        s.label(row["sj"], 176.53, y_neg, size=1.3)

        # --- non-inverting input to ground --------------------------------
        s.wire((180.34, y_pos), (180.34, y + 10.16))
        gnd(180.34, y + 10.16, key=f"op{uref}{uunit}")

        # --- capacitor bank: fast always, nice and slow behind DIP poles ---
        y_a, y_b = y - BANK_LO, y - BANK_HI
        s.wire((SJ_X, y_a), (C_SLOW, y_a))
        s.wire((C_FAST, y_b), (OUT_X, y_b))
        cf, cn, cs = row["caps"]
        # fast branch -- a bare capacitor
        s.place("Device:C", cf, "2.2nF", C_FAST, y - 27.94,
                footprint=parts.PARTS["C_0805"]["footprint"],
                fields=passive_fields("2.2nF"),
                ref_off=(2.54, -2.2), val_off=(2.54, 1.1),
                ref_justify="left", val_justify="left")
        s.wire((C_FAST, y_a), (C_FAST, y - 24.13))
        s.wire((C_FAST, y - 31.75), (C_FAST, y_b))
        s.junction(C_FAST, y_a)
        s.junction(C_FAST, y_b)
        # nice and slow branches -- capacitor in series with one switch pole
        for (bx, cref, cval, pole, tag) in (
                (C_NICE, cn, "100nF", row["poles"][0], "nice!"),
                (C_SLOW, cs, "470nF", row["poles"][1], "slow!")):
            lcsc = "100nF_C0G" if cval == "100nF" else cval
            s.place("Device:C", cref, cval, bx, y - 17.78,
                    footprint=parts.PARTS["C_1206"]["footprint"],
                    fields=passive_fields(lcsc),
                    ref_off=(2.54, -2.2), val_off=(2.54, 1.1),
                    ref_justify="left", val_justify="left")
            s.place("lorenz:SW_DIP_x06_Poles", "SW1", "SW_DIP_x06", bx,
                    y - 33.02, rot=90, unit=pole, footprint=fp("SW_DIP6"),
                    fields=part_fields("SW_DIP6"),
                    ref_off=(5.6, -0.6), val_off=(5.6, 2.6),
                    hide_value=True, ref_justify="left")
            s.wire((bx, y - 21.59), (bx, y - 27.94))
            s.wire((bx, y - 38.1), (bx, y_b))
            s.junction(bx, y_a)
            s.junction(bx, y_b)
        s.text("fast!", C_FAST - 1.27, y_b - 3.81, size=1.6, justify="right")
        s.text("nice!", C_NICE - 1.27, y_b - 3.81, size=1.6, justify="right")
        s.text("slow!", C_SLOW - 1.27, y_b - 3.81, size=1.6, justify="right")
        s.text("C", SJ_X + 2.54, y_a - 2.03, size=2.0)

        # --- output node, series resistor, BNC ----------------------------
        s.wire((195.58, y_out), (OUT_X, y_out))
        testpoint(205.74, y_out - 6.35, row["label"], rot=0, dx=2.2, dy=-1.0)
        s.wire((205.74, y_out), (205.74, y_out - 6.35))
        s.junction(205.74, y_out)
        s.wire((OUT_X, y_b), (OUT_X, y + RET_DY))
        s.junction(OUT_X, y_out)
        s.junction(OUT_X, y_b)
        s.place("Device:R_US", row["outres"], "100R", RS_CX, y_out, rot=90,
                footprint=rfp(), fields=passive_fields("100R"),
                ref_off=(0, -6.6), val_off=(0, -3.3))
        s.wire((OUT_X, y_out), (RS_CX - 3.81, y_out))
        s.place("Connector:Conn_Coaxial", row["bnc"], "BNC", BNC_X, y_out,
                footprint=fp("BNC"), fields=part_fields("BNC"),
                ref_off=(5.08, -5.08), val_off=(5.08, -1.9),
                ref_justify="left", val_justify="left")
        s.wire((RS_CX + 3.81, y_out), s.pin(row["bnc"], 1, "1"))
        s.wire((BNC_X, y_out + 5.08), (BNC_X, y_out + 11.43))
        gnd(BNC_X, y_out + 11.43, key=f"bnc{row['bnc']}")
        s.label({"x": "x", "-y": "-y", "z": "z"}[row["out"]],
                OUT_X, y_out + 11.43, size=1.5)
        s.text(row["label"], 232.41, y_out - 3.81, size=3.2)
        s.text(row["note"], SJ_X - 1.27, y + 16.51, size=1.8, justify="right")

    # ==================================================== multipliers ======
    # U3 forms -xz/100 and U4 forms -xy/100.  The sign inversions come free
    # by swapping the differential inputs -- no extra op-amps, as Paul notes.
    mults = [
        dict(ref="U3", my=MULT_Y[0], xin="x", yin="z", swap="y",
             dest=(142.24, ROW_Y[1] - 12.7), legend="-xz/100"),
        dict(ref="U4", my=MULT_Y[1], xin="-y", yin="x", swap="x",
             dest=(142.24, ROW_Y[2] - 6.35), legend="-xy/100"),
    ]
    for m in mults:
        ref, my = m["ref"], m["my"]
        s.place("lorenz:MPY634", ref, "MPY634", MULT_CX, my, unit=1,
                footprint=fp("MPY634"), fields=part_fields("MPY634"),
                ref_off=(-10.16, -16.51), val_off=(-10.16, -13.33),
                ref_justify="left", val_justify="left")
        px1, px2 = s.pin(ref, 1, "1"), s.pin(ref, 1, "2")
        py1, py2 = s.pin(ref, 1, "6"), s.pin(ref, 1, "7")
        psf = s.pin(ref, 1, "4")
        pz1, pw, pz2 = s.pin(ref, 1, "13"), s.pin(ref, 1, "14"), s.pin(ref, 1, "12")

        # the two signal inputs, tapped off the bus lanes
        if m["swap"] == "y":                      # x on X1, z on Y2 (inverts)
            sig = [(px1, m["xin"]), (py2, m["yin"])]
            grounded = [px2, py1]
            tie = True
        else:                                     # -y on X1, x on Y1
            sig = [(px1, m["xin"]), (py1, m["yin"])]
            grounded = [px2, py2]
            tie = False
        for (pt, net) in sig:
            feeds[net].append(pt)

        if tie:            # the two grounded pins are adjacent: one tie, one symbol
            (gx, gy1), (_, gy2) = grounded[0], grounded[1]
            s.wire(grounded[0], (GNDCOL, gy1))
            s.wire((GNDCOL, gy1), (GNDCOL, gy2))
            s.wire((GNDCOL, gy2), grounded[1])
            s.wire((GNDCOL, (gy1 + gy2) / 2), (GNDCOL - 7.62, (gy1 + gy2) / 2))
            s.junction(GNDCOL, (gy1 + gy2) / 2)
            gnd(GNDCOL - 7.62, (gy1 + gy2) / 2, key=f"{ref}g")
        else:              # a signal runs between them: two separate stubs
            for i, pt in enumerate(grounded):
                s.wire(pt, (GNDCOL, pt[1]))
                gnd(GNDCOL, pt[1], key=f"{ref}g{i}")

        s.no_connect(*psf)
        s.text("SF left open:", psf[0] - 3.81, psf[1] - 1.0, size=1.4, justify="right")
        s.text("x10 V scale factor", psf[0] - 3.81, psf[1] + 1.8, size=1.4,
               justify="right")

        # Z1 back to the output, Z2 to ground -- the standard multiplier hookup
        s.wire(pw, m["dest"] if False else (JOG_X, pw[1]))
        s.wire(pz1, (93.98, pz1[1]), (93.98, pw[1]))
        s.junction(93.98, pw[1])
        s.wire(pz2, (ZJOG, pz2[1]), (ZJOG, pz2[1] + 8.89))
        gnd(ZJOG, pz2[1] + 8.89, key=f"{ref}z2")
        s.text("Z1 to output, Z2 to ground:", pz2[0] + 2.54, pz2[1] + 12.7, size=1.4)
        s.text("the plain multiplier connection", pz2[0] + 2.54, pz2[1] + 15.4, size=1.4)

        testpoint(120.65, pw[1] - 6.35, m["legend"], rot=0, dx=2.2, dy=-1.0)
        s.wire((120.65, pw[1]), (120.65, pw[1] - 6.35))
        s.junction(120.65, pw[1])

        # drop down the jog column into the summing resistor
        s.label("xz" if ref == "U3" else "xy", JOG_X, pw[1] + 6.35, size=1.5)
        dx, dy = m["dest"]
        s.wire((JOG_X, pw[1]), (JOG_X, dy), (dx, dy))
        s.text(m["legend"], JOG_X + 1.9, pw[1] - 2.2, size=1.9)

    # ============================== the chaos lamp, driven by x, -y and z ===
    # Three signals, three colours, one lamp.  The signals swing either side of
    # ground, so the lamp's common cathode is held at -1.5 V by U2B -- the half
    # of U2 Paul never needed -- and each colour then lights only while its own
    # signal is above its own turn-on voltage.  Red marks the +x wing, green
    # the -x wing, and blue brightens with z, so in "slow!" the colour walks
    # around the attractor with the trajectory.
    for (lane, ly, ref, val, rx, note) in (
            (BUS_X, RGB_R, "R16", "1.5k", 83.82, "x  -> red"),
            (BUS_NY, RGB_G, "R17", "6.8k", 95.25, "-y -> green"),
            (BUS_Z, RGB_B, "R18", "4.7k", 104.14, "z  -> blue")):
        # The three rows are close together, so the resistors step to the
        # right as they go down and each one's labels sit over its own body.
        s.place("Device:R_US", ref, val, rx, ly, rot=90, footprint=rfp(),
                fields=passive_fields(val),
                ref_off=(0, -4.4), val_off=(0, -1.9))
        feeds[{BUS_X: "x", BUS_NY: "-y", BUS_Z: "z"}[lane]].append((rx - 3.81, ly))
        s.wire((rx + 3.81, ly), (LED_CX - 5.08, ly))
        s.text(note, 62.23, ly - 1.4, size=1.6)
    s.place("lorenz:LED_RGB_CC", "D4", "RGB", LED_CX, RGB_G,
            footprint=fp("LED_RGB"), fields=part_fields("LED_RGB"),
            ref_off=(-7.62, -9.8), val_off=(-7.62, -6.8),
            ref_justify="right", val_justify="right")
    s.place("lorenz:LF412", "U2", "LF412", BUF_CX, RGB_G, unit=2, mirror="y",
            footprint=fp("LF412"), fields=part_fields("LF412"),
            ref_off=(0, 9.4), val_off=(0, 12.6), hide_value=True)
    s.text("1/2 LF412", BUF_CX, RGB_G + 12.6, size=1.7)
    k_pin = s.pin("D4", 1, "4")
    b_out, b_neg, b_pos = (s.pin("U2", 2, "7"), s.pin("U2", 2, "6"),
                           s.pin("U2", 2, "5"))
    s.wire(k_pin, b_out)
    # the follower's feedback, taken above the body
    s.wire(b_out, (b_out[0], RGB_R - 2.54), (b_neg[0], RGB_R - 2.54), b_neg)
    s.junction(*b_out)
    tp_vled = testpoint(134.62, RGB_G - 2.54, "-1.5V", rot=0, dx=-2.2, dy=-1.0,
                        justify="right")
    s.wire((134.62, RGB_G), (134.62, RGB_G - 2.54))
    s.junction(134.62, RGB_G)

    # --- the reference the buffer holds the cathode at --------------------
    NODE_X = 186.69
    s.wire(b_pos, (NODE_X, b_pos[1]))
    s.place("Device:R_US", "R20", "33k", NODE_X + 3.81, b_pos[1], rot=90,
            footprint=rfp(), fields=passive_fields("33k"),
            ref_off=(0, -4.4), val_off=(0, 3.4))
    s.wire((NODE_X + 7.62, b_pos[1]), (NODE_X + 12.7, b_pos[1]))
    rail("-12V", NODE_X + 12.7, b_pos[1] + 3.81, rot=180, to=b_pos[1])
    for (ref, val, cx, lib, key) in (
            ("C24", "100nF", 172.72, "Device:C", "100nF"),
            ("R19", "4.7k", 181.61, "Device:R_US", "4.7k")):
        s.place(lib, ref, val, cx, b_pos[1] + 6.35,
                footprint=(parts.PARTS["C_0805"]["footprint"] if ref[0] == "C"
                           else rfp()),
                fields=passive_fields(key),
                ref_off=(2.4, -1.0), val_off=(2.4, 2.2),
                ref_justify="left", val_justify="left")
        s.wire((cx, b_pos[1]), (cx, b_pos[1] + 2.54))
        s.wire((cx, b_pos[1] + 10.16), (cx, b_pos[1] + 12.7))
        gnd(cx, b_pos[1] + 12.7, key=f"ref{ref}")
        s.junction(cx, b_pos[1])
    s.text("-12 V x 4.7k / (4.7k + 33k) = -1.5 V, buffered so",
           190.5, 288.0, size=1.4)
    s.text("the lamp current cannot drag the reference about.",
           190.5, 290.7, size=1.4)
    s.text("CHAOS LAMP", 62.23, 262.0, size=2.4)

    # ======================================= bus lanes and return lanes =====
    lanes = {"x": BUS_X, "-y": BUS_NY, "z": BUS_Z}
    returns = {"x": ROW_Y[0] + RET_DY, "-y": ROW_Y[1] + RET_DY, "z": ROW_Y[2] + RET_DY}
    for name, row in zip(("x", "-y", "z"), rows):
        lane = lanes[name]
        ry = returns[name]
        # output -> down -> left to the lane
        s.wire((OUT_X, ry), (lane, ry))
        taps = sorted(feeds[name], key=lambda p: p[1])
        ys = [p[1] for p in taps] + [ry]
        s.wire((lane, min(ys)), (lane, max(ys)))
        for (tx, ty) in taps:
            s.wire((lane, ty), (tx, ty))
            s.junction(lane, ty)
        s.junction(lane, ry)
        # Paul labels the bus wherever it leaves for a load
        for (tx, ty) in taps:
            s.text(name, lane + 2.2, ty - 1.3, size=2.2)

    # ======================================================== power ========
    # USB-C 5 V -> isolated +/-15 V module -> 78L12 / 79L12 -> +/-12 V.
    # The module on its own is unregulated and climbs toward +/-18 V at light
    # load, which is the MPY634's absolute maximum; the two regulators pin the
    # rails and strip the converter's 100 kHz ripple.
    PY_TOP, PY_MID, PY_BOT = 312.42, 330.2, 351.79

    s.place("Connector:USB_C_Receptacle_USB2.0_16P", "J1", "USB-C", 45.72, 340.36,
            footprint=fp("USBC"), fields=part_fields("USBC"),
            ref_off=(-11.43, -20.32), val_off=(-11.43, -17.14),
            ref_justify="left", val_justify="left")
    vbus = s.pin("J1", 1, "A4")
    for nc in ("A6", "A7", "A8", "B6", "B7", "B8"):
        s.no_connect(*s.pin("J1", 1, nc))
    gpin = s.pin("J1", 1, "A1")
    s.wire(gpin, (gpin[0], gpin[1] + 5.08))
    gnd(gpin[0], gpin[1] + 5.08, key="usb", net="GNDU")
    sh = s.pin("J1", 1, "SH")
    s.wire(sh, (sh[0], sh[1] + 5.08))
    gnd(sh[0], sh[1] + 5.08, key="shell", net="GNDU")
    s.text("shell and cable screen stay", sh[0] - 1.27, sh[1] + 10.16, size=1.4)
    s.text("on the USB side of the barrier", sh[0] - 1.27, sh[1] + 12.86, size=1.4)

    # CC pull-downs: without these a USB-C charger never turns 5 V on.
    for (ref, pin_name, cx) in (("R11", "A5", 74.93), ("R12", "B5", 87.63)):
        pt = s.pin("J1", 1, pin_name)
        s.place("Device:R_US", ref, "5.1k", cx, 340.36, footprint=rfp(),
                fields=passive_fields("5.1k"),
                ref_off=(2.54, -2.2), val_off=(2.54, 1.1),
                ref_justify="left", val_justify="left")
        s.wire(pt, (cx, pt[1]), (cx, 336.55))
        s.wire((cx, 344.17), (cx, 349.25))
        gnd(cx, 349.25, key=f"cc{ref}", net="GNDU")
    s.text("5.1k on each CC line tells a", 74.93, 356.0, size=1.4)
    s.text("USB-C source to supply 5 V", 74.93, 358.7, size=1.4)

    s.place("Device:Polyfuse", "F1", "500mA", 104.14, vbus[1], rot=90,
            footprint=fp("FUSE"), fields=part_fields("FUSE"),
            ref_off=(0, -6.6), val_off=(0, -3.7))
    s.wire(vbus, (100.33, vbus[1]))
    s.wire((107.95, vbus[1]), (123.19, vbus[1]))
    rail("+5V", 123.19, vbus[1] - 3.81, to=vbus[1])
    s.junction(123.19, vbus[1])
    # VBUS is a passive pin, so ERC needs to be told this really is a source
    s.place("power:PWR_FLAG", "#FLG01", "PWR_FLAG", 114.3, vbus[1] - 3.81,
            in_bom=False, on_board=False, hide_ref=True, val_off=(0, -3.81))
    s.wire((114.3, vbus[1] - 3.81), (114.3, vbus[1]))
    s.junction(114.3, vbus[1])
    # ...and GNDU is a supply too: the converter drives GND through its COM
    # pin, but nothing on the board drives the USB side's ground.
    s.place("power:PWR_FLAG", "#FLG02", "PWR_FLAG", 62.23, 361.95,
            in_bom=False, on_board=False, hide_ref=True, val_off=(0, -3.81))
    s.wire((62.23, 361.95), (62.23, 365.76))
    gnd(62.23, 365.76, key="flgu", net="GNDU")

    for (ref, val, cx, key) in (("C10", "10uF", 123.19, "10uF"),
                                ("C11", "100nF", 135.89, "100nF")):
        s.place("Device:C", ref, val, cx, vbus[1] + 12.7,
                footprint=parts.PARTS["C_0805"]["footprint"],
                fields=passive_fields(key),
                ref_off=(2.54, -2.2), val_off=(2.54, 1.1),
                ref_justify="left", val_justify="left")
        s.wire((cx, vbus[1]), (cx, vbus[1] + 8.89))
        s.wire((cx, vbus[1] + 16.51), (cx, vbus[1] + 21.59))
        gnd(cx, vbus[1] + 21.59, key=f"bulk{ref}", net="GNDU")
        if cx != 135.89:
            s.junction(cx, vbus[1])
    s.wire((123.19, vbus[1]), (135.89, vbus[1]))

    s.place("lorenz:DCDC_A0515S", "U5", parts.PARTS["DCDC"]["value"],
            165.1, PY_MID, footprint=fp("DCDC"), fields=part_fields("DCDC"),
            ref_off=(-12.7, -11.43), val_off=(-12.7, -8.25),
            ref_justify="left", val_justify="left")
    vin, vinn = s.pin("U5", 1, "1"), s.pin("U5", 1, "2")
    vop, com, von = s.pin("U5", 1, "6"), s.pin("U5", 1, "5"), s.pin("U5", 1, "4")
    s.wire((135.89, vbus[1]), (142.24, vbus[1]), (142.24, vin[1]), vin)
    s.junction(135.89, vbus[1])
    s.wire(vinn, (142.24, vinn[1]), (142.24, 342.9))
    gnd(142.24, 342.9, key="dcin", net="GNDU")
    s.wire(vop, (186.69, vop[1]), (186.69, PY_TOP))
    s.wire(com, (198.12, com[1]), (198.12, 342.9))
    gnd(198.12, 342.9, key="dccom")
    # No PWR_FLAG on ground: U5's COM pin is already a power output, and two
    # power outputs on one net is itself an ERC error.
    s.wire(von, (191.77, von[1]), (191.77, PY_BOT))

    # --- the isolation barrier, and the three parts that straddle it ------
    # The converter is isolated, so the analog ground can float and take its
    # potential from whatever the scope's ground clip decides.  That is the
    # whole point of paying for an isolated module: no mains-referenced loop
    # runs through the signal ground while you are looking at 100 mV of chaos.
    # It is not left completely adrift -- 1 M drains static, 2.2 nF gives the
    # converter's 100 kHz common-mode current a way home, and JP1 is there for
    # anyone who would rather have the two grounds hard-tied.
    BX_L, BX_R = 120.65, 158.75
    BY = 355.6
    gnd(BX_L, BY, key="isoU", up=True, net="GNDU")
    gnd(BX_R, BY, key="isoA", up=True)
    s.wire((BX_L, BY), (BX_L, BY + 12.7))
    s.wire((BX_R, BY), (BX_R, BY + 12.7))
    for (ref, val, yb, lib, fld, half) in (
            ("JP1", "GND TIE", BY + 2.54, "Jumper:SolderJumper_2_Open",
             None, 5.08),
            ("R21", "1M", BY + 7.62, "Device:R_US", "1M", 3.81),
            ("C25", "2.2nF", BY + 12.7, "Device:C", "2.2nF", 3.81)):
        s.place(lib, ref, val, 139.7, yb, rot=0 if ref == "JP1" else 90,
                footprint=(fp("JUMPER") if ref == "JP1" else
                           rfp() if ref == "R21" else
                           parts.PARTS["C_0805"]["footprint"]),
                fields=passive_fields(fld) if fld else {},
                in_bom=(ref != "JP1"),
                ref_off=(0, -4.4), val_off=(0, 3.4))
        s.wire((BX_L, yb), (139.7 - half, yb))
        s.wire((139.7 + half, yb), (BX_R, yb))
    s.text("ISOLATION BARRIER", BX_L, BY - 4.0, size=2.0)
    for i, line in enumerate((
            "JP1 open: the analog ground floats, and a scope's",
            "ground clip is what sets it -- so no mains-referenced",
            "loop runs through the signal ground.  1 M drains",
            "static and 2.2 nF takes the converter's 100 kHz",
            "common-mode current home.  Bridge JP1 to give the",
            "isolation up and tie the two grounds together.")):
        s.text(line, 165.1, BY + 1.8 + i * 2.7, size=1.4)

    # +/-15 V bulk, then the two regulators.  Both bulk capacitors hang on
    # the inside of their rail, which keeps the strip below the negative rail
    # clear for the isolation barrier.
    for (ref, cx, ylev, sgn) in (("C12", 205.74, PY_TOP, +1),
                                 ("C13", 217.17, PY_BOT, -1)):
        s.place("Device:C", ref, "10uF", cx, ylev + 11.43 * sgn,
                footprint=parts.PARTS["C_0805"]["footprint"],
                fields=passive_fields("10uF"),
                ref_off=(2.54, -2.2), val_off=(2.54, 1.1),
                ref_justify="left", val_justify="left")
        s.wire((cx, ylev), (cx, ylev + 7.62 * sgn))
        s.wire((cx, ylev + 15.24 * sgn), (cx, ylev + 20.32 * sgn))
        gnd(cx, ylev + 20.32 * sgn, key=f"blk{ref}", up=(sgn < 0))
        s.junction(cx, ylev)
    s.wire((186.69, PY_TOP), (228.6, PY_TOP))
    s.wire((191.77, PY_BOT), (228.6, PY_BOT))
    rail("+15V", 215.9, PY_TOP - 3.81, to=PY_TOP)
    s.junction(215.9, PY_TOP)
    rail("-15V", 215.9, PY_BOT + 3.81, rot=180, to=PY_BOT)
    s.junction(215.9, PY_BOT)

    s.place("Regulator_Linear:L78L12_SOT89", "U6", "78L12", 236.22, PY_TOP,
            footprint=fp("REG_POS"), fields=part_fields("REG_POS"),
            ref_off=(0, -9.5), val_off=(0, -6.3))
    s.place("Regulator_Linear:L79L12_SOT89", "U7", "79L12", 236.22, PY_BOT,
            footprint=fp("REG_NEG"), fields=part_fields("REG_NEG"),
            ref_off=(0, 9.5), val_off=(0, 6.3))
    for (ureg, ipin, opin, gpin_, sign, ylev) in (
            ("U6", "3", "1", "2", +1, PY_TOP), ("U7", "2", "3", "1", -1, PY_BOT)):
        ip, op, gp = (s.pin(ureg, 1, ipin), s.pin(ureg, 1, opin),
                      s.pin(ureg, 1, gpin_))
        s.wire((228.6, ylev), ip)
        s.wire(gp, (gp[0], gp[1] + 5.08 * sign))
        gnd(gp[0], gp[1] + 5.08 * sign, key=f"reg{ureg}", up=(sign < 0))
        s.wire(op, (262.89, ylev))
        rail("+12V" if sign > 0 else "-12V", 262.89,
             ylev - 3.81 * sign, rot=0 if sign > 0 else 180, to=ylev)
        s.junction(262.89, ylev)
        cref = "C14" if sign > 0 else "C15"
        cx = 251.46
        s.place("Device:C", cref, "10uF", cx, ylev + 11.43 * sign,
                footprint=parts.PARTS["C_0805"]["footprint"],
                fields=passive_fields("10uF"),
                ref_off=(2.54, -2.2), val_off=(2.54, 1.1),
                ref_justify="left", val_justify="left")
        s.wire((cx, ylev), (cx, ylev + 7.62 * sign))
        s.wire((cx, ylev + 15.24 * sign), (cx, ylev + 20.32 * sign))
        gnd(cx, ylev + 20.32 * sign, key=f"out{cref}", up=(sign < 0))
        s.junction(cx, ylev)

    # ================================ rail lamps and probe points =========
    # One lamp per rail, not one lamp for all of them: the old single green
    # LED across +12 V said nothing about -12 V or about the USB input, so it
    # could sit there looking healthy with half the board dead.
    s.text("RAIL LAMPS", 20.32, 381.0, size=2.4)
    s.text("one per rail, three colours,", 20.32, 385.0, size=1.5)
    s.text("so a dark one names itself", 20.32, 388.0, size=1.5)
    for (ref_r, ref_d, rail_name, rval, colour, key, lx) in (
            ("R13", "D1", "+5V", "2.2k", "yellow", "LED_Y", 78.74),
            ("R14", "D2", "+12V", "4.7k", "green", "LED_G", 96.52),
            ("R15", "D3", "-12V", "10k", "white", "LED_W", 114.3)):
        led_fields = part_fields(key)
        neg = rail_name.startswith("-")
        # positive rails: rail -> R -> lamp -> ground.  The negative one runs
        # the other way, ground -> lamp -> R -> rail, so the lamp still points
        # the way the current flows.
        if neg:
            gnd(lx, 386.08, key=f"lamp{ref_d}", up=True)
            s.place("Device:LED", ref_d, colour, lx, 391.16, rot=90,
                    footprint=parts.PARTS[key]["footprint"], fields=led_fields,
                    ref_off=(5.6, -1.9), val_off=(5.6, 1.9))
            s.place("Device:R_US", ref_r, rval, lx, 401.32, footprint=rfp(),
                    fields=passive_fields(rval),
                    ref_off=(-5.6, -1.9), val_off=(-5.6, 1.9))
            rail(rail_name, lx, 405.13, rot=180)
        else:
            rail(rail_name, lx, 386.08)
            s.place("Device:R_US", ref_r, rval, lx, 391.16, footprint=rfp(),
                    fields=passive_fields(rval),
                    ref_off=(-5.6, -1.9), val_off=(-5.6, 1.9))
            s.place("Device:LED", ref_d, colour, lx, 401.32, rot=90,
                    footprint=parts.PARTS[key]["footprint"], fields=led_fields,
                    ref_off=(5.6, -1.9), val_off=(5.6, 1.9))
            gnd(lx, 405.13, key=f"lamp{ref_d}",
                net="GNDU" if rail_name == "+5V" else "GND")
        s.wire((lx, 386.08), (lx, 387.35))
        s.wire((lx, 394.97), (lx, 397.51))

    # --- probe points for every DC rail ----------------------------------
    s.text("PROBE POINTS", 135.89, 381.0, size=2.4)
    s.text("a plated hole for a probe tip, one per rail, plus three wire",
           135.89, 385.0, size=1.5)
    s.text("loops a scope's ground clip can bite on", 135.89, 388.0, size=1.5)
    TPY, TPTOP = 400.05, 393.7
    for i, name in enumerate(("+5V", "+15V", "-15V", "+12V", "-12V")):
        tx = 138.43 + i * 15.24
        rail(name, tx, TPTOP, to=TPY)
        testpoint(tx, TPY, name, dx=1.9, dy=4.0)
    for i, (name, net) in enumerate((("GND", "GND"), ("GNDU", "GNDU"))):
        tx = 138.43 + (5 + i) * 15.24
        gnd(tx, TPTOP, up=True, net=net)
        s.text(name, tx + 1.9, TPTOP - 1.6, size=1.27)
        s.wire((tx, TPTOP), (tx, TPY))
        testpoint(tx, TPY, name, dx=1.9, dy=4.0)
    for i in range(3):
        tx = 259.08 + i * 15.24
        gnd(tx, TPTOP, up=True)
        s.wire((tx, TPTOP), (tx, TPY))
        testpoint(tx, TPY, "SCOPE GND", dx=1.9, dy=4.0, loop=True)
    s.text("scope ground clips", 259.08, 388.0, size=1.5)

    s.text("POWER:  USB-C 5 V in, +/-12 V out", 20.32, 303.0, size=2.6)
    s.text("about 25 mA per rail; the 2 W module is rated +/-66 mA",
           20.32, 307.5, size=1.6)
    s.polyline([(18.0, 296.0), (270.0, 296.0)], width=0.3, key="powrule")

    # ============================================== supply pins and caps ===
    s.text("SUPPLY PINS AND BYPASSING", 285.75, 26.0, size=2.6)
    s.text("one 0.1 uF at every supply pin, right at the package",
           285.75, 30.5, size=1.6)
    s.polyline([(283.0, 19.0), (283.0, 178.0), (411.48, 178.0), (411.48, 19.0),
                (283.0, 19.0)], width=0.2, style="dash", key="bypbox")
    byp = [("U1", 3, "LF412", "U1  x and -y integrators"),
           ("U2", 3, "LF412", "U2  z integrator + lamp buffer"),
           ("U3", 2, "MPY634", "U3  x z multiplier"),
           ("U4", 2, "MPY634", "U4  x y multiplier")]
    for i, (uref, uunit, lib, caption) in enumerate(byp):
        bx = 295.91 + i * 30.48
        by = 88.9
        s.place(f"lorenz:{lib}", uref, lib, bx, by, unit=uunit,
                footprint=fp(lib), fields=part_fields(lib),
                ref_off=(-3.81, 0.0), val_off=(0, 0), hide_value=True,
                ref_justify="right")
        vp, vm = s.pin(uref, uunit, "8" if lib == "LF412" else "16"), None
        vm = s.pin(uref, uunit, "4" if lib == "LF412" else "10")
        s.wire(vp, (bx, 60.96))
        rail("+12V", bx, 60.96)
        s.wire(vm, (bx, 116.84))
        rail("-12V", bx, 116.84, rot=180)
        for (cref, cy, tag) in ((f"C{16+2*i}", 68.58, "+"),
                                (f"C{17+2*i}", 109.22, "-")):
            cx = bx + 13.97
            s.place("Device:C", cref, "100nF", cx, cy,
                    footprint=parts.PARTS["C_0805"]["footprint"],
                    fields=passive_fields("100nF"),
                    ref_off=(2.29, -2.2), val_off=(2.29, 1.1),
                    ref_justify="left", val_justify="left")
            if tag == "+":
                s.wire((cx, cy - 3.81), (cx, 60.96), (bx, 60.96))
                s.wire((cx, cy + 3.81), (cx, cy + 8.89))
                gnd(cx, cy + 8.89, key=f"byp{cref}")
            else:
                s.wire((cx, cy + 3.81), (cx, 116.84), (bx, 116.84))
                s.wire((cx, cy - 3.81), (cx, cy - 8.89))
                gnd(cx, cy - 8.89, key=f"byp{cref}", up=True)
            s.junction(bx, 60.96 if tag == "+" else 116.84)
        s.text(caption, bx - 4.0, 133.35 + (i % 2) * 4.5, size=1.4)


    # ================================== the owl's face, and how it works ===
    pts = owl_xz(width=118.0, height=92.0, cx=487.68, cy=95.0)
    s.polyline(pts, width=0.2, key="owl")
    s.polyline([(425.45, 145.0), (425.45, 38.0)], width=0.4, key="owlz")
    s.polyline([(422.95, 43.0), (425.45, 38.0), (427.95, 43.0)], width=0.4, key="owlza")
    s.polyline([(425.45, 145.0), (556.26, 145.0)], width=0.4, key="owlx")
    s.polyline([(551.26, 142.5), (556.26, 145.0), (551.26, 147.5)], width=0.4,
               key="owlxa")
    s.text("z", 419.1, 40.0, size=3.2)
    s.text("x", 551.0, 152.0, size=3.2)
    s.text("Hook x and z to a scope in X-Y and this is what you get: the attractor's",
           425.45, 23.0, size=1.9)
    s.text("characteristic owl's face.  The trace below is the real solution of these",
           425.45, 26.8, size=1.9)
    s.text("equations, integrated at s = 10, r = 28, b = 8/3.", 425.45, 30.6, size=1.9)

    # ---------------------------------------------------- the notes box ---
    BX0, BY0, BX1, BY1 = 283.0, 186.0, 578.0, 356.0
    s.polyline([(BX0, BY0), (BX1, BY0), (BX1, BY1), (BX0, BY1), (BX0, BY0)],
               width=0.3, style="dash", key="notesbox")
    L = BX0 + 6.0
    y = BY0 + 10.0
    s.text("HOW THIS CIRCUIT SOLVES THE EQUATIONS", L, y, size=3.2)
    y += 9.0
    for line in ("dx/dt = s (y - x)          s = 10",
                 "dy/dt = r x - y - x z      r = 28",
                 "dz/dt = x y - b z          b = 8/3"):
        s.text(line, L + 4.0, y, size=2.6)
        y += 6.5
    y += 3.0
    for line in (
        "Each op-amp is an integrator with the terms of one derivative summed at its",
        "inverting input, so the weight of every term is simply  1 MEG / R :",
    ):
        s.text(line, L, y, size=1.9)
        y += 4.2
    y += 1.5
    for line in (
        "R2 = R1 = 100k    ->  1M/100k  = 10.00   = s          (and the -x damping)",
        "R3 = 35.7k        ->  1M/35.7k = 28.01   = r",
        "R5 = 1M           ->  1M/1M    =  1.00   = the -y term",
        "R7 = 374k         ->  1M/374k  =  2.674  = b   (8/3 = 2.667, 0.3 % high)",
        "R4 = R6 = 10k     ->  1M/10k   = 100     cancels the multipliers' /100",
    ):
        s.text(line, L + 4.0, y, size=1.9)
        y += 4.2
    y += 3.0
    for line in (
        "Voltages carry the dimensionless variables at 0.1 V per unit, so x swings",
        "+/-2 V, y +/-2.7 V and z runs 0 to 4.8 V.  An MPY634 forms A*B/10, so the",
        "product of two 0.1 V/unit signals comes out 100x too small -- which is exactly",
        "what the 10k weighting resistors R4 and R6 put back.  The minus signs on both",
        "products are free: U3 and U4 simply have their differential inputs swapped.",
        "",
        "The time scale is tau = 1 MEG x C, and C is switchable:",
    ):
        s.text(line, L, y, size=1.9)
        y += 4.2
    y += 2.0
    # A drawn table rather than a run of sentences: the two switch banks are
    # what you actually touch, so they get a column each and a rule between
    # them, and the speed you are asking for names the row.
    # One column per switch pole, so the "off" you read is directly under the
    # pole you have to push -- and the two banks are ruled apart.
    C0 = L + 4.0
    POLE = [L + 38.0 + 8.0 * i for i in range(3)] + \
           [L + 70.0 + 8.0 * i for i in range(3)]
    RULE_A, RULE_B = L + 62.0, L + 96.0
    C3, C4 = L + 102.0, L + 128.0
    s.text("SW1 pole", (POLE[0] + POLE[5]) / 2.0 - 7.0, y - 3.6, size=1.8)
    s.text("speed", C0, y, size=1.8)
    for i, px in enumerate(POLE):
        s.text(str(i + 1), px, y, size=1.8, justify=None)
    s.text("C", C3, y, size=1.8)
    s.text("tau = 1M x C", C4, y, size=1.8)
    s.polyline([(C0 - 1.0, y + 1.6), (C4 + 26.0, y + 1.6)], width=0.25,
               key="swtab/head")
    for i, rx in enumerate((RULE_A, RULE_B)):
        s.polyline([(rx, y - 1.4), (rx, y + 16.5)], width=0.25,
                   key=f"swtab/rule{i}")
    y += 5.0
    for (speed, a, b, cval, tau) in (
            ("fast!", "off", "off", "2.2 nF", "2.2 ms"),
            ("nice!", "ON", "off", "102 nF", "102 ms"),
            ("slow!", "off", "ON", "472 nF", "472 ms")):
        s.text(speed, C0, y, size=1.9)
        for i, px in enumerate(POLE):
            s.text(a if i < 3 else b, px, y, size=1.9, justify=None)
        s.text(cval, C3, y, size=1.9)
        s.text(tau, C4, y, size=1.9)
        y += 5.0
    y += 1.0
    s.text("Never both banks ON: that is 572 nF, which works but is not one of",
           L, y, size=1.9)
    y += 4.2
    s.text("the three settings the board is labelled for.", L, y, size=1.9)
    y += 6.0
    s.text("Paul's original ran on a bench +/-15 V supply and used 2000 pF, 0.1 uF and",
           L, y, size=1.9)
    y += 4.2
    s.text("0.47 uF.  Here the three values are built up in parallel because no supplier",
           L, y, size=1.9)
    y += 4.2
    s.text("stocks a 3-pole 3-position switch; 2.2 nF is always fitted.",
           L, y, size=1.9)

    # -------------------------------------------- mechanical --------------
    # Four M3 holes.  Three BNCs on one edge means cables lever on the board;
    # it wants feet or standoffs, not to sit loose on the bench.
    s.text("MOUNTING", 292.1, 368.3, size=2.4)
    s.text("Four M3 holes, one per board corner.  No electrical function,",
           292.1, 373.4, size=1.6)
    s.text("but with three BNCs along one edge the cables lever on the",
           292.1, 377.2, size=1.6)
    s.text("board, so it wants standoffs rather than a bare bench.",
           292.1, 381.0, size=1.6)
    for i in range(4):
        s.place("Mechanical:MountingHole", f"MH{i + 1}", "MountingHole",
                297.2 + i * 17.78, 394.0,
                footprint="MountingHole:MountingHole_3.2mm_M3",
                in_bom=False, ref_off=(0, -5.08), val_off=(0, 5.08),
                hide_value=True)

    # ------------------------------- Paul's note, where Paul puts it -------
    s.text("C  =  0.47 uF   (slow!)", 20.32, 26.0, size=3.4)
    s.text("=  0.1 uF    (nice!)", 32.0, 33.5, size=3.4)
    s.text("=  2000 pF   (fast!)", 32.0, 41.0, size=3.4)
    s.text("...built here as 2.2 nF always fitted, plus 100 nF and 470 nF", 20.32, 48.0,
           size=1.7)
    s.text("switched in by SW1.  See the notes at the right of the sheet.", 20.32, 51.5,
           size=1.7)

    return s, rows, feeds


if __name__ == "__main__":
    s, rows, feeds = build()
    added = s.add_missing_junctions()
    if added:
        print(f"  auto-placed {added} junction(s) where wires meet end-to-middle")
    bad = s.check_grid()
    if bad:
        print(f"  !! {len(bad)} off-grid endpoint(s):")
        for what, pt in bad[:12]:
            print(f"       {what} at {pt}")
        raise SystemExit("off-grid endpoints would confuse KiCad's connectivity")
    s.write(OUT)
    print(f"  wrote {os.path.relpath(OUT)}")
