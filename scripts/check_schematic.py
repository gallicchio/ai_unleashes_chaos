#!/usr/bin/env python3
"""Check the schematic sheet the way a reader would: is anything on top of
anything else, and is it all inside the frame?

Text extents are estimated from KiCad's stroke font, whose advance measures
0.92 x the text height per character (calibrated against KiCad's own
GetBoundingBox on this sheet).  The estimate is deliberately generous, so a
clean report means clean with room to spare.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexp_parse import parse_file

CHAR_W = 0.92          # per unit of text height
LINE_H = 1.25
PAPER = {"A4": (297.0, 210.0), "A3": (420.0, 297.0),
         "A2": (594.0, 420.0), "A1": (841.0, 594.0)}
FRAME = 10.0           # printed border
# KiCad's own title block, bottom right.  Nothing may land in it.
TITLE_W, TITLE_H = 120.0, 42.0


def text_box(x, y, txt, size, justify, rot=0):
    w = max(len(txt), 1) * size * CHAR_W
    h = size * LINE_H
    if rot in (90, 270):
        w, h = h, w
    if "left" in justify:
        x0 = x
    elif "right" in justify:
        x0 = x - w
    else:
        x0 = x - w / 2
    return (x0, y - h / 2, x0 + w, y + h / 2)


def overlaps(a, b, slack=0.0):
    return not (a[2] - slack <= b[0] or b[2] - slack <= a[0]
                or a[3] - slack <= b[1] or b[3] - slack <= a[1])


def collect(path):
    root = parse_file(path)
    paper = root.first("paper").atom(0)
    W, H = PAPER.get(paper, PAPER["A3"])
    items = []

    def eff(node):
        e = node.first("effects")
        if e is None:
            return 1.27, "", False
        f = e.first("font")
        size = float(f.first("size").atom(0)) if f and f.first("size") else 1.27
        j = e.first("justify")
        just = " ".join(str(a) for a in j.atoms()) if j else ""
        hidden = e.first("hide") is not None and e.first("hide").atom(0) == "yes"
        return size, just, hidden

    for t in root.kids("text"):
        at = t.first("at")
        size, just, hidden = eff(t)
        if hidden:
            continue
        rot = int(float(at.atom(2))) if len(at.atoms()) > 2 else 0
        for i, line in enumerate(t.atom(0).split("\n")):
            items.append((f"text {line[:34]!r}",
                          text_box(float(at.atom(0)),
                                   float(at.atom(1)) + i * size * LINE_H,
                                   line, size, just, rot)))
    for l in root.kids("label"):
        at = l.first("at")
        size, just, hidden = eff(l)
        items.append((f"label {l.atom(0)!r}",
                      text_box(float(at.atom(0)), float(at.atom(1)),
                               l.atom(0), size, just or "left")))
    for s in root.kids("symbol"):
        ref = next((p.atom(1) for p in s.kids("property")
                    if p.atom(0) == "Reference"), "?")
        if ref.startswith("#"):
            continue
        for p in s.kids("property"):
            if p.atom(0) not in ("Reference", "Value"):
                continue
            if p.first("hide") is not None and p.first("hide").atom(0) == "yes":
                continue
            at = p.first("at")
            size, just, hidden = eff(p)
            if hidden:
                continue
            items.append((f"{ref}.{p.atom(0)} {p.atom(1)!r}",
                          text_box(float(at.atom(0)), float(at.atom(1)),
                                   p.atom(1), size, just)))
    return W, H, items


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "hardware",
        "lorenz.kicad_sch")
    W, H, items = collect(path)
    problems = []

    inner = (FRAME, FRAME, W - FRAME, H - FRAME)
    title = (W - FRAME - TITLE_W, H - FRAME - TITLE_H, W - FRAME, H - FRAME)
    for (name, box) in items:
        if not (box[0] >= inner[0] and box[1] >= inner[1]
                and box[2] <= inner[2] and box[3] <= inner[3]):
            problems.append(f"outside the frame: {name} at "
                            f"({box[0]:.1f},{box[1]:.1f})-({box[2]:.1f},{box[3]:.1f})")
        if overlaps(box, title, slack=0.5):
            problems.append(f"in the title block: {name}")

    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if overlaps(items[i][1], items[j][1], slack=0.35):
                problems.append(f"overlap: {items[i][0]}  <->  {items[j][0]}")

    print(f"  sheet {W:.0f} x {H:.0f} mm, {len(items)} text items checked")
    for p in problems[:40]:
        print(f"  FAIL {p}")
    if problems:
        print(f"\n{len(problems)} schematic layout problem(s)")
        return 1
    print("  no text overlaps, nothing outside the frame or in the title block")
    return 0


if __name__ == "__main__":
    sys.exit(main())
