#!/usr/bin/env python3
"""A maze router for the Lorenz board.

Grid A* over the copper layers.  Ground is not routed: it is poured on every
layer and stitched with vias, so the router only handles signal and supply
nets.  Front-layer routes prefer horizontal runs and back-layer routes prefer
vertical ones, which is what keeps a two-layer board readable.

Clearance is measured as a true distance to each piece of copper, not to its
bounding box.  That matters: with box inflation the corner diagonally out of a
0.5 mm-pitch USB-C pad looks blocked when a 0.3 mm track actually fits.

Reads  out/pcb_geom_<n>.json  (written by gen_pcb.py under KiCad's Python)
Writes out/routes_<n>.json    (segments, vias and stitches, in millimetres)
"""
import heapq, json, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcb_place as P

GRID = 0.20            # mm per cell
CLEARANCE = 0.20       # matches the project design rules
# One width everywhere.  The rails carry about 20 mA, so 0.3 mm is a factor
# of ten more copper than needed, and a single width lets one halo serve every
# net -- with a wider power width the halo has to be sized for it, and that
# extra 0.05 mm is exactly what blocks the escape from a 0.5 mm-pitch USB-C
# pad.
TRACK = 0.30           # every track
POWER_TRACK = 0.30
VIA_DIA = 0.80
VIA_DRILL = 0.30
HOLE_TO_HOLE = 0.50
EDGE_KEEPOUT = 0.45    # copper to board edge, with margin over the 0.3 rule

# One grid serves every net, so halos are sized for the widest track.
PAD_HALO = CLEARANCE + POWER_TRACK / 2.0
VIA_HALO = CLEARANCE + VIA_DIA / 2.0

POWER_NETS = {"+5V", "+12V", "-12V", "+15V", "-15V"}

# Nets carried by a plane instead of tracks.  On two layers that is ground
# alone; the four-layer stack adds +12 V on the second inner layer, which is
# the classic signal / ground / power / signal arrangement.
# GNDU is the USB side of the isolation barrier: its own pour in the bottom
# left corner of the board, never touching the analog ground.
PLANES = {2: ["GND", "GNDU"], 4: ["GND", "GNDU"]}
# Nets that also get a plane of their own, but are still routed normally: the
# plane is tied to the routed copper by vias dropped onto its own tracks.
PLANE_TIED = {4: ["+12V"]}

STEP, DIAG = 10, 14
OFF_AXIS = 3           # gentle bias toward the layer's preferred direction
VIA_COST = 120

HARD = 9               # halo_cnt value meaning "nobody may route here"


def track_width(net):
    return POWER_TRACK if net in POWER_NETS else TRACK


