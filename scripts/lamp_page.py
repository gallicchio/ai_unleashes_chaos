"""The page that plays the rev B chaos-lamp candidates.  Used by
scripts/lamp_gallery2.py; kept apart so the Python there stays readable."""
import json
import numpy as np

CSS = r"""
/* Layout: a black bench well with the live lamp and its strip on the left,
   the ranked candidates down the right, notes underneath. */
:root{
  --ground:#E3E7E4; --panel:#F6F8F6; --well:#060807; --ink:#10150F;
  --muted:#58615A; --line:#C3CBC4; --line-soft:#D7DDD8; --brass:#8C6C0E;
  --brass-soft:#E8DDB8; --ok:#2F6B3A; --warn:#8A4B12;
  --font-body:"IBM Plex Sans Condensed","Helvetica Neue",Arial,sans-serif;
  --font-mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --ground:#0B0E0C; --panel:#131714; --well:#000000; --ink:#DCE2DC;
    --muted:#8C968D; --line:#262C27; --line-soft:#1B201C; --brass:#D6AE3A;
    --brass-soft:#382E12; --ok:#7CC48A; --warn:#E0A060; color-scheme:dark;
  }
}
:root[data-theme="dark"]{
  --ground:#0B0E0C; --panel:#131714; --well:#000000; --ink:#DCE2DC;
  --muted:#8C968D; --line:#262C27; --line-soft:#1B201C; --brass:#D6AE3A;
  --brass-soft:#382E12; --ok:#7CC48A; --warn:#E0A060; color-scheme:dark;
}
*{box-sizing:border-box}
body{margin:0; background:var(--ground); color:var(--ink);
  font:400 15px/1.55 var(--font-body); padding-inline:16px; padding-block:0 48px}
.mono,code{font-family:var(--font-mono); font-variant-numeric:tabular-nums}
header,main,.notes,footer{max-width:1320px; margin-inline:auto}
header{padding-block:24px 16px; border-bottom:1px solid var(--line)}
h1{margin:0; font-weight:600; font-size:clamp(24px,3.4vw,34px);
  letter-spacing:.015em; text-wrap:balance}
h1 span{color:var(--muted); font-weight:400}
.lede{margin:8px 0 0; max-width:70ch; color:var(--muted); font-size:14px}
.bar{display:flex; flex-wrap:wrap; gap:10px 18px; align-items:center;
  margin-top:14px}
.seg{display:flex; flex-wrap:wrap; gap:0; border:1px solid var(--line);
  border-radius:3px; overflow:hidden}
.seg button{font:inherit; font-size:13px; color:var(--ink); background:var(--panel);
  border:0; border-right:1px solid var(--line); padding:6px 12px; cursor:pointer}
.seg button:last-child{border-right:0}
.seg button span{color:var(--muted); font-family:var(--font-mono); font-size:11.5px;
  margin-left:4px}
.seg button[aria-pressed="true"]{background:var(--brass-soft)}
.seg button:focus-visible,.row:focus-visible,.ctl:focus-visible{
  outline:2px solid var(--brass); outline-offset:1px}
.hint{color:var(--muted); font-size:12.5px}

main{display:grid; gap:24px; grid-template-columns:minmax(0,1fr) 320px;
  padding-top:20px}
@media (max-width:920px){main{grid-template-columns:minmax(0,1fr)}}
.stage{min-width:0}
.bench{background:var(--well); border:1px solid var(--line); border-radius:3px;
  display:grid; grid-template-columns:200px minmax(0,1fr); gap:18px;
  padding:18px; align-items:center}
@media (max-width:620px){.bench{grid-template-columns:minmax(0,1fr)}}
.lampwell{display:grid; place-items:center; height:180px; position:relative}
.lamp{width:34px; height:34px; border-radius:6px; background:#000;
  box-shadow:0 0 0 1px #1a1f1b}
.lampcap{position:absolute; bottom:0; left:0; right:0; text-align:center;
  font-family:var(--font-mono); font-size:11px; color:#7d877e}
.strip{min-width:0}
.strip canvas{display:block; width:100%; height:auto; image-rendering:pixelated;
  max-width:100%}
.ruler{display:flex; justify-content:space-between; gap:8px; margin-top:6px;
  font-family:var(--font-mono); font-size:11px; color:#7d877e}

.headline{display:flex; flex-wrap:wrap; align-items:baseline; gap:8px 14px;
  margin:18px 0 4px}
.idx{font-family:var(--font-mono); font-size:28px; font-weight:500;
  color:var(--brass)}
.title{font-size:19px; font-weight:600}
.badge{font-size:11.5px; letter-spacing:.08em; text-transform:uppercase;
  border:1px solid var(--line); border-radius:2px; padding:1px 7px;
  color:var(--muted)}
.badge.go{color:var(--ok); border-color:var(--ok)}
.badge.new{color:var(--warn); border-color:var(--warn)}
.say{margin:2px 0 0; max-width:74ch}

.hues{margin:16px 0 0}
.hues h3,.spec h3{margin:0 0 6px; font-size:11.5px; letter-spacing:.1em;
  text-transform:uppercase; color:var(--muted); font-weight:500}
.hist{display:grid; grid-template-columns:repeat(12,minmax(0,1fr)); gap:3px;
  align-items:end; height:92px; border-bottom:1px solid var(--line);
  position:relative}
.hist i{display:block; border-radius:2px 2px 0 0; min-height:1px}
.hist .even{position:absolute; left:0; right:0; border-top:1px dashed var(--muted);
  pointer-events:none}
.hlab{display:grid; grid-template-columns:repeat(12,minmax(0,1fr)); gap:3px;
  font-size:10.5px; color:var(--muted); text-align:center; margin-top:3px}
.hlab span{overflow:hidden; text-overflow:ellipsis; white-space:nowrap}

.cols{display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr));
  gap:18px 28px; margin-top:18px}
dl{display:grid; grid-template-columns:auto minmax(0,1fr); gap:3px 16px; margin:0;
  font-size:13.5px; align-items:baseline}
dt{color:var(--muted); font-size:11.5px; letter-spacing:.07em;
  text-transform:uppercase; white-space:nowrap}
dd{margin:0; min-width:0; overflow-wrap:anywhere}
dd .u{color:var(--muted)}
.meter{display:inline-block; vertical-align:middle; width:70px; height:6px;
  background:var(--line-soft); border-radius:3px; overflow:hidden; margin-right:6px}
.meter b{display:block; height:100%; background:var(--brass)}

.controls{display:flex; flex-wrap:wrap; gap:8px; margin-top:18px}
.ctl{font:inherit; font-size:13px; color:var(--ink); background:var(--panel);
  border:1px solid var(--line); border-radius:3px; padding:6px 13px;
  cursor:pointer}
.ctl:hover{border-color:var(--brass)}

.rail{min-width:0}
.rail h2{margin:0 0 8px; font-size:12px; letter-spacing:.1em;
  text-transform:uppercase; color:var(--muted); font-weight:500}
.list{border-top:1px solid var(--line-soft); max-height:78vh; overflow:auto}
@media (max-width:920px){.list{max-height:none}}
.row{display:grid; grid-template-columns:30px minmax(0,1fr) auto; gap:4px 10px;
  width:100%; text-align:left; padding:8px 8px; border:0;
  border-bottom:1px solid var(--line-soft); background:none; color:var(--ink);
  font:inherit; font-size:12.5px; cursor:pointer}
.row:hover{background:var(--panel)}
.row[aria-current="true"]{background:var(--brass-soft);
  box-shadow:inset 3px 0 0 var(--brass)}
.row .n{font-family:var(--font-mono); color:var(--muted)}
.row .sc{font-family:var(--font-mono); color:var(--muted); text-align:right}
.row .what{min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap}
.mini{grid-column:2 / 4; display:grid; grid-template-columns:repeat(12,1fr);
  gap:1px; height:8px}
.mini i{display:block; border-radius:1px}
.sep{padding:10px 8px 4px; font-size:11px; letter-spacing:.1em;
  text-transform:uppercase; color:var(--muted)}

.notes{margin-top:34px; padding-top:14px; border-top:1px solid var(--line);
  display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr));
  gap:6px 36px; font-size:13.5px}
.notes h2{grid-column:1 / -1; margin:0 0 4px; font-size:12px;
  letter-spacing:.1em; text-transform:uppercase; color:var(--muted);
  font-weight:500}
.notes p{margin:0 0 10px; max-width:68ch}
footer{margin-top:18px; color:var(--muted); font-size:12.5px}
@media (prefers-reduced-motion:reduce){.lamp{transition:none}}
"""

