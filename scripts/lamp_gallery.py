#!/usr/bin/env python3
"""Render what the chaos lamp would look like, for a hundred wirings of it.

Integrates the Lorenz system, drives the LED model in scripts/lamp_model.py
from the three real node voltages, and rasters the resulting colour as a strip
of time: left to right, wrapping at the end of each row with a black row
between, so the picture is a few minutes of the lamp at the "slow!" setting.

    python3 scripts/lamp_gallery.py [--all] [--out docs/lamp]

Each option varies four things: which signal drives which colour, whether the
lamp is common-cathode or common-anode, what the buffered reference voltage
is, and how the three series resistors are chosen.  Options that come out
black, white or one flat colour are dropped, and the rest are thinned to the
hundred most different from each other.
"""
import argparse, json, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lamp_model as LM
from lorenz_curve import trajectory

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

W, ROWS = 320, 96            # samples per row, rows per picture
DT = 0.01                    # dimensionless time per sample
TAU_SLOW = 0.472             # seconds per time unit at the "slow!" setting
VOLTS_PER_UNIT = 0.1
SCALE = 3                    # screen pixels per sample

# E24, 470 ohm to 1 M: what you can actually buy as a JLCPCB basic part
E24 = [round(m * 10 ** d, 6) for d in range(2, 6)
       for m in (1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0,
                 3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1)]
E24 = [r for r in E24 if 470.0 <= r <= 22.0e3]

# Below this the die is not putting out light anybody would call "on": a
# 3528 red at 20 uA is about a third of a millicandela.
VISIBLE_MCD = 2.0
BRIGHT_ENOUGH_MCD = 25.0

SIGNALS = ("x", "-y", "z")
PERMS = [(0, 1, 2), (0, 2, 1), (1, 0, 2), (1, 2, 0), (2, 0, 1), (2, 1, 0)]
DIES = ("R", "G", "B")


def signals():
    """The three node voltages, in volts, sampled every DT."""
    n = W * ROWS
    dt_int = 0.001
    every = int(round(DT / dt_int))
    pts = np.array(trajectory(dt=dt_int, n=n * every + 40000, skip=40000))
    pts = pts[::every][:n]
    x, y, z = pts[:, 0], pts[:, 1], pts[:, 2]
    return np.stack([x, -y, z]) * VOLTS_PER_UNIT


def pick_resistor(die, v_max, i_target):
    """Smallest E24 value whose peak current is at most i_target."""
    for r in E24:
        if die.current(v_max, r) <= i_target:
            return r
    return E24[-1]


def resistors(dies, v_max, style):
    """Three series resistors, by one of four rules."""
    if style.startswith("i"):                      # equal peak current
        target = {"i05": 0.5e-3, "i15": 1.5e-3, "i40": 4.0e-3}[style]
        return [pick_resistor(d, v, target) for d, v in zip(dies, v_max)]
    if style == "equal":                           # one value for all three
        r = sorted(pick_resistor(d, v, 1.5e-3) for d, v in zip(dies, v_max))[1]
        return [r, r, r]
    if style == "bal":                             # equal peak brightness
        # aim every die at the dimmest one's achievable peak, so the colour is
        # a fair mix rather than green with hints of the other two
        peaks = [d.mcd(d.current(v, E24[0])) for d, v in zip(dies, v_max)]
        want = min([p for p in peaks if p > 0] or [0.0])
        out = []
        for d, v in zip(dies, v_max):
            i_want = 0.020 * (want / d.iv20) ** (1 / d.gamma) if want else 0.0
            out.append(pick_resistor(d, v, min(max(i_want, 5e-5), 5e-3)))
        return out
    raise ValueError(style)


