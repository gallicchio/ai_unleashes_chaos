"""Component placement for the Lorenz board.

Laid out the way the schematic reads: signal flows left to right in three
horizontal bands, one per integrator, with the two multipliers on the left
feeding the middle band and the lower band, the outputs leaving on BNCs at the
right edge, and the whole power chain kept in its own strip along the bottom.

The bottom-left corner of that strip is a separate copper island: the DC/DC
converter is isolated, so the USB side of the board has its own ground plane
which meets the analog ground only at R21, C25 and JP1.

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
# check that no track crosses the gap, so there is one place to change them.
ISLAND = (0.0, 77.0, 42.5, BOARD_H)       # x0, y0, x1, y1 of the GNDU plane
ISLAND_GAP = 1.0                          # clearance to the GND plane

PLACE = {
    # ---- multipliers, on the left, each between the bands it feeds -------
    "U3": (22.0, 31.5, 0),      # x*z  -> -y integrator
    "U4": (22.0, 56.5, 0),      # x*y  ->  z integrator
    "C20": (31.5, 24.0, 90), "C21": (31.5, 39.0, 90),     # U3 bypass
    "C22": (31.5, 49.0, 90), "C23": (31.5, 64.0, 90),     # U4 bypass
    "TP4": (45.5, 31.5, 0),     # -x z / 100, off U3's output
    "TP5": (48.0, 56.5, 0),     # -x y / 100, off U4's output

    # ---- summing resistors, a column per band ---------------------------
    "R1": (42.0, 15.0, 90),     # -y -> x integrator
    "R2": (42.0, 21.0, 90),     #  x -> x integrator
    "R3": (42.0, 38.0, 90),     #  x -> -y integrator
    "R4": (42.0, 44.0, 90),     # xz -> -y integrator
    "R5": (42.0, 50.0, 90),     # -y -> -y integrator
    "R6": (42.0, 63.0, 90),     # xy -> z integrator
    "R7": (42.0, 69.0, 90),     #  z -> z integrator

    # ---- capacitor banks: fast / nice / slow, one row per integrator -----
    "C1": (49.0, 15.0, 90), "C2": (54.0, 15.0, 90), "C3": (59.0, 15.0, 90),
    # The middle bank sits a little further from its row than the other two:
    # that is what leaves a clear band for the switch legend, which has to
    # line up with the six sliders and so cannot go anywhere else.
    "C4": (49.0, 34.0, 90), "C5": (54.0, 34.0, 90), "C6": (59.0, 34.0, 90),
    "C7": (49.0, 63.0, 90), "C8": (54.0, 63.0, 90), "C9": (59.0, 63.0, 90),
    # The one control, turned so its six sliders run left to right with the
    # legend that explains them directly underneath.
    "SW1": (66.0, 52.0, 90),

    # ---- op-amps: U1 carries x and -y, U2 carries z and the lamp buffer --
    "U1": (78.0, 29.0, 0), "C16": (78.0, 22.0, 90), "C17": (78.0, 36.0, 90),
    "U2": (78.0, 69.0, 0), "C18": (78.0, 62.0, 90), "C19": (78.0, 76.0, 90),

    # ---- the chaos lamp's cathode reference, beside its buffer ----------
    "R19": (70.0, 62.0, 90), "R20": (70.0, 66.0, 90), "C24": (70.0, 70.0, 90),
    "TP6": (74.0, 73.5, 0),     # the -1.5 V reference

    # ---- series output resistors, probe pads and the BNCs ---------------
    "R8":  (86.0, 19.0, 90), "J2": (93.0, 19.0, 0), "TP1": (86.0, 14.0, 0),
    "R9":  (86.0, 44.0, 90), "J3": (93.0, 44.0, 0), "TP2": (86.0, 39.0, 0),
    "R10": (86.0, 69.0, 90), "J4": (93.0, 69.0, 0), "TP3": (86.0, 64.0, 0),

    # ---- the chaos lamp itself, in the gap between two BNCs -------------
    "D4":  (93.5, 56.0, 0),
    "R16": (85.0, 52.0, 90), "R17": (85.0, 56.0, 90), "R18": (85.0, 60.0, 90),

    # ---- USB side of the barrier, all inside the GNDU island ------------
    # 13.05 rather than 13.0: that puts the 0.5 mm-pitch CC pads on the
    # router's 0.2 mm grid, which is the only way a 0.3 mm track escapes
    # between them with 0.2 mm clearance either side.
    "J1":  (13.05, 94.0, 0),
    # The CC pull-downs sit directly above their own pads, so each escape from
    # the 0.5 mm-pitch row is a 2.5 mm straight run and neither competes with
    # VBUS for the corridor above the connector.
    "R11": (11.8, 86.4, 90), "R12": (14.8, 86.4, 90),
    "F1":  (24.0, 86.0, 90),
    "C10": (30.0, 86.0, 90), "C11": (33.0, 86.0, 90),
    "R13": (22.0, 80.0, 0), "D1": (27.0, 80.0, 0),         # +5 V lamp
    "TP7": (32.0, 80.0, 0), "TP13": (37.0, 80.0, 0),       # +5 V, GNDU

    # ---- the converter straddles the split ------------------------------
    # Pin 1 is the footprint origin and the pins run +x on a 2.54 mm pitch,
    # with the module's own barrier in the 5.08 mm gap between pins 2 and 4.
    # Putting that gap over the board's gap is the whole trick.
    "U5":  (37.92, 93.0, 0),

    # ---- the three parts that bridge the two grounds --------------------
    "JP1": (43.0, 79.0, 0), "R21": (43.0, 82.0, 0), "C25": (43.0, 85.0, 0),

    # ---- analog side of the power strip ---------------------------------
    "C12": (59.0, 86.0, 90), "C13": (59.0, 93.0, 90),
    "U6":  (78.0, 90.0, 0), "U7": (88.0, 90.0, 0),
    "C14": (84.0, 85.0, 90), "C15": (94.0, 87.0, 90),
    "R14": (70.0, 96.5, 0), "D2": (75.0, 96.5, 0),         # +12 V lamp
    "R15": (81.0, 96.5, 0), "D3": (86.0, 96.5, 0),         # -12 V lamp

    # ---- probe pads for the rails, in a row you can read --------------
    "TP8":  (52.0, 80.0, 0),    # +15 V
    "TP9":  (57.0, 80.0, 0),    # -15 V
    "TP10": (62.0, 80.0, 0),    # +12 V
    "TP11": (67.0, 80.0, 0),    # -12 V
    "TP12": (72.0, 80.0, 0),    # GND

    # ---- wire loops for a scope's ground clip ---------------------------
    # One beside the outputs, one beside the probe pads, one in the middle of
    # the board, so a clip is never far from what you are probing.  They stay
    # out of the left-hand third because that is where the back carries the
    # equations, and a drilled hole punches a gap in the legend.
    "TP14": (93.0, 80.0, 0),
    "TP15": (81.0, 80.0, 0),
    "TP16": (48.0, 76.0, 0),

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
