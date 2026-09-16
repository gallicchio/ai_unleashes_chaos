"""Component placement for the Lorenz board.

The board reads the way the schematic does: signal flows left to right in
three horizontal bands, one per integrator.  The multipliers sit at the far
left, in the third of the board that used to be empty, and everything else is
spread out behind them, so each part has room for its own legend instead of
having the legend pushed somewhere else.

Each band ends in the same straight line: op-amp output, probe pad, the 100
ohm series resistor lying horizontally, BNC.  Anyone can see what the probe
pad is for, because it is on the wire between the op-amp and the jack.

The bottom strip is the power chain.  Its left-hand corner is a separate
copper island: the DC/DC converter is isolated, so the USB side has its own
ground plane, meeting the analog ground only at R18, C25 and JP1.

(x, y) are the footprint centres in millimetres from the top-left board corner;
rot is degrees counter-clockwise.
"""

BOARD_W, BOARD_H = 100.0, 100.0
EDGE = 0.0                      # board outline runs (0,0) .. (BOARD_W, BOARD_H)

ROW_Y = (19.0, 44.0, 69.0)      # x, -y and z integrator bands

# --- the isolation split -------------------------------------------------
# GNDU fills the bottom-left corner up to these edges; GND fills everything
# else but stops 1 mm short, so the two planes never come within 1 mm of each
# other.  Both numbers are used by the router, by the zone outlines and by the
# check that no GNDU pad lands outside the island.
ISLAND = (0.0, 77.0, 42.5, BOARD_H)       # x0, y0, x1, y1 of the GNDU plane
ISLAND_GAP = 1.0                          # clearance to the GND plane

