"""Fast check of the string's brightness by register: the median level of harmonics 1..20
(relative to the frame total) of the player's recordings in each pitch band, against steady
notes of the instrument (with vibrato) in the same bands. Seconds, not minutes.
   python regprofile.py violin [--dsp lab/violin-lab.dsp] [pressure=0.5] [name=value ...]"""
import os, sys, numpy as np
import analysis as A, synth as S, evaluate as E

BANDS = {"violin": [180, 260, 350, 480, 650, 900, 1300], "cello": [60, 85, 120, 170, 240, 340, 480]}

def rel(H):
    return H - 10 * np.log10(np.nansum(10 ** (H / 10), 1))[:, None]

def target_profiles(inst, K=20):
    c = E.CFG[inst]
    d = np.load(os.path.join(E.ROOT, "refs", c["who"] + ".npz"))
    R = rel(d["H"][:, :40])[:, :K]
    out = []
    for a, b in zip(BANDS[inst][:-1], BANDS[inst][1:]):
        m = (d["f0"] >= a) & (d["f0"] < b)
        out.append(np.nanmedian(R[m], 0))
    return np.array(out)

def inst_profiles(so, inst, extra, pressure=0.5, K=20):
    out = []
    for a, b in zip(BANDS[inst][:-1], BANDS[inst][1:]):
        rows = []
        for f in np.geomspace(a, b, 7)[:6] * 1.04:
            x = S.note(so, f, pressure, 0.5, 0.5, hold=1.6, total=1.6, vib_hz=5.8, vib_cents=20, vib_delay=0.1, extra=extra)
            seg = x[int(0.5 * S.SR):]
            t = np.arange(0, len(seg) / S.SR - 0.1, 0.01)
            ff = np.interp(t + 0.5, np.arange(int(1.6 * S.SR / 64)) * 64 / S.SR,
                           S.note_ctl(f, pressure, hold=1.6, total=1.6, vib_hz=5.8, vib_cents=20, vib_delay=0.1)[:, 0, 0])
            _, H, _ = A.harmonics(seg, t, ff, np.ones(len(t), bool), kmax=40)
            rows.append(rel(H)[:, :K])
        out.append(np.nanmedian(np.concatenate(rows), 0))
    return np.array(out)

if __name__ == "__main__":
    inst = sys.argv[1]; args = sys.argv[2:]
    dsp = os.path.join(E.ROOT, "tools", "timbre", args[args.index("--dsp") + 1]) if "--dsp" in args else os.path.join(E.ROOT, E.CFG[inst]["dsp"])
    extra = dict((a.split("=")[0], float(a.split("=")[1])) for a in args if "=" in a)
    p = extra.pop("pressure", 0.5)
    so = S.build(dsp)
    T = target_profiles(inst); I = inst_profiles(so, inst, extra, p)
    D = I - T
    print("instrument - recording (dB), harmonics 1..12 | 13-20 mean;  last col = rms over 1..20")
    for i, (a, b) in enumerate(zip(BANDS[inst][:-1], BANDS[inst][1:])):
        print(f"  {a:4d}-{b:4d}: " + " ".join(f"{v:+5.1f}" for v in D[i, :12]) + f" | {np.nanmean(D[i, 12:20]):+5.1f}   {np.sqrt(np.nanmean(D[i] ** 2)):4.1f}")
    print(f"  overall rms {np.sqrt(np.nanmean(D ** 2)):.2f} dB")
