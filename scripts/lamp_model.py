#!/usr/bin/env python3
"""What the chaos lamp actually looks like.

Four questions have to be answered with numbers before anyone can judge a
resistor value by eye:

 1. given the op-amp output voltage, how much current flows in each LED?
 2. given that current, how much light comes out, in each colour?
 3. given those three luminous intensities, what colour does a person see?
 4. and how does a person see it *in time* -- what survives the eye's own
    blurring of a colour that changes every few tens of milliseconds?

(1) is a diode I-V curve with a series resistance.  (2) is the datasheet's
luminous intensity at 20 mA, scaled by the current *and* by how the die's
efficiency changes with current.  (3) is the real CIE 1931 2-degree observer:
each die's spectrum is integrated against the colour matching functions and
the three tristimulus vectors are added.  (4) is a two-stage 20 ms low-pass,
applied to the light (which is linear) before anything is judged.

Two sets of die parameters live here.

REVA is the model rev A's lamp was chosen with.  The boards came back and
showed it was wrong in the direction that matters: it let every die conduct
0.3-0.45 V too early (ideality factors of 3.2 and 5), and it had the two
InGaN dies (green, blue) losing efficiency at low current when they gain it,
while the AlGaInP red loses it.  At the half-milliamp this lamp runs at, the
real green and blue are 2-3x brighter *relative to red* than REVA said.

MHPA3528 is the corrected model of the part on the board.  Its low-current
forward voltages are typical of the two chip materials, and its efficiency
curves are the textbook ABC model (InGaN: peak efficiency near a milliamp,
droop above it) and SRH-plus-radiative (AlGaInP: efficiency still climbing
at 20 mA).  None of this is on the part's datasheet, whose curves stop at
1 mA and are the same template shifted for all three colours -- so every
parameter here also has a range (SPREAD), and a design is only accepted if
it looks right across that range.

Run this file to self-test the colour pipeline against published values.
"""
import numpy as np

VT = 0.02585                      # kT/q at 25 C

# CIE 1931 2-degree standard observer, 5 nm steps, 380..780 nm.
_CIE = """
380 0.001368 0.000039 0.006450   385 0.002236 0.000064 0.010550
390 0.004243 0.000120 0.020050   395 0.007650 0.000217 0.036210
400 0.014310 0.000396 0.067850   405 0.023190 0.000640 0.110200
410 0.043510 0.001210 0.207400   415 0.077630 0.002180 0.371300
420 0.134380 0.004000 0.645600   425 0.214770 0.007300 1.039050
430 0.283900 0.011600 1.385600   435 0.328500 0.016840 1.622960
440 0.348280 0.023000 1.747060   445 0.348060 0.029800 1.782600
450 0.336200 0.038000 1.772110   455 0.318700 0.048000 1.744100
460 0.290800 0.060000 1.669200   465 0.251100 0.073900 1.528100
470 0.195360 0.090980 1.287640   475 0.142100 0.112600 1.041900
480 0.095640 0.139020 0.812950   485 0.057950 0.169300 0.616200
490 0.032010 0.208020 0.465180   495 0.014700 0.258600 0.353300
500 0.004900 0.323000 0.272000   505 0.002400 0.407300 0.212300
510 0.009300 0.503000 0.158200   515 0.029100 0.608200 0.111700
520 0.063270 0.710000 0.078250   525 0.109600 0.793200 0.057250
530 0.165500 0.862000 0.042160   535 0.225750 0.914850 0.029840
540 0.290400 0.954000 0.020300   545 0.359700 0.980300 0.013400
550 0.433450 0.994950 0.008750   555 0.512050 1.000000 0.005750
560 0.594500 0.995000 0.003900   565 0.678400 0.978600 0.002750
570 0.762100 0.952000 0.002100   575 0.842500 0.915400 0.001800
580 0.916300 0.870000 0.001650   585 0.978600 0.816300 0.001400
590 1.026300 0.757000 0.001100   595 1.056700 0.694900 0.001000
600 1.062200 0.631000 0.000800   605 1.045600 0.566800 0.000600
610 1.002600 0.503000 0.000340   615 0.938400 0.441200 0.000240
620 0.854450 0.381000 0.000190   625 0.751400 0.321000 0.000100
630 0.642400 0.265000 0.000050   635 0.541900 0.217000 0.000030
640 0.447900 0.175000 0.000020   645 0.360800 0.138200 0.000010
650 0.283500 0.107000 0.000000   655 0.218700 0.081600 0.000000
660 0.164900 0.061000 0.000000   665 0.121200 0.044580 0.000000
670 0.087400 0.032000 0.000000   675 0.063600 0.023200 0.000000
680 0.046770 0.017000 0.000000   685 0.032900 0.011920 0.000000
690 0.022700 0.008210 0.000000   695 0.015840 0.005723 0.000000
700 0.011359 0.004102 0.000000   705 0.008111 0.002929 0.000000
710 0.005790 0.002091 0.000000   715 0.004109 0.001484 0.000000
720 0.002899 0.001047 0.000000   725 0.002049 0.000740 0.000000
730 0.001440 0.000520 0.000000   735 0.001000 0.000361 0.000000
740 0.000690 0.000249 0.000000   745 0.000476 0.000172 0.000000
750 0.000332 0.000120 0.000000   755 0.000235 0.000085 0.000000
760 0.000166 0.000060 0.000000   765 0.000117 0.000042 0.000000
770 0.000083 0.000030 0.000000   775 0.000059 0.000021 0.000000
780 0.000042 0.000015 0.000000
"""
_rows = np.array([float(v) for v in _CIE.split()]).reshape(-1, 4)
LAM = _rows[:, 0]
XBAR, YBAR, ZBAR = _rows[:, 1], _rows[:, 2], _rows[:, 3]