def render(cfg, sig, dies):
    """Colour for every sample, plus the numbers that describe the option."""
    order = cfg["perm"]
    drive_src = [sig[order[k]] for k in range(3)]
    lo = [s.min() for s in drive_src]
    hi = [s.max() for s in drive_src]
    vref = cfg["vref"]
    if cfg["part"] == "CC":
        drive = [s - vref for s in drive_src]
        v_max = [h - vref for h in hi]
    else:
        drive = [vref - s for s in drive_src]
        v_max = [vref - l for l in lo]
    rs = cfg.get("r") or resistors(dies, v_max, cfg["rstyle"])
    cur = [dies[k].current(drive[k], rs[k]) for k in range(3)]
    mcd = [dies[k].mcd(cur[k]) for k in range(3)]
    xyz = sum(m[:, None] * dies[k].xyz[None, :] for k, m in enumerate(mcd))
    # the datasheet allows 5 V in reverse on each junction
    v_rev = max(float(max(-d.min(), 0.0)) for d in drive)
    stats = dict(r=rs, v_rev=v_rev,
                 i_peak=[float(c.max() * 1e3) for c in cur],
                 mcd_peak=[float(m.max()) for m in mcd],
                 i_mean=[float(c.mean() * 1e3) for c in cur])
    return xyz, stats


def score(xyz):
    """How interesting is this one?  Colour spread, and not all black/white.

    "Lit" is measured in real millicandela, not against the picture's own
    exposure: otherwise a lamp running at two microamps scores well because
    its own darkness has been normalised away.
    """
    lum = xyz[:, 1]
    if lum.max() < BRIGHT_ENOUGH_MCD:
        return 0.0, dict(lit=0.0, spread=0.0, u=1 / 3, v=1 / 3, flicker=0.0)
    white = np.percentile(lum, 99.0)
    lit = float((lum > VISIBLE_MCD).mean())
    s = xyz.sum(axis=1)
    ok = s > 1e-9
    u = np.where(ok, xyz[:, 0] / np.maximum(s, 1e-9), 1 / 3)
    v = np.where(ok, xyz[:, 1] / np.maximum(s, 1e-9), 1 / 3)
    w = lum / lum.sum()
    umean, vmean = float((u * w).sum()), float((v * w).sum())
    spread = float(np.sqrt(((u - umean) ** 2 + (v - vmean) ** 2) * w).sum() * 30)
    # A lamp that is on all the time is fine as long as its colour moves; one
    # that is nearly always dark is not.
    return spread * min(1.0, lit / 0.15), dict(
        lit=lit, spread=spread, u=umean, v=vmean,
        flicker=float(np.mean(np.abs(np.diff(np.sign(lum - VISIBLE_MCD))) > 0)))


def to_image(xyz, scale=SCALE, compress=0.55):
    """Colour strip.  Luminance is compressed before the sRGB gamma, because
    a dark-adapted eye looking at a small lamp does the same: without it the
    picture is a hard on/off and all the shading in between is lost."""
    lum = np.maximum(xyz[:, 1], 1e-12)
    white = max(np.percentile(lum, 99.0), 1e-9)
    gain = np.where(lum > 1e-9, (lum / white) ** compress / (lum / white), 0.0)
    rgb = LM.to_srgb(xyz * gain[:, None], 1.0)
    rows = rgb.reshape(ROWS, W, 3)
    out = np.zeros((ROWS * 2 - 1, W, 3), dtype=np.uint8)
    out[0::2] = rows
    return np.kron(out, np.ones((scale, scale, 1), dtype=np.uint8))


def all_configs():
    out = []
    for part in ("CC", "CA"):
        # Below the signal minimum every colour is always on and the lamp
        # wanders through hues; near the maximum only the extremes light and
        # it flashes.  Both are worth looking at, so the grid covers both.
        vrefs = (-8.0, -6.0, -4.5, -3.0, -2.2, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0) \
            if part == "CC" else \
            (8.0, 6.0, 5.0, 4.0, 3.2, 2.6, 2.2, 1.8, 1.4, 1.0, 0.5)
        for perm in PERMS:
            for vref in vrefs:
                for rstyle in ("i05", "i15", "i40", "equal", "bal"):
                    out.append(dict(part=part, perm=perm, vref=vref,
                                    rstyle=rstyle))
    return out