JS = r"""
const P = window.LAMP2;
const ALL = P.candidates.map((c, i) => ({...c, key: 'c' + i}));
ALL.push({...P.reva.new, key: 'reva-new', ref: 'new'});
ALL.push({...P.reva.old, key: 'reva-old', ref: 'old'});
const SPEEDS = P.speeds;
let cur = 0, speed = 'slow!', playing = true;

// sRGB byte <-> linear light
const LIN = new Float32Array(256);
for (let i = 0; i < 256; i++) {
  const c = i / 255;
  LIN[i] = c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
}
function enc(l) {
  l = Math.max(0, Math.min(1, l));
  const c = l <= 0.0031308 ? 12.92 * l : 1.055 * Math.pow(l, 1 / 2.4) - 0.055;
  return Math.round(c * 255);
}
const cache = {};
function samples(c) {
  if (!cache[c.key]) {
    const b = atob(c.anim), n = b.length / 3, f = new Float32Array(b.length);
    for (let i = 0; i < b.length; i++) f[i] = LIN[b.charCodeAt(i)];
    cache[c.key] = {f, n};
  }
  return cache[c.key];
}

// ---------------------------------------------------------------- lamp ----
const lamp = document.getElementById('lamp');
let phase = 0, last = performance.now();
function frame(now) {
  const c = ALL[cur], s = samples(c);
  const dt = Math.min(0.1, (now - last) / 1000); last = now;
  if (playing) {
    const per = 1 / (P.anim_dt * SPEEDS[speed]);      // samples per second
    const a = phase, b = phase + dt * per;
    let r = 0, g = 0, bl = 0, k = 0;
    const n0 = Math.floor(a), n1 = Math.max(n0 + 1, Math.floor(b));
    for (let i = n0; i < n1 && k < 4000; i++, k++) {
      const j = (i % s.n) * 3;
      r += s.f[j]; g += s.f[j + 1]; bl += s.f[j + 2];
    }
    phase = b % s.n;
    if (k) { r /= k; g /= k; bl /= k; }
    const col = `rgb(${enc(r)},${enc(g)},${enc(bl)})`;
    const y = 0.2126 * r + 0.7152 * g + 0.0722 * bl;
    const glow = Math.round(8 + 40 * Math.sqrt(Math.min(1, y * 1.5)));
    lamp.style.background = col;
    lamp.style.boxShadow = `0 0 ${glow}px ${Math.round(glow / 3)}px ${col}, 0 0 0 1px #1a1f1b`;
  }
  requestAnimationFrame(frame);
}

// ---------------------------------------------------------------- strip ---
const strip = document.getElementById('strip');
function drawStrip() {
  const c = ALL[cur], s = samples(c), W = 880, ROWS = 10;
  const dts = P.anim_dt * SPEEDS[speed];              // seconds per sample
  const a = Math.exp(-dts / 0.020);                    // the eye, two stages
  const lin = new Float32Array(s.n * 3);
  let p = [s.f[0], s.f[1], s.f[2]], q = [s.f[0], s.f[1], s.f[2]];
  for (let i = 0; i < s.n; i++) for (let ch = 0; ch < 3; ch++) {
    p[ch] = a * p[ch] + (1 - a) * s.f[3 * i + ch];
    q[ch] = a * q[ch] + (1 - a) * p[ch];
    lin[3 * i + ch] = q[ch];
  }
  const per = s.n / (ROWS * W), RH = 8, GAP = 4;
  strip.width = W; strip.height = ROWS * (RH + GAP) - GAP;
  const ctx = strip.getContext('2d');
  const img = ctx.createImageData(W, strip.height);
  for (let row = 0; row < ROWS; row++) for (let x = 0; x < W; x++) {
    const i0 = Math.floor((row * W + x) * per), i1 = Math.max(i0 + 1, Math.floor((row * W + x + 1) * per));
    let r = 0, g = 0, b = 0;
    for (let i = i0; i < i1; i++) { r += lin[3 * i]; g += lin[3 * i + 1]; b += lin[3 * i + 2]; }
    const k = i1 - i0; r = enc(r / k); g = enc(g / k); b = enc(b / k);
    for (let yy = 0; yy < RH; yy++) {
      const o = ((row * (RH + GAP) + yy) * W + x) * 4;
      img.data[o] = r; img.data[o + 1] = g; img.data[o + 2] = b; img.data[o + 3] = 255;
    }
  }
  for (let o = 3; o < img.data.length; o += 4) if (!img.data[o]) img.data[o] = 255;
  ctx.putImageData(img, 0, 0);
  const total = s.n * dts;
  document.getElementById('r0').textContent = 't = 0';
  document.getElementById('r1').textContent = fmtS(total / ROWS) + ' per row, as the eye keeps it';
  document.getElementById('r2').textContent = 't = ' + fmtS(total);
}
function fmtS(t) { return t >= 1 ? t.toFixed(t >= 10 ? 0 : 1) + ' s' : (t * 1000).toFixed(0) + ' ms'; }

// ------------------------------------------------------------ details -----
function sectorsOf(c) { return (c[speed === 'nice!' || speed === 'fast!' ? 'nice!' : 'slow!']).sectors; }
function drawHist(c) {
  const h = document.getElementById('hist'), sh = sectorsOf(c);
  const mx = Math.max(1 / 12 * 1.8, ...sh);
  h.textContent = '';
  sh.forEach((v, i) => {
    const e = document.createElement('i');
    e.style.height = (100 * v / mx).toFixed(1) + '%';
    e.style.background = P.sector_rgb[i];
    e.title = `${P.sectors[i]}: ${(100 * v).toFixed(1)} %`;
    h.appendChild(e);
  });
  const ev = document.createElement('div');
  ev.className = 'even'; ev.style.bottom = (100 / 12 / mx).toFixed(1) + '%';
  ev.title = 'every hue equally often'; h.appendChild(ev);
}
function meter(v) { return `<span class="meter"><b style="width:${(100 * Math.max(0, Math.min(1, v))).toFixed(0)}%"></b></span>`; }
function ohm(r) { return r >= 1e6 ? (r / 1e6) + 'M' : r >= 1e3 ? (r / 1e3) + 'k' : r + 'R'; }
const DIE = ['red', 'green', 'blue'], SIG = ['x', '-y', 'z'];
function spec(c) {
  const L = c.lamp || {part: 'CA', vref: 3.2, src: [2, 0, 1], rs: [470, 3900, 1500], ro: [null, null, null], rail: ['GND', 'GND', 'GND']};
  const st = c[speed === 'nice!' || speed === 'fast!' ? 'nice!' : 'slow!'];
  const part = L.part === 'CA' ? 'MHPA3528CRGBCT, common anode' : 'MHPC3528CRGBCT, common cathode';
  const d = c.divider;
  const ref = d ? (d.r_gnd ? `${ohm(d.r_gnd)} to GND, ${ohm(d.r_rail)} to ${d.rail}` +
      (Math.abs(d.v - L.vref) > 0.005 ? ` (makes ${d.v.toFixed(2)} V, well inside the rail's own ±4 %)` : '')
      : 'common pin straight to GND') : '12k to GND, 33k to +12V';
  let dies = '';
  for (let k = 0; k < 3; k++) {
    let t = `${SIG[L.src[k]]} through ${ohm(L.rs[k])}`;
    if (L.rs2 && L.rs2[k]) t += ` and ${SIG[L.src2[k]]} through ${ohm(L.rs2[k])}`;
    if (L.ro && L.ro[k]) t += ` <span class="u">+ ${ohm(L.ro[k])} to ${L.rail[k]}</span>`;
    dies += `<dt>${DIE[k]}</dt><dd class="mono">${t} <span class="u">· ${c.i_peak[k]} mA peak, ${c.i_mean[k]} mA mean</span></dd>`;
  }
  let rework = '';
  if ((c.dropin || c.plus1) && d && d.r_gnd) {
    const ch = [['R15', 470, L.rs[0]], ['R13', 3900, L.rs[1]], ['R14', 1500, L.rs[2]],
                ['R16', 12000, d.r_gnd], ['R17', 33000, d.r_rail]]
      .filter(t => t[1] !== t[2]).map(t => `${t[0]} ${ohm(t[1])} &rarr; ${ohm(t[2])}`);
    if (c.plus1) ch.push(`add ${ohm(L.ro[2])} from D1 pin 2 (blue) to ${L.rail[2]}`);
    rework = `<dt>rework</dt><dd class="mono">${ch.join(', ') || 'nothing'} <span class="u">on a rev A board${c.plus1 ? '' : '; nothing else changes'}</span></dd>`;
  }
  const extra = (L.ro || []).filter(v => v).length + (L.rs2 || []).filter(v => v).length;
  document.getElementById('wiring').innerHTML =
    `<dt>lamp</dt><dd>${part}</dd>` +
    `<dt>common pin</dt><dd class="mono">${L.vref.toFixed(2)} V <span class="u">· ${ref}, buffered by U2B</span></dd>` + dies +
    rework +
    `<dt>parts</dt><dd>${3 + extra} resistors on the dies${extra ? `, ${extra} more than rev A` : ', as on rev A'}, plus the reference divider</dd>` +
    `<dt>reverse</dt><dd class="mono">${c.v_rev.toFixed(1)} V <span class="u">worst case, of the 5 V the part allows</span></dd>`;
  const rob = c.robust;
  document.getElementById('looks').innerHTML =
    `<dt>vivid</dt><dd>${meter(st.vivid)}<span class="mono">${(100 * st.vivid).toFixed(0)} %</span> <span class="u">of the time lit and saturated</span></dd>` +
    `<dt>hues</dt><dd>${meter(st.even)}<span class="mono">${(12 * st.even).toFixed(1)}</span> <span class="u">of 12 hue sectors, effectively</span></dd>` +
    `<dt>score</dt><dd class="mono">${st.score.toFixed(3)} <span class="u">vivid × evenness, at ${speed === 'nice!' || speed === 'fast!' ? 'nice!' : 'slow!'}</span></dd>` +
    (rob ? `<dt>real parts</dt><dd class="mono">${rob.p20.toFixed(3)} – ${rob.med.toFixed(3)} <span class="u">20th percentile to median over 24 LEDs × 3 r settings</span></dd>` : '') +
    `<dt>saturation</dt><dd class="mono">${st.sat.toFixed(2)} <span class="u">mean while lit; 1 = no more than two dies on</span></dd>` +
    (c.vref_sens ? `<dt>+12 V ± 4 %</dt><dd class="mono">${c.vref_sens[0].toFixed(3)} / ${c.vref_sens[1].toFixed(3)} <span class="u">score with the rail 4 % low / high</span></dd>` : '') +
    (c.hue_speed ? `<dt>motion</dt><dd class="mono">${c.hue_speed.toFixed(0)}°/s <span class="u">median hue speed at slow!</span></dd>` : '');
}
function show(k) {
  cur = (k + ALL.length) % ALL.length;
  const c = ALL[cur];
  document.getElementById('idx').textContent = c.ref ? 'A' : String(c.n).padStart(2, '0');
  document.getElementById('title').textContent = c.ref ? (c.ref === 'new' ? 'Rev A as built, corrected model' : 'Rev A as the old model drew it') : c.name;
  const b = document.getElementById('badges');
  b.innerHTML = c.ref ? '<span class="badge">reference</span>' :
    (c.revb ? '<span class="badge go">built on rev B</span> ' : '') +
    (c.dropin ? '<span class="badge go">try it on a rev A board</span>' :
     c.plus1 ? '<span class="badge go">rev A + one resistor</span>' : '<span class="badge new">needs rev B</span>') +
    (c.topo === 'B' && !c.plus1 ? ' <span class="badge">+ offset resistors</span>' : '') +
    (c.topo === 'C' ? ' <span class="badge">blended signals</span>' : '') +
    (c.lamp.part === 'CC' ? ' <span class="badge">common cathode</span>' : '');
  document.getElementById('say').textContent = c.say || '';
  spec(c); drawHist(c); drawStrip();
  document.querySelectorAll('.row').forEach(r => r.setAttribute('aria-current', r.dataset.k == cur ? 'true' : 'false'));
  try { history.replaceState(null, '', '#' + c.key); } catch (e) {}
}
function list() {
  const L = document.getElementById('list');
  const add = (i) => {
    const c = ALL[i], b = document.createElement('button');
    b.className = 'row'; b.dataset.k = i;
    const st = c['slow!'];
    const sc = c.robust ? c.robust.med : st.score;
    b.innerHTML = `<span class="n">${c.ref ? 'A' : String(c.n).padStart(2, '0')}</span>` +
      `<span class="what">${c.ref ? (c.ref === 'new' ? 'rev A, corrected model' : 'rev A, old model') : c.name}</span>` +
      `<span class="sc">${sc.toFixed(2)}</span><span class="mini">` +
      st.sectors.map((v, j) => `<i style="background:${P.sector_rgb[j]};opacity:${Math.min(1, 0.12 + v * 8).toFixed(2)}"></i>`).join('') + '</span>';
    b.onclick = () => show(i);
    L.appendChild(b);
  };
  for (let i = 0; i < P.candidates.length; i++) add(i);
  const s = document.createElement('div'); s.className = 'sep'; s.textContent = 'for comparison'; L.appendChild(s);
  add(ALL.length - 2); add(ALL.length - 1);
}
document.querySelectorAll('.seg button').forEach(b => b.onclick = () => {
  speed = b.dataset.speed;
  document.querySelectorAll('.seg button').forEach(x => x.setAttribute('aria-pressed', x === b ? 'true' : 'false'));
  show(cur);
});
document.getElementById('prev').onclick = () => show(cur - 1);
document.getElementById('next').onclick = () => show(cur + 1);
document.getElementById('play').onclick = (e) => { playing = !playing; e.target.textContent = playing ? 'Pause' : 'Play'; };
addEventListener('keydown', e => {
  if (e.key === 'ArrowRight' || e.key === 'ArrowDown') { show(cur + 1); e.preventDefault(); }
  if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') { show(cur - 1); e.preventDefault(); }
});
list();
const h = location.hash.slice(1), at = ALL.findIndex(c => c.key === h);
show(at >= 0 ? at : 0);
requestAnimationFrame(frame);
"""

