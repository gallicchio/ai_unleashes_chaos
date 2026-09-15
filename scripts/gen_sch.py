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

    def gnd(x, y, key="", up=False):
        """Drop a ground symbol; `up` flips it for a wire arriving from below."""
        s.place("power:GND", pwr_ref(), "GND", x, y, rot=180 if up else 0,
                in_bom=False, on_board=False, hide_ref=True, hide_value=True)

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
            label="x", note="dx/dt = 10 (y - x)"),
        dict(  # dy/dt = 28x - y - xz
            opa=("U1", 2), out="-y", y=ROW_Y[1],
            res=[("R4", "10k", -12.7, "xz"), ("R3", "35.7k", 0.0, "x"),
                 ("R5", "1M", +12.7, "-y")],
            caps=("C4", "C5", "C6"), poles=(2, 5), outres="R9", bnc="J3",
            label="-y", note="dy/dt = 28 x - y - x z"),
        dict(  # dz/dt = xy - (8/3) z
            opa=("U2", 1), out="z", y=ROW_Y[2],
            res=[("R6", "10k", -6.35, "xy"), ("R7", "374k", +6.35, "z")],
            caps=("C7", "C8", "C9"), poles=(3, 6), outres="R10", bnc="J4",
            label="z", note="dz/dt = x y - 2.674 z"),
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

        # drop down the jog column into the summing resistor
        s.label("xz" if ref == "U3" else "xy", JOG_X, pw[1] + 6.35, size=1.5)
        dx, dy = m["dest"]
        s.wire((JOG_X, pw[1]), (JOG_X, dy), (dx, dy))
        s.text(m["legend"], JOG_X + 1.9, pw[1] - 2.2, size=1.9)

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
    gnd(gpin[0], gpin[1] + 5.08, key="usb")
    sh = s.pin("J1", 1, "SH")
    s.wire(sh, (sh[0], sh[1] + 5.08))
    gnd(sh[0], sh[1] + 5.08, key="shell")
    s.text("shell grounded here only", sh[0] - 1.27, sh[1] + 10.16, size=1.4,
           justify="right")

    # CC pull-downs: without these a USB-C charger never turns 5 V on.
    for (ref, pin_name, cx) in (("R11", "A5", 74.93), ("R12", "B5", 87.63)):
        pt = s.pin("J1", 1, pin_name)
        s.place("Device:R_US", ref, "5.1k", cx, 340.36, footprint=rfp(),
                fields=passive_fields("5.1k"),
                ref_off=(2.54, -2.2), val_off=(2.54, 1.1),
                ref_justify="left", val_justify="left")
        s.wire(pt, (cx, pt[1]), (cx, 336.55))
        s.wire((cx, 344.17), (cx, 349.25))
        gnd(cx, 349.25, key=f"cc{ref}")
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

    for (ref, val, cx, key) in (("C10", "10uF", 123.19, "10uF"),
                                ("C11", "100nF", 135.89, "100nF")):
        s.place("Device:C", ref, val, cx, vbus[1] + 12.7,
                footprint=parts.PARTS["C_0805"]["footprint"],
                fields=passive_fields(key),
                ref_off=(2.54, -2.2), val_off=(2.54, 1.1),
                ref_justify="left", val_justify="left")
        s.wire((cx, vbus[1]), (cx, vbus[1] + 8.89))
        s.wire((cx, vbus[1] + 16.51), (cx, vbus[1] + 21.59))
        gnd(cx, vbus[1] + 21.59, key=f"bulk{ref}")
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
    gnd(142.24, 342.9, key="dcin")
    s.wire(vop, (186.69, vop[1]), (186.69, PY_TOP))
    s.wire(com, (198.12, com[1]), (198.12, 342.9))
    gnd(198.12, 342.9, key="dccom")
    # No PWR_FLAG on ground: U5's COM pin is already a power output, and two
    # power outputs on one net is itself an ERC error.
    s.text("output common tied to", 198.12 + 2.54, 348.0, size=1.4)
    s.text("input ground -- the", 198.12 + 2.54, 350.7, size=1.4)
    s.text("isolation is not used", 198.12 + 2.54, 353.4, size=1.4)
    s.wire(von, (191.77, von[1]), (191.77, PY_BOT))

    # +/-15 V bulk, then the two regulators
    for (ref, cx, ylev, tag) in (("C12", 205.74, PY_TOP, "+15V"),
                                 ("C13", 205.74, PY_BOT, "-15V")):
        dy = 11.43 if tag == "+15V" else -11.43
        s.place("Device:C", ref, "10uF", cx, ylev + dy,
                footprint=parts.PARTS["C_0805"]["footprint"],
                fields=passive_fields("10uF"),
                ref_off=(2.54, -2.2), val_off=(2.54, 1.1),
                ref_justify="left", val_justify="left")
        s.wire((cx, ylev), (cx, ylev + dy - 3.81 * (1 if dy > 0 else -1)))
        s.wire((cx, ylev + dy + 3.81 * (1 if dy > 0 else -1)),
               (cx, ylev + dy + 7.62 * (1 if dy > 0 else -1)))
        gnd(cx, ylev + dy + 7.62 * (1 if dy > 0 else -1), key=f"blk{ref}",
            up=(dy < 0))
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
        s.wire((cx, ylev + 15.24 * sign), (cx, ylev + 19.05 * sign))
        gnd(cx, ylev + 19.05 * sign, key=f"out{cref}", up=(sign < 0))
        s.junction(cx, ylev)

    # rails-OK lamp, hung off +12 V so it proves the whole chain at a glance
    LEDX = 276.86
    s.wire((262.89, PY_TOP), (LEDX, PY_TOP))
    s.junction(262.89, PY_TOP)
    s.place("Device:R_US", "R13", "4.7k", LEDX, 321.31, footprint=rfp(),
            fields=passive_fields("4.7k"),
            ref_off=(-2.54, -2.2), val_off=(-2.54, 1.1),
            ref_justify="right", val_justify="right")
    s.place("Device:LED", "D1", "green", LEDX, 334.01, rot=90,
            footprint=fp("LED"), fields=part_fields("LED"),
            ref_off=(-3.81, -2.2), val_off=(-3.81, 1.1),
            ref_justify="right", val_justify="right")
    s.wire((LEDX, PY_TOP), (LEDX, 317.5))
    s.wire((LEDX, 325.12), (LEDX, 330.2))
    s.wire((LEDX, 337.82), (LEDX, 342.9))
    gnd(LEDX, 342.9, key="led")
    s.text("rails OK", LEDX - 2.54, 347.0, size=1.6, justify="right")

    s.text("POWER:  USB-C 5 V in, +/-12 V out", 20.32, 303.0, size=2.6)
    s.text("about 20 mA per rail; the 2 W module is rated +/-66 mA",
           20.32, 307.5, size=1.6)
    s.polyline([(18.0, 296.0), (270.0, 296.0)], width=0.3, key="powrule")

    # ============================================== supply pins and caps ===
    s.text("SUPPLY PINS AND BYPASSING", 285.75, 26.0, size=2.6)
    s.text("one 0.1 uF at every supply pin, right at the package",
           285.75, 30.5, size=1.6)
    s.polyline([(283.0, 19.0), (283.0, 178.0), (420.0, 178.0), (420.0, 19.0),
                (283.0, 19.0)], width=0.2, style="dash", key="bypbox")
    byp = [("U1", 3, "LF412", "U1  x and -y integrators"),
           ("U2", 3, "LF412", "U2  z integrator (B half spare)"),
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

    # U2B is spare -- park it as a grounded follower, and say so
    s.place("lorenz:LF412", "U2", "LF412", 355.6, 152.4, unit=2,
            footprint=fp("LF412"), fields=part_fields("LF412"),
            ref_off=(1.27, 7.62), val_off=(1.27, 10.8), hide_value=True,
            ref_justify="left")
    n_in, p_in = s.pin("U2", 2, "6"), s.pin("U2", 2, "5")
    n_out = s.pin("U2", 2, "7")
    s.wire(p_in, (p_in[0] - 5.08, p_in[1]), (p_in[0] - 5.08, p_in[1] + 5.08))
    gnd(p_in[0] - 5.08, p_in[1] + 5.08, key="u2bp")
    s.wire(n_in, (n_in[0] - 2.54, n_in[1]), (n_in[0] - 2.54, n_in[1] - 8.89),
           (n_out[0] + 2.54, n_out[1] - 8.89), (n_out[0] + 2.54, n_out[1]), n_out)
    s.text("U2B is spare -- Paul only needed one and a half", 330.2, 166.0, size=1.4)
    s.text("LF412s too.  An unused op-amp is parked as a", 330.2, 168.7, size=1.4)
    s.text("unity-gain follower with its input grounded.", 330.2, 171.4, size=1.4)

    # ================================== the owl's face, and how it works ===
    pts = owl_xz(width=118.0, height=92.0, cx=487.68, cy=95.0)
    s.polyline(pts, width=0.2, key="owl")
    s.polyline([(419.1, 145.0), (419.1, 38.0)], width=0.4, key="owlz")
    s.polyline([(416.6, 43.0), (419.1, 38.0), (421.6, 43.0)], width=0.4, key="owlza")
    s.polyline([(419.1, 145.0), (556.26, 145.0)], width=0.4, key="owlx")
    s.polyline([(551.26, 142.5), (556.26, 145.0), (551.26, 147.5)], width=0.4,
               key="owlxa")
    s.text("z", 412.75, 40.0, size=3.2)
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
    y += 1.0
    for line in (
        "SW1-1,2,3 off   SW1-4,5,6 off   C = 2.2 nF     fast!   ~3 ms per lobe",
        "SW1-1,2,3 ON    SW1-4,5,6 off   C = 102 nF     nice!   ~0.15 s per lobe",
        "SW1-1,2,3 off   SW1-4,5,6 ON    C = 472 nF     slow!   ~0.7 s per lobe",
    ):
        s.text(line, L + 4.0, y, size=1.9)
        y += 4.2
    y += 2.0
    s.text("Paul's original ran on a bench +/-15 V supply and used 2000 pF, 0.1 uF and",
           L, y, size=1.9)
    y += 4.2
    s.text("0.47 uF.  Here the three values are built up in parallel because no supplier",
           L, y, size=1.9)
    y += 4.2
    s.text("stocks a 3-pole 3-position switch; 2.2 nF is always fitted.",
           L, y, size=1.9)

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
