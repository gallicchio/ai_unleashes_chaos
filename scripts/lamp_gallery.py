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
:root{
  --ground:#E4E7E5; --panel:#F7F8F7; --well:#0B0D0C; --ink:#11150F;
  --muted:#5D655E; --line:#C6CDC6; --line-soft:#D9DED9; --brass:#9A7A18;
  --brass-soft:#E9DFBE; --die-r:#FF2D16; --die-g:#12E04A; --die-b:#2B4BFF;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --ground:#0C0F0D; --panel:#141815; --well:#000000; --ink:#DDE3DD;
    --muted:#8B958C; --line:#252B26; --line-soft:#1C211D; --brass:#D9B23F;
    --brass-soft:#3A3013;
  }
}
:root[data-theme="dark"]{
  --ground:#0C0F0D; --panel:#141815; --well:#000000; --ink:#DDE3DD;
  --muted:#8B958C; --line:#252B26; --line-soft:#1C211D; --brass:#D9B23F;
  --brass-soft:#3A3013;
}
*{box-sizing:border-box}
body{
  margin:0; background:var(--ground); color:var(--ink);
  font:400 15px/1.55 "IBM Plex Sans Condensed","Helvetica Neue",Arial,sans-serif;
  padding:0 20px 56px;
}
.mono,code{font-family:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
  font-variant-numeric:tabular-nums}
header{max-width:1320px; margin:0 auto; padding:26px 0 18px;
  border-bottom:1px solid var(--line)}
h1{margin:0; font-weight:600; font-size:clamp(24px,3.4vw,34px);
  letter-spacing:.015em; text-wrap:balance}
h1 span{color:var(--muted); font-weight:400}
.lede{margin:9px 0 0; max-width:66ch; color:var(--muted); font-size:14px}
.dies{display:flex; gap:14px; margin:14px 0 0; flex-wrap:wrap;
  font-size:12px; letter-spacing:.09em; text-transform:uppercase;
  color:var(--muted)}
.die{display:flex; align-items:center; gap:6px}
.chip{width:11px; height:11px; border-radius:2px; box-shadow:0 0 7px currentColor}
.chip.r{background:var(--die-r); color:var(--die-r)}
.chip.g{background:var(--die-g); color:var(--die-g)}
.chip.b{background:var(--die-b); color:var(--die-b)}

main{max-width:1320px; margin:0 auto; display:grid; gap:26px;
  grid-template-columns:minmax(0,1fr) 290px; padding-top:22px}
@media (max-width:900px){ main{grid-template-columns:minmax(0,1fr)} }

.stage{min-width:0}
.well{background:var(--well); border:1px solid var(--line);
  padding:14px; display:block}
.well img{display:block; width:100%; height:auto; image-rendering:pixelated}
.ruler{display:flex; justify-content:space-between; align-items:baseline;
  margin-top:7px; font-size:11px; letter-spacing:.07em; color:var(--muted)}
.ruler b{font-weight:400; color:var(--ink)}

.headline{display:flex; align-items:baseline; gap:14px; flex-wrap:wrap;
  margin:20px 0 2px}
.idx{font-size:30px; font-weight:500; color:var(--brass)}
.wiring{display:flex; gap:12px; flex-wrap:wrap; font-size:15px}
.w{display:flex; align-items:center; gap:6px}
.kind{font-size:12px; letter-spacing:.1em; text-transform:uppercase;
  color:var(--muted); border:1px solid var(--line); border-radius:2px;
  padding:2px 7px}

dl.spec{display:grid; grid-template-columns:auto 1fr; gap:3px 20px;
  margin:16px 0 0; font-size:13.5px; align-items:baseline}
dl.spec dt{color:var(--muted); font-size:11.5px; letter-spacing:.09em;
  text-transform:uppercase; white-space:nowrap}
dl.spec dd{margin:0}
dl.spec dd .u{color:var(--muted)}

.controls{display:flex; gap:9px; align-items:center; margin:20px 0 0;
  flex-wrap:wrap}
button{font:inherit; font-size:13px; color:var(--ink); background:var(--panel);
  border:1px solid var(--line); border-radius:2px; padding:6px 13px;
  cursor:pointer}
button:hover{border-color:var(--brass)}
button:focus-visible{outline:2px solid var(--brass); outline-offset:2px}
.hint{color:var(--muted); font-size:12.5px}

.rail{min-width:0}
.filters{display:flex; gap:6px; flex-wrap:wrap; margin-bottom:10px}
.filters button{padding:4px 9px; font-size:12px; letter-spacing:.04em}
.filters button[aria-pressed="true"]{background:var(--brass-soft);
  border-color:var(--brass); color:var(--ink)}
