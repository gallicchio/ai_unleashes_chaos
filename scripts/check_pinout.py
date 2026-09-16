#!/usr/bin/env python3
"""Check every IC's pin assignment against the datasheet and a second source.

A pin table copied wrongly is the kind of mistake that survives ERC, DRC,
parity and every other check in this project, and then arrives as a board that
does not work.  So each one is written out here from the datasheet named
beside it, checked against the symbol this project actually uses, and -- where
somebody else has published the same part -- checked again against KiCad's own
library, which was drawn by different people from the same document.

    python3 scripts/check_pinout.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kienv
from sexp_parse import parse_file

HERE = os.path.dirname(os.path.abspath(__file__))
LOCAL_SYM = os.path.join(HERE, "..", "hardware", "lib", "lorenz.kicad_sym")
LOCAL_FP = os.path.join(HERE, "..", "hardware", "lib", "lorenz.pretty")

# ---------------------------------------------------------------- sources --
# number -> name, transcribed from the document named in the comment.
DATASHEET = {
    # TI MPY634 (SBFS017A), "PIN CONFIGURATIONS / Top View", SOIC 'KU'
    "MPY634": ({1: "X1", 2: "X2", 3: "NC", 4: "SF", 5: "NC", 6: "Y1", 7: "Y2",
                8: "NC", 9: "NC", 10: "V-", 11: "NC", 12: "Z2", 13: "Z1",
                14: "W", 15: "NC", 16: "V+"},
               "Analog:MPY634KU",
               {1: "X_{1}", 2: "X_{2}", 3: "NC", 4: "SF", 5: "NC",
                6: "Y_{1}", 7: "Y_{2}", 8: "NC", 9: "NC", 10: "-V_{S}",
                11: "NC", 12: "Z_{2}", 13: "Z_{1}", 14: "V_{O}", 15: "NC",
                16: "+V_{S}"}),
    # TI LF412 (SLOS091), SOIC-8 -- the universal dual op-amp pinout
    "LF412": ({1: "", 2: "-", 3: "+", 4: "V-", 5: "+", 6: "-", 7: "", 8: "V+"},
              "Amplifier_Operational:LM2904",   # what TL072 extends
              {1: "", 2: "-", 3: "+", 4: "V-", 5: "+", 6: "-", 7: "",
               8: "V+"}),
    # YLPTEC A0515S-2WR2, pin table: 1 Vin, 2 GND, 4 -Vo, 5 0V, 6 +Vo
    # ("双路" = dual output column); pin 3 is absent from the package.
    "DCDC_A0515S": ({1: "+Vin", 2: "-Vin", 4: "-Vout", 5: "COM", 6: "+Vout"},
                    None, None),
    # MEIHUA MHPA3528CRGBCT (LPDS-0001481 Rev.1 p.2, "Polarity"): common
    # anode on 1, cathodes 2 blue, 3 green, 4 red.  The common-cathode
    # MHPC3528CRGBCT in the same package is 1 red, 2 blue, 3 green, 4 cathode
    # -- the same dies, but 1 and 4 change places, so the boards differ.
    "LED_RGB_CA": ({1: "A", 2: "B", 3: "G", 4: "R"}, None, None),
}

# Parts used straight from KiCad's library: the datasheet is checked against
# the stock symbol rather than against one drawn here.
STOCK = {
    # CJ78L12 SOT-89 outline drawing: 1 OUT, 2 GND, 3 IN.  L78L12_SOT89
    # extends MC78L05_SOT89, which is where the pins live.
    "Regulator_Linear:MC78L05_SOT89": {1: "OUT", 2: "GND", 3: "IN"},
    # CJ79L12 SOT-89 outline drawing: 1 GND, 2 IN, 3 OUT
    "Regulator_Linear:L79L05_SOT89": {1: "GND", 2: "VI", 3: "VO"},
}

# Footprints must offer exactly the pads the symbol drives.
FOOTPRINT_PINS = {
    "lorenz:DCDC_SIP_A05xxS_1W_2W": {"1", "2", "4", "5", "6"},
    "lorenz:LED_RGB_PLCC4_3.5x2.8mm": {"1", "2", "3", "4"},
    "lorenz:SW_DIP_SPSTx06_KingTek_DSIC06_P2.54mm":
        {str(i) for i in range(1, 13)},
    "lorenz:TestPoint_ScopeGnd_Loop_2x1.1mm": {"1"},
    "lorenz:PTC_1812_4532Metric": {"1", "2"},
    # Bourns 3386 datasheet, "3386P" outline: 1 CCW, 2 wiper, 3 CW.
    "lorenz:Potentiometer_Bourns_3386P_Vertical": {"1", "2", "3"},
    "lorenz:BNC_KYWE_RightAngle": {"1", "2"},
}


def sym_pins(lib_path, name):
    """number -> name for every pin of a symbol, across all its units."""
    root = parse_file(lib_path)
    out = {}
    for sym in root.kids("symbol"):
        if sym.atom(0) != name:
            continue
        for unit in sym.kids("symbol"):
            for pin in unit.kids("pin"):
                out[pin.first("number").atom(0)] = pin.first("name").atom(0)
    if not out:
        raise SystemExit(f"symbol {name} not found in {lib_path}")
    return out


def fp_pads(path):
    root = parse_file(path)
    return {p.atom(0) for p in root.kids("pad") if p.atom(0)}


def main():
    share = kienv.share_dir()
    problems, notes = [], []

    def need(cond, msg):
        (notes if cond else problems).append(("ok " if cond else "FAIL")
                                             + "  " + msg)

    for name, (sheet, stock_id, stock_pins) in DATASHEET.items():
        mine = sym_pins(LOCAL_SYM, name)
        need({int(k): v for k, v in mine.items()} == sheet,
             f"{name}: {len(sheet)} pins match the datasheet")
        if stock_id:
            lib, sym = stock_id.split(":")
            path = os.path.join(share, "symbols", lib + ".kicad_symdir",
                                sym + ".kicad_sym")
            got = {int(k): v for k, v in sym_pins(path, sym).items()}
            need(got == stock_pins,
                 f"{name}: and KiCad's own {stock_id} agrees, pin for pin")

    for sym_id, sheet in STOCK.items():
        lib, sym = sym_id.split(":")
        path = os.path.join(share, "symbols", lib + ".kicad_symdir",
                            sym + ".kicad_sym")
        if not os.path.exists(path):      # the extended base lives elsewhere
            import glob
            hits = [f for f in glob.glob(os.path.join(
                share, "symbols", lib + ".kicad_symdir", "*.kicad_sym"))
                if f'(symbol "{sym}"' in open(f).read()]
            path = hits[0] if hits else path
        got = {int(k): v for k, v in sym_pins(path, sym).items()}
        need(got == sheet, f"{sym_id}: matches the SOT-89 outline drawing")

    for fpid, want in FOOTPRINT_PINS.items():
        lib, name = fpid.split(":")
        path = (os.path.join(LOCAL_FP, name + ".kicad_mod") if lib == "lorenz"
                else os.path.join(share, "footprints", lib + ".pretty",
                                  name + ".kicad_mod"))
        got = fp_pads(path)
        need(got == want,
             f"{fpid}: pads {sorted(want, key=lambda s: int(s))} all present")

    print("\n".join(notes))
    if problems:
        print()
        print("\n".join(problems))
        print(f"\n{len(problems)} pinout check(s) FAILED")
        return 1
    print(f"\nall {len(notes)} pinout checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