def spread_out(cands, want):
    """Greedy max-min: keep the ones least like the ones already kept."""
    feats = np.array([[c["stats"]["lit"], c["stats"]["spread"],
                       c["stats"]["u"], c["stats"]["v"],
                       c["stats"].get("flicker", 0.0),
                       np.log10(max(c["stats"]["i_peak"][0], 1e-3)),
                       np.log10(max(c["stats"]["i_peak"][1], 1e-3)),
                       np.log10(max(c["stats"]["i_peak"][2], 1e-3))]
                      for c in cands])
    feats = (feats - feats.mean(0)) / (feats.std(0) + 1e-9)
    chosen = [int(np.argmax([c["score"] for c in cands]))]
    d = np.linalg.norm(feats - feats[chosen[0]], axis=1)
    while len(chosen) < min(want, len(cands)):
        k = int(np.argmax(d))
        chosen.append(k)
        d = np.minimum(d, np.linalg.norm(feats - feats[k], axis=1))
    return [cands[i] for i in chosen]


DIV_E24 = [round(m * 10 ** d, 6) for d in range(3, 6)
           for m in (1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0,
                     3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1)]
DIV_E24 = [r for r in DIV_E24 if 1.0e3 <= r <= 220.0e3]


def divider(vref):
    """Two E24 resistors that make `vref` from a +/-12 V rail and ground.

    Returns (rail, r_to_ground, r_to_rail, realised voltage).  The buffer sees
    a few tens of kilohms, which its JFET inputs do not notice, and the pair
    wastes well under a milliamp.
    """
    if abs(vref) < 1e-9:
        return ("GND", None, None, 0.0)
    rail = 12.0 if vref > 0 else -12.0
    best = None
    for rg in DIV_E24:
        for rr in DIV_E24:
            if not (20e3 <= rg + rr <= 300e3):
                continue
            v = rail * rg / (rg + rr)
            err = abs(v - vref)
            if best is None or err < best[0]:
                best = (err, rg, rr, v)
    return ("+12V" if rail > 0 else "-12V", best[1], best[2], best[3])


def label(cfg):
    p = cfg["perm"]
    m = "  ".join(f"{DIES[k]}={SIGNALS[p[k]]}" for k in range(3))
    kind = "common cathode" if cfg["part"] == "CC" else "common anode"
    rs = "/".join(f"{r/1000:g}k" if r >= 1000 else f"{r:g}" for r in cfg["r"])
    return f"{m}   {kind} at {cfg['vref']:+.1f} V   R = {rs}"



GALLERY_CSS = """
:root { color-scheme: dark; }
* { box-sizing: border-box; }
body { margin:0; background:#0b0c0e; color:#e6e6e6;
       font:14px/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace; }
header { padding:14px 18px 10px; border-bottom:1px solid #23262b; }
h1 { margin:0 0 4px; font-size:17px; letter-spacing:.06em; }
.sub { color:#8b929c; font-size:12px; }
main { display:flex; gap:18px; padding:16px 18px 40px; flex-wrap:wrap; }
.stage { flex:1 1 640px; min-width:320px; }
figure { margin:0; }
img.big { width:100%; height:auto; image-rendering:pixelated;
          border:1px solid #23262b; background:#000; }
.caption { margin-top:10px; font-size:13px; }
.caption b { color:#fff; }
table.spec { border-collapse:collapse; margin-top:10px; font-size:12px; }
table.spec td { padding:2px 12px 2px 0; vertical-align:top; color:#b9c0ca; }
table.spec td:first-child { color:#7d858f; white-space:nowrap; }
.side { flex:0 0 220px; max-height:78vh; overflow:auto; }
.side button { display:block; width:100%; text-align:left; margin:0 0 4px;
  padding:5px 7px; font:inherit; font-size:11px; background:#14161a;
  color:#c9d1d9; border:1px solid #23262b; border-radius:4px; cursor:pointer; }
.side button.on { background:#1f6feb33; border-color:#1f6feb; color:#fff; }
.nav { margin:10px 0 0; display:flex; gap:8px; align-items:center; }
.nav button { font:inherit; padding:5px 12px; background:#14161a; color:#c9d1d9;
  border:1px solid #23262b; border-radius:4px; cursor:pointer; }
.hint { color:#7d858f; font-size:12px; }
@media (max-width:760px){ .side{flex:1 1 100%; max-height:none;} }
"""

