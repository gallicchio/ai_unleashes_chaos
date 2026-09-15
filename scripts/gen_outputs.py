#!/usr/bin/env python3
"""Produce everything a fab needs: gerbers, drill files, BOM, CPL and prints.

The BOM and CPL are written in the column layout JLCPCB expects, which
NextPCB and CircuitHub also accept.
"""
import csv, io, os, re, shutil, sys, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kienv, parts

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
HW = os.path.join(ROOT, "hardware")
OUT = os.path.join(ROOT, "out")

GERBER_LAYERS_2 = ("F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,"
                   "F.Mask,B.Mask,Edge.Cuts")
GERBER_LAYERS_4 = ("F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,"
                   "F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts")

# Parts whose orientation in the CPL is worth a glance in the fab's preview:
# anything that is not rotationally symmetric.
ORIENTATION_SENSITIVE = ["U1", "U2", "U3", "U4", "U5", "U6", "U7",
                         "J1", "SW1", "D1"]


def board_files(stem):
    return (os.path.join(HW, stem + ".kicad_pcb"),
            os.path.join(HW, stem + ".kicad_sch"))


def export_fab(stem, layers):
    pcb, _ = board_files(stem)
    gdir = os.path.join(OUT, stem, "gerbers")
    shutil.rmtree(gdir, ignore_errors=True)
    os.makedirs(gdir, exist_ok=True)
    kienv.cli("pcb", "export", "gerbers",
              "--layers", GERBER_LAYERS_4 if layers == 4 else GERBER_LAYERS_2,
              "--no-protel-ext", "--subtract-soldermask",
              "--use-drill-file-origin", "-o", gdir + os.sep, pcb)
    kienv.cli("pcb", "export", "drill", "--format", "excellon",
              "--drill-origin", "plot", "--excellon-units", "mm",
              "--excellon-separate-th", "--generate-map", "--map-format", "gerberx2",
              "-o", gdir + os.sep, pcb)
    zpath = os.path.join(OUT, stem, f"{stem}-gerbers.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for name in sorted(os.listdir(gdir)):
            z.write(os.path.join(gdir, name), name)
    return zpath, sorted(os.listdir(gdir))


def export_cpl(stem):
    """Pick-and-place in JLCPCB's column layout."""
    pcb, _ = board_files(stem)
    raw = os.path.join(OUT, stem, "_pos.csv")
    kienv.cli("pcb", "export", "pos", "--format", "csv", "--units", "mm",
              "--side", "both", "--use-drill-file-origin", "--exclude-dnp",
              "-o", raw, pcb)
    rows = list(csv.DictReader(open(raw)))
    path = os.path.join(OUT, stem, f"{stem}-cpl.csv")
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for r in rows:
            w.writerow([r["Ref"], f'{float(r["PosX"]):.4f}',
                        f'{float(r["PosY"]):.4f}',
                        "Top" if r["Side"].lower().startswith("t") else "Bottom",
                        f'{float(r["Rot"]):.1f}'])
    os.remove(raw)
    return path, len(rows)


def lcsc_for(ref, value):
    """The order code for one designator, from the single parts table."""
    key = {"U1": "LF412", "U2": "LF412", "U3": "MPY634", "U4": "MPY634",
           "U5": "DCDC", "U6": "REG_POS", "U7": "REG_NEG",
           "J1": "USBC", "J2": "BNC", "J3": "BNC", "J4": "BNC",
           "SW1": "SW_DIP6", "D1": "LED", "F1": "FUSE"}.get(ref)
    if key:
        p = parts.PARTS[key]
        return p["lcsc"], p["mpn"], p["price"], p.get("jlc_type", "extended")
    # passives are keyed by value; the 1206 C0G part is a special case
    v = value
    if ref.startswith("C") and v == "100nF" and int(ref[1:]) in (2, 5, 8):
        v = "100nF_C0G"
    p = parts.PASSIVES.get(v)
    if not p:
        return "", "", 0.0, "extended"
    return p["lcsc"], p["mpn"], p["price"], p.get("jlc_type", "extended")


def export_bom(stem):
    _, sch = board_files(stem)
    raw = os.path.join(OUT, stem, "_bom.csv")
    kienv.cli("sch", "export", "bom", "--fields",
              "Reference,Value,Footprint,${QUANTITY}",
              "--labels", "Reference,Value,Footprint,Qty",
              "--group-by", "Value,Footprint", "--exclude-dnp",
              "--ref-range-delimiter", "", "-o", raw, sch)
    groups = list(csv.DictReader(open(raw)))
    os.remove(raw)

    lines, unknown, total = [], [], 0.0
    for g in groups:
        refs = [r.strip() for r in g["Reference"].split(",") if r.strip()]
        value, fp = g["Value"], g["Footprint"]
        lcsc, mpn, price, jlc = lcsc_for(refs[0], value)
        if not lcsc:
            unknown.append(f"{','.join(refs)} ({value})")
        qty = len(refs)
        total += price * qty
        lines.append({"Comment": value, "Designator": ",".join(refs),
                      "Footprint": fp.split(":")[-1], "LCSC Part #": lcsc,
                      "MPN": mpn, "Qty": qty, "Unit $": f"{price:.4f}",
                      "Ext $": f"{price * qty:.3f}", "JLC": jlc})
    lines.sort(key=lambda r: (r["Designator"][0], len(r["Designator"]),
                              r["Designator"]))

    path = os.path.join(OUT, stem, f"{stem}-bom.csv")
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, ["Comment", "Designator", "Footprint",
                                "LCSC Part #"], extrasaction="ignore")
        w.writeheader()
        for r in lines:
            w.writerow(r)
    full = os.path.join(OUT, stem, f"{stem}-bom-costed.csv")
    with open(full, "w", newline="") as fh:
        w = csv.DictWriter(fh, ["Comment", "Designator", "Footprint",
                                "LCSC Part #", "MPN", "Qty", "Unit $",
                                "Ext $", "JLC"])
        w.writeheader()
        for r in lines:
            w.writerow(r)
    return path, full, lines, total, unknown