# CIE XYZ (D65) -> linear sRGB
XYZ_TO_RGB = np.array([[3.2406255, -1.5372080, -0.4986286],
                       [-0.9689307, 1.8757561, 0.0415175],
                       [0.0557101, -0.2040211, 1.0569959]])

D65_XYZ = np.array([0.95047, 1.0, 1.08883])


# ------------------------------------------------ efficiency vs current ----
# Each returns the die's efficiency at current i RELATIVE TO ITS EFFICIENCY
# AT 20 mA, so luminous intensity is  Iv20 * (i / 20 mA) * rel(i).

class PowerLaw:
    """Rev A's assumption: Iv goes as (i / 20 mA)^gamma, gamma > 1 for all."""

    def __init__(self, gamma):
        self.gamma = gamma

    def rel(self, i):
        return (np.maximum(i, 1e-15) / 0.020) ** (self.gamma - 1.0)


class SRH:
    """AlGaInP: Shockley-Read-Hall loss against radiative recombination.

    With carrier density n, current goes as A n + B n^2 and light as B n^2.
    i0 = A^2/B is the current where the two are comparable; far below it
    light goes as i^2, far above it as i.  Small AlGaInP dies have a large A
    (surface recombination at the mesa walls), so i0 sits around 0.1-0.5 mA
    and the die is still gaining efficiency at 20 mA.
    """

    def __init__(self, i0):
        self.i0 = i0

    def _eta(self, i):
        u = 4.0 * np.maximum(i, 1e-15) / self.i0
        return 1.0 - (2.0 / u) * (np.sqrt(1.0 + u) - 1.0)

    def rel(self, i):
        return self._eta(i) / self._eta(0.020)


class ABC:
    """InGaN: the ABC model, IQE = B n^2 / (A n + B n^2 + C n^3).

    Written in terms of the current at peak efficiency i_pk and the quality
    Q = B / sqrt(A C): with m = n / n_peak,
        IQE(m)        = 1 / (1 + (1/m + m) / Q)
        i(m) / i_pk   = m (1/Q + m + m^2/Q) / (1 + 2/Q)
    InGaN peaks at a few A/cm^2 -- about a milliamp for a die this size --
    and droops above it, which is why a green or blue die at half a milliamp
    is *more* efficient than at the 20 mA its datasheet quotes.
    """

    def __init__(self, i_pk, q):
        self.i_pk, self.q = i_pk, q
        m = np.logspace(-5, 4, 3000)
        ratio = m * (1.0 / q + m + m * m / q) / (1.0 + 2.0 / q)
        self._lr, self._lm = np.log(ratio), np.log(m)

    def _eta(self, i):
        lr = np.log(np.maximum(i, 1e-15) / self.i_pk)
        m = np.exp(np.interp(lr, self._lr, self._lm))
        return 1.0 / (1.0 + (1.0 / m + m) / self.q)

    def rel(self, i):
        return self._eta(i) / self._eta(0.020)