GALLERY_JS = """
const S = window.LAMP;
let i = 0;
const img = document.getElementById('big');
const cap = document.getElementById('cap');
const list = document.getElementById('list');
S.options.forEach((o, k) => {
  const b = document.createElement('button');
  b.textContent = String(k + 1).padStart(3, '0') + '  ' + o.label.replace(/\s+/g, ' ');
  b.onclick = () => show(k);
  list.appendChild(b);
});
function mA(v){ return v.map(x => x.toFixed(2)).join(' / '); }
function show(k) {
  i = (k + S.options.length) % S.options.length;
  const o = S.options[i];
  img.src = o.file;
  img.alt = o.label;
  const d = o.div.r_gnd
      ? o.div.r_gnd/1000 + 'k to GND, ' + o.div.r_rail/1000 + 'k to ' + o.div.rail
      : 'none -- tie the common pin straight to ground';
  cap.innerHTML =
    '<div class="caption"><b>' + String(i + 1).padStart(3, '0') + '</b> &nbsp; ' +
    o.label + '</div>' +
    '<table class="spec">' +
    '<tr><td>lamp</td><td>' + o.mpn + ' (' + o.lcsc + '), ' +
      (o.part === 'CC' ? 'common cathode' : 'common anode') + '</td></tr>' +
    '<tr><td>reference</td><td>' + o.vref.toFixed(1) + ' V &nbsp; divider: ' + d +
      ' &nbsp; (U2B buffers it)</td></tr>' +
    '<tr><td>series R</td><td>R ' + o.r[0] + ' &nbsp; G ' + o.r[1] +
      ' &nbsp; B ' + o.r[2] + ' ohm</td></tr>' +
    '<tr><td>peak mA</td><td>' + mA(o.i_peak) + ' &nbsp; (mean ' + mA(o.i_mean) +
      ')</td></tr>' +
    '<tr><td>peak mcd</td><td>' + o.mcd_peak.join(' / ') + '</td></tr>' +
    '<tr><td>lit</td><td>' + (100 * o.lit).toFixed(0) + '% of the time &nbsp; ' +
      'worst reverse ' + o.v_rev.toFixed(1) + ' V of 5 V allowed</td></tr>' +
    '</table>';
  [...list.children].forEach((b, k2) => b.classList.toggle('on', k2 === i));
  list.children[i].scrollIntoView({ block: 'nearest' });
  history.replaceState(null, '', '#' + (i + 1));
}
document.getElementById('prev').onclick = () => show(i - 1);
document.getElementById('next').onclick = () => show(i + 1);
addEventListener('keydown', e => {
  if (e.key === 'ArrowRight' || e.key === ' ') { show(i + 1); e.preventDefault(); }
  if (e.key === 'ArrowLeft') { show(i - 1); e.preventDefault(); }
  if (e.key === 'Home') show(0);
  if (e.key === 'End') show(S.options.length - 1);
});
show(Math.max(0, (parseInt(location.hash.slice(1), 10) || 1) - 1));
"""


def write_gallery(out, index):
    """A page for flipping through the options with the arrow keys."""
    meta = json.dumps(dict(width=W, rows=ROWS, dt=DT, tau_slow=TAU_SLOW,
                           options=index), separators=(",", ":"))
    ms = DT * TAU_SLOW * 1e3
    secs = W * ROWS * DT * TAU_SLOW
    html = f"""<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Chaos lamp options</title>
<style>{GALLERY_CSS}</style>
<header>
  <h1>CHAOS LAMP &mdash; {len(index)} wirings</h1>
  <div class="sub">Each picture is {secs:.0f} seconds of the lamp at the
  &ldquo;slow!&rdquo; setting, read left to right and wrapping at the end of
  every row, {ms:.1f} ms per pixel, with a black row between passes.
  Colour is computed from the datasheet's forward voltages and luminous
  intensities through the CIE 1931 observer; brightness is compressed the way
  a dark-adapted eye compresses it.  Arrow keys to flip.</div>
</header>
<main>
  <div class="stage">
    <figure><img class="big" id="big" alt=""></figure>
    <div id="cap"></div>
    <div class="nav">
      <button id="prev">&larr; previous</button>
      <button id="next">next &rarr;</button>
      <span class="hint">or use the arrow keys</span>
    </div>
  </div>
  <div class="side" id="list"></div>
</main>
<script>window.LAMP={meta};</script>
<script>{GALLERY_JS}</script>
"""
    with open(os.path.join(out, "index.html"), "w") as fh:
        fh.write(html)



