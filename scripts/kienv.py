"""Locate the KiCad 10 toolchain and expose helpers for running it.

Finding the shared symbol and footprint libraries is the fiddly part.  An
extracted AppImage may put them under `share/kicad` or `usr/share/kicad`; a
distribution package puts them under /usr/share; macOS hides them inside the
bundle; and a *plain* AppImage keeps them inside its own squashfs, where they
only exist while the image is mounted.  This module handles all four, mounting
the AppImage itself if that is all it can find and keeping it mounted for as
long as the build runs.

The one thing it will not do is believe a directory just because it is called
"symbols".  `~/.local/share/kicad/10.0/symbols` exists on any machine where
KiCad has ever run and is normally *empty*: it is where your own libraries go,
not where KiCad's are.  Pointing the build at it fails later, deep inside a
symbol lookup, which is a bad place to learn about it -- so a candidate is
only accepted if a known stock library is actually in it.
"""
import atexit, glob, os, re, select, shutil, subprocess, sys

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


# Where a plain (unextracted) AppImage might be sitting.  KiCad 10 first: a
# machine that has kept its old KiCad 9 AppImage would otherwise build against
# the wrong libraries and fail a long way from here.
APPIMAGE_DIRS = ["~/.local/bin", "~/Downloads", "~/Applications", "~/bin",
                 "~/.local/opt", "/opt"]


def find_appimages():
    out = []
    env = os.environ.get("KICAD_APPIMAGE")
    if env:
        out.append(os.path.expanduser(env))
    for d in APPIMAGE_DIRS:
        out += sorted(glob.glob(os.path.join(os.path.expanduser(d),
                                             "[Kk]icad*.[Aa]pp[Ii]mage")))
    out = [p for p in out if os.path.isfile(p) and os.access(p, os.X_OK)]
    ten = [p for p in out if re.search(r"kicad[-_]?10[.\-_]",
                                       os.path.basename(p), re.I)]
    return ten + [p for p in out if p not in ten]


APPRUN = find_apprun()
PLAIN_CLI = shutil.which("kicad-cli")
_SHARE = None
_TRIED = []
_MOUNT = None            # the --appimage-mount process, kept alive on purpose
_MOUNTED = None          # which .AppImage that process has open


def _mount_appimage(img, wait=30.0):
    """Mount a plain AppImage and return its mount point.

    `--appimage-mount` prints the mount point on stdout and holds the mount
    open until it is killed, so the process is kept for the life of this one
    and torn down by atexit.  The mount point is exported to the environment
    as well, so the scripts this build shells out to share it instead of each
    mounting its own copy.
    """
    global _MOUNT
    try:
        p = subprocess.Popen([img, "--appimage-mount"],
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             text=True)
    except OSError as e:
        _TRIED.append(f"{img}: cannot run ({e})")
        return None
    ready, _, _ = select.select([p.stdout], [], [], wait)
    point = p.stdout.readline().strip() if ready else ""
    if not point or not os.path.isdir(point):
        _TRIED.append(f"{img}: --appimage-mount gave nothing usable")
        p.terminate()
        return None
    _MOUNT = p
    atexit.register(_unmount)
    return point


def _unmount():
    global _MOUNT
    if _MOUNT is not None:
        _MOUNT.terminate()
        try:
            _MOUNT.wait(timeout=10)
        except Exception:
            _MOUNT.kill()
        _MOUNT = None


def _use_appimage():
    """Last resort: mount an AppImage and adopt what is inside it."""
    global APPRUN
    for img in find_appimages():
        point = _mount_appimage(img)
        if not point:
            continue
        run = os.path.join(point, "AppRun")
        share = next((d for d in (os.path.join(point, "usr", "share", "kicad"),
                                  os.path.join(point, "share", "kicad"))
                      if _looks_right(d)), None)
        if os.access(run, os.X_OK) and share:
            global _MOUNTED
            APPRUN = run
            _MOUNTED = img
            # children of this process inherit the same mount
            os.environ["KICAD_APPRUN"] = run
            os.environ["KICAD_SHARE_DIR"] = share
            _TRIED.append(f"mounted {img} -> {share}")
            return share
        _TRIED.append(f"{img}: mounted at {point}, but no libraries in it")
        _unmount()
    return None


