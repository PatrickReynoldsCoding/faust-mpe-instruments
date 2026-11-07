"""Attacks and note changes, recording against instrument (same notes, same performance).
  rise      ms from the note's start until it is within 3 dB of its own median level
  dip       for slurred note changes (gap < 25 ms): how far the level drops at the change, dB
  clean     how periodic the first 40 ms are (YIN periodicity, 1 = clean)
   python onsets.py violin [--dsp lab/violin-lab.dsp] [name=value ...]"""
import os, sys, pickle, numpy as np
import analysis as A, perform as P, synth as S, evaluate as E

def measure(x, notes, fmin, fmax):
    t, f0, per, rms = A.track_f0(x, fmin, fmax)
    db = 20 * np.log10(rms + 1e-9)
    out = dict(rise_gap=[], rise_leg=[], dip=[], clean_gap=[], clean_leg=[])
    for k, n in enumerate(notes):
        i0, i1 = n["i0"], min(n["i1"], len(db))
        if i1 - i0 < 20: continue
        med = np.median(db[i0:i1])
        gap = n["start"] - notes[k - 1]["end"] if k else 9
        r = np.nonzero(db[i0:i1] > med - 3)[0]
        rise = r[0] * A.HOP / A.SR * 1000 if len(r) else np.nan
        clean = np.mean(per[i0:i0 + 8])
        if gap > 0.06:
            out["rise_gap"].append(rise); out["clean_gap"].append(clean)
        elif gap < 0.025:
            out["rise_leg"].append(rise); out["clean_leg"].append(clean)
            a = max(0, i0 - 4)
            out["dip"].append(med - np.min(db[a:i0 + 12]))
    return out

def run(inst, dsp, extra):
    c = E.CFG[inst]
    so = S.build(os.path.join(E.ROOT, dsp or c["dsp"]))
    passages = pickle.load(open(os.path.join(E.ROOT, "refs", f"{c['who']}-passages.pkl"), "rb"))
    L = E.calibrate(so, c["cal"], extra)
    all_db = np.concatenate([n["db"] for p in passages for n in p["notes"]])
    lmap = E.level_map(L, np.array(c["cal"]), None, np.percentile(all_db, 95))
    R, I = {}, {}
    for p in passages:
        x = A.load(os.path.join(E.ROOT, "refs", c["who"], p["file"] + ".wav"))[int(p["start"] * A.SR):int((p["start"] + p["dur"]) * A.SR)]
        y = S.render(so, P.controls(p["notes"], p["dur"] + 0.5, lmap), extra)[:len(x)]
        y = P.add_room(np.pad(y, (0, len(x) - len(y))), **E.ROOM)
        for d, sig in ((R, x), (I, y)):
            for k, v in measure(sig, p["notes"], c["fmin"], c["fmax"]).items():
                d.setdefault(k, []).extend(v)
    q = lambda v: f"{np.nanmedian(v):6.1f} ({np.nanpercentile(v, 25):.1f}-{np.nanpercentile(v, 75):.1f})"
    print(f"{'':22s}{'recording':>24s}{'instrument':>24s}")
    for k, lbl in (("rise_gap", "rise after a gap, ms"), ("rise_leg", "rise when slurred, ms"), ("dip", "dip at slur, dB"),
                   ("clean_gap", "clean start, gap"), ("clean_leg", "clean start, slur")):
        print(f"{lbl:22s}{q(R[k]):>24s}{q(I[k]):>24s}   n={len(R[k])}")

if __name__ == "__main__":
    inst = sys.argv[1]; args = sys.argv[2:]
    dsp = os.path.join("tools", "fitting", "timbre", args[args.index("--dsp") + 1]) if "--dsp" in args else None
    run(inst, dsp, dict((a.split("=")[0], float(a.split("=")[1])) for a in args if "=" in a))