.list{max-height:74vh; overflow:auto; border-top:1px solid var(--line-soft);
  scrollbar-width:thin}
.row{display:grid; grid-template-columns:34px 30px 1fr auto; gap:9px;
  align-items:center; width:100%; text-align:left; padding:7px 8px;
  border:0; border-bottom:1px solid var(--line-soft); border-radius:0;
  background:none; font-size:12.5px}
.row:hover{background:var(--panel); border-color:var(--line-soft)}
.row[aria-current="true"]{background:var(--brass-soft);
  box-shadow:inset 3px 0 0 var(--brass)}
.row .n{color:var(--muted)}
.row .bar{display:flex; gap:2px}
.row .bar i{width:8px; height:8px; border-radius:1px; display:block}
.row .v{color:var(--muted)}
@media (max-width:900px){ .list{max-height:46vh} }
@media (prefers-reduced-motion:no-preference){
  .well img{transition:opacity .12s ease}
}
footer{max-width:1320px; margin:34px auto 0; padding-top:16px;
  border-top:1px solid var(--line); color:var(--muted); font-size:12.5px;
  max-width:1320px}
footer p{margin:0 0 6px; max-width:74ch}
"""

GALLERY_JS = r"""
const S = window.LAMP, OPTS = S.options;
const DIE = ['--die-r','--die-g','--die-b'];
const img = document.getElementById('shot');
const list = document.getElementById('list');
let i = 0, filter = 'all';

