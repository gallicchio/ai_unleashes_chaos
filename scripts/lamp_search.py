#!/usr/bin/env python3
"""Find the chaos lamp wirings that show every hue, vividly, about equally.

    python3 scripts/lamp_search.py [--quick] [--out docs/lamp2]

Two topologies are searched, both built from parts already on the board:

  A  rev A's own: one reference on the lamp's common pin (U2B and a
     divider), one series resistor per die.  Every die's threshold then
     sits one forward drop from the same reference.  Exhaustive: both lamp
     parts x 27 ways to hand x, -y, z to the three dies x 81 references x
     every E12 resistor on every die.

  B  the same plus one resistor per die from its pin to a rail, which gives
     each die a threshold of its own.  Too big to enumerate; searched by
     sampling around the best A designs and at random, then polished.

Every survivor is then re-judged against 24 plausible real parts (the
datasheet's brightness bins, forward-voltage spread and the efficiency
curves' uncertainty) at three settings of the r knob, and ranked on the
median.  A design that only works for the nominal LED is not a design.
"""
import argparse, json, os, sys, time
import multiprocessing as mp
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lamp_model as LM
import lamp_core as LC

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

E12 = [1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2]
E24 = [1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0,
       3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1]
R_GRID = [round(m * 10 ** d) for d in (2, 3, 4) for m in E12
          if 150 <= m * 10 ** d <= 47000]
E24_ALL = [round(m * 10 ** d) for d in (2, 3, 4, 5) for m in E24
           if 100 <= m * 10 ** d <= 470000]
VREFS = {"CA": np.round(np.arange(-0.5, 7.51, 0.1), 2),
         "CC": np.round(np.arange(-7.5, 0.51, 0.1), 2)}
EVERY = 8          # table decimation: 0.04 time units, 19 ms at slow!
COARSE = 8         # further decimation for the first pass (1250 samples)

G = {}             # shared with forked workers: tables, signals, dies


# ------------------------------------------------------------ tables ----