BODY = """<header>
  <h1>Chaos lamp <span>&mdash; rev B candidates</span></h1>
  <p class="lede">Each candidate is one way to wire the lamp, judged by a model
  corrected against the rev A boards.  The square on the left plays it in real
  time at the speed you pick; the strip beside it is what the eye keeps of it,
  a row at a time.  The bars show how its vivid moments spread around the hue
  circle, with the dashed line where every hue would get equal time.</p>
  <div class="bar">
    <div class="seg" role="group" aria-label="Speed switch setting">
      <button data-speed="slow!" aria-pressed="true">slow!<span>472 ms</span></button>
      <button data-speed="slower!" aria-pressed="false">slower!<span>572 ms</span></button>
      <button data-speed="nice!" aria-pressed="false">nice!<span>102 ms</span></button>
      <button data-speed="fast!" aria-pressed="false">fast!<span>2.2 ms</span></button>
    </div>
    <span class="hint">Arrow keys step through the list.</span>
  </div>
</header>
<main>
  <section class="stage">
    <div class="bench">
      <div class="lampwell"><div class="lamp" id="lamp"></div>
        <div class="lampcap">the lamp, live</div></div>
      <div class="strip"><canvas id="strip" width="880" height="116"></canvas>
        <div class="ruler"><span id="r0"></span><span id="r1"></span><span id="r2"></span></div></div>
    </div>
    <div class="headline"><span class="idx" id="idx">01</span>
      <span class="title" id="title"></span><span id="badges"></span></div>
    <p class="say" id="say"></p>
    <div class="hues"><h3>where the vivid moments fall</h3>
      <div class="hist" id="hist"></div>
      <div class="hlab">%HLAB%</div></div>
    <div class="cols">
      <div class="spec"><h3>how it looks</h3><dl id="looks"></dl></div>
      <div class="spec"><h3>how it is wired</h3><dl id="wiring"></dl></div>
    </div>
    <div class="controls">
      <button class="ctl" id="prev">&larr; Previous</button>
      <button class="ctl" id="next">Next &rarr;</button>
      <button class="ctl" id="play">Pause</button>
    </div>
  </section>
  <aside class="rail"><h2>Ranked by median score over real parts</h2><div class="list" id="list"></div></aside>
</main>
<section class="notes">
  <h2>Reading the numbers</h2>
  %NOTES%
</section>
<footer>Generated by <span class="mono">scripts/lamp_search.py</span> and
<span class="mono">scripts/lamp_gallery2.py</span> in
<span class="mono">gallicchio/ai_unleashes_chaos</span>.</footer>
"""