class Grid:
    def __init__(self, geom):
        self.w, self.h = geom["board_w"], geom["board_h"]
        self.layers = list(geom["copper"])
        self.nl = len(self.layers)
        # tracks only ever run on the outer layers; anything between them is
        # a plane, and a via still passes through it
        self.route_layers = [0] if self.nl == 1 else [0, self.nl - 1]
        self.nx = int(math.ceil(self.w / GRID)) + 1
        self.ny = int(math.ceil(self.h / GRID)) + 1
        shape = (self.nl, self.ny, self.nx)
        self.core = np.zeros(shape, dtype=np.int16)
        self.halo_cnt = np.zeros(shape, dtype=np.uint8)
        self.halo_net = np.zeros(shape, dtype=np.int16)
        self.novia = np.zeros((self.ny, self.nx), dtype=bool)
        self.net_id, self.net_name = {}, {0: ""}

    # ---- indexing ------------------------------------------------------
    def idx(self, l, iy, ix):
        return (l * self.ny + iy) * self.nx + ix

    def cell(self, x, y):
        return int(round(x / GRID)), int(round(y / GRID))

    def pos(self, ix, iy):
        return ix * GRID, iy * GRID

    def nid(self, name):
        if name not in self.net_id:
            self.net_id[name] = len(self.net_id) + 1
            self.net_name[self.net_id[name]] = name
        return self.net_id[name]

    def window(self, x0, y0, x1, y1):
        ix0 = max(0, int(math.floor(x0 / GRID)))
        ix1 = min(self.nx - 1, int(math.ceil(x1 / GRID)))
        iy0 = max(0, int(math.floor(y0 / GRID)))
        iy1 = min(self.ny - 1, int(math.ceil(y1 / GRID)))
        return ix0, iy0, ix1, iy1

    # ---- stamping ------------------------------------------------------
    def _apply(self, layers, dist, ix0, iy0, halo, nid, hard=False):
        """Write copper (dist <= 0) and its halo into the grid."""
        inside = dist <= 0.0
        near = dist <= halo
        iy1, ix1 = iy0 + dist.shape[0], ix0 + dist.shape[1]
        for l in layers:
            core = self.core[l, iy0:iy1, ix0:ix1]
            cnt = self.halo_cnt[l, iy0:iy1, ix0:ix1]
            who = self.halo_net[l, iy0:iy1, ix0:ix1]
            if hard:
                cnt[near] = HARD
                core[inside] = -1
                continue
            fresh = near & (cnt == 0)
            other = near & (cnt == 1) & (who != nid)
            who[fresh] = nid
            cnt[fresh] = 1
            cnt[other] = 2
            core[inside] = nid

    def stamp_rect(self, layers, x0, y0, x1, y1, net, halo, hard=False):
        nid = self.nid(net) if net else 0
        ix0, iy0, ix1, iy1 = self.window(x0 - halo, y0 - halo,
                                         x1 + halo, y1 + halo)
        if ix1 < ix0 or iy1 < iy0:
            return
        X, Y = np.meshgrid(np.arange(ix0, ix1 + 1) * GRID,
                           np.arange(iy0, iy1 + 1) * GRID)
        dx = np.maximum(np.maximum(x0 - X, X - x1), 0.0)
        dy = np.maximum(np.maximum(y0 - Y, Y - y1), 0.0)
        self._apply(layers, np.hypot(dx, dy), ix0, iy0, halo, nid, hard)

    def stamp_capsule(self, layer, ax, ay, bx, by, width, net, halo):
        """A track segment: everything within width/2 of the centre line."""
        nid = self.nid(net)
        r = width / 2.0
        ix0, iy0, ix1, iy1 = self.window(min(ax, bx) - r - halo,
                                         min(ay, by) - r - halo,
                                         max(ax, bx) + r + halo,
                                         max(ay, by) + r + halo)
        if ix1 < ix0 or iy1 < iy0:
            return
        X, Y = np.meshgrid(np.arange(ix0, ix1 + 1) * GRID,
                           np.arange(iy0, iy1 + 1) * GRID)
        vx, vy = bx - ax, by - ay
        L2 = vx * vx + vy * vy
        if L2 < 1e-12:
            t = np.zeros_like(X)
        else:
            t = np.clip(((X - ax) * vx + (Y - ay) * vy) / L2, 0.0, 1.0)
        d = np.hypot(X - (ax + t * vx), Y - (ay + t * vy)) - r
        self._apply([layer], d, ix0, iy0, halo, nid)

    def block_vias(self, x0, y0, x1, y1):
        ix0, iy0, ix1, iy1 = self.window(x0, y0, x1, y1)
        if ix1 >= ix0 and iy1 >= iy0:
            self.novia[iy0:iy1 + 1, ix0:ix1 + 1] = True

    def masks(self, nid):
        """Flat passability for one net, plus where a via has room.

        Computing these with array ops once per connection keeps the search
        loop cheap; testing the same conditions cell by cell inside A* made an
        earlier version unusably slow.
        """
        # A net is always allowed to sit on its own copper: clearance does not
        # apply between a pad and the track landing on it.  Without this a
        # 0.3 mm USB-C pad is unreachable, because its neighbours' halos cover
        # the pad itself.
        mine = self.core == nid
        free = (self.core == 0) & ((self.halo_cnt == 0)
                                   | ((self.halo_cnt == 1)
                                      & (self.halo_net == nid)))
        ok = mine | free
        r = int(math.ceil(VIA_HALO / GRID))
        room = np.ones((self.ny, self.nx), dtype=bool)
        for l in range(self.nl):
            a = ok[l]
            e = a.copy()
            for d in range(1, r + 1):           # separable erosion
                e &= np.roll(a, d, axis=1) & np.roll(a, -d, axis=1)
            f = e.copy()
            for d in range(1, r + 1):
                f &= np.roll(e, d, axis=0) & np.roll(e, -d, axis=0)
            room &= f
        room[:r, :] = False
        room[-r:, :] = False
        room[:, :r] = False
        room[:, -r:] = False
        room &= ~self.novia
        return ok.reshape(-1), room.reshape(-1)