class Die:
    """One colour of one LED.

    lam_p, fwhm   peak wavelength and spectral width (nm), Gaussian spectrum
    iv20          luminous intensity at 20 mA (mcd)
    n, rs         ideality factor and series resistance of the diode
    vf20 | v01    the voltage the I-V is anchored on: at 20 mA, or at 0.1 mA
    eff           efficiency relative to 20 mA, one of the classes above
    """

    def __init__(self, name, lam_p, fwhm, iv20, n, rs, eff,
                 vf20=None, v01=None):
        self.name, self.lam_p, self.fwhm, self.iv20 = name, lam_p, fwhm, iv20
        self.n, self.rs, self.eff = n, rs, eff
        if v01 is not None:
            i_a, v_a = 1e-4, v01
        else:
            i_a, v_a = 0.020, vf20
        self.i_s = i_a / np.expm1((v_a - i_a * rs) / (n * VT))
        self.xyz = self._chromaticity()
        self._grid = np.logspace(-11, np.log10(0.05), 5000)
        self._vd = self.v_of_i(self._grid)

    def v_of_i(self, i):
        i = np.asarray(i, dtype=float)
        return self.n * VT * np.log1p(np.maximum(i, 0.0) / self.i_s) + i * self.rs

    def _spectrum(self, lam=LAM):
        sigma = self.fwhm / 2.3548
        return np.exp(-0.5 * ((lam - self.lam_p) / sigma) ** 2)

    def _chromaticity(self):
        """Unit-luminance XYZ for this die's own spectrum."""
        s = self._spectrum()
        X, Y, Z = (s * XBAR).sum(), (s * YBAR).sum(), (s * ZBAR).sum()
        return np.array([X / Y, 1.0, Z / Y])

    def xy(self):
        v = self.xyz
        return v[0] / v.sum(), v[1] / v.sum()

    def dominant_nm(self):
        return dominant_wavelength(*self.xy())

    def current(self, v_drive, r):
        """Current through this die with `r` in series and `v_drive` across.

        Solved by inverting V(I) = Vd(I) + I*r on a log grid, which is
        vectorised and monotone, rather than iterating per sample.
        """
        vtot = self._vd + self._grid * r
        v = np.asarray(v_drive, dtype=float)
        i = np.interp(v, vtot, self._grid, left=0.0, right=self._grid[-1])
        return np.where(v <= vtot[0], 0.0, i)

    def mcd(self, i):
        i = np.asarray(i, dtype=float)
        return np.where(i > 0, self.iv20 * (i / 0.020) * self.eff.rel(i), 0.0)


def dominant_wavelength(x, y, white=(1 / 3, 1 / 3)):
    """Spectral wavelength on the line from `white` through (x, y), 1 nm."""
    lam = np.arange(380.0, 700.5, 1.0)
    X, Y, Z = (np.interp(lam, LAM, c) for c in (XBAR, YBAR, ZBAR))
    s = X + Y + Z
    ang = np.arctan2(Y / s - white[1], X / s - white[0])
    want = np.arctan2(y - white[1], x - white[0])
    return float(lam[np.argmin(np.abs(np.angle(np.exp(1j * (ang - want)))))])


# The model rev A's lamp was chosen with (MEIHUA MHPC3528CRGBCT datasheet,
# LPDS-0001482), kept so that choice can be re-examined.  Its ideality
# factors of 3.2 and 5 put the dies' turn-on 0.3-0.45 V too low, and its
# gamma > 1 has InGaN losing efficiency at low current, which is backwards.
REVA = {
    "R": Die("red", 630.0, 20.0, 337.0, n=3.2, rs=10.0, eff=PowerLaw(1.05),
             vf20=2.00),
    "G": Die("green", 515.0, 32.0, 1685.0, n=5.0, rs=15.0, eff=PowerLaw(1.15),
             vf20=3.00),
    "B": Die("blue", 460.0, 25.0, 500.0, n=5.0, rs=15.0, eff=PowerLaw(1.15),
             vf20=3.05),
}
MHPC3528 = REVA          # the name scripts/lamp_gallery.py knows it by