def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=os.path.join(ROOT, "docs", "lamp"))
    ap.add_argument("--want", type=int, default=100)
    ap.add_argument("--all", action="store_true", help="render every option")
    a = ap.parse_args()

    sig = signals()
    dies = [LM.MHPC3528[k] for k in DIES]
    print(f"  {W} x {ROWS} = {W*ROWS} samples at {DT} time units "
          f"({DT*TAU_SLOW*1e3:.1f} ms each at the slow setting, "
          f"{W*ROWS*DT*TAU_SLOW:.0f} s in all)")
    print(f"  signal ranges: " + ", ".join(
        f"{SIGNALS[i]} {sig[i].min():+.2f}..{sig[i].max():+.2f} V" for i in range(3)))

    cands = []
    for cfg in all_configs():
        cfg = dict(cfg)
        xyz, stats = render(cfg, sig, dies)
        sc, st = score(xyz)
        st.update(stats)
        cfg["r"] = stats["r"]
        cfg["v_rev"] = stats["v_rev"]
        cfg["stats"], cfg["score"] = st, sc
        cands.append(cfg)
    print(f"  {len(cands)} configurations evaluated")

    good = [c for c in cands if c["score"] > 0.35 and c["stats"]["lit"] > 0.10
            and c["v_rev"] <= 5.0]
    print(f"  {len(good)} of them are not black, white or one flat colour")
    keep = good if a.all else spread_out(good, a.want)
    keep.sort(key=lambda c: (c["part"], c["perm"], c["vref"], c["rstyle"]))

    os.makedirs(a.out, exist_ok=True)
    for f in os.listdir(a.out):
        if f.startswith("opt-") and f.endswith(".png"):
            os.remove(os.path.join(a.out, f))
    from PIL import Image
    index = []
    for i, cfg in enumerate(keep, 1):
        xyz, _ = render(cfg, sig, dies)
        img = Image.fromarray(to_image(xyz))
        name = f"opt-{i:03d}.png"
        img.save(os.path.join(a.out, name), optimize=True)
        rail, rg, rr, vgot = divider(cfg["vref"])
        index.append(dict(file=name, label=label(cfg), **{
            k: cfg[k] for k in ("part", "perm", "vref", "rstyle")},
            r=[int(v) for v in cfg["r"]],
            lcsc="C2962096" if cfg["part"] == "CC" else "C2962095",
            mpn="MHPC3528CRGBCT" if cfg["part"] == "CC" else "MHPA3528CRGBCT",
            div=dict(rail=rail, r_gnd=rg and int(rg), r_rail=rr and int(rr),
                     v=round(vgot, 3)),
            i_peak=[round(v, 3) for v in cfg["stats"]["i_peak"]],
            i_mean=[round(v, 3) for v in cfg["stats"]["i_mean"]],
            mcd_peak=[round(v, 1) for v in cfg["stats"]["mcd_peak"]],
            v_rev=round(cfg["v_rev"], 2),
            lit=round(cfg["stats"]["lit"], 3)))
    with open(os.path.join(a.out, "options.json"), "w") as fh:
        json.dump(dict(width=W, rows=ROWS, dt=DT, tau_slow=TAU_SLOW,
                       options=index), fh, indent=1)
    write_gallery(a.out, index)
    total = sum(os.path.getsize(os.path.join(a.out, o["file"])) for o in index)
    print(f"  wrote {len(index)} images to {os.path.relpath(a.out, ROOT)}/ "
          f"({total/1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
