"""Where does the instrument differ from the recording? Median difference (instrument minus
recording, dB) of each harmonic's level relative to the frame total, by register.
   python diag.py violin [--dsp lab/violin-lab.dsp] [name=value ...]"""
import os, sys, pickle, numpy as np
import analysis as A, perform as P, synth as S, evaluate as E

def collect(inst, dsp, extra, max_passages=10):
    c = E.CFG[inst]
    so = S.build(os.path.join(E.ROOT, dsp or c["dsp"]))
    passages = pickle.load(open(os.path.join(E.ROOT, "refs", f"{c['who']}-passages.pkl"), "rb"))[:max_passages]
    L = E.calibrate(so, c["cal"], extra)
    all_db = np.concatenate([n["db"] for p in passages for n in p["notes"]])
    lmap = E.level_map(L, np.array(c["cal"]), None, np.percentile(all_db, 95))
    out = dict(Ht=[], Hs=[], f0=[], dbt=[], dbs=[])
    for p in passages:
        x = A.load(os.path.join(E.ROOT, "refs", c["who"], p["file"] + ".wav"))[int(p["start"] * A.SR):int((p["start"] + p["dur"]) * A.SR)]
        y = S.render(so, P.controls(p["notes"], p["dur"] + 0.5, lmap), extra)[:len(x)]
        y = np.pad(y, (0, len(x) - len(y)))
        yr = P.add_room(y, **E.ROOM)
        t = np.arange(len(x) // A.HOP + 1) * A.HOP / A.SR
        mask = np.zeros(len(t), bool); fs = np.zeros(len(t))
        for n in p["notes"]:
            mask[n["i0"] + int(os.environ.get("SKIP_FRAMES", 4)):n["i1"] - 2] = True; seg = fs[n["i0"]:n["i1"]]; seg[:] = n["hz"][:len(seg)]
        mask &= np.arange(len(t)) % 2 == 0
        it, Ht, _ = A.harmonics(x, t, fs, mask, kmax=30)
        _, Hs, _ = A.harmonics(yr, t, fs, mask, kmax=30)
        out["Ht"].append(Ht); out["Hs"].append(Hs); out["f0"].append(fs[it])
    return {k: np.concatenate(v) for k, v in out.items() if v}

def rel(H):
    return H - 10 * np.log10(np.nansum(10 ** (H / 10), 1))[:, None]

if __name__ == "__main__":
    inst = sys.argv[1]; args = sys.argv[2:]
    dsp = os.path.join("tools", "fitting", "timbre", args[args.index("--dsp") + 1]) if "--dsp" in args else None
    extra = dict((a.split("=")[0], float(a.split("=")[1])) for a in args if "=" in a)
    d = collect(inst, dsp, extra)
    ok = np.isfinite(d["Hs"]).any(1) & (np.nansum(10 ** (d["Hs"] / 10), 1) > 1e-12)
    D = rel(d["Hs"][ok]) - rel(d["Ht"][ok]); f0 = d["f0"][ok]
    edges = [180, 300, 450, 650, 900, 1300, 3000] if inst == "violin" else [60, 90, 130, 180, 260, 400, 1100]
    print("instrument - recording, dB; rows = f0 band, cols = harmonic 1..12, then 13-20 and 21-30")
    for a, b in zip(edges[:-1], edges[1:]):
        m = (f0 >= a) & (f0 < b)
        if m.sum() < 20: continue
        med = np.nanmedian(D[m], 0)
        print(f"  {a:4d}-{b:4d} Hz n={m.sum():5d}: " + " ".join(f"{v:+5.1f}" for v in med[:12]) +
              f" | {np.nanmedian(D[m][:, 12:20]):+5.1f} {np.nanmedian(D[m][:, 20:30]):+5.1f}")