# The part on the board: MEIHUA MHPA3528CRGBCT (LCSC C2962095), datasheet
# LPDS-0001481.  Dominant wavelengths 622 / 525 / 465 nm; luminous intensity
# is the geometric middle of each colour's full bin range (225-450,
# 1120-2250, 285-715 mcd).  The I-V is anchored at 0.1 mA, where this lamp
# lives, on values typical of the two chip materials; each lands its 20 mA
# forward voltage inside the datasheet's min-max column.
MHPA3528 = {
    "R": Die("red", 625.0, 18.0, 318.0, n=1.8, rs=6.0, eff=SRH(0.20e-3),
             v01=1.64),
    "G": Die("green", 524.0, 32.0, 1587.0, n=2.5, rs=13.0,
             eff=ABC(0.5e-3, 4.0), v01=2.40),
    "B": Die("blue", 463.5, 22.0, 451.0, n=2.35, rs=10.0,
             eff=ABC(1.0e-3, 6.0), v01=2.52),
}

# Datasheet columns, used by the self-test and by SPREAD
VF20_RANGE = {"R": (1.7, 2.3), "G": (2.7, 3.3), "B": (2.7, 3.4)}
IV20_RANGE = {"R": (225.0, 450.0), "G": (1120.0, 2250.0), "B": (285.0, 715.0)}


def spread(rng, nominal=MHPA3528):
    """One plausible real part: bins, forward voltages and efficiency curves
    drawn from the ranges the datasheet and the chip physics allow."""
    out = {}
    for k, d in nominal.items():
        lo, hi = IV20_RANGE[k]
        iv20 = float(np.exp(rng.uniform(np.log(lo), np.log(hi))))
        v01 = d.v_of_i(1e-4) + float(np.clip(rng.normal(0.0, 0.04), -0.08, 0.08))
        n = d.n * float(np.exp(rng.normal(0.0, 0.12)))
        if isinstance(d.eff, SRH):
            eff = SRH(float(np.exp(rng.uniform(np.log(0.07e-3), np.log(0.5e-3)))))
        else:
            eff = ABC(d.eff.i_pk * float(np.exp(rng.uniform(-0.7, 0.7))),
                      d.eff.q * float(np.exp(rng.uniform(-0.35, 0.35))))
        out[k] = Die(d.name, d.lam_p, d.fwhm, iv20, n=n, rs=d.rs, eff=eff,
                     v01=v01)
    return out


# --------------------------------------------------------- perception ----

def xyz_to_xy(xyz):
    s = np.maximum(xyz.sum(axis=-1), 1e-30)
    return xyz[..., 0] / s, xyz[..., 1] / s


def xyz_to_uv(xyz):
    """CIE 1976 u', v' -- the CIE's own near-uniform chromaticity plane."""
    d = np.maximum(xyz[..., 0] + 15.0 * xyz[..., 1] + 3.0 * xyz[..., 2], 1e-30)
    return 4.0 * xyz[..., 0] / d, 9.0 * xyz[..., 1] / d


D65_UV = tuple(float(v) for v in xyz_to_uv(D65_XYZ))

_OK_M1 = np.array([[0.8189330101, 0.3618667424, -0.1288597137],
                   [0.0329845436, 0.9293118715, 0.0361456387],
                   [0.0482003018, 0.2643662691, 0.6338517070]])
_OK_M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468],
                   [1.9779984951, -2.4285922050, 0.4505937099],
                   [0.0259040371, 0.7827717662, -0.8086757660]])


def oklab(xyz):
    """Bjorn Ottosson's OKLab, from D65-relative XYZ.  Its hue angle is the
    most evenly spaced of the simple colour spaces, which is what matters
    when the question is whether all hues get equal time."""
    lms = np.cbrt(xyz @ _OK_M1.T)
    return lms @ _OK_M2.T


def hue_deg(xyz):
    """OKLab hue angle, 0..360, of each colour -- independent of brightness,
    since scaling XYZ scales a and b together."""
    lab = oklab(xyz)
    return np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360.0


