"""Component placement for the Lorenz board.

Laid out the way the schematic reads: signal flows left to right in three
horizontal bands, one per integrator, with the two multipliers on the left
feeding the middle band and the lower band, the outputs leaving on BNCs at the
right edge, and the whole power chain kept in its own strip along the bottom.

(x, y) are the footprint centres in millimetres from the top-left board corner;
rot is degrees counter-clockwise.
"""

BOARD_W, BOARD_H = 100.0, 100.0
EDGE = 0.0                      # board outline runs (0,0) .. (BOARD_W, BOARD_H)

ROW_Y = (20.0, 46.0, 72.0)      # x, -y and z integrator bands
POWER_Y = 88.0

PLACE = {
    # ---- multipliers, on the left, each between the bands it feeds -------
    "U3": (22.0, 33.0, 0),      # x*z  -> -y integrator
    "U4": (22.0, 59.0, 0),      # x*y  ->  z integrator
    "C20": (31.5, 25.0, 90), "C21": (31.5, 41.0, 90),     # U3 bypass
    "C22": (31.5, 51.0, 90), "C23": (31.5, 67.0, 90),     # U4 bypass

    # ---- summing resistors, a column per band ---------------------------
    "R1": (42.0, 16.0, 90),     # -y -> x integrator
    "R2": (42.0, 22.0, 90),     #  x -> x integrator
    "R3": (42.0, 40.0, 90),     #  x -> -y integrator
    "R4": (42.0, 46.0, 90),     # xz -> -y integrator
    "R5": (42.0, 52.0, 90),     # -y -> -y integrator
    "R6": (42.0, 66.0, 90),     # xy -> z integrator
    "R7": (42.0, 72.0, 90),     #  z -> z integrator

    # ---- capacitor banks: fast / nice / slow, one row per integrator -----
    "C1": (49.0, 16.0, 90), "C2": (54.0, 16.0, 90), "C3": (59.0, 16.0, 90),
    "C4": (49.0, 40.0, 90), "C5": (54.0, 40.0, 90), "C6": (59.0, 40.0, 90),
    "C7": (49.0, 66.0, 90), "C8": (54.0, 66.0, 90), "C9": (59.0, 66.0, 90),
    "SW1": (66.0, 53.0, 0),     # the one control -- reachable, mid board

    # ---- op-amps: U1 carries x and -y, U2 carries z ---------------------
    "U1": (78.0, 30.0, 0), "C16": (78.0, 23.0, 90), "C17": (78.0, 37.0, 90),
    "U2": (78.0, 72.0, 0), "C18": (78.0, 65.0, 90), "C19": (78.0, 79.0, 90),

    # ---- series output resistors and the BNCs ---------------------------
    "R8":  (86.0, 20.0, 90), "J2": (93.0, 20.0, 0),
    "R9":  (86.0, 46.0, 90), "J3": (93.0, 46.0, 0),
    "R10": (86.0, 72.0, 90), "J4": (93.0, 72.0, 0),

    # ---- power strip along the bottom -----------------------------------
    # 13.05 rather than 13.0: that puts the 0.5 mm-pitch CC pads on the
    # router's 0.2 mm grid, which is the only way a 0.3 mm track escapes
    # between them with 0.2 mm clearance either side.
    "J1":  (13.05, 94.0, 0),                               # USB-C, bottom left
    # The CC pull-downs sit directly above their own pads, so each escape from
    # the 0.5 mm-pitch row is a 2.5 mm straight run and neither competes with
    # VBUS for the corridor above the connector.  Their lower ends go to the
    # ground plane, so they need no routing at all.
    "R11": (11.8, 86.4, 90), "R12": (14.8, 86.4, 90),
    "F1":  (24.0, 84.0, 90),
    "C10": (31.0, 84.0, 90), "C11": (35.0, 84.0, 90),
    "U5":  (48.0, 91.0, 0),                                # +/-15 V module
    "C12": (70.0, 84.0, 90), "C13": (70.0, 96.0, 90),
    "U6":  (78.0, 89.0, 0), "U7": (88.0, 89.0, 0),
    "C14": (84.0, 83.0, 90), "C15": (94.0, 83.0, 90),
    "R13": (82.0, 96.0, 90), "D1": (88.0, 96.0, 90),

    # ---- M3 mounting holes, one per corner ------------------------------
    "MH1": (4.0, 4.0, 0), "MH2": (96.0, 4.0, 0),
    "MH3": (4.0, 96.0, 0), "MH4": (96.0, 96.0, 0),
}

# Reference-designator text nudges, so silkscreen never lands on a pad.
REF_OFFSET = {}