def _table_job(args):
    part, vi, k, s = args
    sig, dies = G["sig"], G["dies"]
    vref = VREFS[part][vi]
    d = dies[LC.DIES[k]]
    drive = (vref - sig[s]) if part == "CA" else (sig[s] - vref)
    out = np.zeros((len(R_GRID), sig.shape[1] // EVERY), np.float32)
    peak = np.zeros(len(R_GRID))
    for ri, r in enumerate(R_GRID):
        i = d.current(drive, r)
        peak[ri] = i.max()
        m = LM.eye_filter(d.mcd(i), LC.DT * LC.SPEEDS["slow!"])
        out[ri] = m[::EVERY]
    return args, out, peak


def build_tables(pool):
    sig = G["sig"]
    T = sig.shape[1] // EVERY
    shape = (2, len(VREFS["CA"]), 3, 3, len(R_GRID), T)
    tab = np.zeros(shape, np.float32)
    peak = np.zeros(shape[:-1])
    jobs = [(p, vi, k, s) for p in ("CA", "CC") for vi in range(shape[1])
            for k in range(3) for s in range(3)]
    for (p, vi, k, s), out, pk in pool.imap_unordered(_table_job, jobs, 16):
        pi = 0 if p == "CA" else 1
        tab[pi, vi, k, s] = out
        peak[pi, vi, k, s] = pk
    return tab, peak


# ------------------------------------------------------ topology A ------

def _usable(pi, vi, k, s):
    """Resistor indices worth trying on one die: the reverse voltage is
    within the part's 5 V (with margin for a wider r), the peak current is
    between 0.1 and 6 mA, and the die actually lights sometimes."""
    part = ("CA", "CC")[pi]
    vref = VREFS[part][vi]
    lo, hi = G["range"][s]
    rev = (hi - vref) if part == "CA" else (vref - lo)
    if rev > 4.6:
        return []
    pk = G["peak"][pi, vi, k, s]
    tab = G["tab"][pi, vi, k, s]
    out = []
    for ri in range(len(R_GRID)):
        if not (1e-4 <= pk[ri] <= 6e-3):
            continue
        if tab[ri].max() < 1.5:
            continue
        out.append(ri)
    return out


def _judge_batch(mcd):
    return LC.judge(mcd, G["x3"].astype(mcd.dtype), G["gamut"], every=1)


def _search_a_job(args):
    pi, vi, assign = args
    # first pass on every other E12 value (E6); refine_a() fills in
    lists = [[ri for ri in _usable(pi, vi, k, assign[k]) if ri % 2 == 0]
             for k in range(3)]
    if any(len(l) == 0 for l in lists):
        return args, []
    tab = G["tab"]
    series = [np.ascontiguousarray(tab[pi, vi, k, assign[k]][lists[k]][:, ::COARSE])
              for k in range(3)]
    combos = np.array(np.meshgrid(*[np.arange(len(l)) for l in lists],
                                  indexing="ij")).reshape(3, -1).T
    best = []
    for c0 in range(0, len(combos), 1500):
        cb = combos[c0:c0 + 1500]
        mcd = np.stack([series[k][cb[:, k]] for k in range(3)], axis=1)
        j = _judge_batch(mcd)
        ok = (j["bright"] >= 8.0) & (j["bright"] <= 250.0)
        sc = np.where(ok, j["score"], 0.0)
        top = np.argsort(sc)[::-1][:12]
        for t in top:
            if sc[t] <= 0:
                continue
            rs = tuple(lists[k][cb[t, k]] for k in range(3))
            best.append((float(sc[t]), float(j["vivid"][t]),
                         float(j["even"][t]), rs))
    best.sort(reverse=True)
    return args, best[:12]


def search_a(pool, smoke=False):
    jobs = []
    assigns = [(a, b, c) for a in range(3) for b in range(3) for c in range(3)]
    for pi in (0, 1):
        for vi in range(len(VREFS["CA"])):
            if smoke and vi % 8:
                continue
            for asg in assigns:
                if smoke and asg not in ((2, 0, 1), (0, 2, 1), (1, 2, 0)):
                    continue
                jobs.append((pi, vi, asg))
    results = []
    t0 = time.time()
    for n, (args, best) in enumerate(pool.imap_unordered(_search_a_job, jobs, 4)):
        pi, vi, asg = args
        for (sc, viv, ev, rs) in best:
            results.append(dict(pi=pi, vi=[vi, vi, vi], src=asg, ri=rs,
                                coarse=sc, vivid=viv, even=ev))
        if n % 500 == 0:
            print(f"    A: {n}/{len(jobs)} ({time.time()-t0:.0f} s)", flush=True)
    return results


def _refine_a_job(c):
    """Polish one topology-A design: move the shared reference and each
    resistor to its neighbours on the full E12 grid, keep what improves."""
    nv, nr = len(VREFS["CA"]), len(R_GRID)
    best = dict(pi=c["pi"], vi=list(c["vi"]), src=list(c["src"]), ri=list(c["ri"]))
    bs = _eval_ids([best])[0][0]
    for _ in range(8):
        nbrs = []
        for dv in (-2, -1, 0, 1, 2):
            for d0 in (-1, 0, 1):
                for d1 in (-1, 0, 1):
                    for d2 in (-1, 0, 1):
                        v = best["vi"][0] + dv
                        ri = [best["ri"][0] + d0, best["ri"][1] + d1,
                              best["ri"][2] + d2]
                        if not (0 <= v < nv) or min(ri) < 0 or max(ri) >= nr:
                            continue
                        n = dict(pi=best["pi"], vi=[v, v, v], src=best["src"], ri=ri)
                        if _valid(n):
                            nbrs.append(n)
        if not nbrs:
            break
        sc, _ = _eval_ids(nbrs)
        k = int(np.argmax(sc))
        if sc[k] <= bs + 1e-4:
            break
        best, bs = nbrs[k], float(sc[k])
    return float(bs), best


def refine_a(pool, shortlist):
    out = []
    for sc, c in pool.imap_unordered(_refine_a_job, shortlist, 4):
        out.append(dict(c, coarse=sc))
    out.sort(key=lambda c: -c["coarse"])
    return out


# ------------------------------------------------------ topology B ------

def _eval_ids(cands, coarse=True):
    """Score candidates given as table indices: part, vref index per die,
    source per die, resistor index per die."""
    tab = G["tab"]
    step = COARSE if coarse else 1
    mcd = np.stack([np.stack([tab[c["pi"], c["vi"][k], k, c["src"][k],
                                  c["ri"][k], ::step] for k in range(3)])
                    for c in cands])
    j = _judge_batch(mcd)
    ok = (j["bright"] >= 8.0) & (j["bright"] <= 250.0)
    return np.where(ok, j["score"], 0.0), j


def _valid(c):
    part = ("CA", "CC")[c["pi"]]
    for k in range(3):
        vref = VREFS[part][c["vi"][k]]
        lo, hi = G["range"][c["src"][k]]
        rev = (hi - vref) if part == "CA" else (vref - lo)
        if rev > 4.6:
            return False
        pk = G["peak"][c["pi"], c["vi"][k], k, c["src"][k], c["ri"][k]]
        if not (1e-4 <= pk <= 6e-3):
            return False
    return True


def _mutate(c, rng, scale=1.0):
    c = dict(pi=c["pi"], vi=list(c["vi"]), src=list(c["src"]), ri=list(c["ri"]))
    nv, nr = len(VREFS["CA"]), len(R_GRID)
    k = int(rng.integers(3))
    what = rng.random()
    if what < 0.45:
        c["vi"][k] = int(np.clip(c["vi"][k] + rng.normal(0, 4 * scale), 0, nv - 1))
    elif what < 0.85:
        c["ri"][k] = int(np.clip(c["ri"][k] + np.round(rng.normal(0, 2 * scale)),
                                 0, nr - 1))
    else:
        c["src"][k] = int(rng.integers(3))
    return c


def _search_b_job(args):
    seed, starts = args
    rng = np.random.default_rng(seed)
    nv, nr = len(VREFS["CA"]), len(R_GRID)
    pop = []
    for c in starts:
        if _valid(c):
            pop.append(c)
    while len(pop) < 60:
        c = dict(pi=int(rng.integers(2)), vi=list(rng.integers(0, nv, 3)),
                 src=list(rng.integers(0, 3, 3)), ri=list(rng.integers(0, nr, 3)))
        if _valid(c):
            pop.append(c)
    sc, _ = _eval_ids(pop)
    order = np.argsort(sc)[::-1]
    pop = [pop[i] for i in order]
    sc = sc[order]
    # a small evolutionary polish: mutate the best, keep what improves
    for gen in range(60):
        kids = []
        for i in range(40):
            parent = pop[min(int(rng.exponential(6)), len(pop) - 1)]
            kid = _mutate(parent, rng, scale=1.0 if gen < 30 else 0.5)
            if _valid(kid):
                kids.append(kid)
        if not kids:
            continue
        ks, _ = _eval_ids(kids)
        allc = pop + kids
        alls = np.concatenate([sc, ks])
        order = np.argsort(alls)[::-1][:60]
        pop = [allc[i] for i in order]
        sc = alls[order]
    return [(float(s), c) for s, c in zip(sc[:20], pop[:20])]


def search_b(pool, seeds_from, n_jobs=256):
    rng = np.random.default_rng(12345)
    jobs = []
    for j in range(n_jobs):
        starts = []
        if seeds_from and j < n_jobs * 3 // 4:
            base = seeds_from[j % len(seeds_from)]
            starts = [dict(pi=base["pi"], vi=list(base["vi"]),
                           src=list(base["src"]), ri=list(base["ri"]))]
        jobs.append((int(rng.integers(1 << 30)), starts))
    out = []
    t0 = time.time()
    for n, res in enumerate(pool.imap_unordered(_search_b_job, jobs, 1)):
        out.extend(res)
        if n % 32 == 0:
            print(f"    B: {n}/{len(jobs)} ({time.time()-t0:.0f} s)", flush=True)
    return out


# ------------------------------------------------ realise and verify ----

V_ON = {"R": 1.69, "G": 2.48, "B": 2.59}     # each die at about 0.3 mA


def realise(c):
    """Turn table indices into a Lamp that can be built.  Topology A is
    already buildable.  For B the common pin takes the middle die's
    reference and each other die gets a resistor R_o from its pin to a rail,
    which moves the reference that die effectively sees by

        delta = (R_s / R_o) (Vref - Vrail - Von)     common anode
        delta = (R_s / R_o) (Vref - Vrail + Von)     common cathode

    Either way a pull towards -12 V moves it up and a pull towards +12 V
    moves it down.  R_o is the E24 value nearest the exact one; the built
    circuit is what gets judged afterwards, not this approximation."""
    part = ("CA", "CC")[c["pi"]]
    v = [float(VREFS[part][i]) for i in c["vi"]]
    rs = [float(R_GRID[i]) for i in c["ri"]]
    if len(set(c["vi"])) == 1:
        return LC.Lamp(part, v[0], c["src"], rs)
    vref = float(np.median(v))
    ro, rail = [None] * 3, ["GND"] * 3
    for k in range(3):
        delta = v[k] - vref
        if abs(delta) < 0.05:
            continue
        vr = -12.0 if delta > 0 else 12.0
        von = V_ON[LC.DIES[k]] * (-1.0 if part == "CA" else 1.0)
        want = rs[k] * (vref - vr + von) / delta
        ro[k] = min(E24_ALL, key=lambda e: abs(np.log(e / want)))
        rail[k] = "+12V" if vr > 0 else "-12V"
    return LC.Lamp(part, vref, c["src"], rs, ro, rail)


def verify(lamp, dies, r=28.0, t_units=400.0, seed=1, speed="slow!"):
    sig = LC.signals(r, t_units, seed)
    mcd, cur = lamp.light(sig, dies, speed)
    j = LC.judge(mcd, LC.dies_xyz(dies), LM.Gamut(dies))
    j = {k: (float(v) if np.ndim(v) == 0 else v) for k, v in j.items()}
    j["i_peak"] = [float(c.max() * 1e3) for c in cur]
    j["i_mean"] = [float(c.mean() * 1e3) for c in cur]
    j["v_rev"] = lamp.reverse_volts(sig)
    return j


def _robust_job(args):
    idx, lamp_d, variant_seeds, rs_ = args
    lamp = LC.Lamp(**lamp_d)
    rows = []
    for vs in variant_seeds:
        dies = LM.spread(np.random.default_rng(vs)) if vs >= 0 else LM.MHPA3528
        for r in rs_:
            j = verify(lamp, dies, r=r, t_units=300.0, seed=2)
            rows.append((j["score"], j["vivid"], j["even"], j["lit"], j["sat"],
                         j["bright"], max(j["i_peak"])))
    return idx, np.array(rows)


def robust(pool, lamps, n_var=24, rs_=(26.0, 28.0, 31.0)):
    seeds = [-1] + list(range(1000, 1000 + n_var - 1))
    jobs = [(i, l.as_dict(), seeds, rs_) for i, l in enumerate(lamps)]
    out = [None] * len(lamps)
    t0 = time.time()
    for n, (i, rows) in enumerate(pool.imap_unordered(_robust_job, jobs, 1)):
        out[i] = rows
        if n % 40 == 0:
            print(f"    robust: {n}/{len(jobs)} ({time.time()-t0:.0f} s)", flush=True)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=os.path.join(ROOT, "docs", "lamp2"))
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--smoke", action="store_true",
                    help="a few minutes end to end, to test the pipeline")
    ap.add_argument("--procs", type=int, default=max(1, os.cpu_count() - 2))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    dies = LM.MHPA3528
    sig = LC.signals(28.0, 400.0, seed=0)
    G.update(sig=sig, dies=dies, x3=LC.dies_xyz(dies), gamut=LM.Gamut(dies))
    # the widest each signal gets over the r knob's working range
    wide = LC.signals(31.0, 200.0, seed=3)
    G["range"] = [(float(min(s.min(), w.min())), float(max(s.max(), w.max())))
                  for s, w in zip(sig, wide)]
    print("  signal ranges at r = 28..31: " + ", ".join(
        f"{n} {lo:+.2f}..{hi:+.2f} V" for n, (lo, hi) in zip(LC.SIGNALS, G["range"])))

    t0 = time.time()
    with mp.get_context("fork").Pool(a.procs) as pool:
        tab, peak = build_tables(pool)
    G.update(tab=tab, peak=peak)
    print(f"  light tables: {tab.shape}, {tab.nbytes/1e9:.1f} GB, "
          f"{time.time()-t0:.0f} s")

    import pickle
    stash = os.path.join(a.out, "search_stages.pkl")
    with mp.get_context("fork").Pool(a.procs) as pool:
        ra = search_a(pool, smoke=a.smoke)
        ra.sort(key=lambda c: -c["coarse"])
        print(f"  A: {len(ra)} shortlisted, best coarse score {ra[0]['coarse']:.3f}")
        # polish the best of each signal assignment, and the best overall
        by_asg = {}
        for c in ra:
            by_asg.setdefault((c["pi"], tuple(c["src"])), []).append(c)
        short = ra[:300] + [c for l in by_asg.values() for c in l[:12]]
        ra = refine_a(pool, short) + ra[300:]
        ra.sort(key=lambda c: -c["coarse"])
        print(f"  A: refined; best coarse score {ra[0]['coarse']:.3f}")
        pickle.dump(dict(ra=ra), open(stash, "wb"))
        seeds = ra[:64]
        rb = search_b(pool, seeds, n_jobs=32 if a.smoke else 64 if a.quick else 384)
        rb.sort(key=lambda t: -t[0])
        print(f"  B: {len(rb)} shortlisted, best coarse score {rb[0][0]:.3f}")
        pickle.dump(dict(ra=ra, rb=rb), open(stash, "wb"))

    # full-resolution rescoring of the shortlists, then dedupe.  The best
    # drop-ins for the rev A board (common anode, red = z, green = x,
    # blue = -y, so only resistor values change) are kept whatever their
    # rank: they are the ones that can be tried on the boards already built.
    dropin = [c for c in ra if c["pi"] == 0 and tuple(c["src"]) == (2, 0, 1)]
    print(f"  A: best drop-in for rev A scores {dropin[0]['coarse']:.3f}"
          if dropin else "  A: no drop-in for rev A survived")
    cand = dropin[:150] + ra[:1500] + [c for _, c in rb[:3000]]
    seen, uniq = set(), []
    for c in cand:
        key = (c["pi"], tuple(c["vi"]), tuple(c["src"]), tuple(c["ri"]))
        if key not in seen:
            seen.add(key)
            uniq.append(c)
    fine = []
    for i0 in range(0, len(uniq), 200):
        sc, j = _eval_ids(uniq[i0:i0 + 200], coarse=False)
        fine.extend(sc)
    order = np.argsort(fine)[::-1]
    uniq = [uniq[i] for i in order]
    fine = [fine[i] for i in order]
    print(f"  {len(uniq)} distinct designs rescored; best {fine[0]:.3f}")

    # realise the best, keeping topology A and B both represented
    keep_d = [c for c in uniq if len(set(c["vi"])) == 1 and c["pi"] == 0
              and tuple(c["src"]) == (2, 0, 1)][:60]
    n_keep = 12 if a.smoke else 250
    keep_a = [c for c in uniq if len(set(c["vi"])) == 1
              and c not in keep_d][:n_keep]
    keep_b = [c for c in uniq if len(set(c["vi"])) > 1][:n_keep]
    keep_a = keep_d + keep_a
    lamps = [realise(c) for c in keep_a + keep_b]
    with mp.get_context("fork").Pool(a.procs) as pool:
        rob = robust(pool, lamps, n_var=2 if a.smoke else 8 if a.quick else 24)
    pickle.dump(dict(ra=ra, rb=rb, lamps=[l.as_dict() for l in lamps], rob=rob),
                open(stash, "wb"))
    rows = []
    for l, c, rr in zip(lamps, keep_a + keep_b, rob):
        med = np.median(rr, axis=0)
        p20 = np.percentile(rr[:, 0], 20)
        rows.append(dict(lamp=l.as_dict(), desc=l.describe(),
                         topo="A" if l.ro == (None, None, None) else "B",
                         score_med=float(med[0]), score_p20=float(p20),
                         vivid_med=float(med[1]), even_med=float(med[2]),
                         lit_med=float(med[3]), sat_med=float(med[4]),
                         bright_med=float(med[5]), ipk_max=float(rr[:, 6].max())))
    rows.sort(key=lambda r: -r["score_med"])
    with open(os.path.join(a.out, "search.json"), "w") as fh:
        json.dump(dict(rows=rows, range=G["range"]), fh, indent=1,
                  default=lambda o: o.item() if hasattr(o, "item") else str(o))
    for r in rows[:25]:
        print(f"  {r['topo']} med {r['score_med']:.3f} p20 {r['score_p20']:.3f} "
              f"vivid {r['vivid_med']:.2f} even {r['even_med']:.2f}  {r['desc']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
