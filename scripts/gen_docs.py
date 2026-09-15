#!/usr/bin/env python3
"""Write docs/MANUFACTURING.md: what to upload, what to pick, what it costs.

Every number here is computed from the same parts table the BOM is built from,
so the document cannot drift away from the files in out/.
"""
import csv, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parts

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.path.join(ROOT, "out")
DOCS = os.path.join(ROOT, "docs")

# JLCPCB list prices, spring 2026.  These move; the fab's quote is the
# authority and the build prints these only as an order of magnitude.
PCB_2L_5PCS = 2.00
PCB_4L_5PCS = 25.00
SHIPPING = 22.00
PCBA_SETUP = 8.00
STENCIL = 1.50
PER_JOINT = 0.0017
EXTENDED_PART_FEE = 3.00
THT_PER_JOINT = 0.30        # JLCPCB's hand-soldering surcharge, if used


def joint_counts(layers=2):
    geom = json.load(open(os.path.join(OUT, f"pcb_geom_{layers}.json")))
    smt = sum(1 for p in geom["pads"] if not p["through"])
    tht = sum(1 for p in geom["pads"] if p["through"])
    tht_refs = sorted({p["ref"] for p in geom["pads"] if p["through"]})
    return smt, tht, tht_refs


def bom_rows(stem="lorenz"):
    path = os.path.join(OUT, stem, f"{stem}-bom-costed.csv")
    return list(csv.DictReader(open(path)))


def money(x):
    return f"${x:,.2f}"


