#!/usr/bin/env python3
"""Check schlib's library-space -> sheet-space pin mapping against KiCad itself.

Places a resistor at each of the four rotations, drops a uniquely named label on
each computed pin location, then asks kicad-cli for the netlist.  If the mapping
is right, every label's net contains exactly the pin it was placed on.
"""
import os, re, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kienv
from schlib import Sheet
from sexp_parse import parse_file


def main():
    tmp = tempfile.mkdtemp(prefix="rotcheck-")
    sch = Sheet(kienv.share_dir(), paper="A2", title="rotation check")
    expect = {}
    # An asymmetric symbol is needed: a resistor's pins sit on x = 0, so a
    # mirror about the vertical axis would move nothing and prove nothing.
    # A stock symbol, so that this test depends on nothing the build generates.
    cases = [(r, m) for r in (0, 90, 180, 270) for m in (None, "x", "y")]
    for i, (rot, mir) in enumerate(cases):
        x, y = 40.0 + (i % 4) * 60, 45.0 + (i // 4) * 55
        ref = f"U{i+1}"
        sch.place("Amplifier_Operational:LM2904", ref, "LM2904", x, y,
                  rot=rot, mirror=mir, unit=1)
        for pin_no in ("1", "2", "3"):
            px, py = sch.pin(ref, 1, pin_no)
            name = f"N{rot}{mir or 'n'}P{pin_no}"
            sch.label(name, px, py)
            expect[name] = f"{ref}-{pin_no}"
    path = os.path.join(tmp, "rot.kicad_sch")
    sch.write(path)
    kienv.cli("sch", "upgrade", path)
    netlist = os.path.join(tmp, "rot.net")
    kienv.cli("sch", "export", "netlist", "--format", "kicadsexpr",
              "-o", netlist, path)

    root = parse_file(netlist)
    nets = {}
    for net in root.first("nets").kids("net"):
        nm = net.first("name").atom(0).lstrip("/")
        nodes = [f'{nd.first("ref").atom(0)}-{nd.first("pin").atom(0)}'
                 for nd in net.kids("node")]
        nets[nm] = sorted(nodes)

    bad = []
    for name, want in expect.items():
        got = nets.get(name)
        if got != [want]:
            bad.append(f"  {name}: expected [{want}], got {got}")
    if bad:
        print("ROTATION MAPPING WRONG:")
        print("\n".join(bad))
        print("\nall nets:", {k: v for k, v in nets.items()})
        return 1
    print(f"pin mapping OK across rotations and mirrors ({len(expect)} pins checked)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