def ware_cowan(xyz):
    """Helmholtz-Kohlrausch: how much brighter a saturated light looks than
    its luminance says.  Ware & Cowan (1983), for self-luminous colours:
    log10(B/L) = 0.256 - 0.184y - 2.527xy + 4.656x^3y + 4.657xy^4.
    About 1.7 for this lamp's blue, 1.5 for its red, 1.2 for its green."""
    x, y = xyz_to_xy(xyz)
    return 10.0 ** (0.256 - 0.184 * y - 2.527 * x * y + 4.656 * x ** 3 * y
                    + 4.657 * x * y ** 4)


class Gamut:
    """The triangle of colours the three dies can make, in u'v'.

    saturation() is how far a colour sits from white towards the edge of
    that triangle along its own hue direction: 0 is white, 1 is as vivid as
    this lamp can make that hue -- which happens exactly when no more than
    two dies are lit."""

    def __init__(self, dies):
        pts = []
        for k in "RGB":
            u, v = xyz_to_uv(dies[k].xyz)
            pts.append((float(u), float(v)))
        self.v = np.array(pts)
        self.w = np.array(D65_UV)

    def saturation(self, u, v):
        p = np.stack([u, v], axis=-1) - self.w
        best = np.full(p.shape[:-1], np.inf)
        for a, b in ((0, 1), (1, 2), (2, 0)):
            A, B = self.v[a] - self.w, self.v[b] - self.w
            e = B - A
            den = p[..., 0] * e[1] - p[..., 1] * e[0]
            with np.errstate(divide="ignore", invalid="ignore"):
                t = (A[0] * e[1] - A[1] * e[0]) / den
                q = (A[0] * p[..., 1] - A[1] * p[..., 0]) / den
            ok = (t > 0) & (q >= -1e-9) & (q <= 1 + 1e-9)
            best = np.where(ok, np.minimum(best, t), best)
        s = np.where(np.isfinite(best), 1.0 / best, 0.0)
        return np.clip(s, 0.0, 1.0)


def eye_filter(sig, dt_s, tau_s=0.020, stages=2):
    """What the eye keeps of a light that changes: two first-order stages
    of `tau_s` each, applied along the last axis to a *linear* quantity
    (intensity), sampled every `dt_s` seconds.  Colour flicker faster than
    about 8 Hz is averaged away, which is why a 30 ms red flash can be a
    stripe in a rendered picture and invisible on the bench."""
    from scipy.signal import lfilter
    a = float(np.exp(-dt_s / tau_s))
    out = np.asarray(sig, dtype=float)
    for _ in range(stages):
        zi = out[..., :1] * a
        out, _ = lfilter([1.0 - a], [1.0, -a], out, axis=-1, zi=zi)
    return out


def to_srgb(xyz, white_level):
    """Tristimulus (arbitrary luminance units) -> 8-bit sRGB.

    `white_level` is the luminance that maps to full scale: a dark-adapted eye
    looking at a small lamp sets its own exposure, so every picture here is
    scaled to its own bright end rather than to an absolute candela figure.
    Colours brighter than the screen can show are dimmed as a whole rather
    than clipped channel by channel, which would shift their hue.
    """
    lin = xyz @ XYZ_TO_RGB.T / white_level
    lin = np.clip(lin, 0.0, None)
    over = lin.max(axis=-1, keepdims=True)
    lin = lin / np.where(over > 1.0, over, 1.0)
    srgb = np.where(lin <= 0.0031308, 12.92 * lin,
                    1.055 * np.power(lin, 1 / 2.4) - 0.055)
    return np.clip(np.round(srgb * 255), 0, 255).astype(np.uint8)


