#!/usr/bin/env python3
"""Build the Lorenz PCB: outline, placement, nets, routing and silkscreen.

Runs under KiCad's bundled Python (it needs pcbnew).  Invoke it through
make.py, or directly as:  <AppRun> python3.11 scripts/gen_pcb.py <layers>
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew
from sexp_parse import parse_file
import pcb_place as P

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.abspath(os.path.join(HERE, "..", "hardware"))
LOCAL_FP = os.path.join(HW, "lib", "lorenz.pretty")
SHARE_FP = None          # filled in from the KiCad install


def mm(v):
    return pcbnew.FromMM(float(v))


def pt(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))


def find_share():
    here = os.path.dirname(os.path.abspath(pcbnew.__file__))
    for up in range(2, 8):
        base = os.path.abspath(os.path.join(here, *([".."] * up)))
        cand = os.path.join(base, "share", "kicad", "footprints")
        if os.path.isdir(cand):
            return cand
    for cand in ("/usr/share/kicad/footprints",
                 os.path.expanduser(
                     "~/.local/kicad10/AppDir/usr/share/kicad/footprints")):
        if os.path.isdir(cand):
            return cand
    raise SystemExit("cannot find KiCad's footprint libraries")


def load_fp(fpid):
    lib, name = fpid.split(":")
    path = LOCAL_FP if lib == "lorenz" else os.path.join(SHARE_FP, lib + ".pretty")
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None:
        raise SystemExit(f"footprint {fpid} not found in {path}")
    return fp


def read_netlist(path):
    root = parse_file(path)
    comps = {}
    for c in root.first("components").kids("comp"):
        fields = {}
        fl = c.first("fields")
        if fl is not None:
            for f in fl.kids("field"):
                nm = f.first("name").atom(0)
                val = f.atom(0)
                if nm not in ("Footprint", "Datasheet", "Description") and val:
                    fields[nm] = val
        comps[c.first("ref").atom(0)] = {
            "value": c.first("value").atom(0),
            "footprint": c.first("footprint").atom(0),
            "fields": fields,
        }
    nets = {}
    for n in root.first("nets").kids("net"):
        # keep the sheet path; stripping it makes DRC's parity check unhappy
        name = n.first("name").atom(0)
        nets[name] = [(x.first("ref").atom(0), x.first("pin").atom(0))
                      for x in n.kids("node")]
    return comps, nets


def board_outline(board):
    w, h = P.BOARD_W, P.BOARD_H
    r = 3.0                                   # rounded corners
    segs = [((r, 0), (w - r, 0)), ((w, r), (w, h - r)),
            ((w - r, h), (r, h)), ((0, h - r), (0, r))]
    for (a, b) in segs:
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pt(*a)); s.SetEnd(pt(*b))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
        board.Add(s)
    for (cx, cy, a0) in ((r, r, 180), (w - r, r, 270), (w - r, h - r, 0), (r, h - r, 90)):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_ARC)
        s.SetCenter(pt(cx, cy))
        import math
        sx = cx + r * math.cos(math.radians(a0))
        sy = cy + r * math.sin(math.radians(a0))
        s.SetStart(pt(sx, sy))
        s.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(90, pcbnew.DEGREES_T), True)
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
        board.Add(s)


LAYER_BY_NAME = None


def layer_id(name):
    global LAYER_BY_NAME
    if LAYER_BY_NAME is None:
        LAYER_BY_NAME = {}
        for l in range(pcbnew.PCB_LAYER_ID_COUNT):
            LAYER_BY_NAME[pcbnew.LayerName(l)] = l
    return LAYER_BY_NAME[name]


def add_routes(board, routes_path, layers):
    """Lay down the tracks, vias and ground planes the router worked out."""
    import json
    data = json.load(open(routes_path))
    nets = {board.GetNetInfo().GetNetItem(i).GetNetname():
            board.GetNetInfo().GetNetItem(i)
            for i in range(board.GetNetInfo().GetNetCount())}
    ntrack = nvia = 0
    for net, r in data["routes"].items():
        ni = nets.get(net)
        for s in r["segments"]:
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(pt(s["x1"], s["y1"]))
            t.SetEnd(pt(s["x2"], s["y2"]))
            t.SetWidth(mm(s["width"]))
            t.SetLayer(layer_id(s["layer"]))
            if ni:
                t.SetNet(ni)
            board.Add(t)
            ntrack += 1
        for v in r["vias"]:
            nvia += add_via(board, v["x"], v["y"], ni, layers)
    gnd = nets.get("GND")
    for v in data.get("stitches", []):
        nvia += add_via(board, v["x"], v["y"], gnd, layers)

    # ground planes on every copper layer, stitched by the vias above
    cu = list(board.GetEnabledLayers().CuStack())
    for l in cu:
        z = pcbnew.ZONE(board)
        z.SetLayer(l)
        if gnd:
            z.SetNet(gnd)
        z.SetAssignedPriority(0)
        # Solid on SMD pads -- an 0805 or SOIC ground pad is too small for two
        # thermal spokes, and starving one is both an electrical and a DRC
        # problem.  Through-hole pads (BNC ground posts, the converter, the
        # USB-C shell) keep their relief so they can still be hand-soldered.
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL)
        z.SetThermalReliefGap(mm(0.3))
        z.SetThermalReliefSpokeWidth(mm(0.5))
        z.SetLocalClearance(mm(0.25))
        z.SetMinThickness(mm(0.2))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        outline = z.Outline()
        outline.NewOutline()
        m = 0.3
        for (x, y) in ((m, m), (P.BOARD_W - m, m),
                       (P.BOARD_W - m, P.BOARD_H - m), (m, P.BOARD_H - m)):
            outline.Append(mm(x), mm(y))
        board.Add(z)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    return ntrack, nvia


def add_via(board, x, y, net, layers):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pt(x, y))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetDrill(mm(0.3))
    v.SetWidth(mm(0.6))
    cu = list(board.GetEnabledLayers().CuStack())
    v.SetLayerPair(cu[0], cu[-1])
    if net:
        v.SetNet(net)
    board.Add(v)
    return 1


def build(layers, netlist_path, out_path):
    global SHARE_FP
    SHARE_FP = find_share()
    comps, nets = read_netlist(netlist_path)
    board = pcbnew.CreateEmptyBoard()
    board.SetCopperLayerCount(layers)

    # --- nets -----------------------------------------------------------
    netmap = {}
    for name in sorted(nets):
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        netmap[name] = ni
    pad_net = {}
    for name, nodes in nets.items():
        for node in nodes:
            pad_net[node] = name

    # --- footprints -----------------------------------------------------
    placed = {}
    for ref, info in sorted(comps.items()):
        if ref not in P.PLACE:
            raise SystemExit(f"{ref} has no entry in pcb_place.PLACE")
        x, y, rot = P.PLACE[ref]
        fp = load_fp(info["footprint"])
        fp.SetFPIDAsString(info["footprint"])   # parity wants the full Lib:Name
        fp.SetReference(ref)
        fp.SetValue(info["value"])
        for fname, fval in info["fields"].items():
            fp.SetField(fname, fval)
        # BOM fields are data, not artwork: keep them off the silkscreen
        for f in fp.GetFields():
            if f.GetName() in ("Reference", "Value"):
                continue
            f.SetVisible(False)
            f.SetLayer(pcbnew.F_Fab)
        # the schematic leaves Description empty; match it so parity is clean
        if fp.HasField("Description"):
            fp.SetField("Description", "")
        board.Add(fp)
        fp.SetPosition(pt(x, y))
        if rot:
            fp.SetOrientationDegrees(rot)
        for pad in fp.Pads():
            key = (ref, pad.GetNumber())
            if key in pad_net:
                pad.SetNet(netmap[pad_net[key]])
        placed[ref] = fp

    board_outline(board)
    pcbnew.SaveBoard(out_path, board)
    return board, placed, netmap, nets


def export_geometry(board, path, layers):
    """Dump pad and outline geometry for the router (which runs elsewhere)."""
    import json
    pads = []
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        for pad in fp.Pads():
            box = pad.GetBoundingBox()
            lset = pad.GetLayerSet().CuStack()
            on = [pcbnew.LayerName(l) for l in lset]
            # A custom-shaped pad (the SOT-89 tab, for one) is not centred on
            # its anchor, so the copper extent has to come from the bounding
            # box itself -- assuming otherwise let tracks run over the tab.
            pads.append({
                "ref": ref, "pad": pad.GetNumber(),
                "net": pad.GetNetname(),
                "x": pcbnew.ToMM(pad.GetPosition().x),
                "y": pcbnew.ToMM(pad.GetPosition().y),
                "cx": pcbnew.ToMM(box.GetCenter().x),
                "cy": pcbnew.ToMM(box.GetCenter().y),
                "w": pcbnew.ToMM(box.GetWidth()), "h": pcbnew.ToMM(box.GetHeight()),
                "through": pad.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH,
                                                  pcbnew.PAD_ATTRIB_NPTH),
                "layers": on,
                "drill": pcbnew.ToMM(pad.GetDrillSizeX()),
            })
    data = {"board_w": P.BOARD_W, "board_h": P.BOARD_H,
            "layers": layers, "pads": pads,
            "copper": [pcbnew.LayerName(l) for l in board.GetEnabledLayers().CuStack()]}
    with open(path, "w") as fh:
        json.dump(data, fh, indent=1)
    return len(pads)


if __name__ == "__main__":
    layers = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    netlist = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HW, "..", "out", "lorenz.net")
    out = sys.argv[3] if len(sys.argv) > 3 else os.path.join(
        HW, "lorenz.kicad_pcb" if layers == 2 else "lorenz-4layer.kicad_pcb")
    stage = os.environ.get("LORENZ_STAGE", "place")
    if stage == "route":
        routes = os.path.abspath(os.path.join(HW, "..", "out",
                                              f"routes_{layers}.json"))
        b = pcbnew.LoadBoard(out)
        nt, nv = add_routes(b, routes, layers)
        pcbnew.SaveBoard(out, b)
        print(f"  routed {os.path.relpath(out)}: {nt} tracks, {nv} vias, "
              f"{len(list(b.Zones()))} ground zones")
        raise SystemExit(0)
    b, placed, netmap, nets = build(layers, netlist, out)
    geom = os.path.join(os.path.dirname(out), "..", "out",
                        f"pcb_geom_{layers}.json")
    n = export_geometry(b, os.path.abspath(geom), layers)
    print(f"  wrote {os.path.relpath(out)}: {len(placed)} footprints, "
          f"{len(nets)} nets, {layers} layers; {n} pads -> "
          f"{os.path.relpath(os.path.abspath(geom))}")
