#!/usr/bin/env python3
"""Topology C: let each die watch a blend of two signals.

    python3 scripts/lamp_search_mix.py [--out docs/lamp2] [--quick]

A die fed from two op-amp outputs through two resistors sees their weighted
average.  That matters here because the signals are phase-shifted copies of
each other around a wing: y leads x by about 40 degrees, z lags x by about
50, and x - y is -dx/dt / s, a quarter cycle ahead of x.  A blend can put a
die's peak anywhere in the orbit, which one signal alone cannot -- and three
dies peaking a third of an orbit apart make the hue turn.

This searches blends, thresholds and gains per die by an evolutionary
polish from many random starts (the space is far too big to enumerate),
realises the best with E24 resistors, and writes them to search_mix.json in
the same form scripts/lamp_search.py writes search.json, so the gallery can
rank all three topologies together.
"""
import argparse, json, os, sys, time
import multiprocessing as mp
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lamp_model as LM
import lamp_core as LC
from lamp_search import E24_ALL, V_ON, robust

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
G = {}
EVAL_T = 200.0          # time units per evaluation during the search


def _drive(p, k, sig):
    """Open-circuit volts die k sees for parameter set p (before any
    offset): f*s1 + (1-f)*s2, or just s1."""
    s1, s2, f = p["s1"][k], p["s2"][k], p["f"][k]
    v = sig[s1] if s2 is None else f * sig[s1] + (1.0 - f) * sig[s2]
    return v


def evaluate(p, sig=None, dies=None, every=8):
    sig = G["sig"] if sig is None else sig
    dies = G["dies"] if dies is None else dies
    mcd, peaks = [], []
    for k, d in enumerate(LC.DIES):
        v = _drive(p, k, sig)
        drive = (p["vr"][k] - v) if p["part"] == "CA" else (v - p["vr"][k])
        i = dies[d].current(drive, p["r"][k])
        peaks.append(i.max())
        mcd.append(dies[d].mcd(i))
    mcd = LM.eye_filter(np.stack(mcd), LC.DT * LC.SPEEDS["slow!"])
    j = LC.judge(mcd, G["x3"], G["gamut"], every=every)
    ok = 8.0 <= j["bright"] <= 250.0 and all(1e-4 <= pk <= 6e-3 for pk in peaks)
    return (float(j["score"]) if ok else 0.0), j


def _valid(p):
    for k in range(3):
        lo, hi = G["range_mix"](p, k)
        rev = (hi - p["vr"][k]) if p["part"] == "CA" else (p["vr"][k] - lo)
        if rev > 4.6:
            return False
        if p["s2"][k] is not None:
            r1 = p["r"][k] / p["f"][k]
            r2 = p["r"][k] / (1.0 - p["f"][k])
            s1r, s2r = G["range"][p["s1"][k]], G["range"][p["s2"][k]]
            cross = max(abs(s1r[1] - s2r[0]), abs(s2r[1] - s1r[0])) / (r1 + r2)
            if cross > 3e-3:
                return False
    return True


def _range_mix(p, k):
    v = _drive(p, k, G["sig"])
    return float(v.min()), float(v.max())


def _random(rng):
    part = "CA" if rng.random() < 0.5 else "CC"
    p = dict(part=part, s1=[], s2=[], f=[], vr=[], r=[])
    for k in range(3):
        s1 = int(rng.integers(3))
        s2 = None if rng.random() < 0.3 else int((s1 + rng.integers(1, 3)) % 3)
        p["s1"].append(s1)
        p["s2"].append(s2)
        p["f"].append(float(rng.uniform(0.15, 0.85)))
        p["r"].append(float(np.exp(rng.uniform(np.log(330), np.log(33000)))))
        lo, hi = _range_mix(p, k)
        von = V_ON[LC.DIES[k]]
        # a threshold somewhere inside the blend's own swing
        t = rng.uniform(lo, hi)
        p["vr"].append(float(t + von if part == "CA" else t - von))
    return p


def _mutate(p, rng, scale):
    q = {k: (list(v) if isinstance(v, list) else v) for k, v in p.items()}
    k = int(rng.integers(3))
    what = rng.random()
    if what < 0.35:
        q["vr"][k] += float(rng.normal(0, 0.25 * scale))
    elif what < 0.6:
        q["r"][k] *= float(np.exp(rng.normal(0, 0.35 * scale)))
        q["r"][k] = float(np.clip(q["r"][k], 150, 68000))
    elif what < 0.8:
        q["f"][k] = float(np.clip(q["f"][k] + rng.normal(0, 0.12 * scale), 0.08, 0.92))
    elif what < 0.9:
        s1 = int(rng.integers(3))
        q["s1"][k] = s1
        if q["s2"][k] == s1:
            q["s2"][k] = int((s1 + 1) % 3)
    else:
        q["s2"][k] = None if q["s2"][k] is not None else int((q["s1"][k] + rng.integers(1, 3)) % 3)
    return q