PLACE = {
    # ---- the left edge is the input edge ---------------------------------
    # SYNC IN X sits in line with the x output on the opposite edge, because
    # that is what you plug into it, and its chain runs straight down the
    # edge: jack, weight knob, then across into the summing column beside the
    # x term it perturbs.  The r knob is directly below the weight knob, so
    # the two controls are on the same edge and turn the same way.
    "J5":  (7.0, 19.0, 180),    # SYNC IN X, barrel off the left edge
    "RV2": (9.0, 33.54, 0),     # sync weight; body centres on (9, 31)
    "R20": (18.0, 39.0, 90),    # 1M holding the wiper node down
    "RV1": (9.0, 48.54, 0),     # r knob; body centres on (9, 46)

    # ---- multipliers, clear of the input edge ----------------------------
    "U3": (21.0, 26.5, 0),      # x*z  -> -y integrator
    "U4": (21.0, 61.5, 0),      # x*y  ->  z integrator
    "C20": (32.0, 22.0, 90), "C21": (32.0, 31.0, 90),     # U3 bypass
    "C22": (32.0, 57.0, 90), "C23": (32.0, 66.0, 90),     # U4 bypass
    # The two multiplier products are probed where they arrive at their
    # summing resistors, which is both the clearest place on the front and
    # clear of the equations on the back.
    "TP4": (30.0, 44.0, 0),     # -x z / 100, on its way into R4
    "TP5": (30.0, 63.0, 0),     # -x y / 100, on its way into R6

    # ---- summing resistors, a column per band ---------------------------
    # Row 2 reads down the column in the same order as the schematic, and the
    # sync resistor is the next one down from R3: the two of them are the x
    # term and the perturbation on it, and they meet before anything else.
    "R1": (35.0, 14.0, 0),     # -y -> x integrator
    "R2": (35.0, 20.0, 0),     #  x -> x integrator
    "R5": (35.0, 38.0, 0),     # -y -> -y integrator
    "R4": (35.0, 44.0, 0),     # xz -> -y integrator
    "R3": (35.0, 50.0, 0),     #  x -> -y integrator
    "R19": (35.0, 56.0, 0),    # SYNC IN X -> the same node as R3
    "R6": (35.0, 63.0, 0),     # xy -> z integrator
    "R7": (35.0, 69.0, 0),     #  z -> z integrator

    # ---- capacitor banks: fast / nice / slow, one row per integrator -----
    # The middle bank sits further from its row than the other two; that is
    # what leaves a clear band above the switch for the legend, which has to
    # line up with the six sliders and so cannot go anywhere else.
    # The 470 nF hangs on poles 1-3, at the left-hand end of the switch, and
    # the 100 nF on poles 4-6 at the right-hand end, so each capacitor sits
    # over the pole it belongs to and no two branches have to cross.
    "C1": (43.0, 16.0, 90), "C3": (49.0, 16.0, 90), "C2": (55.0, 16.0, 90),
    "C4": (43.0, 26.0, 90), "C6": (49.0, 26.0, 90), "C5": (55.0, 26.0, 90),
    "C7": (43.0, 66.0, 90), "C9": (49.0, 66.0, 90), "C8": (55.0, 66.0, 90),
    # The one control, turned so its six sliders run left to right with the
    # legend that explains them directly above.  It sits as high as the middle
    # capacitor bank allows, which is what leaves the bottom third of the board
    # open for the lamp reference, the credit line and the ground tie.
    "SW1": (56.0, 46.0, 90),

    # ---- op-amps: U1 carries x and -y, U2 carries z and the lamp buffer --
    "U1": (72.0, 19.0, 0), "C16": (65.0, 15.0, 90), "C17": (65.0, 23.0, 90),
    "U2": (72.0, 69.0, 0), "C18": (65.0, 65.0, 90), "C19": (65.0, 73.0, 90),

    # ---- output: op-amp, probe pad, series resistor, jack, in a line -----
    "TP1": (80.0, 19.0, 0), "R8":  (85.5, 19.0, 0), "J2": (93.0, 19.0, 0),
    "TP2": (80.0, 44.0, 0), "R9":  (85.5, 44.0, 0), "J3": (93.0, 44.0, 0),
    "TP3": (80.0, 69.0, 0), "R10": (85.5, 69.0, 0), "J4": (93.0, 69.0, 0),

    # ---- the chaos lamp, between two jacks, fed from the left ------------
    "R13": (70.0, 48.0, 0), "R14": (70.0, 55.0, 0), "R15": (70.0, 62.0, 0),
    "D1":  (83.0, 56.5, 0),
    "TP6": (88.0, 60.0, 0),     # the +3.2 V anode rail, beside the lamp
    # the +3.2 V reference, in the band the switch used to occupy: R17 down
    # from +12 V, then R16 and C24 in parallel to ground
    "R17": (50.0, 59.0, 0), "R16": (55.0, 59.0, 90), "C24": (59.0, 59.0, 90),

    # ---- USB side of the barrier, all inside the GNDU island ------------
    # 13.05 rather than 13.0: that puts the 0.5 mm-pitch CC pads on the
    # router's 0.2 mm grid, which is the only way a 0.3 mm track escapes
    # between them with 0.2 mm clearance either side.
    # The mating face of this receptacle is 3.65 mm in front of its origin
    # and its printed outline another 0.25 mm in front of that, so 95.85
    # leaves the connector half a millimetre inside the board edge with its
    # silkscreen exactly on the 0.15 mm silk-to-edge rule.  That half
    # millimetre is what a cable with a big moulded body needs: at the 6 mm
    # setback this started at, the moulding hits the laminate before the plug
    # is home.
    "J1":  (13.05, 95.85, 0),
    # The CC pull-downs sit directly above their own pads, so each escape from
    # the 0.5 mm-pitch row is a 2.5 mm straight run and neither competes with
    # VBUS for the corridor above the connector.
    "R11": (11.8, 88.8, 90), "R12": (14.8, 88.8, 90),
    "F1":  (24.0, 86.0, 0),
    "C10": (30.0, 86.0, 90), "C11": (34.0, 86.0, 90),
    "TP7": (24.0, 79.5, 0), "TP13": (32.0, 79.5, 0),      # +5 V, GNDU

    # ---- the converter straddles the split ------------------------------
    # Pin 1 is the footprint origin and the pins run +x on a 2.54 mm pitch,
    # with the module's own barrier in the 5.08 mm gap between pins 2 and 4.
    # Putting that gap over the board's gap is the whole trick.
    "U5":  (37.92, 94.0, 0),

    # ---- the three parts that bridge the two grounds --------------------
    "JP1": (43.0, 79.0, 0), "R18": (43.0, 82.5, 0), "C25": (43.0, 86.0, 0),

    # ---- analog side of the power strip ---------------------------------
    # +15 V lane along y = 90, -15 V along y = 96: bulk, a 100 nF at the
    # regulator's own input pin, the regulator, a 100 nF at its output pin,
    # then the +/-12 V bulk.
    # U5's body reaches x = 55.6, so the analog half of the strip starts
    # after it, in two lanes with room for a legend between them.
    "C12": (59.0, 86.0, 90), "C26": (64.5, 86.0, 90),
    "U6":  (70.0, 86.0, 0),
    "C27": (76.0, 86.0, 90), "C14": (81.0, 86.0, 90),
    "C13": (59.0, 95.0, 90), "C28": (64.0, 95.0, 90),
    "U7":  (70.0, 95.0, 0),
    "C29": (76.5, 95.0, 90), "C15": (82.0, 95.0, 90),

    # ---- probe pads for the rails, in a row you can read ----------------
    "TP8":  (50.0, 79.5, 0),    # +15 V
    "TP9":  (57.0, 79.5, 0),    # -15 V
    "TP10": (64.0, 79.5, 0),    # +12 V
    "TP11": (71.0, 79.5, 0),    # -12 V
    "TP12": (78.0, 79.5, 0),    # GND

    # ---- wire loops for a scope's ground clip ---------------------------
    # One beside the jacks, one beside the probe row, one in the middle by the
    # capacitor banks, so a clip is never far from what you are probing.
    "TP14": (92.0, 79.5, 0),
    "TP15": (91.0, 90.5, 0),
    "TP16": (56.0, 72.0, 0),

    # ---- M3 mounting holes, one per corner ------------------------------
    "MH1": (4.0, 4.0, 0), "MH2": (96.0, 4.0, 0),
    "MH3": (4.0, 96.0, 0), "MH4": (96.0, 96.0, 0),
}

# Reference-designator text nudges, so silkscreen never lands on a pad.
REF_OFFSET = {}


def in_island(x, y, margin=0.0):
    x0, y0, x1, y1 = ISLAND
    return (x0 - margin <= x <= x1 + margin) and (y0 - margin <= y <= y1 + margin)


def island_outline(margin):
    """The GNDU plane's outline, inset by `margin` from the board edge."""
    x0, y0, x1, y1 = ISLAND
    return [(max(x0, margin), max(y0, margin)),
            (x1, max(y0, margin)), (x1, BOARD_H - margin),
            (max(x0, margin), BOARD_H - margin)]


def ground_outline(margin):
    """Everything else: the board, with the island (plus the gap) notched out."""
    x0, y0, x1, y1 = ISLAND
    cx, cy = x1 + ISLAND_GAP, y0 - ISLAND_GAP
    return [(margin, margin), (BOARD_W - margin, margin),
            (BOARD_W - margin, BOARD_H - margin), (cx, BOARD_H - margin),
            (cx, cy), (margin, cy)]
