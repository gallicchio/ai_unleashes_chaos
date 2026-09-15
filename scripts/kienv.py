"""Locate the KiCad 10 toolchain and expose helpers for running it.

Finding the shared symbol and footprint libraries is the fiddly part: an
extracted AppImage may put them under `share/kicad` or `usr/share/kicad`, a
distribution package puts them under /usr/share, and macOS hides them inside
the bundle.  Rather than guess, this asks KiCad's own Python for the
`KICAD_STOCK_DATA_HOME` its launcher sets, and only falls back to searching if
that fails.
"""
import os, shutil, subprocess, sys

APPRUN_CANDIDATES = [
    os.path.expanduser("~/.local/kicad10/AppDir/AppRun"),
    os.path.expanduser("~/.local/kicad10/squashfs-root/AppRun"),
    os.path.expanduser("~/kicad10/AppDir/AppRun"),
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
_SHARE = None
_TRIED = []


def _looks_right(d):
    return bool(d) and os.path.isdir(os.path.join(d, "symbols")) \
        and os.path.isdir(os.path.join(d, "footprints"))


def _ask_kicad():
    """KiCad's launcher exports KICAD_STOCK_DATA_HOME; believe it."""
    code = ("import os,sys\n"
            "p = os.environ.get('KICAD_STOCK_DATA_HOME','')\n"
            "if not p:\n"
            "    import pcbnew\n"
            "    here = os.path.dirname(os.path.abspath(pcbnew.__file__))\n"
            "    for up in range(1, 10):\n"
            "        base = os.path.abspath(os.path.join(here, *(['..'] * up)))\n"
            "        for sub in ('share/kicad', 'usr/share/kicad'):\n"
            "            c = os.path.join(base, sub)\n"
            "            if os.path.isdir(os.path.join(c, 'symbols')):\n"
            "                p = c; break\n"
            "        if p: break\n"
            "sys.stdout.write(p)\n")
    for cmd in ([APPRUN, "python3.11", "-c", code] if APPRUN else [],
                [sys.executable, "-c", code]):
        if not cmd:
            continue
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        except Exception:
            continue
        d = (r.stdout or "").strip()
        _TRIED.append(f"asked KiCad's Python -> {d or '(nothing)'}")
        if _looks_right(d):
            return d
    return None


def share_dir():
    """Directory holding the stock symbol/footprint libraries."""
    global _SHARE
    if _SHARE:
        return _SHARE
    override = os.environ.get("KICAD_SHARE_DIR")
    if override:
        _TRIED.append(f"$KICAD_SHARE_DIR = {override}")
        if _looks_right(override):
            _SHARE = override
            return _SHARE

    cands = []
    if APPRUN:
        base = os.path.dirname(os.path.abspath(APPRUN))
        for up in range(0, 4):
            root = os.path.abspath(os.path.join(base, *([".."] * up)))
            cands += [os.path.join(root, "share", "kicad"),
                      os.path.join(root, "usr", "share", "kicad")]
    for v in ("KICAD10_SYMBOL_DIR", "KICAD9_SYMBOL_DIR", "KICAD_SYMBOL_DIR"):
        if os.environ.get(v):
            cands.append(os.path.dirname(os.environ[v]))
    cands += ["/usr/share/kicad", "/usr/local/share/kicad",
              os.path.expanduser("~/.local/share/kicad"),
              "/Applications/KiCad/KiCad.app/Contents/SharedSupport",
              "C:/Program Files/KiCad/10.0/share/kicad"]
    for c in cands:
        _TRIED.append(c)
        if _looks_right(c):
            _SHARE = c
            return _SHARE

    found = _ask_kicad()
    if found:
        _SHARE = found
        return _SHARE

    raise SystemExit(
        "Cannot locate KiCad's shared symbol and footprint libraries.\n"
        "Tried:\n  " + "\n  ".join(_TRIED) +
        "\n\nSet KICAD_SHARE_DIR to the directory that contains 'symbols' and\n"
        "'footprints' (inside an extracted AppImage that is usually\n"
        "<AppDir>/share/kicad or <AppDir>/usr/share/kicad).")


def cli(*args, check=True, capture=True, timeout=1800):
    """Run `kicad-cli <args>` with whichever KiCad we found."""
    if APPRUN:
        cmd = [APPRUN, "kicad-cli", *args]
    elif PLAIN_CLI:
        cmd = [PLAIN_CLI, *args]
    else:
        raise SystemExit(
            "KiCad 10 was not found.\n"
            "Install it so that `kicad-cli` is on PATH, or set KICAD_APPRUN to\n"
            "an extracted KiCad AppImage's AppRun -- see docs/MANUFACTURING.md.")
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


def describe():
    """One line per located piece, for the build banner."""
    out = [f"KiCad {version()}"]
    out.append(f"  runner    {APPRUN or PLAIN_CLI}")
    out.append(f"  libraries {share_dir()}")
    return "\n".join(out)
