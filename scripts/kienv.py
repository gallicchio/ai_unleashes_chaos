"""Locate the KiCad 10 toolchain and expose helpers for running it."""
import os, shutil, subprocess, sys

APPRUN_CANDIDATES = [
    os.path.expanduser("~/.local/kicad10/AppDir/AppRun"),
    os.path.expanduser("~/.local/kicad10/squashfs-root/AppRun"),
]
_ENV_APPRUN = os.environ.get("KICAD_APPRUN")
if _ENV_APPRUN:
    APPRUN_CANDIDATES.insert(0, _ENV_APPRUN)


def find_apprun():
    for c in APPRUN_CANDIDATES:
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return None


APPRUN = find_apprun()
PLAIN_CLI = shutil.which("kicad-cli")


def share_dir():
    """Directory holding the stock symbol/footprint libraries."""
    if APPRUN:
        d = os.path.join(os.path.dirname(APPRUN), "usr", "share", "kicad")
        if os.path.isdir(d):
            return d
    for d in ("/usr/share/kicad", "/usr/local/share/kicad"):
        if os.path.isdir(d):
            return d
    raise SystemExit("Cannot locate KiCad shared data (symbols/footprints).")


def cli(*args, check=True, capture=True, timeout=900):
    """Run `kicad-cli <args>` with whichever KiCad we found."""
    if APPRUN:
        cmd = [APPRUN, "kicad-cli", *args]
    elif PLAIN_CLI:
        cmd = [PLAIN_CLI, *args]
    else:
        raise SystemExit(
            "KiCad 10 not found.  Install it, or set KICAD_APPRUN to an extracted\n"
            "KiCad AppImage's AppRun (see docs/MANUFACTURING.md)."
        )
    r = subprocess.run(cmd, capture_output=capture, text=True, timeout=timeout)
    if check and r.returncode != 0:
        sys.stderr.write((r.stdout or "") + (r.stderr or ""))
        raise SystemExit(f"kicad-cli {' '.join(args)} failed ({r.returncode})")
    return r


def python(script, *args, check=True, timeout=1800):
    """Run a script under KiCad's bundled Python (the one with `pcbnew`)."""
    if APPRUN:
        cmd = [APPRUN, "python3.11", script, *args]
    else:
        cmd = [sys.executable, script, *args]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if check and r.returncode != 0:
        sys.stderr.write((r.stdout or "") + (r.stderr or ""))
        raise SystemExit(f"{os.path.basename(script)} failed ({r.returncode})")
    return r


def version():
    return cli("--version").stdout.strip()
