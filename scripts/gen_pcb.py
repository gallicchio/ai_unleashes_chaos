#!/usr/bin/env python3
"""Build the Lorenz PCB: outline, placement, nets, routing and silkscreen.

Runs under KiCad's bundled Python (it needs pcbnew).  Invoke it through
make.py, or directly as:  <AppRun> python3.11 scripts/gen_pcb.py <layers>
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew
from sexp_parse import parse_file
import pcb_place as P

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.abspath(os.path.join(HERE, "..", "hardware"))
LOCAL_FP = os.path.join(HW, "lib", "lorenz.pretty")
SHARE_FP = None          # filled in from the KiCad install


def mm(v):
    return pcbnew.FromMM(float(v))


def pt(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))


def find_share():
    here = os.path.dirname(os.path.abspath(pcbnew.__file__))
    for up in range(2, 8):
        base = os.path.abspath(os.path.join(here, *([".."] * up)))
        cand = os.path.join(base, "share", "kicad", "footprints")
        if os.path.isdir(cand):
            return cand
    for cand in ("/usr/share/kicad/footprints",
                 os.path.expanduser(
                     "~/.local/kicad10/AppDir/usr/share/kicad/footprints")):
        if os.path.isdir(cand):
            return cand
    raise SystemExit("cannot find KiCad's footprint libraries")


def load_fp(fpid):
    lib, name = fpid.split(":")
    path = LOCAL_FP if lib == "lorenz" else os.path.join(SHARE_FP, lib + ".pretty")
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None:
        raise SystemExit(f"footprint {fpid} not found in {path}")
    return fp


def read_netlist(path):
    root = parse_file(path)
    comps = {}
    for c in root.first("components").kids("comp"):
        fields = {}
        fl = c.first("fields")
        if fl is not None:
            for f in fl.kids("field"):
                nm = f.first("name").atom(0)
                val = f.atom(0)
                if nm not in ("Footprint", "Datasheet", "Description") and val:
                    fields[nm] = val
        ts = c.first("tstamps")
        val = c.first("value").atom(0)
        comps[c.first("ref").atom(0)] = {
            "value": "" if val == "~" else val,
            "footprint": c.first("footprint").atom(0),
            "fields": fields,
            "tstamp": ts.atom(0) if ts is not None else "",
        }
    nets = {}
    for n in root.first("nets").kids("net"):
        # keep the sheet path; stripping it makes DRC's parity check unhappy
        name = n.first("name").atom(0)
        nets[name] = [(x.first("ref").atom(0), x.first("pin").atom(0))
                      for x in n.kids("node")]
    return comps, nets


def board_outline(board):
    w, h = P.BOARD_W, P.BOARD_H
    r = 3.0                                   # rounded corners
    segs = [((r, 0), (w - r, 0)), ((w, r), (w, h - r)),
            ((w - r, h), (r, h)), ((0, h - r), (0, r))]
    for (a, b) in segs:
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pt(*a)); s.SetEnd(pt(*b))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
        board.Add(s)
    for (cx, cy, a0) in ((r, r, 180), (w - r, r, 270), (w - r, h - r, 0), (r, h - r, 90)):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_ARC)
        s.SetCenter(pt(cx, cy))
        import math
        sx = cx + r * math.cos(math.radians(a0))
        sy = cy + r * math.sin(math.radians(a0))
        s.SetStart(pt(sx, sy))
        s.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(90, pcbnew.DEGREES_T), True)
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
        board.Add(s)


import pcb_silk as SILK

SILK_CLEAR = 0.25          # silkscreen to pad, a touch over the 0.15 rule
LAYER_BY_NAME = None


def layer_id(name):
    global LAYER_BY_NAME
    if LAYER_BY_NAME is None:
        LAYER_BY_NAME = {}
        for l in range(pcbnew.PCB_LAYER_ID_COUNT):
            LAYER_BY_NAME[pcbnew.LayerName(l)] = l
    return LAYER_BY_NAME[name]


def add_routes(board, routes_path, layers):
    """Lay down the tracks, vias and ground planes the router worked out."""
    import json
    data = json.load(open(routes_path))
    nets = {board.GetNetInfo().GetNetItem(i).GetNetname():
            board.GetNetInfo().GetNetItem(i)
            for i in range(board.GetNetInfo().GetNetCount())}
    ntrack = nvia = 0
    for net, r in data["routes"].items():
        ni = nets.get(net)
        for s in r["segments"]:
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(pt(s["x1"], s["y1"]))
            t.SetEnd(pt(s["x2"], s["y2"]))
            t.SetWidth(mm(s["width"]))
            t.SetLayer(layer_id(s["layer"]))
            if ni:
                t.SetNet(ni)
            board.Add(t)
            ntrack += 1
        for v in r["vias"]:
            nvia += add_via(board, v["x"], v["y"], ni, layers)
    for v in data.get("stitches", []):
        nvia += add_via(board, v["x"], v["y"], nets.get(v.get("net", "GND")),
                        layers)

    # Two layers: ground poured on both.  Four: signal / ground / power /
    # signal, with the second inner layer carrying +12 V.  Every layer also
    # carries the USB side's own ground in the bottom-left corner, cut out of
    # the analog pour with a 1 mm gap, because the converter is isolated and
    # the two grounds must not touch anywhere.
    cu = list(board.GetEnabledLayers().CuStack())
    plane_of = {l: "GND" for l in cu}
    if layers == 4 and len(cu) == 4:
        plane_of[cu[2]] = "+12V"
    plan = [(l, plane_of[l], (P.island_outline(0.3) if plane_of[l] == "GNDU"
                              else P.ground_outline(0.3)), 0) for l in cu]
    plan += [(l, "GNDU", P.island_outline(0.3), 1) for l in cu]
    for (l, netname, outline_pts, priority) in plan:
        z = pcbnew.ZONE(board)
        z.SetLayer(l)
        zn = nets.get(netname)
        if zn:
            z.SetNet(zn)
        # Distinct priorities, and not for the usual reason: two zones of equal
        # priority on one layer are filled in whichever order the filler's
        # threads get to them, and the results differ in the last nanometre of
        # every arc.  Ranking them makes the fill -- and so the gerbers --
        # reproducible.  The outlines do not overlap, so the ranking itself
        # changes nothing.
        z.SetAssignedPriority(priority)
        # Solid on SMD pads -- an 0805 or SOIC ground pad is too small for two
        # thermal spokes, and starving one is both an electrical and a DRC
        # problem.  Through-hole pads (BNC ground posts, the converter, the
        # USB-C shell) keep their relief so they can still be hand-soldered.
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL)
        z.SetThermalReliefGap(mm(0.3))
        z.SetThermalReliefSpokeWidth(mm(0.5))
        z.SetLocalClearance(mm(0.25))
        z.SetMinThickness(mm(0.2))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        outline = z.Outline()
        outline.NewOutline()
        for (x, y) in outline_pts:
            outline.Append(mm(x), mm(y))
        board.Add(z)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    return ntrack, nvia


def add_via(board, x, y, net, layers):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pt(x, y))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetDrill(mm(0.3))
    v.SetWidth(mm(0.6))
    cu = list(board.GetEnabledLayers().CuStack())
    v.SetLayerPair(cu[0], cu[-1])
    if net:
        v.SetNet(net)
    # Tented: 400-odd stitching vias with open mask would make the silkscreen
    # unprintable and invite solder balls during assembly.
    v.SetFrontTentingMode(pcbnew.TENTING_MODE_TENTED)
    v.SetBackTentingMode(pcbnew.TENTING_MODE_TENTED)
    board.Add(v)
    return 1


# ---------------------------------------------------------- silkscreen ----
def pad_boxes(board, margin=SILK_CLEAR, through_only=False):
    boxes = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if through_only and pad.GetAttribute() not in (
                    pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH):
                continue
            b = pad.GetBoundingBox()
            boxes.append((pcbnew.ToMM(b.GetLeft()) - margin,
                          pcbnew.ToMM(b.GetTop()) - margin,
                          pcbnew.ToMM(b.GetRight()) + margin,
                          pcbnew.ToMM(b.GetBottom()) + margin))
    return boxes


def bbox_mm(item):
    b = item.GetBoundingBox()
    return (pcbnew.ToMM(b.GetLeft()), pcbnew.ToMM(b.GetTop()),
            pcbnew.ToMM(b.GetRight()), pcbnew.ToMM(b.GetBottom()))


def overlaps(a, b):
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def inside_board(box, margin=0.4):
    return (box[0] >= margin and box[1] >= margin
            and box[2] <= P.BOARD_W - margin and box[3] <= P.BOARD_H - margin)


class SilkSpace:
    """Keeps track of what silkscreen has already claimed."""

    def __init__(self, board):
        self.pads = pad_boxes(board)
        # a footprint's own outline is silkscreen too, so legends must dodge it
        for fp in board.GetFootprints():
            for it in fp.GraphicalItems():
                if it.GetLayer() == pcbnew.F_SilkS:
                    b = bbox_mm(it)
                    self.pads.append((b[0] - 0.15, b[1] - 0.15,
                                      b[2] + 0.15, b[3] + 0.15))
        self.taken = []

    def free(self, box):
        if not inside_board(box):
            return False
        for b in self.pads:
            if overlaps(box, b):
                return False
        for b in self.taken:
            if overlaps(box, b):
                return False
        return True

    def claim(self, box):
        self.taken.append(box)


def style_text(item, size, thickness=0.15, layer=pcbnew.F_SilkS):
    item.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    item.SetTextThickness(mm(thickness))
    item.SetLayer(layer)
    if layer == pcbnew.B_SilkS:
        item.SetMirrored(True)
    return item


CANDIDATES = [(0, -1), (0, 1), (-1, 0), (1, 0),
              (-1, -1), (1, -1), (-1, 1), (1, 1)]


def place_field(field, space, fp, size, reserve, prefer=None):
    """Nudge a footprint field outward until it clears every pad.

    `prefer` is tried first: a row of identical probe pads needs its names
    directly above it, not wherever the outward search finds a gap.
    """
    style_text(field, size)
    field.SetVisible(True)
    cx = pcbnew.ToMM(fp.GetPosition().x)
    cy = pcbnew.ToMM(fp.GetPosition().y)
    field.SetTextAngleDegrees(0)
    if prefer:
        field.SetPosition(pt(cx + prefer[0], cy + prefer[1]))
        box = bbox_mm(field)
        if space.free(box):
            space.claim(box)
            return True
    for step in [x * 0.4 for x in range(2, 24)]:
        for (dx, dy) in CANDIDATES:
            field.SetPosition(pt(cx + dx * step, cy + dy * step))
            box = bbox_mm(field)
            if space.free(box):
                space.claim(box)
                return True
    field.SetVisible(False)
    return False


def add_text_near(board, space, x, y, txt, size, thickness=0.15, reach=9.0):
    """Like add_text, but allowed to drift until it finds room."""
    t = add_text(board, space, x, y, txt, size, thickness=thickness)
    if t is not None:
        return t
    for step in [d * 0.5 for d in range(1, int(reach / 0.5) + 1)]:
        for (dx, dy) in CANDIDATES:
            t = add_text(board, space, x + dx * step, y + dy * step, txt,
                         size, thickness=thickness)
            if t is not None:
                return t
    return None


def add_text(board, space, x, y, txt, size, layer=pcbnew.F_SilkS,
             thickness=0.15, must_fit=True, angle=0):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(txt)
    style_text(t, size, thickness, layer)
    t.SetTextAngleDegrees(angle)
    t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
    t.SetPosition(pt(x, y))
    box = bbox_mm(t)
    if must_fit and not space.free(box):
        return None
    space.claim(box)
    board.Add(t)
    return t


def add_qr(board, url, cx, cy, module, missing, what):
    """One QR code on the back, drawn as merged rows of filled rectangles.

    Mirrored in board coordinates, because a back-layer drawing is seen from
    the other side: exactly what SetMirrored does for back-layer text.  The
    modules have to touch -- a QR decoder finds the symbol by the 1:1:3:1:1
    run lengths across a finder pattern, and a gap of any size breaks that --
    so each run of dark modules in a row becomes one rectangle.
    """
    import qrcode_gen
    m = qrcode_gen.encode(url, "M")
    n = len(m)
    x0, y0 = cx - n * module / 2.0, cy - n * module / 2.0
    rects = 0
    for r in range(n):
        c = 0
        while c < n:
            if not m[r][c]:
                c += 1
                continue
            a = c
            while c < n and m[r][c]:
                c += 1
            sh = pcbnew.PCB_SHAPE(board)
            sh.SetShape(pcbnew.SHAPE_T_RECT)
            # column j of the matrix is drawn at n-1-j: mirrored, so it reads
            # the right way round when you turn the board over
            sh.SetStart(pt(x0 + (n - c) * module, y0 + r * module))
            sh.SetEnd(pt(x0 + (n - a) * module, y0 + (r + 1) * module))
            sh.SetFilled(True)
            sh.SetWidth(0)
            sh.SetLayer(pcbnew.B_SilkS)
            board.Add(sh)
            rects += 1
    # Prove the drawing is the code: sample the centre of every module out of
    # the rectangles that were actually placed, and compare with the matrix.
    ok = 0
    for r in range(n):
        for c in range(n):
            x = x0 + (n - 1 - c) * module + module / 2.0
            y = y0 + r * module + module / 2.0
            hit = any(sh.GetShape() == pcbnew.SHAPE_T_RECT
                      and sh.GetLayer() == pcbnew.B_SilkS
                      and sh.GetStart().x <= mm(x) <= sh.GetEnd().x
                      and sh.GetStart().y <= mm(y) <= sh.GetEnd().y
                      for sh in board.GetDrawings()
                      if isinstance(sh, pcbnew.PCB_SHAPE))
            if hit == bool(m[r][c]):
                ok += 1
    if ok != n * n:
        missing.append(f"{what} QR: {n * n - ok} module(s) drawn wrong")
    return n, rects


def add_speed_table(board, space, missing):
    """The switch legend, set out over the switch it explains.

    The six sliders run left to right, so each off/ON cell is centred on the
    slider it refers to and a bar separates the two banks.  The row tells you
    the speed; the columns tell you what to push.
    """
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    sw = fps["SW1"]
    poles = {}
    for pad in sw.Pads():
        if pad.GetNumber().isdigit() and int(pad.GetNumber()) <= 6:
            poles[int(pad.GetNumber())] = pcbnew.ToMM(pad.GetPosition().x)
    xs = [poles[i] for i in sorted(poles)]
    mid = (xs[2] + xs[3]) / 2.0
    y = SILK.SPEED_TABLE_Y
    left = min(xs) - 2.0
    right = max(xs) + 2.0

    # header: which slider is which
    for i, x in enumerate(xs):
        if add_text(board, space, x, y, str(i + 1), 1.0, must_fit=False) is None:
            missing.append(f"speed table pole {i + 1}")
    add_text(board, space, left - 4.0, y, "SW1", 1.0, must_fit=False)
    add_text(board, space, right + 7.0, y, "C", 1.0, must_fit=False)
    for (i, (speed, a, b, cval, tau)) in enumerate(SILK.SPEED_ROWS):
        ry = y + 1.8 + i * 1.8
        add_text(board, space, left - 4.0, ry, speed, 1.0, must_fit=False)
        for k, x in enumerate(xs):
            add_text(board, space, x, ry, a if k < 3 else b, 0.9,
                     must_fit=False)
        add_text(board, space, right + 7.0, ry, cval, 1.0, must_fit=False)
    bot = y + 1.8 + len(SILK.SPEED_ROWS) * 1.8 - 0.6
    add_text(board, space, mid, y - 2.4, "SPEED SELECT", 1.0, must_fit=False)
    below = pcbnew.ToMM(sw.GetBoundingBox().GetBottom()) + 1.7
    if add_text_near(board, space, mid - 3.0, below,
                     "ON is marked on the switch", 0.9, reach=3.0) is None:
        missing.append("speed table footnote")
    for (x1, y1, x2, y2) in ((mid, y - 1.4, mid, bot),          # between banks
                             (left - 8.0, y + 0.9, right + 11.0, y + 0.9)):
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(pt(x1, y1))
        seg.SetEnd(pt(x2, y2))
        seg.SetWidth(mm(0.15))
        seg.SetLayer(pcbnew.F_SilkS)
        board.Add(seg)
        space.claim((min(x1, x2) - 0.1, min(y1, y2) - 0.1,
                     max(x1, x2) + 0.1, max(y1, y2) + 0.1))


def add_silk(board):
    """Legends on the front, the equations, the owl and the codes on the back."""
    from lorenz_curve import owl_xz
    space = SilkSpace(board)
    back = SilkSpace.__new__(SilkSpace)      # back side: only the drilled pads
    back.pads = pad_boxes(board, through_only=True)
    back.taken = []
    missing = []

    # --- whose circuit it is, and where to find it -----------------------
    for (x, y, txt, size, thick) in SILK.FRONT_NOTES:
        if add_text(board, space, x, y, txt, size, thickness=thick) is None:
            missing.append(f"front note {txt!r}")

    # --- what each connector does ----------------------------------------
    fps = {fp.GetReference(): fp for fp in board.GetFootprints()}
    for (ref, dx, dy, txt, size) in SILK.PORT_LABELS:
        fp = fps[ref]
        x = pcbnew.ToMM(fp.GetPosition().x) + dx
        y = pcbnew.ToMM(fp.GetPosition().y) + dy
        if add_text_near(board, space, x, y, txt, size, thickness=0.3) is None:
            missing.append(f"port label {txt}")
    for (ref, dx, dy, txt, size) in SILK.PART_LABELS:
        fp = fps[ref]
        x = pcbnew.ToMM(fp.GetPosition().x) + dx
        y = pcbnew.ToMM(fp.GetPosition().y) + dy
        if add_text_near(board, space, x, y, txt, size) is None:
            missing.append(f"part label {txt} at {ref}")
    if add_text_near(board, space, 13.05, 82.0, "USB-C  5 V in", 1.4) is None:
        missing.append("USB-C label")

    # --- the speed table, set out over the switch it explains -------------
    add_speed_table(board, space, missing)

    # --- reference designator and value on every part ---------------------
    # Parts with an anchored field go first: a row of identical probe pads is
    # only readable if every name is in the same place relative to its pad, and
    # the first legend to claim a spot keeps it.
    def order(f):
        ref = f.GetReference()
        return (0 if ref[:2] in SILK.FIELD_ANCHOR else 1, ref)

    for fp in sorted(board.GetFootprints(), key=order):
        ref = fp.GetReference()
        if ref.startswith("MH"):
            fp.Reference().SetVisible(False)
            fp.Value().SetVisible(False)
            continue
        anchor = SILK.FIELD_ANCHOR.get(ref[:2], {})
        if not place_field(fp.Reference(), space, fp, 1.0, True,
                           anchor.get("Reference")):
            missing.append(f"{ref} reference")
        val = fp.Value()
        if val.GetText() and not place_field(val, space, fp, 0.9, True,
                                             anchor.get("Value")):
            val.SetVisible(False)
            missing.append(f"{ref} value ({val.GetText()})")

    # --- back side: title, mathematics, the owl and the two codes --------
    # The codes go down first and claim their space, because they are the one
    # thing on this board that cannot be nudged: a QR code is only a QR code
    # at exactly the size and spacing it was generated at.
    for (qx, qy, key, caption) in SILK.QR_CODES:
        n, rects = add_qr(board, SILK.URLS[key], qx, qy, SILK.QR_MODULE,
                          missing, key)
        half = n * SILK.QR_MODULE / 2.0
        back.claim((qx - half - 0.3, qy - half - 0.3,
                    qx + half + 0.3, qy + half + 0.3))
        for i, line in enumerate(caption):
            if add_text(board, back, qx, SILK.QR_CAPTION_Y + i * 2.1, line,
                        1.0, layer=pcbnew.B_SilkS) is None:
                missing.append(f"QR caption {line!r}")
    for (x, y, txt, size, thick) in SILK.BACK_TITLE:
        if add_text(board, back, x, y, txt, size, layer=pcbnew.B_SilkS,
                    thickness=thick) is None:
            missing.append(f"back title {txt!r}")
    bx, y = SILK.BACK_BLOCK_AT
    for (size, line) in SILK.BACK_BLOCK:
        if line:
            if add_text(board, back, bx, y, line, size, layer=pcbnew.B_SilkS,
                        thickness=0.25 if size > 2 else 0.15) is None:
                missing.append(f"back line {line!r}")
        y += (size * 1.5 + 0.9) if line else 1.4
    ox, oy, ocap, osize = SILK.OWL_CAPTION[0], SILK.OWL_CAPTION[1], \
        SILK.OWL_CAPTION[2], SILK.OWL_CAPTION[3]
    if add_text(board, back, ox, oy, ocap, osize,
                layer=pcbnew.B_SilkS) is None:
        missing.append("back owl caption")
    # The attractor is an open curve, so it is drawn as a run of segments; a
    # polygon would close it with a chord straight across the owl's face.
    pts = owl_xz(n_max=1100, n=24000, **SILK.OWL)
    for (a, b) in zip(pts, pts[1:]):
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetStart(pt(*a))
        seg.SetEnd(pt(*b))
        seg.SetWidth(mm(0.12))
        seg.SetLayer(pcbnew.B_SilkS)
        board.Add(seg)

    return missing


# ------------------------------------------------------ reproducibility ---
def stabilise_uuids(board):
    """Give every board item a UUID derived from what it *is*.

    pcbnew hands out random UUIDs, and writes some collections in UUID order,
    so two builds of an identical design produce files that differ everywhere.
    Deriving each UUID from a description of the item instead makes the build
    reproducible, which is what lets `git diff` on a board file show real
    changes rather than nine thousand lines of noise.
    """
    import uuid as _uuid

    def kiid(key):
        return pcbnew.KIID(str(_uuid.uuid5(_uuid.NAMESPACE_URL,
                                           "lorenz-pcb://" + key)))

    def mm2(pos):
        return f"{pcbnew.ToMM(pos.x):.4f},{pcbnew.ToMM(pos.y):.4f}"

    n = 0
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        fp.SetUuid(kiid(f"fp/{ref}"))
        n += 1
        for pad in fp.Pads():
            pad.SetUuid(kiid(f"fp/{ref}/pad/{pad.GetNumber()}/"
                             f"{mm2(pad.GetPosition())}/{n}"))
            n += 1
        for i, it in enumerate(fp.GraphicalItems()):
            it.SetUuid(kiid(f"fp/{ref}/gfx/{i}/{it.GetClass()}"))
            n += 1
        for f in fp.GetFields():
            f.SetUuid(kiid(f"fp/{ref}/field/{f.GetName()}"))
            n += 1
    # The index guards against two items that describe identically; without
    # it KiCad rejects the duplicate UUID and hands out a random one instead.
    for i, t in enumerate(board.GetTracks()):
        if isinstance(t, pcbnew.PCB_VIA):
            t.SetUuid(kiid(f"via/{mm2(t.GetPosition())}/{t.GetNetname()}/{i}"))
        else:
            t.SetUuid(kiid(f"trk/{t.GetLayerName()}/{mm2(t.GetStart())}/"
                           f"{mm2(t.GetEnd())}/{t.GetNetname()}/{i}"))
        n += 1
    for i, z in enumerate(board.Zones()):
        z.SetUuid(kiid(f"zone/{z.GetLayerName()}/{z.GetNetname()}/{i}"))
        n += 1
    for i, d in enumerate(board.GetDrawings()):
        txt = d.GetText() if hasattr(d, "GetText") else ""
        d.SetUuid(kiid(f"gfx/{d.GetLayerName()}/{d.GetClass()}/"
                       f"{mm2(d.GetPosition())}/{txt[:40]}/{i}"))
        n += 1
    return n


def save(board, path):
    stabilise_uuids(board)
    pcbnew.SaveBoard(path, board)


def build(layers, netlist_path, out_path):
    global SHARE_FP
    SHARE_FP = find_share()
    comps, nets = read_netlist(netlist_path)
    board = pcbnew.CreateEmptyBoard()
    board.SetCopperLayerCount(layers)

    # --- nets -----------------------------------------------------------
    netmap = {}
    for name in sorted(nets):
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netmap[name] = ni
    pad_net = {}
    for name, nodes in nets.items():
        for node in nodes:
            pad_net[node] = name

    # --- footprints -----------------------------------------------------
    placed = {}
    for ref, info in sorted(comps.items()):
        if ref not in P.PLACE:
            raise SystemExit(f"{ref} has no entry in pcb_place.PLACE")
        x, y, rot = P.PLACE[ref]
        fp = load_fp(info["footprint"])
        fp.SetFPIDAsString(info["footprint"])   # parity wants the full Lib:Name
        # The link back to the schematic symbol.  Without it KiCad cannot
        # cross-probe: clicking a part in one editor highlights nothing in the
        # other, because nothing says which symbol this footprint came from.
        if info["tstamp"]:
            fp.SetPath(pcbnew.KIID_PATH("/" + info["tstamp"]))
        fp.SetSheetname("/")
        fp.SetSheetfile(os.path.basename(out_path).replace(".kicad_pcb",
                                                           ".kicad_sch"))
        fp.SetReference(ref)
        fp.SetValue(info["value"])
        for fname, fval in info["fields"].items():
            fp.SetField(fname, fval)
        # BOM fields are data, not artwork: keep them off the silkscreen
        for f in fp.GetFields():
            if f.GetName() in ("Reference", "Value"):
                continue
            f.SetVisible(False)
            f.SetLayer(pcbnew.F_Fab)
        # the schematic leaves Description empty; match it so parity is clean
        if fp.HasField("Description"):
            fp.SetField("Description", "")
        board.Add(fp)
        fp.SetPosition(pt(x, y))
        if rot:
            fp.SetOrientationDegrees(rot)
        for pad in fp.Pads():
            key = (ref, pad.GetNumber())
            if key in pad_net:
                pad.SetNet(netmap[pad_net[key]])
        # the bundled 3D library is a reduced set and has no model for these
        local = {"J1": "USB_C_HRO_TYPE-C-31-M-12.wrl", "F1": "Fuse_1812.wrl"}
        if ref in local:
            fp.Models().clear()
            m = pcbnew.FP_3DMODEL()
            m.m_Filename = ("${KIPRJMOD}/lib/lorenz.3dshapes/" + local[ref])
            m.m_Scale = pcbnew.VECTOR3D(1 / 2.54, 1 / 2.54, 1 / 2.54)
            m.m_Show = True
            fp.Models().push_back(m)
        if ref[0:2] in ("MH", "TP") or ref[0:2] == "JP":
            # Nothing to buy and nothing for the assembler to place: mounting
            # holes, probe pads, the ground-tie jumper.  The symbols say the
            # same, and DRC's parity check compares the two.
            fp.SetAttributes(fp.GetAttributes()
                             | pcbnew.FP_EXCLUDE_FROM_BOM
                             | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
        if ref.startswith("MH"):
            fp.Value().SetVisible(False)    # "MountingHole" is not a legend
        placed[ref] = fp

    # Every pad on the USB side's ground has to sit inside the island that the
    # GNDU pour covers, or it is a pad with no plane under it and DRC will say
    # only "unconnected".  Check it here, where the reason is obvious.
    stray = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            x = pcbnew.ToMM(pad.GetPosition().x)
            y = pcbnew.ToMM(pad.GetPosition().y)
            net = pad.GetNetname()
            inside = P.in_island(x, y)
            if net == "GNDU" and not inside:
                stray.append(f"{fp.GetReference()}.{pad.GetNumber()} (GNDU) "
                             f"at ({x:.2f}, {y:.2f}) is outside the island")
            if net == "GND" and P.in_island(x, y, -P.ISLAND_GAP):
                stray.append(f"{fp.GetReference()}.{pad.GetNumber()} (GND) "
                             f"at ({x:.2f}, {y:.2f}) is inside the island")
    if stray:
        raise SystemExit("isolation split: " + "; ".join(stray))

    # Drill/place origin at the board's bottom-left corner, so gerbers, drill
    # files and the pick-and-place all share one frame with positive numbers.
    board.GetDesignSettings().SetAuxOrigin(pt(0, P.BOARD_H))
    board_outline(board)
    save(board, out_path)
    return board, placed, netmap, nets


def export_geometry(board, path, layers):
    """Dump pad and outline geometry for the router (which runs elsewhere)."""
    import json
    pads = []
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        for pad in fp.Pads():
            box = pad.GetBoundingBox()
            lset = pad.GetLayerSet().CuStack()
            on = [pcbnew.LayerName(l) for l in lset]
            # A custom-shaped pad (the SOT-89 tab, for one) is not centred on
            # its anchor, so the copper extent has to come from the bounding
            # box itself -- assuming otherwise let tracks run over the tab.
            pads.append({
                "ref": ref, "pad": pad.GetNumber(),
                "net": pad.GetNetname(),
                "x": pcbnew.ToMM(pad.GetPosition().x),
                "y": pcbnew.ToMM(pad.GetPosition().y),
                "cx": pcbnew.ToMM(box.GetCenter().x),
                "cy": pcbnew.ToMM(box.GetCenter().y),
                "w": pcbnew.ToMM(box.GetWidth()), "h": pcbnew.ToMM(box.GetHeight()),
                "through": pad.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH,
                                                  pcbnew.PAD_ATTRIB_NPTH),
                "layers": on,
                "drill": pcbnew.ToMM(pad.GetDrillSizeX()),
            })
    data = {"board_w": P.BOARD_W, "board_h": P.BOARD_H,
            "layers": layers, "pads": pads,
            "copper": [pcbnew.LayerName(l) for l in board.GetEnabledLayers().CuStack()]}
    with open(path, "w") as fh:
        json.dump(data, fh, indent=1)
    return len(pads)


if __name__ == "__main__":
    layers = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    netlist = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HW, "..", "out", "lorenz.net")
    out = sys.argv[3] if len(sys.argv) > 3 else os.path.join(
        HW, "lorenz.kicad_pcb" if layers == 2 else "lorenz-4layer.kicad_pcb")
    stage = os.environ.get("LORENZ_STAGE", "place")
    if stage == "route":
        routes = os.path.abspath(os.path.join(HW, "..", "out",
                                              f"routes_{layers}.json"))
        b = pcbnew.LoadBoard(out)
        nt, nv = add_routes(b, routes, layers)
        missing = add_silk(b)
        save(b, out)
        print(f"  routed {os.path.relpath(out)}: {nt} tracks, {nv} vias, "
              f"{len(list(b.Zones()))} ground zones")
        if missing:
            print(f"  !! {len(missing)} silkscreen item(s) had nowhere to go:")
            for m in missing[:20]:
                print(f"       {m}")
        raise SystemExit(0)
    b, placed, netmap, nets = build(layers, netlist, out)
    geom = os.path.join(os.path.dirname(out), "..", "out",
                        f"pcb_geom_{layers}.json")
    n = export_geometry(b, os.path.abspath(geom), layers)
    print(f"  wrote {os.path.relpath(out)}: {len(placed)} footprints, "
          f"{len(nets)} nets, {layers} layers; {n} pads -> "
          f"{os.path.relpath(os.path.abspath(geom))}")