def export_prints(stem, layers):
    pcb, sch = board_files(stem)
    d = os.path.join(OUT, stem)
    kienv.cli("sch", "export", "pdf", "--black-and-white", "-o",
              os.path.join(d, f"{stem}-schematic.pdf"), sch)
    kienv.cli("pcb", "export", "pdf", "--mode-single", "--black-and-white",
              "--include-border-title", "--layers",
              "F.Cu,F.Silkscreen,Edge.Cuts",
              "-o", os.path.join(d, f"{stem}-assembly-top.pdf"), pcb)
    kienv.cli("pcb", "export", "pdf", "--mode-single", "--black-and-white",
              "--include-border-title", "--mirror", "--layers",
              "B.Silkscreen,Edge.Cuts",
              "-o", os.path.join(d, f"{stem}-assembly-bottom.pdf"), pcb)


def run(stem, layers):
    os.makedirs(os.path.join(OUT, stem), exist_ok=True)
    zpath, names = export_fab(stem, layers)
    cpl, ncpl = export_cpl(stem)
    bom, costed, lines, total, unknown = export_bom(stem)
    export_prints(stem, layers)
    print(f"  {stem}: {len(names)} gerber/drill files -> "
          f"{os.path.relpath(zpath, ROOT)}")
    print(f"  {stem}: {ncpl} placements -> {os.path.relpath(cpl, ROOT)}")
    print(f"  {stem}: {len(lines)} BOM lines, parts ${total:.2f}/board -> "
          f"{os.path.relpath(bom, ROOT)}")
    if unknown:
        print(f"  !! no order code for: {'; '.join(unknown)}")
    return total, lines, unknown


if __name__ == "__main__":
    bad = 0
    for stem, layers in (("lorenz", 2), ("lorenz-4layer", 4)):
        total, lines, unknown = run(stem, layers)
        bad += len(unknown)
    sys.exit(1 if bad else 0)
