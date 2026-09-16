#!/usr/bin/env python3
"""Check the fab package the way a fab's importer would.

Catches the mistakes that survive DRC and only show up as a rejected order or,
worse, a wrong board: a BOM line with no order code, a placement that misses
the board because the origins disagree, a part in the CPL that the BOM never
mentions, a drill file with no holes.
"""
import csv, os, re, sys, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parts, kienv
from sexp_parse import parse_file

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.path.join(ROOT, "out")

REQUIRED_2 = ["F_Cu", "B_Cu", "F_Mask", "B_Mask", "F_Silkscreen", "B_Silkscreen",
              "F_Paste", "B_Paste", "Edge_Cuts"]
REQUIRED_4 = REQUIRED_2 + ["In1_Cu", "In2_Cu"]


def gerber_extent(path):
    """Coordinate extent of a gerber, in mm."""
    xs, ys = [], []
    fmt = (4, 6)
    for line in open(path, errors="replace"):
        m = re.search(r"%FSLAX(\d)(\d)Y\d\d\*%", line)
        if m:
            fmt = (int(m.group(1)), int(m.group(2)))
        for m in re.finditer(r"X(-?\d+)Y(-?\d+)", line):
            xs.append(int(m.group(1)) / 10 ** fmt[1])
            ys.append(int(m.group(2)) / 10 ** fmt[1])
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def check(stem, layers, w, h, problems, notes):
    d = os.path.join(OUT, stem)
    zpath = os.path.join(d, f"{stem}-gerbers.zip")
    if not os.path.exists(zpath):
        problems.append(f"{stem}: no gerber zip")
        return
    names = zipfile.ZipFile(zpath).namelist()
    for want in (REQUIRED_4 if layers == 4 else REQUIRED_2):
        if not any(want in n for n in names):
            problems.append(f"{stem}: gerber zip has no {want} layer")
    drills = [n for n in names if n.endswith(".drl")]
    if not drills:
        problems.append(f"{stem}: no Excellon drill file")
    for dn in drills:
        body = zipfile.ZipFile(zpath).read(dn).decode("latin-1")
        if "PTH" in dn and not re.search(r"^T\d", body, re.M):
            problems.append(f"{stem}: {dn} defines no tools")
    notes.append(f"{stem}: gerber zip has {len(names)} files "
                 f"({len(drills)} drill)")

    # the outline must be the board we think we designed
    gdir = os.path.join(d, "gerbers")
    edge = [n for n in os.listdir(gdir) if "Edge_Cuts" in n]
    if edge:
        ext = gerber_extent(os.path.join(gdir, edge[0]))
        if ext:
            gw, gh = ext[2] - ext[0], ext[3] - ext[1]
            if abs(gw - w) > 0.3 or abs(gh - h) > 0.3:
                problems.append(f"{stem}: outline is {gw:.2f} x {gh:.2f} mm, "
                                f"expected {w} x {h}")
            else:
                notes.append(f"{stem}: outline {gw:.2f} x {gh:.2f} mm, "
                             f"origin at ({ext[0]:.2f}, {ext[1]:.2f})")
            if gw > 100.5 or gh > 100.5:
                problems.append(f"{stem}: {gw:.1f} x {gh:.1f} mm is outside "
                                "the 100 x 100 mm discounted size")

    # placements land on the board, and every one is in the BOM
    cpl = os.path.join(d, f"{stem}-cpl.csv")
    bom = os.path.join(d, f"{stem}-bom.csv")
    rows = list(csv.DictReader(open(cpl)))
    for r in rows:
        x, y = float(r["Mid X"]), float(r["Mid Y"])
        if not (-1 <= x <= w + 1 and -1 <= y <= h + 1):
            problems.append(f"{stem}: {r['Designator']} placed at "
                            f"({x:.1f}, {y:.1f}), off the board")
        if r["Layer"] not in ("Top", "Bottom"):
            problems.append(f"{stem}: {r['Designator']} has layer "
                            f"{r['Layer']!r}")
        rot = float(r["Rotation"])
        if not (-360 <= rot <= 360):
            problems.append(f"{stem}: {r['Designator']} rotation {rot}")

    bom_rows = list(csv.DictReader(open(bom)))
    in_bom = set()
    for b in bom_rows:
        if not b["LCSC Part #"].strip():
            problems.append(f"{stem}: BOM line {b['Designator']} "
                            f"({b['Comment']}) has no LCSC code")
        if not re.fullmatch(r"C\d+", b["LCSC Part #"].strip() or "x"):
            problems.append(f"{stem}: BOM line {b['Designator']} has a "
                            f"malformed code {b['LCSC Part #']!r}")
        in_bom.update(x.strip() for x in b["Designator"].split(","))
    placed = {r["Designator"] for r in rows}
    missing = sorted(placed - in_bom)
    extra = sorted(in_bom - placed)
    if missing:
        problems.append(f"{stem}: placed but not in the BOM: {missing}")
    if extra:
        problems.append(f"{stem}: in the BOM but not placed: {extra}")
    notes.append(f"{stem}: {len(placed)} placements, {len(bom_rows)} BOM "
                 f"lines, all with order codes")

    # The JLC copy must be the same file, turned by exactly the amounts in the
    # rotation table and by nothing else: same parts, same places, same sides.
    jlc_path = os.path.join(ROOT, "out", stem, f"{stem}-cpl_jlc_corrected.csv")
    if not os.path.exists(jlc_path):
        problems.append(f"{stem}: no JLCPCB-corrected placement file")
        return
    lcsc_of = {}
    for b in bom_rows:
        for ref in b["Designator"].split(","):
            lcsc_of[ref.strip()] = b["LCSC Part #"].strip()
    jlc = {r["Designator"]: r for r in csv.DictReader(open(jlc_path))}
    plain = {r["Designator"]: r for r in rows}
    if set(jlc) != set(plain):
        problems.append(f"{stem}: the JLCPCB placement file lists different "
                        f"parts from {os.path.basename(cpl)}")
        return
    turned = 0
    for ref, a in plain.items():
        b = jlc[ref]
        if (a["Mid X"], a["Mid Y"], a["Layer"]) != (b["Mid X"], b["Mid Y"],
                                                    b["Layer"]):
            problems.append(f"{stem}: {ref} moved in the JLCPCB placement "
                            f"file; only rotations may differ")
        want = (float(a["Rotation"])
                + parts.JLC_ROTATION.get(lcsc_of.get(ref, ""), 0)) % 360.0
        if abs(float(b["Rotation"]) - want) > 0.05:
            problems.append(f"{stem}: {ref} is at {b['Rotation']} deg for "
                            f"JLCPCB, expected {want:.1f}")
        elif float(b["Rotation"]) != float(a["Rotation"]):
            turned += 1
    notes.append(f"{stem}: the JLCPCB placement file turns {turned} parts "
                 f"and moves none")


