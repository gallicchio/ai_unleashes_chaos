#!/usr/bin/env python3
"""Build everything: symbols, footprints, schematic, both PCBs and the fab package.

    ./make.py              build and check everything
    ./make.py --quick      skip the self-tests
    ./make.py --stage sch  run one stage only (libs, sch, pcb2, out, docs)
    ./make.py --clean      delete everything the build generates

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

# One board.  The four-layer experiment is gone: measured on the routed
# two-layer board, tracks cover 1.2 % of the back copper, so the pour there is
# already 98.8 % of an unbroken ground plane and a dedicated plane layer buys
# almost nothing at four times the bare-board price.  See docs/DESIGN_REVIEW.md.
BOARDS = [("lorenz", 2)]

# Everything ./make.py writes.  Kept explicit rather than inferred so that
# --clean doubles as the answer to "what in this repository is generated and
# what has to live in git?"  Paths are relative to the repository root; a
# trailing / means the whole directory.
GENERATED = [
    "hardware/lorenz.kicad_sch", "hardware/lorenz.kicad_pcb",
    "hardware/lorenz.kicad_pro",
    "hardware/sym-lib-table", "hardware/fp-lib-table",
    "hardware/lib/lorenz.kicad_sym",
    "hardware/lib/lorenz.pretty/", "hardware/lib/lorenz.3dshapes/",
    "docs/images/", "docs/MANUFACTURING.md",
    "out/",
]
# Written by KiCad itself while you have the project open, never by the build.
ALSO_TRANSIENT = ["hardware/lorenz.kicad_prl", "hardware/fp-info-cache"]


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
    run = kienv.runner()
    if run:
        cmd = [run, "python3.11", os.path.join(SCRIPTS, script), *args]
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
    sys_py("gen_models.py")
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
    out = sys_py("check_schematic.py", sch)
    if "no text overlaps" not in out:
        raise Fail("the schematic sheet has overlapping or stray text")


def stage_pcb(stem, layers):
    banner(f"PCB: {stem} ({layers} layers)")
    pcb = os.path.join(HW, stem + ".kicad_pcb")
    net = os.path.join(OUT, "lorenz.net")
    kicad_py("gen_pcb.py", str(layers), net, pcb)
    sys_py("route.py", str(layers))
    out = kicad_py("gen_pcb.py", str(layers), net, pcb,
                   env={"LORENZ_STAGE": "route"})
    if "had nowhere to go" in out:
        raise Fail("some silkscreen could not be placed")
    # Saving a board through pcbnew rewrites the project file next to it with
    # a default set of design rules, so DRC has to be handed the real ones
    # back before it runs.  Without this the whole "stricter than every fab"
    # claim is checked against KiCad's defaults instead.
    sys_py("gen_project.py")
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


def stage_project():
    """Rewrite the project file last.

    Saving a board through pcbnew rewrites the .kicad_pro alongside it and
    drops the root-sheet entry, which is what links the project to the
    schematic for cross-probing.  Regenerating it here is simpler than trying
    to stop pcbnew touching it.
    """
    banner("project files")
    sys_py("gen_project.py")


def stage_selftest():
    banner("self-tests")
    sys_py("selftest_rotation.py")
    sys_py("qrcode_gen.py")
    sys_py("lamp_model.py")
    sys_py("check_pinout.py")


def clean():
    banner("clean")
    removed = kept = 0
    # Do not disturb KiCad's own per-user state while it has the project open.
    locked = any(n.startswith("~") and n.endswith(".lck")
                 for n in os.listdir(os.path.join(ROOT, "hardware")))
    targets = GENERATED + ([] if locked else ALSO_TRANSIENT)
    if locked:
        print("  KiCad has the project open; leaving its .kicad_prl state alone")
    for rel in targets:
        path = os.path.join(ROOT, rel.rstrip("/"))
        if rel.endswith("/"):
            if os.path.isdir(path):
                n = sum(len(f) for _, _, f in os.walk(path))
                shutil.rmtree(path)
                print(f"  removed {rel} ({n} file(s))")
                removed += n
            else:
                kept += 1
        elif os.path.exists(path):
            os.remove(path)
            print(f"  removed {rel}")
            removed += 1
        else:
            kept += 1
    for name in os.listdir(os.path.join(ROOT, "hardware")):
        if name.startswith("~") and name.endswith(".lck"):
            print(f"  left alone hardware/{name} (KiCad has the project open)")
    print(f"\n{removed} generated file(s) removed"
          + (f", {kept} were already absent" if kept else "")
          + ".\nEverything else in the repository is source: scripts/, docs/*.md,\n"
          "README.md, CLAUDE_CODE_CHAT.md, LICENSE, .gitignore and the\n"
          "docs/history/ and docs/lamp/ pictures.  ./make.py rebuilds the rest.")
    return 0


STAGES = {
    "libs": stage_libs,
    "project": stage_project,
    "sch": stage_sch,
    "pcb2": lambda: stage_pcb(*BOARDS[0]),
    "out": stage_out,
    "docs": stage_docs,
    "selftest": stage_selftest,
}
ORDER = ["libs", "sch", "pcb2", "out", "docs", "project"]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage", choices=sorted(STAGES))
    ap.add_argument("--quick", action="store_true",
                    help="skip the self-tests")
    ap.add_argument("--clean", action="store_true",
                    help="delete everything the build generates, then stop")
    a = ap.parse_args()

    if a.clean:
        return clean()

    if not kienv.have_kicad():
        print("KiCad 10 was not found.\n"
              "Install it so that `kicad-cli` is on PATH, or point\n"
              "KICAD_APPIMAGE at a KiCad 10 .AppImage (an extracted one works\n"
              "too: KICAD_APPRUN=<AppDir>/AppRun) -- see docs/MANUFACTURING.md.")
        return 2
    print(kienv.describe())

    t0 = time.time()
    try:
        if a.stage:
            STAGES[a.stage]()
        else:
            # The self-tests check the generated symbol and footprint
            # libraries against the data sheets, so they run straight after
            # the stage that writes them -- which is what lets a tree that has
            # just been --cleaned build in one go.
            order = list(ORDER)
            if not a.quick:
                order.insert(1, "selftest")
            for name in order:
                STAGES[name]()
    except Fail as e:
        print(f"\nBUILD FAILED: {e}")
        return 1
    print(f"\nBUILD OK in {time.time() - t0:.0f} s. "
          f"Upload out/<board>/<board>-gerbers.zip, -bom.csv and -cpl.csv.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
