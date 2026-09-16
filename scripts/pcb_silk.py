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
    (30.0, 75.5, CREDIT, 1.0, 0.15),
    (85.0, 10.4, DATE + "   " + REV, 1.0, 0.15),
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
BACK_BLOCK_AT = (50.0, 14.2)
BACK_BLOCK = [
    (2.4, "dx/dt = s (y - x)"),
    (2.4, "dy/dt = r x - y - x z"),
    (2.4, "dz/dt = x y - b z"),
    (0.0, ""),
    (1.6, "s = 10     r = 28     b = 8/3"),
    (0.0, ""),
    (1.15, "Every term weighs 1 MEG / R:  R1 = R2 ="),
    (1.15, "100k is s, R3 = 35.7k is r, R7 = 374k is b."),
    (1.15, "The MPY634s form A*B/10 and take their"),
    (1.15, "minus signs from swapped inputs.  0.1 V"),
    (1.15, "per unit; time scale tau = 1 MEG x C."),
]

# The owl, and its caption, on the right of the back.
OWL = dict(cx=69.0, cy=30.0, width=34.0, height=18.0)
OWL_CAPTION = (70.0, 41.3, "x and z on a scope in X-Y draw this", 1.15)

# The two codes, as far apart as the board allows: 62 mm between centres, and
# each one has a clear 20 mm square with no drilled hole in it.
QR_MODULE = 0.6                      # millimetres per module: 33 x 0.6 = 19.8
QR_CODES = [
    (16.0, 56.5, "circuit", ["Paul's original circuit", "seti.harvard.edu"]),
    (76.0, 56.5, "project", ["this project, and how", "it was made"]),
]
QR_CAPTION_Y = 71.5

SPEED_TABLE_Y = 38.2                 # header row, above the switch
SPEED_ROWS = [
    ("fast!", "off", "off", "2.2 nF", "2.2 ms"),
    ("nice!", "ON", "off", "102 nF", "102 ms"),
    ("slow!", "off", "ON", "472 nF", "472 ms"),
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
    ("D1", 0.0, -4.2, "CHAOS LAMP", 1.2),
    ("R13", -5.6, 0.0, "red = x", 1.0),
    ("R14", -5.6, 0.0, "grn = -y", 1.0),
    ("R15", -5.6, 0.0, "blu = z", 1.0),
    ("JP1", 7.2, 0.0, "GND TIE", 1.0),
    ("TP14", 0.0, -2.6, "SCOPE GND", 1.0),
    ("TP15", 0.0, -2.6, "SCOPE GND", 1.0),
    ("TP16", 0.0, -2.6, "SCOPE GND", 1.0),
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
}

IC_NOTES = [
    ("U1", "LF412"), ("U2", "LF412"),
    ("U3", "MPY634"), ("U4", "MPY634"),
    ("U5", "5V -> +/-15V"), ("U6", "78L12"), ("U7", "79L12"),
]
