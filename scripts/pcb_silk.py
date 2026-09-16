"""Silkscreen for the Lorenz board: legends, artwork and the equations.

Front carries what you need with the board in your hand -- whose circuit it
is, where to find it, what each part is and does, what each connector does,
and how to set the speed.  Back carries the story: the equations the circuit
solves, the owl's face the outputs draw on a scope, and a QR code for each of
the two web pages, put as far apart as the board allows so a phone can take
one without the other in shot.

Nothing here may land on a pad or under a package, so every legend is placed
by trial against a map of the real pad rectangles and courtyards, and anything
that cannot be fitted is reported rather than silently dropped.
"""
import parts

TITLE = "AI UNLEASHES CHAOS"
CIRCUIT_BY = "Lorenz attractor  --  circuit by Paul Horowitz"
CIRCUIT_URL = "seti.harvard.edu/unusual_stuff/misc/lorenz.htm"
CREDIT = "PCB by Jason Gallicchio and Claude Opus 5 Max"
PROJECT_URL = "github.com/gallicchio/ai_unleashes_chaos"
DATE = parts.BOARD_DATE
REV = "rev " + parts.REV

URLS = {
    "circuit": "https://seti.harvard.edu/unusual_stuff/misc/lorenz.htm",
    "project": "https://github.com/gallicchio/ai_unleashes_chaos",
}

# Front-side notes.  Paul's name goes directly under the title, at a size you
# can read across a bench, because it is his circuit and that is the first
# thing anyone should see.
# The two attributions go together under the title, largest first: whose
# circuit, then whose board.  The reference URL goes down into the open band
# above the power strip, where there is room for it and where it is not
# competing with the names.  The date and revision are the smallest thing on
# the board, tucked under the credit line they belong to.
FRONT_NOTES = [
    # (x, y, text, size, thickness)
    (50.0, 3.9, TITLE, 2.8, 0.45),
    (50.0, 7.9, CIRCUIT_BY, 1.6, 0.25),
    (50.0, 10.4, CREDIT, 1.1, 0.15),
    (50.0, 12.7, DATE + "   " + REV, 0.9, 0.15),
    (28.0, 72.0, CIRCUIT_URL, 1.0, 0.15),
]

# Back-side title block.
BACK_TITLE = [
    (50.0, 4.8, TITLE, 2.8, 0.45),
    (50.0, 8.8, CIRCUIT_BY, 1.6, 0.25),
    (50.0, 11.4, CREDIT + "    " + DATE + "    " + REV, 1.1, 0.15),
]

# Back-side block: the equations and how the resistors realise them.  Set flush
# left, not centred: it is a paragraph, and a ragged left edge is hard to read.
# The anchor is the *right* end of the block in board coordinates, because a
# back-layer item is mirrored: what is drawn rightmost is what you read first.
BACK_BLOCK_AT = (50.0, 15.0)
# Sized so that no line reaches past x = 14: the SYNC IN X jack and the two
# trimmers are drilled right through that edge of the board, and a hole in the
# middle of an equation is not a typographical effect anyone wants.
BACK_BLOCK = [
    (2.0, "dx/dt = s (y - x)"),
    (2.0, "dy/dt = r x - y - x z"),
    (2.0, "dz/dt = x y - b z"),
    (0.0, ""),
    (1.6, "s = 10     b = 8/3"),
    (1.6, "r = 21 to 37 on the knob"),
]

# ...and the prose that explains them, across the foot of the board, where
# there is room for whole sentences on single lines.  Same right-hand anchor
# as the block above; it stops short of x = 86 so it clears the ground loop's
# drilled slot up in the corner.
BACK_FOOT_AT = (86.0, 81.6)
BACK_FOOT = [
    (1.15, "Every term weighs 1 MEG / R."),
    (1.15, "s is R1 = R2 = 100k, and b is R7 = 374k."),
    (1.15, "r is R3 = 27k plus the knob RV1, which sweeps r from 21 to 37."),
    (1.15, "The MPY634s form A*B/10, and both minus signs come from swapped inputs."),
    (1.15, "Signals are 0.1 V per unit, and the time scale is tau = 1 MEG x C."),
]

# The owl, and its caption, on the right of the back.
OWL = dict(cx=69.0, cy=30.0, width=34.0, height=18.0)
OWL_CAPTION = (70.0, 41.3, "put x and z on 'scope X-Y to see this", 1.15)

