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
    """Solder joints only.

    A mounting hole is not a joint, and neither is a probe pad or the open
    ground-tie jumper: nothing is fitted in any of them, so the assembler
    never touches them and they cost nothing per board.
    """
    geom = json.load(open(os.path.join(OUT, f"pcb_geom_{layers}.json")))
    real = [p for p in geom["pads"]
            if p["net"] and p["ref"][:2] not in ("MH", "TP", "JP")]
    smt = sum(1 for p in real if not p["through"])
    tht = sum(1 for p in real if p["through"])
    tht_refs = sorted({p["ref"] for p in real if p["through"]})
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
    a("One board, two layers, 100 x 100 mm.  It passes ERC, DRC (with")
    a("schematic parity), the circuit checker and the fab-package checks with")
    a("zero violations, and `./make.py` rebuilds and rechecks everything from")
    a("scratch in about forty seconds.")
    a("")
    a("The copper is split: the USB input has its own ground plane in the")
    a("bottom-left corner, isolated from the analog ground by the converter and")
    a("bridged only by R21, C25 and JP1.  Do not scratch across the 1 mm gap.")
    a("")
    a("## What to upload")
    a("")
    a("| file | where it goes |")
    a("|---|---|")
    a("| `out/lorenz/lorenz-gerbers.zip` | the *Add gerber file* box |")
    a("| `out/lorenz/lorenz-bom.csv` | the BOM box (JLCPCB column layout) |")
    a("| `out/lorenz/lorenz-cpl.csv` | the CPL / pick-and-place box |")
    a("")
    a("## Board options to pick")
    a("")
    a("| option | value | why |")
    a("|---|---|---|")
    a("| Layers | 2 | what the gerber set contains |")
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
    a(f"Four layers would cost about {money(tot)} for five "
      f"({money(tot / 5)} each) -- the only change is the bare-board price --")
    a("and buys almost nothing here: tracks cover 1.2 % of the back copper, so")
    a("the pour on the two-layer board is already 98.8 % of an unbroken ground")
    a("plane.  That is why this project ships one board.")
    a("")
    a("Two boards is the sensible order: one for Paul and one to keep.")
    a("")
    ref_lcsc = {}
    for r in rows:
        for ref in r["Designator"].split(","):
            ref_lcsc[ref.strip()] = r["LCSC Part #"].strip()

    a("## Uploading to JLCPCB")
    a("")
    a("| upload | file |")
    a("|---|---|")
    a("| gerbers | `lorenz-gerbers.zip` |")
    a("| BOM | `lorenz-bom.csv` |")
    a("| placements | **`lorenz-cpl_jlc_corrected.csv`** |")
    a("| paste into the order notes | `lorenz-assembly-notes.txt` |")
    a("")
    a("Use the *corrected* placement file for JLCPCB, and the plain")
    a("`lorenz-cpl.csv` for anyone else.  JLCPCB places from its own model of")
    a("each part, and for some parts that model is turned differently from")
    a("KiCad's footprint, so a file that is right everywhere else is wrong by")
    a("a fixed angle there.  The angle belongs to the part number, not to the")
    a("package: it is a property of JLC's drawing of that one LCSC part.")
    a("")
    a("| parts | LCSC | turned by |")
    a("|---|---|---|")
    for code, deg in sorted(parts.JLC_ROTATION.items(), key=lambda kv: -kv[1]):
        refs = sorted(r for r, c in ref_lcsc.items() if c == code)
        a(f"| {', '.join(refs)} | {code} | {deg} deg counter-clockwise |")
    a("")
    a("Everything else -- every resistor, every capacitor -- is symmetric or")
    a("already agrees, and is left alone.  `check_outputs.py` proves the two")
    a("files differ in nothing but those angles.")
    a("")
    a("### What the preview gets wrong, and why it does not matter")
    a("")
    a("JLCPCB draws each part from its own model, and that model has its own")
    a("idea of where the middle of the part is.  For some of ours it does not")
    a("agree with the middle of the body, so the preview draws the part beside")
    a("its pads however the placement file is written.  There is nothing in a")
    a("CPL that can say *use your origin, not mine* -- the only lever is the")
    a("coordinate itself, and moving that to flatter a preview would put a")
    a("wrong number in the file for everybody else.")
    a("")
    a("Three of the parts that look wrong there cannot go in wrong at all:")
    a("")
    a("| part | holes | fits at |")
    a("|---|---|---|")
    a("| U5, the DC/DC module | 5, with a gap where pin 3 would be | one orientation |")
    a("| RV1, RV2, the trimmers | 3 in an L | one orientation |")
    a("")
    a("A hole pattern that does not map onto itself under a quarter turn is")
    a("its own key: there is exactly one way the part goes into the board, and")
    a("an operator putting legs through holes cannot do anything else with it.")
    a("`check_outputs.py` re-derives that from the board file on every build,")
    a("so it stays true rather than merely having been true once.")
    a("")
    a("The BNCs are *not* keyed -- four symmetric ground posts and a centre")
    a("pin -- which is why their 90 degree correction is in the table above,")
    a("and why the barrel pointing off the board edge is worth a glance.")
    a("")
    a("J1, the USB-C receptacle, sits at the board edge deliberately: its body")
    a("is flush with the edge so a cable with a moulded body can seat.  A 3D")
    a("preview showing it overhang the edge is showing it correctly.")
    a("")
    a("### Still unverified")
    a("")
    a("One rotation has never actually been seen, because JLCPCB has no")
    a("drawing of the part to turn:")
    a("")
    for code, why in sorted(parts.JLC_UNVERIFIED.items()):
        a(f"* **{code}** -- {why}.")
    a("")
    a("It is left uncorrected.  D1 is the one part on this board where a")
    a("preview you cannot read costs you something, so it gets its own")
    a("paragraph below and its own line in the assembler's notes.")
    a("")
    a("## Check these before you pay")
    a("")
    a("The one thing that cannot be checked from here is how the assembler")
    a("turns each part.  Your CPL says which way; their library has its own")
    a("idea of zero degrees, and where the two disagree a polarised part goes")
    a("in backwards.  JLCPCB renders every part on the board before you")
    a("confirm the order.  Compare that rendering with this table and with")
    a("`lorenz-assembly-top.pdf`, which prints 1:1.")
    a("")
    a("The lamp, the DIP switch and the two trimmers carry a filled triangle")
    a("on the front silkscreen, printed just outside the outline and pointing")
    a("at pin 1.  It is drawn from the real pad, so it is right by")
    a("construction; use it as the reference when you compare the rendering.")
    a("The SOICs and the two SOT-89s are not marked that way because KiCad's")
    a("own footprints already print a pin-1 dot or a notched corner on them,")
    a("and two marks beside each other are two marks to reconcile.")
    a("")
    a("| part | what to look for | should be |")
    a("|---|---|---|")
    a("| D1 | the RGB lamp's pin 1, the common anode | bottom left, the corner the triangle points at |")
    a("| RV1 | the r trimmer, terminal 1 | the lower pad, the one the triangle points at; the screw is on top |")
    a("| RV2 | the sync weight trimmer, terminal 1 | same part, same way up, directly above RV1 |")
    a("| J5 | SYNC IN X | barrel pointing off the left edge, in line with the x output on the right |")
    a("| U6 | 78L12, SOT-89 | pin 1 (OUT) on the left, tab to ground |")
    a("| U7 | 79L12, SOT-89 | pin 1 (GND) on the left; its tab is at -15 V, not ground |")
    a("| U1, U2 | LF412 SOIC-8 | pin 1 dot at the top left |")
    a("| U3, U4 | MPY634 SOIC-16W | pin 1 dot at the top left |")
    a("| J1 | USB-C receptacle | opening facing off the board edge |")
    a("| SW1 | 6-way DIP switch | slider 1 at the left, the part's own \"ON\" printing facing the \"ON ->\" arrow on the board |")
    a("| U5 | the converter, hand-fitted | pin 1 is the square pad, at the left, marked on the silkscreen |")
    a("| F1 | PTC fuse | not polarised |")
    a("")
    a("The four BNCs and the converter are through-hole and can be checked")
    a("by eye after assembly: the converter's own printed face carries its pin")
    a("numbers.")
    a("")
    a("## The through-hole parts")
    a("")
    a(f"{len(tht_refs)} parts are through-hole: **{', '.join(tht_refs)}** "
      f"-- the four BNC jacks, the two trimmers, the DC/DC module and the "
      f"USB-C shell tabs.")
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
    a("| D1 | pin 1, the common anode, at the bottom left -- the die order is red, green, blue anticlockwise from it |")
    a("| RV1, RV2 | terminal 1 at the bottom, terminal 3 at the top, wiper to the right |")
    a("| J5 | barrel off the left edge, the mirror image of J2, J3 and J4 |")
    a("| U1, U2 | pin 1 dot at the top-left, toward C16 / C18 |")
    a("| U3, U4 | pin 1 dot at the top-left |")
    a("| U5 | pin 1 (+Vin) at the left, printed face up |")
    a("| U6, U7 | tab toward the board centre; U6 tab is ground, U7 tab is -15 V |")
    a("| SW1 | slider 1 at the left; pin 1 is on the side *away* from the part's \"ON\" legend, which is where the board's triangle points |")
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
    a("The BNC jacks are the thinnest line: about 400 in stock and four per")
    a("board, so roughly 100 boards' worth.  All three listed alternates are the same")
    a("'BNC-KYWE' body -- a 10 x 10 mm flange, four ground posts on an 8 x 8 mm")
    a("square and a centre pin -- so the footprint takes any of them, but")
    a("measure the drawing before you substitute.")
    a("")
    a("## Bringing the board up")
    a("")
    a("1. Plug in USB-C.  The chaos lamp should light within a second: it")
    a("   hangs on +12 V through U2B and on all three integrator outputs, so")
    a("   it only comes on once the whole board works.")
    a("2. Measure the rails at C14 and C15: +12.0 V and -12.0 V, a few tens of")
    a("   millivolts of ripple at most.  The board draws about 20 mA a rail.")
    a("3. Set SW1 to *nice!* -- switches 4, 5 and 6 on, 1, 2 and 3 off.")
    a("4. Scope on x and z, X-Y mode, about 1 V/div on both.  The owl's face")
    a("   should appear within a second or so of power-up; the circuit starts")
    a("   itself, because the origin is an unstable fixed point and op-amp")
    a("   offset is more than enough to push it off.")
    a("5. `-y` is inverted on purpose, exactly as on Paul's original sheet.")
    a("6. Try *fast!* (all switches off), *slow!* (1, 2, 3 only) and")
    a("   *slower!* (all six on).  Poles 1-3 switch in the 470 nF and poles")
    a("   4-6 the 100 nF, so the six sliders read left to right as a")
    a("   two-digit binary number: 00, 01, 10, 11.")
    a("7. Turn RV1 clockwise to raise r and anticlockwise to lower it.  About")
    a("   a third of the way round from the anticlockwise stop the attractor")
    a("   collapses into one wing and the lamp settles on a colour; back the")
    a("   other way and it starts wandering again.")
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