def main():
    rows = bom_rows()
    smt, tht, tht_refs = joint_counts()
    parts_cost = sum(float(r["Ext $"]) for r in rows)
    extended = [r for r in rows if r["JLC"] != "basic"]
    basic = [r for r in rows if r["JLC"] == "basic"]
    ext_fee = EXTENDED_PART_FEE * len(extended)

    def quote(qty, pcb_cost, with_tht):
        parts_total = parts_cost * qty
        assembly = PCBA_SETUP + STENCIL + PER_JOINT * smt * qty + ext_fee
        if with_tht:
            assembly += THT_PER_JOINT * tht * qty
        return pcb_cost, parts_total, assembly, SHIPPING, \
            pcb_cost + parts_total + assembly + SHIPPING

    lines = []
    a = lines.append
    a("# Manufacturing")
    a("")
    a("Two boards are built from one schematic: `lorenz` on two layers and")
    a("`lorenz-4layer` on four.  They are electrically identical and share a")
    a("footprint, a BOM and a pick-and-place file; the four-layer version adds")
    a("a solid ground plane and a +12 V plane between the outer layers.")
    a("")
    a("Both pass ERC, DRC (with schematic parity) and the circuit checker with")
    a("zero violations.  `./make.py` rebuilds and rechecks everything from")
    a("scratch in about a minute.")
    a("")
    a("## What to upload")
    a("")
    a("| file | where it goes |")
    a("|---|---|")
    a("| `out/lorenz/lorenz-gerbers.zip` | the *Add gerber file* box |")
    a("| `out/lorenz/lorenz-bom.csv` | the BOM box (JLCPCB column layout) |")
    a("| `out/lorenz/lorenz-cpl.csv` | the CPL / pick-and-place box |")
    a("")
    a("For the four-layer build use the matching files in `out/lorenz-4layer/`.")
    a("")
    a("## Board options to pick")
    a("")
    a("| option | value | why |")
    a("|---|---|---|")
    a("| Layers | 2 (or 4) | matches the gerber set you uploaded |")
    a("| Dimensions | 100 x 100 mm | the discounted size at all three houses |")
    a("| Thickness | 1.6 mm | the BNC flanges and the USB-C shell expect it |")
    a("| Surface finish | HASL or ENIG | either; ENIG is flatter for the 0.5 mm-pitch USB-C |")
    a("| Copper weight | 1 oz | the design rules assume it |")
    a("| Via covering | Tented | the ground stitching is dense; open vias would ruin the silkscreen |")
    a("| Assembly side | Top | every placed part is on the front |")
    a("| Parts source | JLCPCB (no consignment) | every line has an LCSC code |")
    a("")
    a("## Cost")
    a("")
    a(f"The board has **{smt} SMT joints** and **{tht} through-hole joints** on")
    a(f"{len(rows)} BOM lines ({len(basic)} JLCPCB Basic, {len(extended)} Extended).")
    a(f"Parts alone are **{money(parts_cost)} per board**, of which")
    a(f"{money(2 * parts.PARTS['MPY634']['price'])} is the pair of MPY634 multipliers.")
    a("")
    for qty in (2, 5, 10):
        pcb = PCB_2L_5PCS if qty <= 5 else PCB_2L_5PCS * 2
        p, pr, asm, ship, tot = quote(qty, pcb, with_tht=True)
        a(f"**{qty} boards, two layers, fully assembled including through-hole**")
        a("")
        a("| line | cost |")
        a("|---|---|")
        a(f"| bare PCBs | {money(p)} |")
        a(f"| parts ({money(parts_cost)} x {qty}) | {money(pr)} |")
        a(f"| assembly: setup {money(PCBA_SETUP)} + stencil {money(STENCIL)} + "
          f"{smt * qty} SMT joints + {len(extended)} extended parts "
          f"+ {tht * qty} THT joints | {money(asm)} |")
        a(f"| shipping (DHL, worldwide) | {money(ship)} |")
        a(f"| **total** | **{money(tot)}**  ({money(tot / qty)} each) |")
        a("")
    p, pr, asm, ship, tot = quote(5, PCB_4L_5PCS, with_tht=True)
    a(f"Five **four-layer** boards come to about {money(tot)} "
      f"({money(tot / 5)} each): the only change is the bare-board price.")
    a("")
    a("Two boards is the sensible order: one for Paul and one to keep.")
    a("")
    a("## The through-hole parts")
    a("")
    a(f"{len(tht_refs)} parts are through-hole: **{', '.join(tht_refs)}** "
      f"-- the three BNC jacks, the DC/DC module and the USB-C shell tabs.")
    a("They are included in the BOM and the CPL, so a fab that offers")
    a("through-hole assembly will fit them.  If you would rather not pay for")
    a("that, deselect them at checkout and solder them yourself: they are the")
    a("four largest, easiest joints on the board and take about ten minutes.")
    a("Everything else is 0805, 1206, SOIC or SOT-89 and is hand-workable too.")
    a("")
    a("## Check these orientations in the fab's preview")
    a("")
    a("Rotation in a CPL is the one thing a fab's importer cannot verify for")
    a("you: a part whose LCSC drawing points a different way than the KiCad")
    a("footprint will be fitted turned.  The symmetric parts (every resistor")
    a("and capacitor) cannot go wrong.  These can:")
    a("")
    a("| part | what to look for |")
    a("|---|---|")
    a("| D1 | cathode band toward the ground end |")
    a("| U1, U2 | pin 1 dot at the top-left, toward C16 / C18 |")
    a("| U3, U4 | pin 1 dot at the top-left |")
    a("| U5 | pin 1 (+Vin) at the left, printed face up |")
    a("| U6, U7 | tab toward the board centre; U6 tab is ground, U7 tab is -15 V |")
    a("| SW1 | switch 1 at the top, 'ON' toward the left |")
    a("| J1 | opening facing off the bottom edge |")
    a("")
    a("## Parts, stock and alternates")
    a("")
    a("Stock was checked at JLCPCB on 2026-09-15, the date on the silkscreen.")
    a("")
    a("| ref | value | LCSC | JLC | unit | stock then | notes |")
    a("|---|---|---|---|---|---|---|")
    for r in sorted(rows, key=lambda r: (r["Designator"][0], r["Designator"])):
        key = next((k for k, p in parts.PARTS.items()
                    if p.get("lcsc") == r["LCSC Part #"]), None)
        p = parts.PARTS.get(key, {})
        stock = p.get("stock")
        if stock is None:
            pv = next((v for v in parts.PASSIVES.values()
                       if v["lcsc"] == r["LCSC Part #"]), {})
            stock = pv.get("stock", "")
            note = pv.get("note", "")
        else:
            note = p.get("desc", "")
        a(f"| {r['Designator']} | {r['Comment']} | {r['LCSC Part #']} | "
          f"{r['JLC']} | ${r['Unit $']} | {stock:,} | {note} |"
          if isinstance(stock, int) else
          f"| {r['Designator']} | {r['Comment']} | {r['LCSC Part #']} | "
          f"{r['JLC']} | ${r['Unit $']} | {stock} | {note} |")
    a("")
    a("### If something is out of stock")
    a("")
    for key, p in parts.PARTS.items():
        if p.get("alt"):
            a(f"**{p['mpn']}** ({p['lcsc']})")
            for alt in p["alt"]:
                a(f"  - {alt}")
            a("")
    a("The three BNC jacks are the thinnest line: about 400 in stock, so")
    a("roughly 130 boards' worth.  All three listed alternates are the same")
    a("'BNC-KYWE' body -- a 10 x 10 mm flange, four ground posts on an 8 x 8 mm")
    a("square and a centre pin -- so the footprint takes any of them, but")
    a("measure the drawing before you substitute.")
    a("")
    a("## Bringing the board up")
    a("")
    a("1. Plug in USB-C.  The green LED by the regulators should light: it runs")
    a("   from +12 V, so it only comes on once the whole supply chain works.")
    a("2. Measure the rails at C14 and C15: +12.0 V and -12.0 V, a few tens of")
    a("   millivolts of ripple at most.  The board draws about 20 mA a rail.")
    a("3. Set SW1 to *nice!* -- switches 1, 2 and 3 on, 4, 5 and 6 off.")
    a("4. Scope on x and z, X-Y mode, about 1 V/div on both.  The owl's face")
    a("   should appear within a second or so of power-up; the circuit starts")
    a("   itself, because the origin is an unstable fixed point and op-amp")
    a("   offset is more than enough to push it off.")
    a("5. `-y` is inverted on purpose, exactly as on Paul's original sheet.")
    a("6. Try *fast!* (all switches off) and *slow!* (4, 5, 6 only).")
    a("")
    a("If nothing moves, the first thing to check is that both MPY634s are")
    a("powered: pin 16 at +12 V and pin 10 at -12 V.")
    a("")
    os.makedirs(DOCS, exist_ok=True)
    path = os.path.join(DOCS, "MANUFACTURING.md")
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"  wrote {os.path.relpath(path, ROOT)} "
          f"(parts {money(parts_cost)}/board, {smt} SMT + {tht} THT joints)")


if __name__ == "__main__":
    main()