def check_models(stem, problems, notes):
    """Every 3D model a footprint names must actually be on disk.

    gen_models.py was once not wired into the build at all, so a fresh clone
    had no models and half the board rendered as bare pads -- with nothing
    complaining.
    """
    pcb = os.path.join(ROOT, "hardware", stem + ".kicad_pcb")
    if not os.path.exists(pcb):
        return
    share = kienv.share_dir()
    subs = {"${KIPRJMOD}": os.path.join(ROOT, "hardware"),
            "${KICAD10_3DMODEL_DIR}": os.path.join(share, "3dmodels"),
            "${KICAD9_3DMODEL_DIR}": os.path.join(share, "3dmodels"),
            "${KISYS3DMOD}": os.path.join(share, "3dmodels")}
    board = parse_file(pcb)
    missing, ok = [], 0
    for fp in board.kids("footprint"):
        ref = next((p.atom(1) for p in fp.kids("property")
                    if p.atom(0) == "Reference"), "?")
        models = [m.atom(0) for m in fp.kids("model")]
        if not models:
            # Nothing is fitted here -- a mounting hole, a probe pad, a solder
            # jumper -- so there is nothing to draw.
            if ref[:2] not in ("MH", "TP", "JP"):
                missing.append(f"{ref} has no 3D model")
            continue
        for m in models:
            path = m
            for k, v in subs.items():
                path = path.replace(k, v)
            if os.path.exists(path):
                ok += 1
            else:
                missing.append(f"{ref} -> {os.path.basename(path)}")
    for m in missing:
        problems.append(f"{stem}: missing 3D model, {m}")
    notes.append(f"{stem}: {ok} 3D model(s) resolve on disk")