NOTES = [
    "<p><b>Vivid</b> is the fraction of the time the lamp is neither near "
    "black nor near white: its perceived brightness is at least a sixth of its "
    "own bright end, and its colour is at least three quarters of the way "
    "from white to the most saturated colour the three dies can make in that "
    "hue.  That edge is reached exactly when no more than two dies are lit.</p>",
    "<p><b>Hues</b> counts how many of the twelve 30&deg; sectors of the "
    "OKLab hue circle the vivid moments effectively fill: exp(entropy) of "
    "their distribution.  12 would be every hue equally often; rev A fills "
    "about four.  The score is vivid &times; hues / 12.</p>",
    "<p><b>Real parts</b> repeats the judgement for 24 LEDs drawn from what "
    "the datasheet allows (each colour's brightness bin, &plusmn;0.08 V of "
    "forward voltage, and the uncertainty in how efficiency changes with "
    "current) at r = 26, 28 and 31, and quotes the 20th percentile and the "
    "median.  The ranking uses the median.</p>",
    "<p><b>The screen cannot show all of it.</b>  The dies are more saturated "
    "than any monitor's primaries, and a lamp in a dark room is brighter "
    "relative to its surroundings than a square on a page.  Judge hue balance "
    "and rhythm here; the bench will look more vivid, not less.</p>",
]