def _selftest():
    ok = 0
    # 1. equal-energy white sits at x = y = 1/3
    X, Y, Z = XBAR.sum(), YBAR.sum(), ZBAR.sum()
    s = X + Y + Z
    assert abs(X / s - 1 / 3) < 0.004 and abs(Y / s - 1 / 3) < 0.004, (X/s, Y/s)
    print(f"  equal-energy white at x={X/s:.4f} y={Y/s:.4f} (should be 0.3333)")
    ok += 1

    # 2. the luminosity function peaks at 555 nm and is normalised to 1
    peak = int(np.argmax(YBAR))
    assert LAM[peak] == 555.0 and abs(YBAR[peak] - 1.0) < 1e-9
    print("  y-bar peaks at 555 nm with value 1.000")
    ok += 1

    # 3. monochromatic chromaticities against the published table
    for lam, wx, wy in ((450, 0.1566, 0.0177), (520, 0.0743, 0.8338),
                        (600, 0.6270, 0.3725), (630, 0.7079, 0.2920)):
        i = int((lam - 380) / 5)
        t = XBAR[i] + YBAR[i] + ZBAR[i]
        assert abs(XBAR[i] / t - wx) < 0.002 and abs(YBAR[i] / t - wy) < 0.002, lam
        ok += 1
    print("  four monochromatic chromaticities match the published table")

    # 4. the dies' chromaticities land on their datasheets' dominant
    #    wavelengths: 622 / 525 / 465 nm for the part on the board
    for key, want in (("R", 622.0), ("G", 525.0), ("B", 465.0)):
        d = MHPA3528[key]
        got = d.dominant_nm()
        x, y = d.xy()
        print(f"  {d.name:5s} x={x:.4f} y={y:.4f}  dominant {got:.0f} nm "
              f"(datasheet {want:.0f} nm)")
        assert abs(got - want) <= 2.0
        ok += 1

    # 5. the diode model reproduces its anchor, and the corrected dies land
    #    their 20 mA forward voltage inside the datasheet's min-max column
    for dies, anchor in ((REVA, 0.020), (MHPA3528, 1e-4)):
        for d in dies.values():
            v = d.v_of_i(anchor)
            i = d.current(v, 0.0)
            assert abs(i - anchor) / anchor < 0.02, (d.name, i)
            ok += 1
    for k, d in MHPA3528.items():
        lo, hi = VF20_RANGE[k]
        v20 = float(d.v_of_i(0.020))
        assert lo <= v20 <= hi, (d.name, v20)
        ok += 1
    print("  every die's I-V returns its anchor current; the corrected dies'")
    print("  20 mA voltages sit inside the datasheet's min-max column: " +
          ", ".join(f"{d.name} {float(d.v_of_i(0.020)):.2f} V"
                    for d in MHPA3528.values()))

    # 6. the physics the boards taught us: InGaN is *more* efficient at a
    #    milliamp than at 20 mA, AlGaInP less
    rel = {k: float(d.mcd(1e-3) / d.iv20 / 0.05) for k, d in MHPA3528.items()}
    assert rel["G"] > 1.2 and rel["B"] > 1.1 and rel["R"] < 0.85, rel
    print("  at 1 mA, light per milliamp against 20 mA: " +
          ", ".join(f"{MHPA3528[k].name} {rel[k]:.2f}x" for k in "RGB"))
    ok += 1

    # 7. sRGB and OKLab agree that D65 is white
    grey = to_srgb(D65_XYZ, 1.0)
    assert abs(int(grey[0]) - int(grey[1])) <= 1 and abs(int(grey[1]) - int(grey[2])) <= 1
    lab = oklab(D65_XYZ)
    assert abs(lab[0] - 1.0) < 1e-3 and np.hypot(lab[1], lab[2]) < 1e-3, lab
    print(f"  D65 white maps to sRGB {tuple(int(v) for v in grey)} and to "
          f"OKLab L={lab[0]:.3f} with no chroma")
    ok += 1

    # 8. the gamut: white is 0, every die and every two-die mix is 1
    g = Gamut(MHPA3528)
    pts = [MHPA3528[k].xyz for k in "RGB"]
    pts += [pts[0] + pts[1], pts[1] + pts[2], pts[2] + pts[0], D65_XYZ]
    u, v = xyz_to_uv(np.array(pts))
    sat = g.saturation(u, v)
    assert np.all(np.abs(sat[:6] - 1.0) < 1e-6) and sat[6] < 1e-6, sat
    print("  saturation is 1 for each die and each two-die mix, 0 for white")
    ok += 1

    # 9. the eye filter keeps a steady light steady
    flat = eye_filter(np.ones(500), 0.002)
    assert abs(flat[-1] - 1.0) < 1e-9
    step = eye_filter(np.r_[np.zeros(100), np.ones(400)], 0.002)
    assert 0.2 < step[100 + 20] < 0.8
    print("  the eye filter passes a steady light and takes ~40 ms to follow a step")
    ok += 1
    print(f"{ok} colour-model checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
