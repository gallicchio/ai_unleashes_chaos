"""Silkscreen for the Lorenz board: legends, artwork and the equations.

Front carries what you need with the board in your hand -- whose circuit it
is, where to find it, what each part is, what each connector does, and how to
set the speed.  Back carries the story: the equations the circuit solves, the
owl's face the outputs draw on a scope, and a QR code for each of the two web
pages.

Nothing here may land on a pad, so every legend is placed by trial against a
map of the real pad rectangles, and anything that cannot be fitted is reported
rather than silently dropped.
"""
import parts

TITLE = "AI UNLEASHES CHAOS"
CIRCUIT_BY = "Lorenz attractor  --  circuit by Paul Horowitz"
CIRCUIT_URL = "seti.harvard.edu/unusual_stuff/misc/lorenz.htm"
CREDIT = "PCB by Jason Gallicchio and Claude"
PROJECT_URL = "github.com/gallicchio/ai_unleashes_chaos"
DATE = parts.BOARD_DATE
REV = "rev " + parts.REV

URLS = {
    "circuit": "https://seti.harvard.edu/unusual_stuff/misc/lorenz.htm",
    "project": "https://github.com/gallicchio/ai_unleashes_chaos",
}

# Front-side notes, placed by hand where the board has room.  Paul's name goes
# directly under the title, at a size you can read across a bench, because it
# is his circuit and that is the first thing anyone should see.
FRONT_NOTES = [
    # (x, y, text, size, thickness)
    (50.0, 4.2, TITLE, 2.8, 0.45),
    (50.0, 8.2, CIRCUIT_BY, 1.6, 0.25),
    (50.0, 10.8, CIRCUIT_URL, 1.1, 0.15),
    # the rest of the credit goes at the two ends of the same band, where the
    # first row of parts leaves room
    (24.0, 12.9, CREDIT, 1.0, 0.15),
    (76.0, 12.9, DATE + "   " + REV, 1.0, 0.15),
]

# Back-side title block.
BACK_TITLE = [
    (50.0, 4.8, TITLE, 2.8, 0.45),
    (50.0, 8.8, CIRCUIT_BY, 1.6, 0.25),
    (50.0, 11.4, CREDIT + "    " + DATE + "    " + REV, 1.1, 0.15),
]

# Back-side block: the equations and how the resistors realise them.
# It lives in the left-hand third of the board, which carries no through-hole
# pad at all, so the whole block can be set as one column.
BACK_BLOCK_AT = (24.0, 14.6)
# Lines are kept under 36 characters: any wider and the block runs into the
# probe pad beside U3's output, which is drilled and therefore shows up here.
BACK_BLOCK = [
    (2.4, "dx/dt = s (y - x)"),
    (2.4, "dy/dt = r x - y - x z"),
    (2.4, "dz/dt = x y - b z"),
    (0.0, ""),
    (1.6, "s = 10    r = 28    b = 8/3"),
    (0.0, ""),
    (1.15, "Every term weighs 1 MEG / R:  R1 ="),
    (1.15, "R2 = 100k is s, R3 = 35.7k is r,"),
    (1.15, "R7 = 374k is b.  The MPY634s form"),
    (1.15, "A*B/10 and get their minus signs"),
    (1.15, "from swapped inputs.  0.1 V per unit,"),
    (1.15, "time scale tau = 1 MEG x C."),
]

# The owl, and its caption, on the right of the back.
OWL = dict(cx=67.0, cy=32.0, width=32.0, height=22.0)
OWL_CAPTION = (67.0, 46.0, "x and z on a scope in X-Y draw this", 1.15)

# The two QR codes, side by side under the equations.
QR_MODULE = 0.6                      # millimetres per module: 33 x 0.6 = 19.8
QR_CODES = [
    (14.0, 58.5, "circuit", ["Paul's original:", "seti.harvard.edu"]),
    (36.0, 58.5, "project", ["this project:", "github.com/gallicchio"]),
]
QR_CAPTION_Y = 69.8

# Kept narrow on purpose: the only clear patch of board beside SW1 is about
# 15 mm wide.
SPEED_TABLE_Y = 39.6                 # header row, above the switch
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
    ("D1", 0.0, -2.6, "5V", 1.1),
    ("D2", 0.0, -2.6, "+12V", 1.1),
    ("D3", 0.0, -2.6, "-12V", 1.1),
    ("D4", -13.5, -4.0, "R = x", 1.1),
    ("D4", -13.5, 0.0, "G = -y", 1.1),
    ("D4", -13.5, 4.0, "B = z", 1.1),
]

# Where a field would rather sit than wherever the search happens to find room.
# The probe pads are a row of near-identical circles; their names have to be
# directly above them or you cannot tell which is which.
FIELD_ANCHOR = {"TP": {"Value": (0.0, -2.5), "Reference": (0.0, 2.5)}}

IC_NOTES = [
    ("U1", "LF412"), ("U2", "LF412"),
    ("U3", "MPY634"), ("U4", "MPY634"),
    ("U5", "5V -> +/-15V"), ("U6", "78L12"), ("U7", "79L12"),
]
