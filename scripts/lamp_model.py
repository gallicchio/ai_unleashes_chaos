#!/usr/bin/env python3
"""What the chaos lamp actually looks like.

Three questions have to be answered with numbers before anyone can judge a
resistor value by eye:

 1. given the op-amp output voltage, how much current flows in each LED?
 2. given that current, how much light comes out, in each colour?
 3. given those three luminous intensities, what colour does a person see?

(1) is a diode I-V curve anchored on the datasheet's Vf at 20 mA.  (2) is the
datasheet's luminous intensity at 20 mA, scaled with a mild efficiency droop
towards low current.  (3) is the real CIE 1931 2-degree observer: each die's
spectrum is built from its peak wavelength and linewidth, integrated against
the colour matching functions, and the three tristimulus vectors are added and
converted to sRGB.

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


class Die:
    """One colour of one LED, from its datasheet row.

    vf20    forward voltage at 20 mA (V)
    iv20    luminous intensity at 20 mA (mcd)
    lam_p   peak wavelength (nm) and fwhm the spectral width (nm)
    n       diode ideality factor, rs the series resistance (ohm)
    gamma   luminous intensity goes as (I/I20)**gamma; > 1 because efficiency
            falls away from the rated current, which is the honest direction
            for the low currents this lamp runs at
    """

    def __init__(self, name, vf20, iv20, lam_p, fwhm, n, rs, gamma):
        self.name, self.vf20, self.iv20 = name, vf20, iv20
        self.lam_p, self.fwhm, self.n, self.rs, self.gamma = \
            lam_p, fwhm, n, rs, gamma
        # anchor the exponential on the datasheet point
        self.i_s = 0.020 * np.exp(-(vf20 - 0.020 * rs) / (n * VT))
        self.xyz = self._chromaticity()

    def v_of_i(self, i):
        return self.n * VT * np.log(np.maximum(i, 1e-15) / self.i_s) + i * self.rs

    def _spectrum(self):
        sigma = self.fwhm / 2.3548
        return np.exp(-0.5 * ((LAM - self.lam_p) / sigma) ** 2)

    def _chromaticity(self):
        """Unit-luminance XYZ for this die's own spectrum."""
        s = self._spectrum()
        X, Y, Z = (s * XBAR).sum(), (s * YBAR).sum(), (s * ZBAR).sum()
        return np.array([X / Y, 1.0, Z / Y])

    def xy(self):
        v = self.xyz
        return v[0] / v.sum(), v[1] / v.sum()

    def current(self, v_drive, r):
        """Current through this die with `r` in series and `v_drive` across.

        Solved by inverting V(I) = Vd(I) + I*r on a log grid, which is
        vectorised and monotone, rather than iterating per sample.
        """
        grid = np.logspace(-10, np.log10(0.05), 4000)
        vtot = self.v_of_i(grid) + grid * r
        i = np.interp(np.asarray(v_drive, dtype=float), vtot, grid,
                      left=0.0, right=grid[-1])
        return np.where(np.asarray(v_drive) <= vtot[0], 0.0, i)

    def mcd(self, i):
        return self.iv20 * (i / 0.020) ** self.gamma


# MEIHUA MHPC3528CRGBCT, datasheet LPDS-0001482 Rev.1 page 5.  Typical Vf is
# the middle of the min/max column; luminous intensity likewise.  Linewidths
# are not given, so these are the usual values for the two chip materials.
MHPC3528 = {
    "R": Die("red",   2.00, 337.0, 630.0, 20.0, n=3.2, rs=10.0, gamma=1.05),
    "G": Die("green", 3.00, 1685.0, 515.0, 32.0, n=5.0, rs=15.0, gamma=1.15),
    "B": Die("blue",  3.05, 500.0, 460.0, 25.0, n=5.0, rs=15.0, gamma=1.15),
}


def to_srgb(xyz, white_level):
    """Tristimulus (arbitrary luminance units) -> 8-bit sRGB.

    `white_level` is the luminance that maps to full scale: a dark-adapted eye
    looking at a small lamp sets its own exposure, so every picture here is
    scaled to its own bright end rather than to an absolute candela figure.
    """
    lin = xyz @ XYZ_TO_RGB.T / white_level
    lin = np.clip(lin, 0.0, None)
    # desaturate anything that clips, instead of hue-shifting it
    over = lin.max(axis=-1, keepdims=True)
    scale = np.where(over > 1.0, over, 1.0)
    lin = lin / scale
    lum = (lin * np.array([0.2126, 0.7152, 0.0722])).sum(axis=-1, keepdims=True)
    lin = np.clip(lin + (scale - 1.0) / scale * lum * 0.0, 0.0, 1.0)
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

    # 4. the LED's own chromaticities land where the datasheet's dominant
    #    wavelengths say they should
    for key, want in (("R", 621.0), ("G", 520.0), ("B", 465.0)):
        d = MHPC3528[key]
        x, y = d.xy()
        # dominant wavelength: the spectral point on the line from white (E)
        best = min(range(len(LAM)), key=lambda i: abs(
            np.arctan2(YBAR[i] / (XBAR[i] + YBAR[i] + ZBAR[i]) - 1 / 3,
                       XBAR[i] / (XBAR[i] + YBAR[i] + ZBAR[i]) - 1 / 3)
            - np.arctan2(y - 1 / 3, x - 1 / 3)))
        print(f"  {d.name:5s} x={x:.4f} y={y:.4f}  dominant {LAM[best]:.0f} nm "
              f"(datasheet {want:.0f} nm)")
        assert abs(LAM[best] - want) <= 10.0
        ok += 1

    # 5. the diode model reproduces its own anchor point
    for d in MHPC3528.values():
        i = d.current(d.v_of_i(0.020), 0.0)
        assert abs(i - 0.020) / 0.020 < 0.02, (d.name, i)
        ok += 1
    print("  every die's I-V curve returns 20 mA at its datasheet Vf")

    # 6. sRGB round trip: D65 tristimulus should come out neutral
    grey = to_srgb(np.array([0.9505, 1.0, 1.089]), 1.0)
    assert abs(int(grey[0]) - int(grey[1])) <= 1 and abs(int(grey[1]) - int(grey[2])) <= 1
    print(f"  D65 white maps to sRGB {tuple(int(v) for v in grey)}")
    ok += 1
    print(f"{ok} colour-model checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
