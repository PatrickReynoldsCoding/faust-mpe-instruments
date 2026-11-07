"""Split the level wobble of each harmonic inside long notes into the part that follows the
vibrato (a function of the instantaneous pitch: body or room response) and the rest (bow
irregularity, noise, reverb of other notes).
   python amsplit.py violin [--dsp lab/violin-lab.dsp] [name=value ...]"""
import os, sys, pickle, numpy as np
import analysis as A, perform as P, synth as S, evaluate as E

def runs_of(idx, min_len=60):
    out, s = [], 0
    for i in range(1, len(idx) + 1):
        if i == len(idx) or idx[i] != idx[i - 1] + 1:
            if i - s >= min_len: out.append((s, i))
            s = i
    return out

def split(H, f0, idx, groups=((1, 3), (4, 10), (11, 30))):
    res = []
    for lo, hi in groups:
        locked, rand = [], []
        for a, b in runs_of(idx):
            c = 1200 * np.log2(f0[a:b]); c = c - np.convolve(np.pad(c, 20, mode="edge"), np.ones(41) / 41, "valid")
            for k in range(lo - 1, hi):
                h = H[a:b, k]
                if not np.isfinite(h).all(): continue
                d = h - np.convolve(np.pad(h, 20, mode="edge"), np.ones(41) / 41, "valid")
                if np.std(c) < 3: continue                 # no vibrato in this note
                X = np.stack([c ** j for j in range(1, 5)], 1)
                X = (X - X.mean(0)) / (X.std(0) + 1e-9)
                coef, *_ = np.linalg.lstsq(X, d - d.mean(), rcond=None)
                fit = X @ coef
                locked.append(np.std(fit)); rand.append(np.std(d - d.mean() - fit))
        res.append((np.median(locked) if locked else np.nan, np.median(rand) if rand else np.nan))
    return res

def collect(inst, dsp, extra, wet):
    c = E.CFG[inst]
    so = S.build(os.path.join(E.ROOT, dsp or c["dsp"]))
    passages = pickle.load(open(os.path.join(E.ROOT, "refs", f"{c['who']}-passages.pkl"), "rb"))
    L = E.calibrate(so, c["cal"], extra)
    all_db = np.concatenate([n["db"] for p in passages for n in p["notes"]])
    lmap = E.level_map(L, np.array(c["cal"]), None, np.percentile(all_db, 95))
    T, Sd, Sr, F, I = [], [], [], [], []
    for pi, p in enumerate(passages):
        x = A.load(os.path.join(E.ROOT, "refs", c["who"], p["file"] + ".wav"))[int(p["start"] * A.SR):int((p["start"] + p["dur"]) * A.SR)]
        y = S.render(so, P.controls(p["notes"], p["dur"] + 0.5, lmap), extra)[:len(x)]
        y = np.pad(y, (0, len(x) - len(y)))
        yr = P.add_room(y, wet_db=wet)
        t = np.arange(len(x) // A.HOP) * A.HOP / A.SR
        mask = np.zeros(len(t), bool); fs = np.zeros(len(t))
        for n in p["notes"]:
            seg = fs[n["i0"]:n["i1"]]; seg[:] = n["hz"][:len(seg)]
            mask[n["i0"] + 4:min(n["i1"] - 2, len(t))] = True
        it, Ht, _ = A.harmonics(x, t, fs, mask, kmax=30)
        _, Hd, _ = A.harmonics(y, t, fs, mask, kmax=30)
        _, Hr, _ = A.harmonics(yr, t, fs, mask, kmax=30)
        T.append(Ht); Sd.append(Hd); Sr.append(Hr); F.append(fs[it]); I.append(it + pi * 100000)
    return [np.concatenate(v) for v in (T, Sd, Sr, F, I)]

if __name__ == "__main__":
    inst = sys.argv[1]; args = sys.argv[2:]
    dsp = os.path.join("tools", "fitting", "timbre", args[args.index("--dsp") + 1]) if "--dsp" in args else None
    extra = dict((a.split("=")[0], float(a.split("=")[1])) for a in args if "=" in a)
    wet = float(os.environ.get("ROOM_WET", -12))
    Ht, Hd, Hr, f0, idx = collect(inst, dsp, extra, wet)
    for name, H in (("recording", Ht), ("instrument dry", Hd), (f"instrument + room {wet:g} dB", Hr)):
        r = split(H, f0, idx)
        print(f"{name:28s} locked/random dB:  h1-3 {r[0][0]:.1f}/{r[0][1]:.1f}   h4-10 {r[1][0]:.1f}/{r[1][1]:.1f}   h11-30 {r[2][0]:.1f}/{r[2][1]:.1f}")
