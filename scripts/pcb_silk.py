"""Silkscreen for the Lorenz board: legends, artwork and the equations.

Front carries what you need with the board in your hand -- what each part is,
what each connector does, how to set the speed.  Back carries the story: the
equations the circuit solves, Paul's suggested parameters, and the owl's face
the outputs draw on a scope.

Nothing here may land on a pad, so every legend is placed by trial against a
map of the real pad rectangles, and anything that cannot be fitted is reported
rather than silently dropped.
"""

TITLE = "AI UNLEASHES CHAOS"
SUBTITLE = "Lorenz attractor  --  circuit by Paul Horowitz"
CREDIT = "PCB by Jason Gallicchio and Claude"
DATE = "2026-09-15"
REV = "rev A"

# Front-side notes, placed by hand where the board has room.
FRONT_NOTES = [
    # (x, y, text, size, layer-relative rotation)
    (50.0, 5.0, TITLE, 2.6, 0),
    (50.0, 8.6, SUBTITLE, 1.2, 0),
    (50.0, 10.8, CREDIT + "   -   " + DATE + "   -   " + REV, 1.2, 0),
]

# Back-side block: equations, parameters and how to read the board.
# Line lengths are kept short on purpose: the stroke font advances about one
# text height per character, and the BNC ground posts are through-hole, so
# they show up on the back too.
BACK_BLOCK = [
    (2.6, "dx/dt = s (y - x)"),
    (2.6, "dy/dt = r x - y - x z"),
    (2.6, "dz/dt = x y - b z"),
    (0.0, ""),
    (1.6, "s = 10    r = 28    b = 8/3"),
    (0.0, ""),
    (1.2, "Each op-amp integrates one derivative, and"),
    (1.2, "every term is weighted 1 MEG / R:  R1 = R2 ="),
    (1.2, "100k gives s = 10,  R3 = 35.7k gives r = 28.01,"),
    (1.2, "R7 = 374k gives b = 2.674.  The two MPY634s"),
    (1.2, "form A*B/10 and get their minus signs from"),
    (1.2, "swapped inputs.  Signals carry the variables"),
    (1.2, "at 0.1 V per unit.  Time scale: tau = 1 MEG x C."),
]

# Kept narrow on purpose: the only clear patch of board beside SW1 is about
# 15 mm wide.
SPEED_TABLE = [
    "SPEED",
    "1-3  4-6",
    "off off  2.2nF",
    "ON  off  102nF",
    "off  ON  472nF",
    "(fast nice slow)",
]
SPEED_AT = (51.5, 45.5)

# Legends that must sit next to a particular part.
PORT_LABELS = [
    ("J2", 0.0, -7.2, "x", 3.0),
    ("J3", 0.0, -7.2, "-y", 3.0),
    ("J4", 0.0, -7.2, "z", 3.0),
]

IC_NOTES = [
    ("U1", "LF412"), ("U2", "LF412"),
    ("U3", "MPY634"), ("U4", "MPY634"),
    ("U5", "5V -> +/-15V"), ("U6", "78L12"), ("U7", "79L12"),
]
