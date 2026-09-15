#!/usr/bin/env python3
"""Build everything: symbols, footprints, schematic, both PCBs and the fab package.

    ./make.py              build and check everything
    ./make.py --quick      skip the self-tests
    ./make.py --stage sch  run one stage only (libs, sch, pcb2, pcb4, out, docs)

Every stage that can be checked is checked, and the build stops at the first
failure, so a green run means the files in out/ can go straight to a fab.
"""
import argparse, os, shutil, subprocess, sys, time

ROOT = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(ROOT, "scripts")
HW = os.path.join(ROOT, "hardware")
OUT = os.path.join(ROOT, "out")
sys.path.insert(0, SCRIPTS)
import kienv                                     # noqa: E402

BOARDS = [("lorenz", 2), ("lorenz-4layer", 4)]


class Fail(Exception):
    pass


def banner(txt):
    print(f"\n=== {txt} " + "=" * max(0, 64 - len(txt)))


def sys_py(script, *args):
    r = subprocess.run([sys.executable, os.path.join(SCRIPTS, script), *args],
                       capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    if r.returncode:
        sys.stdout.write(r.stderr)
        raise Fail(f"{script} failed")
    return r.stdout


def kicad_py(script, *args, env=None):
    e = dict(os.environ)
    e.update(env or {})
    if kienv.APPRUN:
        cmd = [kienv.APPRUN, "python3.11", os.path.join(SCRIPTS, script), *args]
    else:
        cmd = [sys.executable, os.path.join(SCRIPTS, script), *args]
    r = subprocess.run(cmd, capture_output=True, text=True, env=e)
    sys.stdout.write(r.stdout)
    if r.returncode:
        sys.stdout.write(r.stderr)
        raise Fail(f"{script} failed")
    return r.stdout


def count_violations(path):
    n = 0
    with open(path) as fh:
        for line in fh:
            if line.startswith("["):
                n += 1
    return n


def stage_libs():
    banner("symbol and footprint libraries")
    sys_py("gen_footprints.py")
    sys_py("gen_symbols.py")
    kienv.cli("sym", "upgrade", os.path.join(HW, "lib", "lorenz.kicad_sym"),
              "--force")
    kienv.cli("fp", "upgrade", os.path.join(HW, "lib", "lorenz.pretty"), "--force")
    sys_py("gen_project.py")
    print("  libraries upgraded to the installed KiCad format")


def stage_sch():
    banner("schematic")
    sys_py("gen_sch.py")
    sch = os.path.join(HW, "lorenz.kicad_sch")
    kienv.cli("sch", "upgrade", sch)
    os.makedirs(OUT, exist_ok=True)
    rpt = os.path.join(OUT, "erc.rpt")
    kienv.cli("sch", "erc", "--format", "report", "--severity-all",
              "-o", rpt, sch, check=False)
    n = count_violations(rpt)
    print(f"  ERC: {n} violation(s)")
    if n:
        raise Fail(f"ERC reported {n} violations -- see {os.path.relpath(rpt, ROOT)}")
    net = os.path.join(OUT, "lorenz.net")
    kienv.cli("sch", "export", "netlist", "--format", "kicadsexpr", "-o", net, sch)
    out = sys_py("check_circuit.py", net)
    if "all circuit checks passed" not in out:
        raise Fail("the netlist does not implement the Lorenz equations")
    # the four-layer variant shares the schematic; keep the copy in step
    shutil.copyfile(sch, os.path.join(HW, "lorenz-4layer.kicad_sch"))


def stage_pcb(stem, layers):
    banner(f"PCB: {stem} ({layers} layers)")
    pcb = os.path.join(HW, stem + ".kicad_pcb")
    net = os.path.join(OUT, "lorenz.net")
    kicad_py("gen_pcb.py", str(layers), net, pcb)
    sys_py("route.py", str(layers))
    kicad_py("gen_pcb.py", str(layers), net, pcb, env={"LORENZ_STAGE": "route"})
    rpt = os.path.join(OUT, f"drc-{stem}.rpt")
    kienv.cli("pcb", "drc", "--format", "report", "--severity-all",
              "--schematic-parity", "-o", rpt, pcb, check=False)
    n = count_violations(rpt)
    print(f"  DRC: {n} violation(s)")
    if n:
        raise Fail(f"DRC reported {n} violations -- see {os.path.relpath(rpt, ROOT)}")


def stage_out():
    banner("manufacturing outputs")
    sys_py("gen_outputs.py")
    out = sys_py("check_outputs.py")
    if "ALL FAB CHECKS PASSED" not in out:
        raise Fail("the fab package did not pass its checks")


def stage_docs():
    banner("documentation")
    sys_py("gen_docs.py")


def stage_selftest():
    banner("self-tests")
    sys_py("selftest_rotation.py")


STAGES = {
    "libs": stage_libs,
    "sch": stage_sch,
    "pcb2": lambda: stage_pcb(*BOARDS[0]),
    "pcb4": lambda: stage_pcb(*BOARDS[1]),
    "out": stage_out,
    "docs": stage_docs,
    "selftest": stage_selftest,
}
ORDER = ["libs", "sch", "pcb2", "pcb4", "out", "docs"]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage", choices=sorted(STAGES))
    ap.add_argument("--quick", action="store_true",
                    help="skip the self-tests")
    a = ap.parse_args()

    if kienv.APPRUN is None and kienv.PLAIN_CLI is None:
        print("KiCad 10 was not found.\n"
              "Install it, or point KICAD_APPRUN at an extracted KiCad\n"
              "AppImage's AppRun -- see docs/MANUFACTURING.md.")
        return 2
    print(f"KiCad {kienv.version()}")

    t0 = time.time()
    try:
        if a.stage:
            STAGES[a.stage]()
        else:
            if not a.quick:
                stage_selftest()
            for name in ORDER:
                STAGES[name]()
    except Fail as e:
        print(f"\nBUILD FAILED: {e}")
        return 1
    print(f"\nBUILD OK in {time.time() - t0:.0f} s. "
          f"Upload out/<board>/<board>-gerbers.zip, -bom.csv and -cpl.csv.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
