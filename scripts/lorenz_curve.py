"""Integrate the Lorenz system so the board can wear its own portrait.

Used for the 'owl's face' on the schematic and for the silkscreen artwork, so
the picture on the board is the actual solution of the circuit's equations.
"""


def trajectory(s=10.0, r=28.0, b=8.0 / 3.0, dt=0.002, n=60000, skip=4000,
               x0=1.0, y0=1.0, z0=20.0):
    def f(x, y, z):
        return s * (y - x), r * x - y - x * z, x * y - b * z

    x, y, z = x0, y0, z0
    pts = []
    for i in range(n):
        k1 = f(x, y, z)
        k2 = f(x + dt / 2 * k1[0], y + dt / 2 * k1[1], z + dt / 2 * k1[2])
        k3 = f(x + dt / 2 * k2[0], y + dt / 2 * k2[1], z + dt / 2 * k2[2])
        k4 = f(x + dt * k3[0], y + dt * k3[1], z + dt * k3[2])
        x += dt / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
        y += dt / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
        z += dt / 6 * (k1[2] + 2 * k2[2] + 2 * k3[2] + k4[2])
        if i >= skip:
            pts.append((x, y, z))
    return pts


def owl_xz(width, height, cx, cy, n_max=2600, y_down=True, n=60000):
    """The x-z projection -- the 'owl's face' -- fitted into a box.

    `n` sets how much trajectory is drawn.  It has to be traded against
    n_max: decimating a long run down to a few hundred points turns the
    curve into a scribble of straight jumps, so a picture with a small
    point budget should integrate for fewer turns instead.

    Returns a list of (x, y) in sheet/board millimetres, centred on (cx, cy).
    """
    pts = trajectory(n=n)
    xs = [p[0] for p in pts]
    zs = [p[2] for p in pts]
    x0, x1 = min(xs), max(xs)
    z0, z1 = min(zs), max(zs)
    sx = width / (x1 - x0)
    sz = height / (z1 - z0)
    step = max(1, len(pts) // n_max)
    out = []
    for p in pts[::step]:
        px = cx + (p[0] - (x0 + x1) / 2) * sx
        pz = (p[2] - (z0 + z1) / 2) * sz
        out.append((round(px, 3), round(cy - pz if y_down else cy + pz, 3)))
    return out


if __name__ == "__main__":
    pts = owl_xz(80, 60, 100, 100)
    print(f"{len(pts)} points, "
          f"x {min(p[0] for p in pts):.1f}..{max(p[0] for p in pts):.1f}, "
          f"y {min(p[1] for p in pts):.1f}..{max(p[1] for p in pts):.1f}")