# A directory is only the stock library tree if a stock library is in it.
# Device and Resistor_SMD have shipped with KiCad forever; an empty personal
# symbols directory has neither.
def _looks_right(d):
    if not d or not os.path.isdir(os.path.join(d, "symbols")):
        return False
    sym = os.path.join(d, "symbols")
    if not any(os.path.exists(os.path.join(sym, "Device" + ext))
               for ext in (".kicad_sym", ".kicad_symdir")):
        return False
    return os.path.isdir(os.path.join(d, "footprints", "Resistor_SMD.pretty"))


def runner():
    """The AppRun to use, mounting a plain .AppImage the first time one is
    needed.  Returns None if KiCad is on PATH instead, or nowhere at all."""
    global APPRUN
    if APPRUN is None and _MOUNT is None and PLAIN_CLI is None:
        _use_appimage()
    return APPRUN


def have_kicad():
    return bool(runner() or PLAIN_CLI)


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
        override = os.path.expanduser(override)
        if _looks_right(override):
            _SHARE = override
            return _SHARE
        _TRIED.append(f"$KICAD_SHARE_DIR = {override}  (no stock libraries "
                      f"in it -- is that your *personal* library directory?)")

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

    found = _ask_kicad() or _use_appimage()
    if found:
        _SHARE = found
        return _SHARE

    raise SystemExit(
        "Cannot locate KiCad 10's stock symbol and footprint libraries.\n"
        "Tried:\n  " + "\n  ".join(_TRIED) +
        "\n\nEither point KICAD_APPIMAGE at a KiCad 10 .AppImage, or set\n"
        "KICAD_SHARE_DIR to the directory that holds KiCad's own 'symbols'\n"
        "and 'footprints' -- the one with Device.kicad_symdir in it.  Note\n"
        "that ~/.local/share/kicad/<version> is where *your* libraries go and\n"
        "is normally empty; KiCad's own live with the program.")


def cli(*args, check=True, capture=True, timeout=1800):
    """Run `kicad-cli <args>` with whichever KiCad we found."""
    run = runner()
    if run:
        cmd = [run, "kicad-cli", *args]
    elif PLAIN_CLI:
        cmd = [PLAIN_CLI, *args]
    else:
        raise SystemExit(
            "KiCad 10 was not found.\n"
            "Install it so that `kicad-cli` is on PATH, or point KICAD_APPIMAGE\n"
            "at a KiCad 10 .AppImage -- see docs/MANUFACTURING.md.")
    r = subprocess.run(cmd, capture_output=capture, text=True, timeout=timeout)
    if check and r.returncode != 0:
        sys.stderr.write((r.stdout or "") + (r.stderr or ""))
        raise SystemExit(f"kicad-cli {' '.join(args)} failed ({r.returncode})")
    return r


def python(script, *args, check=True, timeout=1800):
    """Run a script under KiCad's bundled Python (the one with `pcbnew`)."""
    run = runner()
    cmd = [run, "python3.11", script, *args] if run \
        else [sys.executable, script, *args]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if check and r.returncode != 0:
        sys.stderr.write((r.stdout or "") + (r.stderr or ""))
        raise SystemExit(f"{os.path.basename(script)} failed ({r.returncode})")
    return r


def version():
    return cli("--version").stdout.strip()


def describe():
    """One line per located piece, for the build banner."""
    v = version()
    if not v.startswith("10."):
        raise SystemExit(
            f"This project needs KiCad 10; the one that was found reports "
            f"{v!r}.\n  runner  {runner() or PLAIN_CLI}\n"
            "Point KICAD_APPIMAGE at a KiCad 10 .AppImage, or KICAD_APPRUN at\n"
            "an extracted one.")
    out = [f"KiCad {v}"]
    out.append(f"  runner    {runner() or PLAIN_CLI}")
    if _MOUNTED:
        out.append(f"  mounted   {_MOUNTED}")
    out.append(f"  libraries {share_dir()}")
    return "\n".join(out)