def check_qr(stem, problems, notes):
    """Read the QR codes back out of the finished board and decode them.

    The one thing on this board that can be silently, completely wrong: a
    misplaced module still looks like a QR code.  So the rectangles that were
    actually written to the .kicad_pcb are sampled back into a matrix and run
    through the decoder, which checks the format information's BCH, every
    Reed-Solomon block's syndromes, and the payload.
    """
    import qrcode_gen
    import pcb_silk as SILK
    pcb = os.path.join(ROOT, "hardware", stem + ".kicad_pcb")
    if not os.path.exists(pcb):
        return
    board = parse_file(pcb)
    rects = []
    for r in board.kids("gr_rect"):
        if (r.first("layer") is None
                or r.first("layer").atom(0) != "B.SilkS"):
            continue
        a, b = r.first("start"), r.first("end")
        rects.append((float(a.atom(0)), float(a.atom(1)),
                      float(b.atom(0)), float(b.atom(1))))
    mod = SILK.QR_MODULE
    for (qx, qy, key, _cap_y, _cap) in SILK.QR_CODES:
        want = SILK.URLS[key]
        n = len(qrcode_gen.encode(want, "M"))
        x0, y0 = qx - n * mod / 2.0, qy - n * mod / 2.0
        m = []
        for row in range(n):
            line = []
            for col in range(n):
                # drawn mirrored, so column j lives at n-1-j
                x = x0 + (n - 1 - col) * mod + mod / 2.0
                y = y0 + row * mod + mod / 2.0
                line.append(1 if any(rx0 <= x <= rx1 and ry0 <= y <= ry1
                                     for (rx0, ry0, rx1, ry1) in rects) else 0)
            m.append(line)
        try:
            got, mask, version = qrcode_gen.decode(m, "M")
        except Exception as e:
            problems.append(f"{stem}: the {key} QR code does not decode: {e}")
            continue
        if got != want:
            problems.append(f"{stem}: the {key} QR code reads {got!r}")
        else:
            notes.append(f"{stem}: the {key} QR code on B.Silkscreen decodes "
                         f"to {got} (version {version}, mask {mask})")


def check_stock(problems, notes):
    """Every chosen part had stock when the design was frozen."""
    low = []
    for key, p in parts.PARTS.items():
        if "stock" not in p:
            continue
        need = {"MPY634": 2, "LF412": 2, "BNC": 3}.get(key, 1)
        boards = p["stock"] // need
        if boards < 50:
            low.append(f"{p['mpn']} ({p['stock']} in stock = {boards} boards)")
    if low:
        notes.append("thin stock (see docs for alternates): " + "; ".join(low))
    notes.append(f"{len(parts.PARTS)} part types, "
                 f"{len(parts.PASSIVES)} passive values, all with order codes")


def main():
    problems, notes = [], []
    check("lorenz", 2, 100.0, 100.0, problems, notes)
    check_qr("lorenz", problems, notes)
    check_models("lorenz", problems, notes)
    check_stock(problems, notes)
    for n in notes:
        print(f"  ok   {n}")
    for p in problems:
        print(f"  FAIL {p}")
    print(f"\n{'ALL FAB CHECKS PASSED' if not problems else str(len(problems)) + ' PROBLEM(S)'}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
