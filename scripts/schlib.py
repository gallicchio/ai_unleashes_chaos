"""Builder for a KiCad schematic sheet.

Written in the 20250114 (KiCad 9) dialect and handed to `kicad-cli sch upgrade`,
which normalises it to whatever the installed KiCad writes natively.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexp import S, q, n, uid, effects
from sexp_parse import SymbolLibs, Node

SCH_VERSION = "20250114"

# Library-space -> sheet-space for each placement angle.  Symbol libraries use
# Y-up, schematics use Y-down; these were checked against KiCad's own netlister
# by scripts/selftest_rotation.py.
_ROT = {
    0:   lambda px, py: (px, -py),
    90:  lambda px, py: (-py, -px),
    180: lambda px, py: (-px, py),
    270: lambda px, py: (py, px),
}


class Sheet:
    def __init__(self, share_dir, paper="A3", title="", date="", rev="",
                 company="", comments=()):
        self.libs = SymbolLibs(share_dir)
        self.paper = paper
        self.title, self.date, self.rev, self.company = title, date, rev, company
        self.comments = list(comments)
        self.lib_symbols = {}          # lib_id -> resolved Node
        self.items = []                # rendered S nodes, in file order
        self.symbols = []              # (ref, lib_id, x, y, rot, unit, pins)
        self._pin_cache = {}
        self._segments = []            # ((x1,y1),(x2,y2)) for the junction pass
        self._junctions = set()
        self._extra_libs = {}          # lib_id -> Node, for project-local symbols

    # ---------------------------------------------------------- libraries --
    def add_local_lib(self, path, prefix):
        """Register a project .kicad_sym so its symbols can be placed."""
        from sexp_parse import parse_file
        root = parse_file(path)
        for sym in root.kids("symbol"):
            name = sym.atom(0)
            self._extra_libs[f"{prefix}:{name}"] = sym

    def _resolve(self, lib_id):
        if lib_id in self.lib_symbols:
            return self.lib_symbols[lib_id]
        if lib_id in self._extra_libs:
            node = _clone_with_id(self._extra_libs[lib_id], lib_id)
        else:
            lib, name = lib_id.split(":", 1)
            node = self.libs.get(lib, name)
        self.lib_symbols[lib_id] = node
        return node

    def all_pin_numbers(self, lib_id):
        """Every pin of a symbol, across all its units.

        A placed symbol carries a uuid entry for each of them, not just the
        unit on the sheet; emitting only the unit's pins leaves KiCad to invent
        random ones for the rest, and the file stops being reproducible.
        """
        sym = self._resolve(lib_id)
        out = []
        for sub in sym.kids("symbol"):
            for p in sub.kids("pin"):
                num = p.first("number").atom(0)
                if num not in out:
                    out.append(num)
        return out

    def pin_offsets(self, lib_id, unit):
        """{pin number: (px, py)} in library space for one unit."""
        key = (lib_id, unit)
        if key in self._pin_cache:
            return self._pin_cache[key]
        sym = self._resolve(lib_id)
        base = lib_id.split(":", 1)[1]
        out = {}
        for sub in sym.kids("symbol"):
            nm = sub.atom(0) or ""
            parts = nm.rsplit("_", 2)
            u = int(parts[1]) if len(parts) == 3 and parts[1].isdigit() else 0
            if u not in (0, unit):
                continue
            for p in sub.kids("pin"):
                a = p.first("at")
                num = p.first("number").atom(0)
                out[num] = (float(a.atom(0)), float(a.atom(1)))
        self._pin_cache[key] = out
        return out

    # ------------------------------------------------------------ drawing --
    def place(self, lib_id, ref, value, x, y, rot=0, unit=1, footprint="",
              fields=None, mirror=None, hide_value=False, hide_ref=False,
              ref_off=(0, -7.62), val_off=(0, 7.62), in_bom=True, on_board=True,
              dnp=False, ref_justify=None, val_justify=None):
        self._resolve(lib_id)
        sid = uid(f"sym/{ref}/{unit}")
        s = S("symbol")
        s.add(S("lib_id", q(lib_id)), S("at", n(x), n(y), n(rot)))
        if mirror:
            s.add(S("mirror", mirror))
        s.add(S("unit", n(unit)), S("exclude_from_sim", "no"),
              S("in_bom", "yes" if in_bom else "no"),
              S("on_board", "yes" if on_board else "no"),
              S("dnp", "yes" if dnp else "no"), S("uuid", q(sid)))

        # KiCad adds the symbol's rotation to a field's stored angle, so a
        # field on a 90/270-rotated symbol needs 90 stored to read horizontally.
        fang = 90 if int(rot) % 360 in (90, 270) else 0

        def field(name, val, dx, dy, hide, justify=None, size=1.27):
            p = S("property", q(name), q(val))
            p.add(S("at", n(x + dx), n(y + dy), n(fang)))
            if hide:
                p.add(S("hide", "yes"))
            p.add(effects(size=size, justify=justify))
            return p

        s.add(field("Reference", ref, *ref_off, hide_ref, ref_justify),
              field("Value", value, *val_off, hide_value, val_justify),
              field("Footprint", footprint, 0, 0, True),
              field("Datasheet", "", 0, 0, True),
              field("Description", "", 0, 0, True))
        for k, v in (fields or {}).items():
            s.add(field(k, v, 0, 0, True))

        pins = self.pin_offsets(lib_id, unit)
        for num in self.all_pin_numbers(lib_id):
            s.add(S("pin", q(num)).add(S("uuid", q(uid(f"pin/{ref}/{unit}/{num}")))))
        inst = S("instances").add(
            S("project", q("lorenz")).add(
                S("path", q("/" + uid("sheet/root"))).add(
                    S("reference", q(ref)), S("unit", n(unit)))))
        s.add(inst)
        self.items.append(s)
        self.symbols.append((ref, lib_id, x, y, rot, unit, pins, mirror))
        return ref

    def pin(self, ref, unit, number):
        """Absolute sheet coordinates of one pin of a placed symbol."""
        for (r, lib_id, x, y, rot, u, pins, mir) in self.symbols:
            if r == ref and u == unit:
                px, py = pins[str(number)]
                dx, dy = _ROT[int(rot) % 360](px, py)
                # KiCad applies the mirror in sheet space, after the rotation
                if mir == "x":
                    dy = -dy
                elif mir == "y":
                    dx = -dx
                return (round(x + dx, 4), round(y + dy, 4))
        raise KeyError(f"no placed symbol {ref} unit {unit}")

    def wire(self, *points):
        pts = [(round(a, 4), round(b, 4)) for a, b in points]
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            if (x1, y1) == (x2, y2):
                continue
            w = S("wire").add(
                S("pts").add(S("xy", n(x1), n(y1)), S("xy", n(x2), n(y2))),
                S("stroke").add(S("width", "0"), S("type", "default")),
                S("uuid", q(uid(f"wire/{x1},{y1},{x2},{y2}"))))
            self.items.append(w)
            self._segments.append(((x1, y1), (x2, y2)))

    def elbow(self, p, q_, first="h"):
        """Two-segment wire between p and q_ (horizontal-then-vertical)."""
        (x1, y1), (x2, y2) = p, q_
        mid = (x2, y1) if first == "h" else (x1, y2)
        self.wire(p, mid, q_)

    def junction(self, x, y):
        if (round(x, 3), round(y, 3)) in self._junctions:
            return
        self._junctions.add((round(x, 3), round(y, 3)))
        self.items.append(S("junction").add(
            S("at", n(x), n(y)), S("diameter", "0"),
            S("color", "0", "0", "0", "0"),
            S("uuid", q(uid(f"junc/{x},{y}")))))

    def no_connect(self, x, y):
        self.items.append(S("no_connect").add(
            S("at", n(x), n(y)), S("uuid", q(uid(f"nc/{x},{y}")))))

    def text(self, txt, x, y, size=1.5, rot=0, justify="left", bold=False):
        t = S("text", q(txt))
        t.add(S("exclude_from_sim", "no"), S("at", n(x), n(y), n(rot)))
        e = effects(size=size, justify=justify)
        if bold:
            e.first("font").add(S("bold", "yes"))
        t.add(e, S("uuid", q(uid(f"txt/{x},{y},{txt[:24]}"))))
        self.items.append(t)

    def label(self, txt, x, y, size=1.27, rot=0, justify="left"):
        l = S("label", q(txt))
        l.add(S("at", n(x), n(y), n(rot)),
              effects(size=size, justify=justify),
              S("uuid", q(uid(f"lbl/{x},{y},{txt}"))))
        self.items.append(l)

    def polyline(self, points, width=0.15, style="default", key=None):
        pts = S("pts")
        for (px, py) in points:
            pts.add(S("xy", n(px), n(py)))
        self.items.append(S("polyline").add(
            pts, S("stroke").add(S("width", n(width)), S("type", style)),
            S("uuid", q(uid(key or f"poly/{points[0]}/{len(points)}")))))

    def rect(self, x1, y1, x2, y2, width=0.15, style="default", fill="none", key=None):
        self.items.append(S("rectangle").add(
            S("start", n(x1), n(y1)), S("end", n(x2), n(y2)),
            S("stroke").add(S("width", n(width)), S("type", style)),
            S("fill").add(S("type", fill)),
            S("uuid", q(key or f"rect/{x1},{y1}"))))

    def circle(self, cx, cy, r, width=0.15, fill="none", key=None):
        self.items.append(S("circle").add(
            S("center", n(cx), n(cy)), S("radius", n(r)),
            S("stroke").add(S("width", n(width)), S("type", "default")),
            S("fill").add(S("type", fill)),
            S("uuid", q(uid(key or f"circ/{cx},{cy},{r}")))))

    # --------------------------------------------------------- junctions --
    def add_missing_junctions(self):
        """Put a junction wherever a wire end or a pin lands mid-wire.

        KiCad only bonds wires that share an endpoint or carry a junction dot;
        a wire that stops against the middle of another one is *not* connected.
        Two wires merely crossing must stay separate, so a point is only dotted
        when something actually terminates there.
        """
        def key(p):
            return (round(p[0], 3), round(p[1], 3))

        ends = {}
        for (a, b) in self._segments:
            ends[key(a)] = ends.get(key(a), 0) + 1
            ends[key(b)] = ends.get(key(b), 0) + 1

        pins = set()
        for (ref, lib_id, x, y, rot, unit, pin_map, mir) in self.symbols:
            for num in pin_map:
                pins.add(key(self.pin(ref, unit, num)))

        added = 0
        for pt in set(ends) | pins:
            terminates = ends.get(pt, 0) > 0 or pt in pins
            if not terminates:
                continue
            interior = 0
            for (a, b) in self._segments:
                ka, kb = key(a), key(b)
                if pt in (ka, kb):
                    continue
                if _on_segment(pt, ka, kb):
                    interior += 1
            if interior and pt not in self._junctions:
                self.junction(*pt)
                added += 1
        return added

    def check_grid(self, grid=1.27, tol=1e-4):
        """Every wire end and pin must sit on the connection grid.

        Off-grid endpoints still *look* connected but KiCad flags them, and
        they are the classic way to end up with a net that silently is not
        joined.  Returns a list of offending points.
        """
        bad = []

        def off(v):
            return abs(v / grid - round(v / grid)) > tol

        for (a, b) in self._segments:
            for pt in (a, b):
                if off(pt[0]) or off(pt[1]):
                    bad.append(("wire end", pt))
        for (ref, lib_id, x, y, rot, unit, pin_map, mir) in self.symbols:
            for num in pin_map:
                pt = self.pin(ref, unit, num)
                if off(pt[0]) or off(pt[1]):
                    bad.append((f"{ref}.{num}", pt))
        return bad

    # ------------------------------------------------------------- output --
    def render(self):
        root = S("kicad_sch")
        root.add(S("version", SCH_VERSION), S("generator", q("eeschema")),
                 S("generator_version", q("9.0")),
                 S("uuid", q(uid("sheet/root"))), S("paper", q(self.paper)))
        tb = S("title_block").add(S("title", q(self.title)), S("date", q(self.date)),
                                  S("rev", q(self.rev)), S("company", q(self.company)))
        for i, c in enumerate(self.comments, 1):
            tb.add(S("comment", n(i), q(c)))
        root.add(tb)
        ls = S("lib_symbols")
        for lib_id in sorted(self.lib_symbols):
            ls.add(_as_S(self.lib_symbols[lib_id]))
        root.add(ls)
        for it in self.items:
            root.add(it)
        root.add(S("sheet_instances").add(
            S("path", q("/")).add(S("page", q("1")))))
        root.add(S("embedded_fonts", "no"))
        return root.render() + "\n"

    def write(self, path):
        with open(path, "w") as fh:
            fh.write(self.render())


def _on_segment(p, a, b, tol=1e-6):
    """True when p lies strictly between a and b on an axis-aligned segment."""
    (px, py), (ax, ay), (bx, by) = p, a, b
    if abs(ay - by) < tol and abs(py - ay) < tol:
        return min(ax, bx) + tol < px < max(ax, bx) - tol
    if abs(ax - bx) < tol and abs(px - ax) < tol:
        return min(ay, by) + tol < py < max(ay, by) - tol
    return False


def _clone_with_id(sym, lib_id):
    from sexp_parse import _clone
    c = _clone(sym)
    c.items = [lib_id] + c.items[1:]
    return c


class _Raw(S):
    """Wraps an already-parsed Node so it renders inside our S tree."""

    def __init__(self, node):
        super().__init__("")
        self.node = node

    def render(self, depth=0):
        return self.node.render(depth)


def _as_S(node):
    return _Raw(node)
