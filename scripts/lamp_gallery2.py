#!/usr/bin/env python3
"""The candidates for the rev B chaos lamp, as a page you can watch.

    python3 scripts/lamp_gallery2.py [--in docs/lamp2/search.json]
                                     [--out docs/lamp2]

Reads what scripts/lamp_search.py found, picks the best designs that look
different from each other, re-judges each against the corrected LED model,
and writes docs/lamp2/index.html: every candidate plays in real time as a
glowing lamp at the speed you choose, beside a strip of what the eye keeps
of it and where its colours fall around the hue circle.  Rev A's own lamp is
on the page too, under the corrected model, so the model can be checked
against the boards on the bench.
"""
import argparse, base64, json, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lamp_model as LM
import lamp_core as LC
from lamp_search import E24_ALL

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

ANIM_DT = 0.01          # time units per animation sample: 4.7 ms at slow!
ANIM_T = 160.0          # time units of animation: 76 s at slow!


def divider(vref):
    """Two E24 resistors that make `vref` from a +/-12 V rail and ground,
    as rev A's 12k/33k does.  Returns (rail, r_gnd, r_rail, volts)."""
    if abs(vref) < 0.02:
        return ("GND", None, None, 0.0)
    rail = 12.0 if vref > 0 else -12.0
    if rail > 0:
        # rev A has 12k to ground and 33k to +12 V: if changing only one of
        # them lands within 1.5 % -- well inside what the 78L12's own 4 %
        # already moves it -- that is the one to change
        near = [(abs(rail * rg / (rg + rr) - vref), rg, rr)
                for rg, rr in ([(12000, r) for r in E24_ALL] +
                               [(r, 33000) for r in E24_ALL])
                if 20e3 <= rg + rr <= 150e3]
        err, rg, rr = min(near)
        if err <= 0.015 * abs(vref):
            return ("+12V", rg, rr, rail * rg / (rg + rr))
    best = None
    for rg in E24_ALL:
        for rr in E24_ALL:
            if not (20e3 <= rg + rr <= 150e3):
                continue
            v = rail * rg / (rg + rr)
            err = abs(v - vref)
            if best is None or err < best[0]:
                best = (err, rg, rr, v)
    return ("+12V" if rail > 0 else "-12V", best[1], best[2], best[3])


def anim_bytes(lamp, dies, r=28.0, seed=5):
    """Unfiltered colour, gamma-encoded sRGB, one byte per channel.  The
    page averages it over each screen frame in linear light and the viewer's
    own eye does the rest, so it plays true at any speed."""
    sig = LC.signals(r, ANIM_T, seed)[:, ::int(round(ANIM_DT / LC.DT))]
    cur = lamp.currents(sig, dies)
    mcd = np.stack([dies[d].mcd(c) for d, c in zip(LC.DIES, cur)])
    xyz = np.einsum("kt,kc->tc", mcd, LC.dies_xyz(dies))
    # expose for the lamp's bright end after the eye has smoothed it, so a
    # brief spike does not make everything else look dark
    smooth = LM.eye_filter(mcd, ANIM_DT * LC.SPEEDS["slow!"])
    ref = np.percentile(np.einsum("kt,kc->tc", smooth, LC.dies_xyz(dies))[:, 1], 97)
    rgb = LM.to_srgb(xyz, ref)
    return base64.b64encode(rgb.tobytes()).decode()


def study(lamp, dies, r=28.0):
    """Everything the page says about one wiring, judged on a fresh stretch
    of the attractor (not the one it was chosen on)."""
    out = {}
    for speed in ("slow!", "nice!"):
        sig = LC.signals(r, 400.0, seed=7)
        mcd, cur = lamp.light(sig, dies, speed)
        j = LC.judge(mcd, LC.dies_xyz(dies), LM.Gamut(dies))
        out[speed] = dict(
            score=float(j["score"]), vivid=float(j["vivid"]),
            even=float(j["even"]), lit=float(j["lit"]), sat=float(j["sat"]),
            sectors=[round(float(v), 4) for v in LC.sector_shares(j["hist"])])
        if speed == "slow!":
            out["i_peak"] = [round(float(c.max() * 1e3), 2) for c in cur]
            out["i_mean"] = [round(float(c.mean() * 1e3), 3) for c in cur]
            out["die_lit"] = [round(float((m > 0.03 * np.percentile(m, 99)).mean()), 3)
                              if m.max() > 0 else 0.0 for m in mcd]
            out["bright"] = round(float(j["bright"]), 1)
            out["v_rev"] = round(lamp.reverse_volts(sig), 2)
            # quiescent current in any offset resistor
            q = []
            for k in range(3):
                if lamp.ro[k] is None:
                    q.append(0.0)
                    continue
                s = sig[lamp.src[k]]
                vo = LC.RAILS[lamp.rail[k]]
                q.append(round(float(np.abs(s - vo).max()
                                     / (lamp.rs[k] + lamp.ro[k]) * 1e3), 2))
            out["i_offset"] = q
            # current between two op-amp outputs through a blend
            x = []
            for k in range(3):
                if lamp.rs2[k] is None:
                    x.append(0.0)
                    continue
                d = sig[lamp.src[k]] - sig[lamp.src2[k]]
                x.append(round(float(np.abs(d).max()
                                     / (lamp.rs[k] + lamp.rs2[k]) * 1e3), 2))
            out["i_blend"] = x
    return out