def build_grid(geom):
    g = Grid(geom)
    lay_index = {name: i for i, name in enumerate(g.layers)}
    alll = list(range(g.nl))

    b = EDGE_KEEPOUT
    g.stamp_rect(alll, -5, -5, g.w + 5, b, "", 0.0, hard=True)
    g.stamp_rect(alll, -5, g.h - b, g.w + 5, g.h + 5, "", 0.0, hard=True)
    g.stamp_rect(alll, -5, -5, b, g.h + 5, "", 0.0, hard=True)
    g.stamp_rect(alll, g.w - b, -5, g.w + 5, g.h + 5, "", 0.0, hard=True)
    for (cx, cy) in ((3, 3), (g.w - 3, 3), (3, g.h - 3), (g.w - 3, g.h - 3)):
        sx = -1 if cx < g.w / 2 else 1
        sy = -1 if cy < g.h / 2 else 1
        g.stamp_rect(alll, min(cx, cx + sx * 3.5), min(cy, cy + sy * 3.5),
                     max(cx, cx + sx * 3.5), max(cy, cy + sy * 3.5),
                     "", 0.0, hard=True)

    pads = []
    for p in geom["pads"]:
        layers = alll if p["through"] else [lay_index[l] for l in p["layers"]
                                            if l in lay_index]
        hw, hh = p["w"] / 2.0, p["h"] / 2.0
        cx, cy = p.get("cx", p["x"]), p.get("cy", p["y"])
        g.stamp_rect(layers, cx - hw, cy - hh, cx + hw, cy + hh,
                     p["net"] or "", PAD_HALO,
                     hard=not (p["net"] or "").strip())
        if p["through"] and p["drill"] > 0:
            k = p["drill"] / 2.0 + HOLE_TO_HOLE + VIA_DRILL / 2.0
            g.block_vias(p["x"] - k, p["y"] - k, p["x"] + k, p["y"] + k)
        pads.append({**p, "li": layers})
    m = EDGE_KEEPOUT + 0.5
    g.block_vias(-5, -5, g.w + 5, m)
    g.block_vias(-5, g.h - m, g.w + 5, g.h + 5)
    g.block_vias(-5, -5, m, g.h + 5)
    g.block_vias(g.w - m, -5, g.w + 5, g.h + 5)
    return g, pads


def pad_cells(g, pad, nid):
    """Grid cells genuinely inside this pad, on the layers it lives on.

    Anchored on the pad's own position rather than its bounding box, so that a
    route always starts on real copper even for a custom-shaped pad.
    """
    hw = max(min(pad["w"], 1.2) / 2.0 - GRID * 0.5, 0.01)
    hh = max(min(pad["h"], 1.2) / 2.0 - GRID * 0.5, 0.01)
    ix0, iy0, ix1, iy1 = g.window(pad["x"] - hw, pad["y"] - hh,
                                  pad["x"] + hw, pad["y"] + hh)
    out = []
    for l in pad["li"]:
        for iy in range(iy0, iy1 + 1):
            for ix in range(ix0, ix1 + 1):
                x, y = g.pos(ix, iy)
                if abs(x - pad["x"]) <= hw and abs(y - pad["y"]) <= hh \
                        and g.core[l, iy, ix] == nid:
                    out.append(g.idx(l, iy, ix))
    if not out:
        ix, iy = g.cell(pad["x"], pad["y"])
        out = [g.idx(l, iy, ix) for l in pad["li"]]
    return out


DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]


def astar(g, nid, sources, target_set, target_pts, prefer_horiz, masks):
    ok, via_room = masks
    BIG = np.int32(2 ** 30)
    n = g.nl * g.ny * g.nx
    dist = np.full(n, BIG, dtype=np.int32)
    prev = np.full(n, -1, dtype=np.int32)
    nx, stride = g.nx, g.ny * g.nx

    def h(flat):
        l, rem = divmod(int(flat), stride)
        iy, ix = divmod(rem, nx)
        best = BIG
        for (tx, ty) in target_pts:
            dx, dy = abs(ix - tx), abs(iy - ty)
            best = min(best, DIAG * min(dx, dy) + STEP * (max(dx, dy) - min(dx, dy)))
        return best

    heap = []
    for s in sources:
        if dist[s] > 0:
            dist[s] = 0
            heapq.heappush(heap, (h(s), int(s)))
    hit = -1
    while heap:
        f, cur = heapq.heappop(heap)
        d = int(dist[cur])
        if f > d + h(cur):
            continue
        if cur in target_set:
            hit = cur
            break
        l, rem = divmod(cur, stride)
        iy, ix = divmod(rem, nx)
        if l not in g.route_layers:
            continue
        horiz = prefer_horiz[l]
        for (dx, dy) in DIRS:
            jx, jy = ix + dx, iy + dy
            if not (0 <= jx < nx and 0 <= jy < g.ny):
                continue
            nf = g.idx(l, jy, jx)
            if not ok[nf]:
                continue
            if dx and dy:
                if not (ok[g.idx(l, iy, jx)] and ok[g.idx(l, jy, ix)]):
                    continue
                step = DIAG
            else:
                step = STEP + (0 if (bool(dx) == horiz) else OFF_AXIS)
            nd = d + step
            if nd < dist[nf]:
                dist[nf] = nd
                prev[nf] = cur
                heapq.heappush(heap, (nd + h(nf), nf))
        if via_room[iy * nx + ix]:
            for l2 in g.route_layers:
                if l2 == l:
                    continue
                nf = g.idx(l2, iy, ix)
                if not ok[nf]:
                    continue
                nd = d + VIA_COST
                if nd < dist[nf]:
                    dist[nf] = nd
                    prev[nf] = cur
                    heapq.heappush(heap, (nd + h(nf), nf))
    if hit < 0:
        return None
    path, cur = [], hit
    while cur != -1:
        path.append(int(cur))
        cur = int(prev[cur])
    return path[::-1]


def path_to_shapes(g, path, net):
    """Turn a cell path into straight segments plus vias."""
    stride = g.ny * g.nx
    pts = []
    for f in path:
        l, rem = divmod(f, stride)
        iy, ix = divmod(rem, g.nx)
        pts.append((l, ix, iy))
    segs, vias, run = [], [], [pts[0]]
    for prv, p in zip(pts, pts[1:]):
        if p[0] != prv[0]:
            if len(run) > 1:
                segs.append((run[0], run[-1]))
            segs and None
            x, y = g.pos(prv[1], prv[2])
            vias.append((x, y))
            run = [p]
            continue
        if len(run) == 1:
            run.append(p)
            continue
        dxa, dya = run[-1][1] - run[0][1], run[-1][2] - run[0][2]
        dxb, dyb = p[1] - run[-1][1], p[2] - run[-1][2]
        if dxa * dyb == dya * dxb and dxa * dxb >= 0 and dya * dyb >= 0:
            run.append(p)
        else:
            segs.append((run[0], run[-1]))
            run = [run[-1], p]
    if len(run) > 1:
        segs.append((run[0], run[-1]))
    out = [{"layer": g.layers[a[0]],
            "x1": round(a[1] * GRID, 4), "y1": round(a[2] * GRID, 4),
            "x2": round(b[1] * GRID, 4), "y2": round(b[2] * GRID, 4),
            "width": track_width(net)} for (a, b) in segs]
    return out, [{"x": round(x, 4), "y": round(y, 4)} for (x, y) in vias]