# The two codes, as far apart as the board allows: 62 mm between centres, and
# each one has a clear 20 mm square with no drilled hole in it.
QR_MODULE = 0.6                      # millimetres per module: 33 x 0.6 = 19.8
# (x, y, key, first caption line's y, [(size, line), ...]).  Each code carries
# its own URL underneath, so nobody has to point a phone at it to find out
# where it goes.  The two y values differ because the drilled holes differ:
# a QR code is the one thing here that cannot be nudged or shrunk to fit.
QR_CODES = [
    (16.0, 61.0, "circuit", 73.0,
     [(1.0, "Paul's original circuit"),
      (1.0, "seti.harvard.edu/unusual_stuff"),
      (1.0, "/misc/lorenz.htm")]),
    # Kept narrow: the BNC's mounting pads are drilled right through, and a
    # caption that runs over one comes out with a hole in it.
    (76.0, 56.5, "project", 71.0,
     [(1.0, "this project, and how"),
      (1.0, "it was made"),
      (1.0, "github.com/gallicchio"),
      (1.0, "/ai_unleashes_chaos")]),
]

SPEED_TABLE_Y = 31.5                 # header row, above the switch
# Poles 1-3 carry the 470 nF and poles 4-6 the 100 nF, so the six sliders
# read left to right as a two-digit binary number: 00, 01, 10, 11.
SPEED_ROWS = [
    ("fast!", "off", "off", "2.2 nF", "2.2 ms"),
    ("nice!", "off", "ON", "102 nF", "102 ms"),
    ("slow!", "ON", "off", "472 nF", "472 ms"),
    ("slower!", "ON", "ON", "572 nF", "572 ms"),
]

# Legends that must sit next to a particular part.
PORT_LABELS = [
    # Above its jack, the way each output's letter sits above its own jack.
    ("J5", 0.0, -7.2, "SYNC IN X", 1.6),
    ("J5", 15.0, -2.0, "from another board's x", 1.0),
    ("J2", 0.0, -7.2, "x", 3.0),
    ("J3", 0.0, -7.2, "-y", 3.0),
    ("J4", 0.0, -7.2, "z", 3.0),
]

# (reference, dx, dy, text, size) -- small legends anchored to a footprint.
PART_LABELS = [
    ("U3", 0.0, 8.2, "MPY634   x z", 1.1),
    ("U4", 0.0, 8.2, "MPY634   x y", 1.1),
    ("U1", 0.0, -5.2, "LF412 op-amp", 1.1),
    ("U2", 0.0, 5.2, "LF412 op-amp", 1.1),
    ("U5", -16.615, -3.0, "5 V in", 1.0),
    ("U5", 1.385, -3.0, "+/-15 V out", 1.0),
    # The two knobs are 5 mm apart on the left edge with nothing but their
    # own pin-1 marks between them, so their legends go to the right, in the
    # band the multipliers leave clear.
    ("RV2", 16.0, 3.5, "SYNC WEIGHT", 1.1),
    ("RV2", 16.0, 5.8, "CW:  0 .. 10", 0.9),
    ("RV1", 16.0, 0.0, "r  KNOB", 1.3),
    ("RV1", 16.0, 2.3, "CW:  21 .. 37", 0.9),
    ("R19", 0.0, -2.6, "SYNC IN X adds here", 0.9),
    # The lamp's whole story, next to the lamp: which signal drives which die.
    ("D1", 0.0, -8.4, "CHAOS LAMP", 1.2),
    ("D1", 0.0, -6.0, "z = red", 1.0),
    ("D1", 0.0, -4.3, "x = green", 1.0),
    ("D1", 0.0, -2.6, "-y = blue", 1.0),
    ("R13", -5.6, 0.0, "green", 1.0),
    ("R14", -5.6, 0.0, "blue", 1.0),
    ("R15", -5.6, 0.0, "red", 1.0),
]

# Where a field would rather sit than wherever the search happens to find room.
# The probe pads are a row of near-identical circles; their names have to be
# directly above them or you cannot tell which is which.
FIELD_ANCHOR = {
    "TP": {"Value": (0.0, -2.5), "Reference": (0.0, 2.5)},
    # The switch and the two regulators sit in narrow bands; say where their
    # legends go rather than letting the search wander off to find room.
    "SW": {"Reference": (-12.5, -1.0), "Value": (-12.5, 1.5)},
    "U6": {"Reference": (0.0, -3.6), "Value": (0.0, 3.6)},
    "U7": {"Reference": (0.0, -3.6), "Value": (0.0, 3.6)},
    # The two trimmers are 5 mm apart on the left edge; without this their
    # designators drift and it stops being obvious which 20k is which.
    "RV": {"Reference": (-3.4, 7.3), "Value": (3.4, 7.3)},
    # "GND TIE" belongs under the credit line, not over it.
    "JP": {"Reference": (-4.6, -3.6), "Value": (0.9, -3.6)},
}

# Parts whose Value field would only repeat the legend beside them.  The two
# multipliers are the crowded corner of the board and "MPY634" is already
# printed under each of them in full.
HIDE_VALUE = {"U3", "U4"}

IC_NOTES = [
    ("U1", "LF412"), ("U2", "LF412"),
    ("U3", "MPY634"), ("U4", "MPY634"),
    ("U5", "5V -> +/-15V"), ("U6", "78L12"), ("U7", "79L12"),
]