def vref_sensitivity(lamp, dies, r=28.0):
    """Score with the +12 V rail 4 % low and 4 % high (the 78L12's
    tolerance), which moves the reference -- and every threshold -- with
    it.  Topology B's offset resistors ride on the rails too."""
    out = []
    sig = LC.signals(r, 300.0, seed=17)
    for f in (0.96, 1.04):
        d = lamp.as_dict()
        d["vref"] = lamp.vref * f
        l2 = LC.Lamp(**d)
        mcd, _ = l2.light(sig, dies, "slow!")
        j = LC.judge(mcd, LC.dies_xyz(dies), LM.Gamut(dies))
        out.append(round(float(j["score"]), 3))
    return out


def hue_speed(lamp, dies, r=28.0):
    """How fast the colour moves around the wheel while it is vivid, in
    degrees per second at slow!, and how long a hue typically lasts."""
    sig = LC.signals(r, 200.0, seed=9)
    mcd, _ = lamp.light(sig, dies, "slow!")
    xyz = np.einsum("kt,kc->tc", mcd[:, ::4], LC.dies_xyz(dies))
    h = LM.hue_deg(xyz)
    dh = np.abs(np.angle(np.exp(1j * np.radians(np.diff(h)))))
    dt_s = 4 * LC.DT * LC.SPEEDS["slow!"]
    return float(np.degrees(np.median(dh)) / dt_s)