def stub(g, cell, centre, net):
    """A short run from a path end to the exact pad centre it belongs to.

    The grid only approximates a pad outline, so a path can finish a fraction
    inside the edge; this makes the connection unambiguous for KiCad.
    """
    stride = g.ny * g.nx
    l, rem = divmod(int(cell), stride)
    iy, ix = divmod(rem, g.nx)
    x, y = g.pos(ix, iy)
    if abs(x - centre[0]) < 1e-9 and abs(y - centre[1]) < 1e-9:
        return None
    return {"layer": g.layers[l],
            "x1": round(centre[0], 4), "y1": round(centre[1], 4),
            "x2": round(x, 4), "y2": round(y, 4),
            "width": track_width(net)}


def stamp_route(g, net, segs, vias):
    lay = {name: i for i, name in enumerate(g.layers)}
    halo = CLEARANCE + track_width(net) / 2.0
    # The halo has to hold the clearance *plus* the half-width of whatever
    # track comes next, or two 0.3 mm tracks end up 0.05 mm apart.
    for s in segs:
        g.stamp_capsule(lay[s["layer"]], s["x1"], s["y1"], s["x2"], s["y2"],
                        s["width"], net, halo)
    for v in vias:
        g.stamp_rect(list(range(g.nl)), v["x"] - VIA_DIA / 2, v["y"] - VIA_DIA / 2,
                     v["x"] + VIA_DIA / 2, v["y"] + VIA_DIA / 2, net, halo)
        k = VIA_DRILL + HOLE_TO_HOLE
        g.block_vias(v["x"] - k, v["y"] - k, v["x"] + k, v["y"] + k)


def in_plane(net, x, y, margin=0.0):
    """Is (x, y) inside the region this plane net is allowed to occupy?

    A stitching via for one plane dropped inside the other plane's island
    would be an isolated piece of copper at best and a short at worst, so
    every via is tested against the same rectangle the zones are cut from.
    """
    inside = P.in_island(x, y, -margin)
    return inside if net == "GNDU" else not P.in_island(x, y, margin + P.ISLAND_GAP)


def stitch_vias(g, pads, net="GND", spacing=4.5, lattice=True):
    """Ground stitching vias wherever every layer is genuinely free.

    Signal tracks cut the front pour into islands; each one needs a via or it
    floats, so this lays a fairly dense lattice and then adds a via beside
    every ground pad that has room, which is what ties the local pour under a
    package back to the plane.
    """
    nid = g.nid(net)
    step = max(1, int(round(spacing / GRID)))
    r = int(math.ceil(VIA_HALO / GRID))
    # A through-hole pad already ties every layer together, so it needs no
    # stitching via beside it -- and a via *near* one leaves a neck of copper
    # between the two, narrower than the minimum connection width, which is a
    # real manufacturing defect rather than a rule-book one.
    for p in pads:
        if not p["through"]:
            continue
        k = VIA_DIA / 2.0 + 0.35
        g.block_vias(p["cx"] - p["w"] / 2 - k, p["cy"] - p["h"] / 2 - k,
                     p["cx"] + p["w"] / 2 + k, p["cy"] + p["h"] / 2 + k)
    _, room = g.masks(nid)
    room = room.reshape(g.ny, g.nx)
    out = []

    def place(ix, iy):
        x, y = g.pos(ix, iy)
        out.append({"x": round(x, 3), "y": round(y, 3)})
        g.stamp_rect(list(range(g.nl)), x - VIA_DIA / 2, y - VIA_DIA / 2,
                     x + VIA_DIA / 2, y + VIA_DIA / 2, net,
                     CLEARANCE + TRACK / 2.0)
        k = VIA_DRILL + HOLE_TO_HOLE
        g.block_vias(x - k, y - k, x + k, y + k)
        return g.masks(nid)[1].reshape(g.ny, g.nx)

    # one beside each surface ground pad first, so no pour island is left
    # floating; the through-hole ones are their own vias
    reach = int(round(2.4 / GRID))
    for p in pads:
        if p["net"] != net or p["through"]:
            continue
        px, py = g.cell(p["x"], p["y"])
        best = None
        for dy in range(-reach, reach + 1):
            for dx in range(-reach, reach + 1):
                iy, ix = py + dy, px + dx
                if not (r <= iy < g.ny - r and r <= ix < g.nx - r):
                    continue
                if not room[iy, ix]:
                    continue
                if not in_plane(net, *g.pos(ix, iy), margin=VIA_DIA / 2):
                    continue
                d = dx * dx + dy * dy
                if best is None or d < best[0]:
                    best = (d, ix, iy)
        if best:
            room = place(best[1], best[2])

    if lattice:
        for iy in range(r, g.ny - r, step):
            for ix in range(r, g.nx - r, step):
                if not room[iy, ix]:
                    continue
                if not in_plane(net, *g.pos(ix, iy), margin=VIA_DIA / 2):
                    continue
                room = place(ix, iy)
    return out


