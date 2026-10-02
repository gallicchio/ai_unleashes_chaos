#!/usr/bin/env python3
"""The chaos lamp, simulated the way the board runs it and judged the way a
person watching it would judge it.

    signals()        the board's own Lorenz system (s = 1M/100k, b = 1M/374k,
                     r from the knob), as the three op-amp output voltages
    Lamp             one wiring of the lamp: which part, which reference,
                     which signal and resistors on each die
    Lamp.light()     each die's luminous intensity over time, already passed
                     through the eye's temporal filter
    judge()          what that looks like: how much of the time the lamp
                     shows a vivid colour, and how evenly those colours are
                     spread around the hue circle

Everything a wiring needs to be built is in the Lamp; everything that decides
whether it is worth building is in judge().
"""
import os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lamp_model as LM

VOLTS_PER_UNIT = 0.1
S_BOARD = 1e6 / 100e3              # R1 = R2 = 100k
B_BOARD = 1e6 / 374e3              # R7 = 374k
DT = 0.005                         # time units per stored sample
SPEEDS = {"fast!": 2.2e-3, "nice!": 0.102, "slow!": 0.472, "slower!": 0.572}
SIGNALS = ("x", "-y", "z")
DIES = ("R", "G", "B")
RAILS = {"GND": 0.0, "+12V": 12.0, "-12V": -12.0}

_CACHE = {}


