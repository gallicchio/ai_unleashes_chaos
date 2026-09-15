"""Minimal helpers for emitting KiCad S-expressions."""
import math, uuid


def q(s):
    """Quote a string the way KiCad does."""
    s = str(s).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{s}"'


def n(v):
    """Format a number: KiCad writes plain decimals, trimming trailing zeros."""
    if isinstance(v, int):
        return str(v)
    v = round(float(v) + 0.0, 6)
    if v == int(v):
        return str(int(v))
    return f"{v:.6f}".rstrip("0").rstrip(".")


def xy(x, y):
    return f"(xy {n(x)} {n(y)})"


def uid(seed=None):
    """Deterministic UUID when seeded, so regenerating gives identical files."""
    if seed is None:
        return str(uuid.uuid4())
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"lorenz://{seed}"))


class S:
    """A tiny S-expression node that renders with KiCad's tab indentation."""

    def __init__(self, tag, *atoms):
        self.tag = tag
        self.atoms = list(atoms)
        self.kids = []

    def add(self, *nodes):
        for node in nodes:
            if node is not None:
                self.kids.append(node)
        return self

    def render(self, depth=0):
        pad = "\t" * depth
        head = self.tag + ("".join(" " + str(a) for a in self.atoms))
        if not self.kids:
            return f"{pad}({head})"
        body = "\n".join(k.render(depth + 1) for k in self.kids)
        return f"{pad}({head}\n{body}\n{pad})"

    def __str__(self):
        return self.render()


def effects(size=1.27, thickness=None, justify=None, hide=False, mirror=False):
    e = S("effects")
    f = S("font", )
    f.add(S("size", n(size), n(size)))
    if thickness is not None:
        f.add(S("thickness", n(thickness)))
    e.add(f)
    if justify:
        parts = justify if isinstance(justify, (list, tuple)) else [justify]
        bad = [p for p in parts if p not in ("left", "right", "top", "bottom", "mirror")]
        if bad:
            raise ValueError(f"KiCad has no {bad} justification "
                             "(valid: left right top bottom mirror; "
                             "centred is the default)")
        e.add(S("justify", *parts))
    if mirror:
        e.add(S("justify", "mirror"))
    if hide:
        e.add(S("hide", "yes"))
    return e


def stroke(width=0.12, type_="solid"):
    return S("stroke").add(S("width", n(width)), S("type", type_))


def at(x, y, rot=None):
    return S("at", n(x), n(y)) if rot is None else S("at", n(x), n(y), n(rot))


def rot_pt(x, y, deg):
    r = math.radians(deg)
    return x * math.cos(r) - y * math.sin(r), x * math.sin(r) + y * math.cos(r)