def sector_rgb():
    """A representative colour for each 30-degree OKLab hue sector."""
    import lamp_model as LM
    out = []
    m1inv = np.linalg.inv(LM._OK_M1)
    m2inv = np.linalg.inv(LM._OK_M2)
    for i in range(12):
        h = np.radians(i * 30.0)
        for c in np.linspace(0.20, 0.02, 40):
            lab = np.array([0.70, c * np.cos(h), c * np.sin(h)])
            lms = (m2inv @ lab) ** 3
            xyz = m1inv @ lms
            rgb = LM.XYZ_TO_RGB @ xyz
            if rgb.min() >= 0 and rgb.max() <= 1:
                break
        srgb = LM.to_srgb(xyz[None, :], 1.0)[0]
        out.append("#%02x%02x%02x" % tuple(int(v) for v in srgb))
    return out


def write(page, path, standalone):
    page = dict(page, sector_rgb=sector_rgb())
    hlab = "".join(f"<span>{n}</span>" for n in page["sectors"])
    body = BODY.replace("%HLAB%", hlab).replace("%NOTES%", "\n  ".join(NOTES))
    head = ('<title>Chaos Lamp Rev B</title>\n'
            '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
            'family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+Condensed:'
            'wght@400;500;600&display=swap">\n'
            f'<style>{CSS}</style>\n')
    data = json.dumps(page, separators=(",", ":"))
    tail = f'<script>window.LAMP2={data};</script>\n<script>{JS}</script>\n'
    if standalone:
        html = ('<!doctype html>\n<html lang="en">\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width,'
                'initial-scale=1,viewport-fit=cover">\n' + head +
                '<body>\n' + body + tail + '</body>\n</html>\n')
    else:
        html = head + body + tail
    with open(path, "w") as fh:
        fh.write(html)