def _job(seed):
    rng = np.random.default_rng(seed)
    pop = []
    while len(pop) < 40:
        p = _random(rng)
        if _valid(p):
            pop.append((evaluate(p)[0], p))
    pop.sort(key=lambda t: -t[0])
    for gen in range(G["gens"]):
        kids = []
        for _ in range(24):
            parent = pop[min(int(rng.exponential(5)), len(pop) - 1)][1]
            kid = _mutate(parent, rng, 1.0 if gen < G["gens"] // 2 else 0.4)
            if _valid(kid):
                kids.append((evaluate(kid)[0], kid))
        pop = sorted(pop + kids, key=lambda t: -t[0])[:40]
    return pop[:8]


def realise(p):
    """E24 resistors for a blend: R1 = R/f and R2 = R/(1-f) put R in
    parallel with the right weights; then the common pin takes the middle
    die's reference and the other two get a resistor to a rail, exactly as
    in topology B."""
    near = lambda v: min(E24_ALL, key=lambda e: abs(np.log(e / v)))
    rs, rs2 = [], []
    for k in range(3):
        if p["s2"][k] is None:
            rs.append(near(p["r"][k]))
            rs2.append(None)
        else:
            rs.append(near(p["r"][k] / p["f"][k]))
            rs2.append(near(p["r"][k] / (1.0 - p["f"][k])))
    vref = float(np.median(p["vr"]))
    ro, rail = [None] * 3, ["GND"] * 3
    for k in range(3):
        delta = p["vr"][k] - vref
        if abs(delta) < 0.05:
            continue
        rk = 1.0 / (1.0 / rs[k] + (0 if rs2[k] is None else 1.0 / rs2[k]))
        vr = -12.0 if delta > 0 else 12.0
        von = V_ON[LC.DIES[k]] * (-1.0 if p["part"] == "CA" else 1.0)
        want = rk * (vref - vr + von) / delta
        ro[k] = near(want)
        rail[k] = "+12V" if vr > 0 else "-12V"
    return LC.Lamp(p["part"], round(vref, 2), p["s1"], rs, ro, rail,
                   src2=p["s2"], rs2=rs2)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=os.path.join(ROOT, "docs", "lamp2"))
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--procs", type=int, default=max(1, os.cpu_count() - 2))
    a = ap.parse_args()
    dies = LM.MHPA3528
    sig = LC.signals(28.0, EVAL_T, seed=0)
    wide = LC.signals(31.0, 200.0, seed=3)
    G.update(sig=sig, dies=dies, x3=LC.dies_xyz(dies), gamut=LM.Gamut(dies),
             range_mix=_range_mix, gens=30 if a.quick else 70,
             range=[(float(min(s.min(), w.min())), float(max(s.max(), w.max())))
                    for s, w in zip(sig, wide)])
    n_jobs = 64 if a.quick else 480
    t0 = time.time()
    found = []
    with mp.get_context("fork").Pool(a.procs) as pool:
        for n, res in enumerate(pool.imap_unordered(_job, range(n_jobs))):
            found.extend(res)
            if n % 40 == 0:
                best = max(f[0] for f in found)
                print(f"    C: {n}/{n_jobs} ({time.time()-t0:.0f} s), best {best:.3f}",
                      flush=True)
    found.sort(key=lambda t: -t[0])
    seen, lamps = set(), []
    for sc, p in found:
        lamp = realise(p)
        key = lamp.describe()
        if key in seen:
            continue
        seen.add(key)
        lamps.append(lamp)
        if len(lamps) >= (60 if a.quick else 300):
            break
    print(f"  C: {len(lamps)} realised; judging against real parts")
    with mp.get_context("fork").Pool(a.procs) as pool:
        rob = robust(pool, lamps, n_var=8 if a.quick else 24)
    rows = []
    for l, rr in zip(lamps, rob):
        med = np.median(rr, axis=0)
        rows.append(dict(lamp=l.as_dict(), desc=l.describe(), topo="C",
                         score_med=float(med[0]),
                         score_p20=float(np.percentile(rr[:, 0], 20)),
                         vivid_med=float(med[1]), even_med=float(med[2]),
                         lit_med=float(med[3]), sat_med=float(med[4]),
                         bright_med=float(med[5]), ipk_max=float(rr[:, 6].max())))
    rows.sort(key=lambda r: -r["score_med"])
    with open(os.path.join(a.out, "search_mix.json"), "w") as fh:
        json.dump(dict(rows=rows), fh, indent=1,
                  default=lambda o: o.item() if hasattr(o, "item") else str(o))
    for r in rows[:15]:
        print(f"  C med {r['score_med']:.3f} p20 {r['score_p20']:.3f} vivid "
              f"{r['vivid_med']:.2f} even {r['even_med']:.2f}  {r['desc']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
