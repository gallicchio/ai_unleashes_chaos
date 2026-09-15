"""A small reader for KiCad S-expression files, plus symbol-library helpers."""
import os, re


class Node:
    __slots__ = ("tag", "items")

    def __init__(self, tag, items=None):
        self.tag = tag
        self.items = items if items is not None else []

    # ---- queries -----------------------------------------------------
    def kids(self, tag=None):
        for it in self.items:
            if isinstance(it, Node) and (tag is None or it.tag == tag):
                yield it

    def first(self, tag):
        return next(self.kids(tag), None)

    def atoms(self):
        return [it for it in self.items if not isinstance(it, Node)]

    def atom(self, i=0, default=None):
        a = self.atoms()
        return a[i] if i < len(a) else default

    # ---- output ------------------------------------------------------
    def render(self, depth=0):
        pad = "\t" * depth
        atoms = self.atoms()
        head = self.tag + "".join(" " + _fmt(a) for a in atoms)
        children = [it for it in self.items if isinstance(it, Node)]
        if not children:
            return f"{pad}({head})"
        body = "\n".join(c.render(depth + 1) for c in children)
        return f"{pad}({head}\n{body}\n{pad})"

    def __str__(self):
        return self.render()


class Sym(str):
    """A bare (unquoted) token, so it round-trips without gaining quotes."""


def _fmt(a):
    if isinstance(a, Sym):
        return str(a)
    if isinstance(a, str):
        return '"' + a.replace("\\", "\\\\").replace('"', '\\"') + '"'
    if isinstance(a, float):
        s = f"{a:.6f}".rstrip("0").rstrip(".")
        return s if s not in ("", "-") else "0"
    return str(a)


_TOKEN = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))')


def parse(text):
    """Parse one top-level S-expression."""
    pos, stack, root = 0, [], None
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m:
            break
        pos = m.end()
        lpar, rpar, qstr, bare = m.groups()
        if lpar:
            node = Node(None)
            if stack:
                stack[-1].items.append(node)
            stack.append(node)
        elif rpar:
            node = stack.pop()
            if not stack:
                root = node
                break
        elif qstr is not None:
            s = qstr.replace('\\"', '"').replace("\\\\", "\\")
            _append(stack, s)
        else:
            _append(stack, Sym(bare))
    return root


def _append(stack, value):
    node = stack[-1]
    if node.tag is None:
        node.tag = str(value)
    else:
        node.items.append(value)


def parse_file(path):
    with open(path, encoding="utf-8") as fh:
        return parse(fh.read())


# --------------------------------------------------------------- symbols ---
class SymbolLibs:
    """Loads symbols from KiCad's shared libraries, resolving `extends`."""

    def __init__(self, share_dir):
        self.share = os.path.join(share_dir, "symbols")
        self._cache = {}

    def _lib_dir(self, lib):
        for suffix in (".kicad_symdir", ""):
            d = os.path.join(self.share, lib + suffix)
            if os.path.isdir(d):
                return d
        return None

    def _raw(self, lib, name):
        key = (lib, name)
        if key in self._cache:
            return self._cache[key]
        d = self._lib_dir(lib)
        node = None
        if d:
            p = os.path.join(d, name + ".kicad_sym")
            if os.path.isfile(p):
                root = parse_file(p)
                node = next((s for s in root.kids("symbol")
                             if s.atom(0) == name), None)
        if node is None:                       # single-file library fallback
            p = os.path.join(self.share, lib + ".kicad_sym")
            if os.path.isfile(p):
                root = parse_file(p)
                node = next((s for s in root.kids("symbol")
                             if s.atom(0) == name), None)
        if node is None:
            raise KeyError(f"symbol {lib}:{name} not found under {self.share}")
        self._cache[key] = node
        return node

    def get(self, lib, name):
        """Return a fully-resolved copy of `lib:name`, ready for lib_symbols."""
        node = self._raw(lib, name)
        ext = node.first("extends")
        if ext is None:
            return _rename(_clone(node), name, f"{lib}:{name}")
        parent_name = ext.atom(0)
        parent = self.get(lib, parent_name)
        merged = _clone(parent)
        # child's own properties win; everything else (graphics, pins) inherited
        child_props = {p.atom(0): p for p in node.kids("property")}
        kept = [it for it in merged.items
                if not (isinstance(it, Node) and it.tag == "property"
                        and it.atom(0) in child_props)]
        merged.items = kept
        for p in child_props.values():
            merged.items.append(_clone(p))
        merged.items = [it for it in merged.items
                        if not (isinstance(it, Node) and it.tag == "extends")]
        return _rename(merged, name, f"{lib}:{name}", old=parent_name)


def _clone(node):
    if not isinstance(node, Node):
        return node
    return Node(node.tag, [_clone(i) for i in node.items])


def _rename(sym, new_name, full_id, old=None):
    """Point a symbol (and its `NAME_u_b` sub-units) at a new name."""
    old = old or sym.atom(0)
    sym.items = [full_id] + sym.items[1:]
    for sub in sym.kids("symbol"):
        a = sub.atom(0)
        if a and a.startswith(old + "_"):
            sub.items = [new_name + a[len(old):]] + sub.items[1:]
    for p in sym.kids("property"):
        if p.atom(0) == "Value" and p.atom(1) == old:
            p.items = [p.items[0], new_name] + p.items[2:]
    return sym