function wiringHTML(o){
  return o.perm.map((sig,k) =>
    `<span class="w"><i class="chip ${'rgb'[k]}"></i>${S.signals[sig]}</span>`
  ).join('');
}
function rows(){
  list.textContent = '';
  OPTS.forEach((o,k) => {
    if (filter === 'cc' && o.part !== 'CC') return;
    if (filter === 'ca' && o.part !== 'CA') return;
    if (filter === 'switchy' && o.lit > 0.75) return;
    if (filter === 'steady' && o.lit <= 0.75) return;
    const b = document.createElement('button');
    b.className = 'row'; b.dataset.k = k;
    b.innerHTML =
      `<span class="n mono">${String(k+1).padStart(3,'0')}</span>` +
      `<span class="bar">` + o.perm.map((sig,j) =>
        `<i style="background:var(${DIE[j]})"></i>`).join('') + `</span>` +
      `<span class="mono">${o.perm.map(s => S.signals[s]).join(' ')}</span>` +
      `<span class="v mono">${o.vref > 0 ? '+' : ''}${o.vref.toFixed(1)}V</span>`;
    b.onclick = () => show(k);
    list.appendChild(b);
  });
  mark();
}
function mark(){
  [...list.children].forEach(b => {
    const on = Number(b.dataset.k) === i;
    b.setAttribute('aria-current', on ? 'true' : 'false');
    if (on) b.scrollIntoView({block:'nearest'});
  });
}
function ma(v){ return v.map(x => x.toFixed(2)).join(' · '); }
function show(k){
  i = (k + OPTS.length) % OPTS.length;
  const o = OPTS[i];
  img.src = o.file;
  img.alt = 'colour of the lamp over ' + S.seconds + ' seconds, option ' + (i+1);
  document.getElementById('idx').textContent = String(i+1).padStart(3,'0');
  document.getElementById('wiring').innerHTML = wiringHTML(o);
  document.getElementById('kind').textContent =
    o.part === 'CC' ? 'common cathode' : 'common anode';
  const d = o.div.r_gnd
    ? `${o.div.r_gnd/1000}k to GND, ${o.div.r_rail/1000}k to ${o.div.rail}`
    : 'none — tie the common pin straight to ground';
  document.getElementById('spec').innerHTML =
    `<dt>lamp</dt><dd class="mono">${o.mpn} <span class="u">(${o.lcsc})</span></dd>` +
    `<dt>reference</dt><dd class="mono">${o.vref.toFixed(1)} V <span class="u">— ${d}, buffered by U2B</span></dd>` +
    `<dt>series R</dt><dd class="mono">${o.r[0]} · ${o.r[1]} · ${o.r[2]} <span class="u">ohm (R13 R14 R15)</span></dd>` +
    `<dt>peak</dt><dd class="mono">${ma(o.i_peak)} <span class="u">mA</span> &nbsp; ${o.mcd_peak.join(' · ')} <span class="u">mcd</span></dd>` +
    `<dt>mean</dt><dd class="mono">${ma(o.i_mean)} <span class="u">mA — ${(100*o.lit).toFixed(0)}% of the time something is lit</span></dd>` +
    `<dt>reverse</dt><dd class="mono">${o.v_rev.toFixed(1)} V <span class="u">of the 5 V the part allows</span></dd>`;
  mark();
  history.replaceState(null, '', '#' + (i+1));
}
document.getElementById('prev').onclick = () => show(i-1);
document.getElementById('next').onclick = () => show(i+1);
document.querySelectorAll('.filters button').forEach(b => {
  b.onclick = () => {
    filter = b.dataset.f;
    document.querySelectorAll('.filters button').forEach(x =>
      x.setAttribute('aria-pressed', x === b ? 'true' : 'false'));
    rows();
  };
});
addEventListener('keydown', e => {
  if (e.target.tagName === 'BUTTON' && e.key === ' ') return;
  if (e.key === 'ArrowRight' || e.key === 'ArrowDown'){ show(i+1); e.preventDefault(); }
  if (e.key === 'ArrowLeft' || e.key === 'ArrowUp'){ show(i-1); e.preventDefault(); }
  if (e.key === 'Home') show(0);
  if (e.key === 'End') show(OPTS.length-1);
});
rows();
show(Math.max(0, (parseInt(location.hash.slice(1),10) || 1) - 1));
"""


def write_gallery(out, index):
    """The page for flipping through the options."""
    ms = DT * TAU_SLOW * 1e3
    secs = W * ROWS * DT * TAU_SLOW
    row_s = W * DT * TAU_SLOW
    meta = json.dumps(dict(width=W, rows=ROWS, dt=DT, tau_slow=TAU_SLOW,
                           seconds=round(secs), signals=list(SIGNALS),
                           options=index), separators=(",", ":"))
    html = f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Chaos Lamp Wirings</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+Condensed:wght@400;500;600&display=swap">
<style>{GALLERY_CSS}</style>
<body>
<header>
  <h1>Chaos lamp <span>&mdash; {len(index)} ways to wire it</span></h1>
  <p class="lede">One RGB lamp on the three outputs of a Lorenz attractor.
  Each picture is {secs:.0f} seconds of it at the &ldquo;slow!&rdquo; setting,
  read left to right and wrapping at the end of every row, {ms:.1f}&nbsp;ms per
  pixel, with a black row between passes.  Colour comes from the datasheet's
  forward voltages and luminous intensities through the CIE&nbsp;1931 observer;
  brightness is compressed the way a dark-adapted eye compresses it.</p>
  <div class="dies">
    <span class="die"><i class="chip r"></i>red die, 621&nbsp;nm</span>
    <span class="die"><i class="chip g"></i>green die, 520&nbsp;nm</span>
    <span class="die"><i class="chip b"></i>blue die, 465&nbsp;nm</span>
  </div>
</header>
<main>
  <section class="stage">
    <figure class="well" style="margin:0"><img id="shot" alt=""></figure>
    <div class="ruler">
      <span>t = 0</span>
      <span><b>{row_s:.1f} s</b> per row &middot; <b>{ms:.1f} ms</b> per pixel</span>
      <span>t = {secs:.0f} s</span>
    </div>
    <div class="headline">
      <span class="idx mono" id="idx">001</span>
      <span class="wiring mono" id="wiring"></span>
      <span class="kind" id="kind"></span>
    </div>
    <dl class="spec" id="spec"></dl>
    <div class="controls">
      <button id="prev">&larr; previous</button>
      <button id="next">next &rarr;</button>
      <span class="hint">or the arrow keys</span>
    </div>
  </section>
  <aside class="rail">
    <div class="filters">
      <button data-f="all" aria-pressed="true">all</button>
      <button data-f="cc" aria-pressed="false">common cathode</button>
      <button data-f="ca" aria-pressed="false">common anode</button>
      <button data-f="switchy" aria-pressed="false">switches</button>
      <button data-f="steady" aria-pressed="false">always lit</button>
    </div>
    <div class="list" id="list"></div>
  </aside>
</main>
<footer>
  <p>&ldquo;Switches&rdquo; means something is dark more than a quarter of the
  time &mdash; the trajectory turning a colour off as it changes wings.
  &ldquo;Always lit&rdquo; means all three dies stay above their turn-on
  voltage and the colour wanders instead of blinking.</p>
  <p>Every option is buildable as drawn: the reference divider hangs off the
  &plusmn;12&nbsp;V rails and is buffered by the half of U2 that Paul never
  needed, and the common-anode ones are the same package with the pin&nbsp;1
  and pin&nbsp;4 connections exchanged.  Generated by
  <span class="mono">scripts/lamp_gallery.py</span> in
  <span class="mono">gallicchio/ai_unleashes_chaos</span>.</p>
</footer>
<script>window.LAMP={meta};</script>
<script>{GALLERY_JS}</script>
</html>
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
