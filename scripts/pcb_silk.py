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
FRONT_NOTES = [
    # (x, y, text, size, thickness)
    (50.0, 3.9, TITLE, 2.8, 0.45),
    (50.0, 7.9, CIRCUIT_BY, 1.6, 0.25),
    (50.0, 10.4, CIRCUIT_URL, 1.1, 0.15),
    (28.0, 72.0, CREDIT, 1.0, 0.15),
    # Out on the empty left side: beside the title it collided with the big
    # "x" over the first jack, which is the one legend on this board that has
    # to be readable from across the room.
    (14.0, 15.0, DATE + "   " + REV, 1.0, 0.15),
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
BACK_BLOCK = [
    (2.4, "dx/dt = s (y - x)"),
    (2.4, "dy/dt = r x - y - x z"),
    (2.4, "dz/dt = x y - b z"),
    (0.0, ""),
    (1.6, "s = 10     r = 21 to 37     b = 8/3"),

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
OWL_CAPTION = (70.0, 41.3, "put x and z on X-Y to see this", 1.15)

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
SPEED_ROWS = [
    ("fast!", "off", "off", "2.2 nF", "2.2 ms"),
    ("nice!", "ON", "off", "102 nF", "102 ms"),
    ("slow!", "off", "ON", "472 nF", "472 ms"),
    ("glacial!", "ON", "ON", "572 nF", "572 ms"),
]

# Legends that must sit next to a particular part.
PORT_LABELS = [
    ("J2", 0.0, -7.2, "x", 3.0),
    ("J3", 0.0, -7.2, "-y", 3.0),
    ("J4", 0.0, -7.2, "z", 3.0),
]

# (reference, dx, dy, text, size) -- small legends anchored to a footprint.
PART_LABELS = [
    ("U3", 0.0, 8.2, "MPY634 multiplier", 1.1),
    ("U4", 0.0, 8.2, "MPY634 multiplier", 1.1),
    ("U1", 0.0, -5.2, "LF412 op-amp", 1.1),
    ("U2", 0.0, 5.2, "LF412 op-amp", 1.1),
    ("U5", -9.0, -5.6, "5 V in", 1.0),
    ("U5", 9.0, -5.6, "+/-15 V out", 1.0),
    ("RV1", 0.0, -9.0, "r  KNOB", 1.3),
    ("RV1", 0.0, 5.5, "CW raises r:  21 .. 37", 0.9),
    ("R19", 0.0, 3.2, "from another", 0.9),
    ("R19", 0.0, 4.9, "board's x", 0.9),
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
    "SW": {"Reference": (0.0, 7.4), "Value": (0.0, 9.4)},
    "U6": {"Reference": (0.0, -3.6), "Value": (0.0, 3.6)},
    "U7": {"Reference": (0.0, -3.6), "Value": (0.0, 3.6)},
    # "GND TIE" belongs under the credit line, not over it.
    "JP": {"Reference": (-4.6, -3.6), "Value": (0.9, -3.6)},
}

IC_NOTES = [
    ("U1", "LF412"), ("U2", "LF412"),
    ("U3", "MPY634"), ("U4", "MPY634"),
    ("U5", "5V -> +/-15V"), ("U6", "78L12"), ("U7", "79L12"),
]