def character(lamp, dies, r=28.0):
    """In words: which hues each wing of the attractor shows.  The lamp's
    story is mostly told by the two wings (x > 0 and x < 0) and by the
    crossings between them, so that is how it is described."""
    sig = LC.signals(r, 300.0, seed=11)
    mcd, _ = lamp.light(sig, dies, "slow!")
    step = 4
    xyz = np.einsum("kt,kc->tc", mcd[:, ::step], LC.dies_xyz(dies))
    x = sig[0, ::step]
    u, v = LM.xyz_to_uv(xyz)
    sat = LM.Gamut(dies).saturation(u, v)
    b = xyz[:, 1] * LM.ware_cowan(xyz)
    j = np.cbrt(b / np.percentile(b, 95))
    w = np.clip((j - 0.30) / 0.25, 0, 1) * np.clip((sat - 0.35) / 0.40, 0, 1)
    sec = ((LM.hue_deg(xyz) + 15.0) // 30.0).astype(int) % 12
    names = [n for _, n in LC.SECTORS]

    def run(mask):
        h = np.bincount(sec[mask], weights=w[mask], minlength=12)
        tot = mask.sum()
        if tot == 0 or h.sum() < 0.05 * tot:
            return "mostly pale or dark"
        h = h / h.sum()
        keep = [i for i in range(12) if h[i] >= 0.12]
        if not keep:
            keep = [int(np.argmax(h))]
        # walk the circle from the largest gap so a run reads in hue order
        gaps = [(keep[(i + 1) % len(keep)] - keep[i]) % 12 for i in range(len(keep))]
        start = (int(np.argmax(gaps)) + 1) % len(keep)
        order = keep[start:] + keep[:start]
        if len(order) == 1:
            return names[order[0]]
        return names[order[0]] + " to " + names[order[-1]]

    wing = 0.6                      # volts: inside a wing, not crossing
    plus, minus = run(x > wing), run(x < -wing)
    cross = run(np.abs(x) <= wing)
    say = (f"On the +x wing it runs {plus}; on the -x wing, {minus}; "
           f"through the crossings, {cross}.")
    return f"{plus} | {minus}", say


def pick(rows, n_total=10):
    """The best designs of each kind that do not look alike.

    Four kinds, from least change to most: a drop-in for the rev A board;
    the common-cathode part with three resistors (a new board, no new
    parts); three resistors plus two that pull thresholds apart; and dies
    fed from blends of two signals.  Each kind gets its best, then the ones
    whose hue shape differs most from those already chosen, among designs
    within 85 % of that kind's best."""
    def feat(r):
        return np.array(r["sectors"]) * 3.0

    kinds = [("dropin", 2, lambda r: r["dropin"]),
             ("plus1", 2, lambda r: r["plus1"]),
             ("cc", 2, lambda r: r["topo"] == "A" and r["lamp"]["part"] == "CC"),
             ("B", 1, lambda r: r["topo"] == "B" and not r["plus1"]),
             ("C", 3, lambda r: r["topo"] == "C")]
    chosen = []
    for _, n, want in kinds:
        pool = sorted([r for r in rows if want(r)], key=lambda r: -r["score_med"])
        if not pool:
            continue
        pool = [r for r in pool if r["score_med"] >= 0.85 * pool[0]["score_med"]][:60]
        mine = [pool[0]]
        while len(mine) < n and len(mine) < len(pool):
            d = []
            names = {c["name"] for c in mine + chosen}
            for r in pool:
                if r in mine:
                    d.append(-1.0)
                    continue
                gap = min(np.abs(feat(r) - feat(c)).sum() for c in mine + chosen)
                # a different story on the wings counts for more than a
                # different histogram: that is what the eye notices
                fresh = 1.0 if r["name"] not in names else 0.35
                d.append(gap * fresh * (0.5 + r["score_med"] / pool[0]["score_med"]))
            k = int(np.argmax(d))
            if d[k] <= 0:
                break
            mine.append(pool[k])
        chosen += mine
    chosen = chosen[:n_total]
    chosen.sort(key=lambda r: -r["score_med"])
    return chosen


def _shape_job(lamp_d):
    lamp = LC.Lamp(**lamp_d)
    st = study(lamp, LM.MHPA3528)
    # gentle on the op-amps: no die above 5 mA, and no more than 2 mA
    # standing in any offset or blend resistor
    gentle = (max(st["i_peak"]) <= 5.0 and max(st["i_offset"]) <= 2.0
              and max(st["i_blend"]) <= 2.0)
    return st["slow!"]["sectors"], character(lamp, LM.MHPA3528)[0], gentle


def _full_job(lamp_d):
    lamp, dies = LC.Lamp(**lamp_d), LM.MHPA3528
    st = study(lamp, dies)
    name, say = character(lamp, dies)
    return dict(name=name, say=say, hue_speed=round(hue_speed(lamp, dies), 0),
                vref_sens=vref_sensitivity(lamp, dies),
                anim=anim_bytes(lamp, dies), **st)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="inp",
                    default=os.path.join(ROOT, "docs", "lamp2", "search.json"))
    ap.add_argument("--out", default=os.path.join(ROOT, "docs", "lamp2"))
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--artifact", default=None,
                    help="also write the page body alone, for publishing")
    a = ap.parse_args()
    data = json.load(open(a.inp))
    rows = data["rows"]
    for extra in ("search_mix.json", "search_plus1.json"):
        f = os.path.join(os.path.dirname(a.inp), extra)
        if os.path.exists(f):
            rows = rows + json.load(open(f))["rows"]
    rows.sort(key=lambda r: -r["score_med"])
    dies = LM.MHPA3528

    # a drop-in fits the rev A board as it is: common anode, one resistor
    # per die, and each die still wired to the signal its trace already
    # goes to (red = z, green = x, blue = -y)
    for r in rows:
        L = r["lamp"]
        same = L["part"] == "CA" and tuple(L["src"]) == (2, 0, 1) and \
            all(v is None for v in L.get("rs2", [None] * 3))
        n_off = sum(v is not None for v in L["ro"])
        r["dropin"] = same and n_off == 0
        # rev A plus one resistor, from the blue die's cathode to a rail
        r["plus1"] = same and n_off == 1 and L["ro"][2] is not None
    keep = rows[:150]
    for want in (lambda r: r["dropin"], lambda r: r["plus1"],
                 lambda r: r["topo"] == "A" and r["lamp"]["part"] == "CC",
                 lambda r: r["topo"] == "A", lambda r: r["topo"] == "B",
                 lambda r: r["topo"] == "C"):
        keep += [r for r in rows[150:] if want(r) and r not in keep][:25]
    rows = sorted(keep, key=lambda r: -r["score_med"])
    # every survivor gets a hue shape, so the picker can tell them apart
    import multiprocessing as mp
    with mp.get_context("fork").Pool(max(1, os.cpu_count() - 2)) as pool:
        shapes = pool.map(_shape_job, [r["lamp"] for r in rows])
        for r, (sh, name, gentle) in zip(rows, shapes):
            r["sectors"], r["name"], r["gentle"] = sh, name, gentle
        print(f"  {sum(r['gentle'] for r in rows)} of {len(rows)} finalists are "
              "gentle on the op-amps")
        chosen = pick([r for r in rows if r["gentle"]], a.n)
        full = pool.map(_full_job, [r["lamp"] for r in chosen])

    out = []
    for i, (r, f) in enumerate(zip(chosen, full), 1):
        lamp = LC.Lamp(**r["lamp"])
        div = divider(lamp.vref)
        out.append(dict(
            n=i, lamp=r["lamp"], topo=r["topo"], dropin=r["dropin"],
            plus1=r["plus1"],
            desc=lamp.describe(), robust=dict(
                med=round(r["score_med"], 3), p20=round(r["score_p20"], 3),
                vivid=round(r["vivid_med"], 3), even=round(r["even_med"], 3)),
            divider=dict(rail=div[0], r_gnd=div[1], r_rail=div[2],
                         v=round(div[3], 3)),
            n_res=lamp.n_resistors(), **f))
        print(f"  {i:2d} {r['topo']} {'drop-in ' if r['dropin'] else ''}"
              f"{'rev A + 1 ' if r['plus1'] else ''}"
              f"med {r['score_med']:.3f} slow {f['slow!']['score']:.3f} "
              f"nice {f['nice!']['score']:.3f}  {lamp.describe()}")

    # rev A as built, under the model it was chosen with and the corrected one
    reva = LC.Lamp("CA", 3.2, (2, 0, 1), (470, 3900, 1500))
    ref = {}
    for key, d in (("old", LM.REVA), ("new", LM.MHPA3528)):
        st = study(reva, d)
        name, say = character(reva, d)
        ref[key] = dict(anim=anim_bytes(reva, d), name=name, say=say,
                        hue_speed=round(hue_speed(reva, d), 0), **st)
    page = dict(anim_dt=ANIM_DT, anim_t=ANIM_T, speeds=LC.SPEEDS,
                sectors=[n for _, n in LC.SECTORS], candidates=out, reva=ref)
    with open(os.path.join(a.out, "candidates.json"), "w") as fh:
        json.dump({k: (v if k != "candidates" else
                       [{kk: vv for kk, vv in c.items() if kk != "anim"}
                        for c in v]) for k, v in page.items()
                   if k != "reva"}, fh, indent=1)
    import lamp_page
    lamp_page.write(page, os.path.join(a.out, "index.html"), standalone=True)
    if a.artifact:
        lamp_page.write(page, a.artifact, standalone=False)
    print(f"  wrote {len(out)} candidates to {os.path.relpath(a.out, ROOT)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


def picture(lamp, dies, path, rows=12, width=900, seconds_per_row=7.5,
            speed="slow!", sectors=None, eye=True):
    """A still of what the eye keeps: `rows` rows of `seconds_per_row`, with
    the hue-sector bars of its vivid moments underneath."""
    from PIL import Image, ImageDraw
    import lamp_page
    sig = LC.signals(28.0, 400.0, seed=13)
    mcd, _ = lamp.light(sig, dies, speed, tau_eye=0.020 if eye else 0.0)
    x3 = LC.dies_xyz(dies)
    dt_s = LC.DT * LC.SPEEDS[speed]
    strip = LC.render_strip(mcd, x3, seconds_per_row, dt_s, rows, width)
    strip = np.kron(strip, np.ones((3, 1, 1), np.uint8))
    if sectors is None:
        j = LC.judge(mcd, x3, LM.Gamut(dies))
        sectors = LC.sector_shares(j["hist"])
    bar_h, gap = 70, 10
    img = Image.new("RGB", (width, strip.shape[0] + gap + bar_h + 16), (0, 0, 0))
    img.paste(Image.fromarray(strip), (0, 0))
    d = ImageDraw.Draw(img)
    cols = lamp_page.sector_rgb()
    top = strip.shape[0] + gap
    mx = max(max(sectors), 1.8 / 12)
    cw = width / 12
    for i, v in enumerate(sectors):
        h = int(round(bar_h * v / mx))
        c = tuple(int(cols[i][k:k + 2], 16) for k in (1, 3, 5))
        d.rectangle([int(i * cw) + 2, top + bar_h - h, int((i + 1) * cw) - 2,
                     top + bar_h], fill=c)
    ey = top + bar_h - int(round(bar_h * (1 / 12) / mx))
    for xx in range(0, width, 8):
        d.line([xx, ey, xx + 4, ey], fill=(140, 150, 140))
    for i, (_, n) in enumerate(LC.SECTORS):
        d.text((int(i * cw) + 4, top + bar_h + 3), n, fill=(150, 160, 150))
    img.save(path, optimize=True)
    return sectors


def _font(size, bold=False):
    from PIL import ImageFont
    for f in (("DejaVuSansCondensed-Bold.ttf" if bold else "DejaVuSansCondensed.ttf"),
              "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/" + f, size)
        except OSError:
            continue
    from PIL import ImageFont as F
    return F.load_default()


def panels(path, items, seconds=40.0, rows=8, width=900, speed="slow!",
           seed=13, row_h=12, gap=5):
    """Several lamps stacked for comparison, each: a label, `rows` rows of
    what the eye keeps over `seconds` of the same stretch of the attractor,
    and the hue bars of its vivid moments.  items: (label, lamp, dies)."""
    from PIL import Image, ImageDraw
    import lamp_page
    cols = lamp_page.sector_rgb()
    sig = LC.signals(28.0, 400.0, seed=seed)
    blocks = []
    for label, lamp, dies in items:
        mcd, _ = lamp.light(sig, dies, speed)
        x3 = LC.dies_xyz(dies)
        dt_s = LC.DT * LC.SPEEDS[speed]
        j = LC.judge(mcd, x3, LM.Gamut(dies))
        sectors = LC.sector_shares(j["hist"])
        st = LC.render_strip(mcd, x3, seconds / rows, dt_s, rows, width, gap=False)
        blocks.append((label, st, sectors, float(j["score"]),
                       float(j["vivid"]), float(j["even"])))
    f_lab, f_small = _font(17, True), _font(12)
    bar_h = 54
    blk_h = 44 + rows * (row_h + gap) + 8 + bar_h + 18 + 16
    img = Image.new("RGB", (width, blk_h * len(blocks)), (5, 7, 6))
    d = ImageDraw.Draw(img)
    for b, (label, st, sectors, sc, viv, ev) in enumerate(blocks):
        y0 = b * blk_h
        d.text((0, y0 + 2), label, font=f_lab, fill=(225, 230, 225))
        d.text((0, y0 + 24),
               f"vivid {100*viv:.0f}% of the time   ·   {12*ev:.1f} of 12 hue "
               f"sectors   ·   score {sc:.2f}   ·   {seconds:.0f} s at {speed}, "
               f"{seconds/rows:.0f} s per row",
               font=f_small, fill=(160, 170, 160))
        y = y0 + 44
        for r in range(rows):
            row = np.repeat(st[r:r + 1], row_h, axis=0)
            img.paste(Image.fromarray(row), (0, y))
            y += row_h + gap
        y += 8
        mx = max(max(sectors), 1.8 / 12)
        cw = width / 12
        for i, v in enumerate(sectors):
            h = int(round(bar_h * v / mx))
            c = tuple(int(cols[i][k:k + 2], 16) for k in (1, 3, 5))
            d.rectangle([int(i * cw) + 2, y + bar_h - h, int((i + 1) * cw) - 2,
                         y + bar_h], fill=c)
        ey = y + bar_h - int(round(bar_h * (1 / 12) / mx))
        for xx in range(0, width, 8):
            d.line([xx, ey, xx + 4, ey], fill=(120, 130, 120))
        for i, (_, n) in enumerate(LC.SECTORS):
            d.text((int(i * cw) + 4, y + bar_h + 2), n, font=f_small,
                   fill=(150, 160, 150))
    img.save(path, optimize=True)