def plane_ties(g, segments, net, want=6):
    """Drop vias onto a net's own tracks so its plane is really connected.

    A stitching via merely *near* a pad works for ground, because ground is
    poured on the pad's own layer too.  A power plane on an inner layer is
    not, so its vias have to land on copper that already belongs to the net.
    """
    nid = g.nid(net)
    _, room = g.masks(nid)
    room = room.reshape(g.ny, g.nx)
    out = []
    for s in sorted(segments, key=lambda s: -((s["x2"] - s["x1"]) ** 2
                                              + (s["y2"] - s["y1"]) ** 2)):
        if len(out) >= want:
            break
        for t in (0.5, 0.35, 0.65, 0.2, 0.8):
            x = s["x1"] + t * (s["x2"] - s["x1"])
            y = s["y1"] + t * (s["y2"] - s["y1"])
            ix, iy = g.cell(x, y)
            if not room[iy, ix]:
                continue
            gx, gy = g.pos(ix, iy)
            out.append({"x": round(gx, 3), "y": round(gy, 3)})
            g.stamp_rect(list(range(g.nl)), gx - VIA_DIA / 2, gy - VIA_DIA / 2,
                         gx + VIA_DIA / 2, gy + VIA_DIA / 2, net,
                         CLEARANCE + TRACK / 2.0)
            k = VIA_DRILL + HOLE_TO_HOLE
            g.block_vias(gx - k, gy - k, gx + k, gy + k)
            room = g.masks(nid)[1].reshape(g.ny, g.nx)
            break
    return out


