#!/usr/bin/env python3
"""The rev A board, with at most one more resistor.

    python3 scripts/lamp_search_reva.py

Keeps rev A's wiring exactly -- common anode, red from z, green from x, blue
from -y -- and searches the reference, the three series resistors, and one
optional resistor from the blue die's cathode to +12 V, which raises blue's
threshold on its own.  Everything in it can be tried on a rev A board with a
soldering iron: new values for R13-R17 and, for the one extra resistor, a
bodge from D1 pin 2 to any +12 V pad.  The best are judged against the same
24 plausible real parts as everything else and written to
docs/lamp2/search_plus1.json for scripts/lamp_gallery2.py.
"""
import json, os, sys
import multiprocessing as mp
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lamp_model as LM
import lamp_core as LC
from lamp_search import robust

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
E24 = [1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0,
       3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1]
G = {}


def e24(lo, hi):
    return [round(m * 10 ** d) for d in range(2, 6) for m in E24
            if lo <= m * 10 ** d <= hi]


def _job(args):
    vref, rr = args
    sig, dies = G["sig"], G["dies"]
    out = []
    for rg in e24(10e3, 68e3):
        for rb in e24(2.2e3, 15e3):
            for ro in [None] + e24(15e3, 220e3):
                lamp = LC.Lamp("CA", vref, (2, 0, 1), (rr, rg, rb),
                               ro=(None, None, ro), rail=("GND", "GND", "+12V"))
                cur = lamp.currents(sig, dies)
                if max(c.max() for c in cur) > 5e-3:
                    continue
                mcd = LM.eye_filter(np.stack([dies[d].mcd(c)
                                              for d, c in zip(LC.DIES, cur)]),
                                    LC.DT * LC.SPEEDS["slow!"])
                j = LC.judge(mcd, G["x3"], G["gamut"], every=16)
                if 8.0 <= j["bright"] <= 250.0:
                    out.append((float(j["score"]), lamp.as_dict()))
    out.sort(key=lambda t: -t[0])
    return out[:5]


def main():
    dies = LM.MHPA3528
    G.update(sig=LC.signals(28.0, 200.0, seed=0), dies=dies,
             x3=LC.dies_xyz(dies), gamut=LM.Gamut(dies))
    jobs = [(round(float(v), 2), rr) for v in np.arange(3.5, 4.41, 0.1)
            for rr in e24(270, 820)]
    procs = max(1, os.cpu_count() - 2)
    with mp.get_context("fork").Pool(procs) as pool:
        res = [x for r in pool.map(_job, jobs) for x in r]
    res.sort(key=lambda t: -t[0])
    plain = [t for t in res if t[1]["ro"][2] is None][:3]
    one = [t for t in res if t[1]["ro"][2] is not None][:12]
    lamps = [LC.Lamp(**t[1]) for t in one + plain]
    with mp.get_context("fork").Pool(procs) as pool:
        rob = robust(pool, lamps, n_var=24)
    rows = []
    for lamp, rr in zip(lamps, rob):
        med = np.median(rr, axis=0)
        rows.append(dict(
            lamp=lamp.as_dict(), desc=lamp.describe(),
            topo="A" if lamp.ro[2] is None else "B",
            score_med=float(med[0]), score_p20=float(np.percentile(rr[:, 0], 20)),
            vivid_med=float(med[1]), even_med=float(med[2]), lit_med=float(med[3]),
            sat_med=float(med[4]), bright_med=float(med[5]),
            ipk_max=float(rr[:, 6].max())))
    rows.sort(key=lambda r: -r["score_med"])
    for r in rows:
        print(f"  {r['topo']} med {r['score_med']:.3f} p20 {r['score_p20']:.3f} "
              f"vivid {r['vivid_med']:.2f} even {r['even_med']:.2f}  {r['desc']}")
    with open(os.path.join(ROOT, "docs", "lamp2", "search_plus1.json"), "w") as fh:
        json.dump(dict(rows=rows), fh, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