def signals(r=28.0, t_units=400.0, seed=0, integrator="dop853"):
    """The three op-amp outputs, in volts, every DT time units, after the
    start-up transient has died away.  Different seeds start from different
    points, so two runs are two independent stretches of the attractor.

    The searches use scipy's DOP853.  The build uses "rk4", a fixed-step
    integrator in numpy alone, so that ./make.py needs nothing it did not
    need before; the two give different trajectories -- it is chaos -- but
    the same statistics, which is all the lamp is judged on."""
    key = (round(r, 4), t_units, seed, integrator)
    if key in _CACHE:
        return _CACHE[key]
    rng = np.random.default_rng(seed)
    y0 = np.array([1.0, 1.0, 20.0]) + rng.normal(0, 0.5, 3)

    def f(t, v):
        x, y, z = v
        return [S_BOARD * (y - x), r * x - y - x * z, x * y - B_BOARD * z]

    warm = 60.0
    n = int(round(t_units / DT))
    if integrator == "rk4":
        h, sub = DT / 4.0, 4
        v = y0.astype(float)
        out = np.empty((3, n))
        steps = int(round(warm / h))
        for i in range(steps + n * sub):
            k1 = np.array(f(0, v))
            k2 = np.array(f(0, v + h / 2 * k1))
            k3 = np.array(f(0, v + h / 2 * k2))
            k4 = np.array(f(0, v + h * k3))
            v = v + h / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
            j = i + 1 - steps
            if j > 0 and j % sub == 0:
                out[:, j // sub - 1] = v
        x, y, z = out
    else:
        from scipy.integrate import solve_ivp
        t_eval = warm + DT * np.arange(n)
        sol = solve_ivp(f, (0.0, t_eval[-1]), y0, t_eval=t_eval,
                        method="DOP853", rtol=1e-9, atol=1e-9)
        x, y, z = sol.y
    res = np.stack([x, -y, z]) * VOLTS_PER_UNIT
    _CACHE[key] = res
    return res


class Lamp:
    """One wiring.

    part     "CA" (MHPA3528CRGBCT, common anode) or "CC" (MHPC3528CRGBCT)
    vref     volts on the common pin, from U2B
    src      which signal drives R, G, B: indices into SIGNALS
    rs       series resistor from that signal to the die, ohms
    ro, rail optional second resistor from the die's pin to a rail, which
             shifts that die's threshold on its own (None: not fitted)
    """

    def __init__(self, part, vref, src, rs, ro=(None, None, None),
                 rail=("GND", "GND", "GND"), src2=(None, None, None),
                 rs2=(None, None, None)):
        self.part, self.vref = str(part), float(vref)
        self.src, self.rs = tuple(int(v) for v in src), tuple(float(v) for v in rs)
        self.ro = tuple(None if v is None else float(v) for v in ro)
        self.rail = tuple(str(v) for v in rail)
        # a second signal on the same die: the die then sees a weighted
        # average of the two, which can lead or lag either of them
        self.src2 = tuple(None if v is None else int(v) for v in src2)
        self.rs2 = tuple(None if v is None else float(v) for v in rs2)

    def thevenin(self, k, sig):
        """The source die k sees, open-circuit volts and resistance: every
        resistor into its pin, from a signal or a rail, in parallel."""
        g = 1.0 / self.rs[k]
        num = sig[self.src[k]] / self.rs[k]
        if self.rs2[k] is not None:
            g = g + 1.0 / self.rs2[k]
            num = num + sig[self.src2[k]] / self.rs2[k]
        if self.ro[k] is not None:
            g = g + 1.0 / self.ro[k]
            num = num + RAILS[self.rail[k]] / self.ro[k]
        return num / g, 1.0 / g

    def currents(self, sig, dies):
        out = []
        for k, d in enumerate(DIES):
            vth, rth = self.thevenin(k, sig)
            drive = (self.vref - vth) if self.part == "CA" else (vth - self.vref)
            out.append(dies[d].current(drive, rth))
        return out

    def light(self, sig, dies, speed="slow!", tau_eye=0.020):
        """(3, T) luminous intensity per die, mcd, after the eye's filter."""
        cur = self.currents(sig, dies)
        mcd = np.stack([dies[d].mcd(c) for d, c in zip(DIES, cur)])
        if tau_eye:
            mcd = LM.eye_filter(mcd, DT * SPEEDS[speed], tau_eye)
        return mcd, cur

    def reverse_volts(self, sig):
        worst = 0.0
        for k in range(3):
            vth, _ = self.thevenin(k, sig)
            rev = (vth - self.vref) if self.part == "CA" else (self.vref - vth)
            worst = max(worst, float(rev.max()))
        return worst

    def describe(self):
        kind = "common anode" if self.part == "CA" else "common cathode"
        bits = []
        for k, d in enumerate(DIES):
            t = f"{d}={SIGNALS[self.src[k]]} via {ohm(self.rs[k])}"
            if self.rs2[k] is not None:
                t += f" & {SIGNALS[self.src2[k]]} via {ohm(self.rs2[k])}"
            if self.ro[k] is not None:
                t += f" (+{ohm(self.ro[k])} to {self.rail[k]})"
            bits.append(t)
        return f"{kind} at {self.vref:+.2f} V; " + ", ".join(bits)

    def as_dict(self):
        return dict(part=self.part, vref=self.vref, src=list(self.src),
                    rs=list(self.rs), ro=list(self.ro), rail=list(self.rail),
                    src2=list(self.src2), rs2=list(self.rs2))

    def n_resistors(self):
        return 3 + sum(v is not None for v in self.ro + self.rs2)


def ohm(r):
    if r >= 1e6:
        return f"{r/1e6:g}M"
    if r >= 1e3:
        return f"{r/1e3:g}k"
    return f"{r:g}R"


def dies_xyz(dies):
    return np.stack([dies[d].xyz for d in DIES])          # (3, 3)


HUE_BINS = 72                  # 5 degree bins for the evenness measure
HUE_SMOOTH = 2.0               # bins of Gaussian smoothing (10 degrees)
_ker = np.exp(-0.5 * (np.arange(-8, 9) / HUE_SMOOTH) ** 2)
_KER = _ker / _ker.sum()


def _smooth_circ(h):
    """Circular Gaussian smoothing of histograms along the last axis."""
    n = h.shape[-1]
    pad = len(_KER) // 2
    hp = np.concatenate([h[..., -pad:], h, h[..., :pad]], axis=-1)
    out = np.zeros_like(h)
    for i, w in enumerate(_KER):
        out += w * hp[..., i:i + n]
    return out


def judge(mcd, xyz3, gamut, every=8):
    """How it looks.  mcd is (..., 3, T) eye-filtered intensity per die.

    Returns a dict of arrays over the leading axes:
      vivid     fraction of the time the lamp shows a vivid colour -- lit
                (not near black) and saturated (not near white)
      even      how evenly those vivid moments spread around the hue circle,
                as exp(entropy) / bins: 1 is every hue equally often
      score     vivid x even
      lit       fraction of the time it is not near black
      sat       mean saturation while lit
      bright    the lamp's bright end (95th percentile), in mcd-equivalent
      hist      the smoothed hue histogram of the vivid moments (72 bins)
    """
    m = mcd[..., ::every]
    xyz = np.einsum("...kt,kc->...tc", m, xyz3)
    u, v = LM.xyz_to_uv(xyz)
    sat = gamut.saturation(u, v)
    b = xyz[..., 1] * LM.ware_cowan(xyz)
    ref = np.percentile(b, 95.0, axis=-1, keepdims=True)
    j = np.cbrt(b / np.maximum(ref, 1e-12))
    w_lit = np.clip((j - 0.30) / 0.25, 0.0, 1.0)
    w_sat = np.clip((sat - 0.35) / 0.40, 0.0, 1.0)
    w = w_lit * w_sat
    hue = LM.hue_deg(xyz)
    idx = np.minimum((hue / (360.0 / HUE_BINS)).astype(int), HUE_BINS - 1)
    lead = w.shape[:-1]
    flat_w = w.reshape(-1, w.shape[-1])
    flat_i = idx.reshape(-1, idx.shape[-1])
    nrow = flat_w.shape[0]
    off = (np.arange(nrow) * HUE_BINS)[:, None]
    hist = np.bincount((flat_i + off).ravel(), weights=flat_w.ravel(),
                       minlength=nrow * HUE_BINS).reshape(nrow, HUE_BINS)
    hist = _smooth_circ(hist)
    tot = hist.sum(axis=-1, keepdims=True)
    p = hist / np.maximum(tot, 1e-12)
    with np.errstate(divide="ignore", invalid="ignore"):
        ent = -np.where(p > 0, p * np.log(p), 0.0).sum(axis=-1)
    even = np.exp(ent) / HUE_BINS
    vivid = flat_w.mean(axis=-1)
    litw = w_lit.reshape(nrow, -1)
    satr = sat.reshape(nrow, -1)
    return dict(
        vivid=vivid.reshape(lead), even=even.reshape(lead),
        score=(vivid * even).reshape(lead),
        lit=litw.mean(axis=-1).reshape(lead),
        sat=((satr * litw).sum(-1) / np.maximum(litw.sum(-1), 1e-9)).reshape(lead),
        bright=ref[..., 0].reshape(lead),
        hist=p.reshape(lead + (HUE_BINS,)))


SECTORS = [  # the twelve 30-degree OKLab hue sectors, by their middles
    (0, "pink"), (30, "red"), (60, "orange"), (90, "amber"),
    (120, "yellow-green"), (150, "green"), (180, "spring"), (210, "cyan"),
    (240, "azure"), (270, "blue"), (300, "violet"), (330, "magenta")]


def sector_shares(hist):
    """Collapse a 72-bin hue histogram into the twelve named sectors."""
    h = np.roll(hist, 3)            # 5-degree bins: sector k is bins 6k-3..6k+2
    return h.reshape(12, 6).sum(axis=1)


def render_strip(mcd, xyz3, seconds_per_row, dt_s, rows, width=900,
                 gap=True):
    """A picture of the lamp over time: left to right, wrapping at the end of
    each row, one black row between passes.  mcd is already eye-filtered, so
    this is what a person would see, not what a camera with a 1 ms shutter
    would see.  Brightness is scaled so the lamp's bright end is full scale;
    a colour at a fifth of that looks dim, as it does on the bench."""
    xyz = np.einsum("kt,kc->tc", mcd, xyz3)
    per_row = seconds_per_row / dt_s
    n = int(rows * per_row)
    xyz = xyz[:n]
    tpix = np.linspace(0, n - 1, rows * width).astype(int)
    xyz = xyz[tpix]
    ref = np.percentile(xyz[:, 1], 95.0)
    rgb = LM.to_srgb(xyz, ref * 1.1)
    img = rgb.reshape(rows, width, 3)
    if gap:
        out = np.zeros((rows * 2 - 1, width, 3), np.uint8)
        out[0::2] = img
        return out
    return img