def route_board(geom, priority=()):
    g, pads = build_grid(geom)
    g._pads = pads
    by_net = {}
    for p in pads:
        if p["net"] and not p["net"].startswith("unconnected-"):
            by_net.setdefault(p["net"], []).append(p)

    prefer_horiz = [True] * g.nl
    prefer_horiz[-1] = False                 # back layer runs vertically
    planes = set(PLANES.get(g.nl, ["GND"]))
    todo = [(n, ps) for n, ps in by_net.items()
            if n not in planes and len(ps) > 1]
    prio = {n: i for i, n in enumerate(priority)}

    def key(item):
        n, ps = item
        span = (max(p["x"] for p in ps) - min(p["x"] for p in ps)) + \
               (max(p["y"] for p in ps) - min(p["y"] for p in ps))
        return (-1, prio[n]) if n in prio else (0 if n in POWER_NETS else 1, span)
    todo.sort(key=key)

    routes, failures = {}, []
    for net, ps in todo:
        nid = g.nid(net)
        remaining = list(ps)
        first = remaining.pop(0)
        cell_pad = {c: (first["x"], first["y"]) for c in pad_cells(g, first, nid)}
        blob = set(cell_pad)
        blob_pts = [g.cell(first["x"], first["y"])]
        segs_all, vias_all = [], []
        while remaining:
            def d2(p):
                px, py = g.cell(p["x"], p["y"])
                return min((px - bx) ** 2 + (py - by) ** 2 for (bx, by) in blob_pts)
            remaining.sort(key=d2)
            nxt = remaining.pop(0)
            src = pad_cells(g, nxt, nid)
            path = astar(g, nid, src, blob, blob_pts, prefer_horiz, g.masks(nid))
            if path is None:
                failures.append((net, f"{nxt['ref']}.{nxt['pad']}"))
                blob |= set(src)
                for c in src:
                    cell_pad[c] = (nxt["x"], nxt["y"])
                blob_pts.append(g.cell(nxt["x"], nxt["y"]))
                continue
            segs, vias = path_to_shapes(g, path, net)
            head = stub(g, path[0], (nxt["x"], nxt["y"]), net)
            tail_pad = cell_pad.get(path[-1])
            tail = stub(g, path[-1], tail_pad, net) if tail_pad else None
            segs = ([head] if head else []) + segs + ([tail] if tail else [])
            stamp_route(g, net, segs, vias)
            segs_all += segs
            vias_all += vias
            blob |= set(path) | set(src)
            for c in src:
                cell_pad[c] = (nxt["x"], nxt["y"])
            blob_pts.append(g.cell(nxt["x"], nxt["y"]))
        # A pad reached twice picks up the same escape stub twice; a doubled
        # track is harmless but it is redundant copper and it makes two board
        # items indistinguishable.
        seen, uniq = set(), []
        for sg in segs_all:
            key = (sg["layer"],) + tuple(sorted(
                [(round(sg["x1"], 4), round(sg["y1"], 4)),
                 (round(sg["x2"], 4), round(sg["y2"], 4))]))
            if key in seen:
                continue
            seen.add(key)
            uniq.append(sg)
        vseen, vuniq = set(), []
        for v in vias_all:
            key = (round(v["x"], 4), round(v["y"], 4))
            if key in vseen:
                continue
            vseen.add(key)
            vuniq.append(v)
        routes[net] = {"segments": uniq, "vias": vuniq}
    return g, routes, failures


def main():
    layers = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.abspath(os.path.join(here, "..", "out"))
    geom = json.load(open(os.path.join(out, f"pcb_geom_{layers}.json")))
    priority, best = (), None
    for attempt in range(5):
        g, routes, failures = route_board(geom, priority)
        if best is None or len(failures) < len(best[1]):
            best, best_g = (routes, failures), g
            best_pads = g._pads
        if not failures:
            best_g, best_pads = g, g._pads
            break
        priority = tuple(dict.fromkeys([n for (n, _) in failures] + list(priority)))
        print(f"  attempt {attempt + 1}: {len(failures)} unrouted, retrying")
    routes, failures = best
    stitches = []
    for i, net in enumerate(PLANES.get(layers, ["GND"])):
        stitches += [dict(v, net=net) for v in
                     stitch_vias(best_g, best_pads, net=net,
                                 spacing=4.5 if net == "GND" else 3.5,
                                 lattice=True)]
    for net in PLANE_TIED.get(layers, []):
        ties = plane_ties(best_g, routes.get(net, {}).get("segments", []), net)
        stitches += [dict(v, net=net) for v in ties]
        if not ties:
            print(f"  !! no via could be placed on the {net} plane's tracks")
    nseg = sum(len(r["segments"]) for r in routes.values())
    nvia = sum(len(r["vias"]) for r in routes.values())
    path = os.path.join(out, f"routes_{layers}.json")
    json.dump({"routes": routes, "failures": failures, "stitches": stitches},
              open(path, "w"), indent=1)
    print(f"  routed {len(routes)} nets: {nseg} segments, {nvia} vias, "
          f"{len(stitches)} plane stitches"
          + (f"; {len(failures)} FAILED" if failures else ""))
    for (net, pad) in failures[:10]:
        print(f"     could not reach {pad} on net {net}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
