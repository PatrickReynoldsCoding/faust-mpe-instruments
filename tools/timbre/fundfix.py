"""The lowest notes: how strong is the fundamental against the strongest of harmonics 1-3, in
the recordings and in the instrument, semitone by semitone over the lowest 1.5 octaves? The
envelope fit is weak there (only those notes' fundamentals land so low), so this measures it
directly and adds the difference to the body correction at those frequencies.
   python fundfix.py violin [--apply]      then: python makebody.py violin --correct"""
import os, sys, numpy as np
import analysis as A, synth as S, evaluate as E

LOW = {"violin": 196.0, "cello": 65.41}

def measure(inst):
    c = E.CFG[inst]
    d = np.load(os.path.join(E.ROOT, "refs", c["who"] + ".npz"))
    so = S.build(os.path.join(E.ROOT, c["dsp"]))
    lo = LOW[inst]
    notes = lo * 2 ** (np.arange(0, 19) / 12)
    rows = []
    for f in notes:
        m = (d["f0"] > f * 2 ** (-0.5 / 12)) & (d["f0"] < f * 2 ** (0.5 / 12))
        H = d["H"][m][:, :3]
        tgt = np.nanmedian(H[:, 0] - np.nanmax(H, 1)) if m.sum() > 40 else np.nan
        x = S.note(so, f, 0.6, 0.5, 0.6, hold=1.6, total=1.6, vib_hz=6, vib_cents=12, vib_delay=0.1)[int(0.5 * S.SR):]
        t = np.arange(0.1, 0.9, 0.01)
        _, Hs, _ = A.harmonics(x, t, np.full(len(t), f), np.ones(len(t), bool), kmax=3)
        ins = np.nanmedian(Hs[:, 0] - np.nanmax(Hs, 1))
        rows.append((f, tgt, ins, m.sum()))
    return np.array(rows)

def main(inst, apply=False):
    r = measure(inst)
    print(f"{'Hz':>7s} {'recording':>10s} {'instrument':>11s} {'frames':>7s}")
    for f, t, i, n in r:
        print(f"{f:7.1f} {t:10.1f} {i:11.1f} {int(n):7d}")
    ok = np.isfinite(r[:, 1])
    diff = np.interp(np.log2(r[:, 0]), np.log2(r[ok, 0]), (r[ok, 1] - r[ok, 2]))
    diff = np.convolve(np.pad(diff, 1, mode="edge"), [0.25, 0.5, 0.25], "valid")      # smooth over semitones
    diff = np.clip(diff, -6, 6)
    print("difference to add (dB):", " ".join(f"{v:+.1f}" for v in diff))
    if apply:
        cp = os.path.join(E.ROOT, "refs", f"{inst}-correction.npz")
        cor = np.load(cp); f, db = cor["f"], cor["db"].copy()
        lo, hi = r[0, 0], r[-1, 0]
        w = np.clip((np.log2(hi * 1.12) - np.log2(f)) / np.log2(1.25), 0, 1)       # taper off above the range
        add = np.interp(np.log2(f), np.log2(r[:, 0]), diff) * w
        np.savez(cp, f=f, db=np.clip(db + 0.8 * add, -12, 12))
        print("applied to", cp)

if __name__ == "__main__":
    main(sys.argv[1], "--apply" in sys.argv)
