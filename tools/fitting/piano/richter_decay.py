"""Match the early decay of the instrument to the recordings, by register.

The recordings' figure is the fundamental's slope (dB/s, constant-Q level) from 0.08 s to 0.45 s after the peak
of each selected note that has 0.55 s free of other strikes (richter_notes.py: r1). The instrument's is the same
measurement on its own note, held (the key down, as with the pedal). The prompt-sound decay time t1 is scaled
by the ratio, per octave band, smoothed over the keyboard, at most a factor of 2 either way and only half-way
per run; t2 (the slow aftersound) follows by the square root.

   python richter_decay.py           report only
   python richter_decay.py apply     scale t1, t2 in refs/richter-params.npz and lib/richter_fit.lib
"""
import os, subprocess, sys, tempfile
import numpy as np
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import richter_fit as RF                                                  # noqa: E402
import richter_transcribe as T                                            # noqa: E402

F, SR, ROOT = RF.F, RF.SR, RF.ROOT
BANDS = [(36, 47), (48, 59), (60, 71), (72, 83), (84, 95)]


def inst_slope(args):
    k, vel = args
    with tempfile.NamedTemporaryFile(suffix=".f32") as f:
        subprocess.run([os.path.join(ROOT, "build", "render"), RF.SO, f.name, f"{RF.hz(k):.4f}", "0", "0.5", f"{vel}", "3.5", "3.5"],
                       check=True, capture_output=True)
        x = np.fromfile(f.name, dtype=np.float32)
    x = np.concatenate([np.zeros(SR // 2), x])
    db = T.semis(T.cqt_db(x))[k - 21]
    fps = SR / T.HOP
    t0 = int(0.5 * fps)
    pk = t0 + int(np.argmax(db[t0:t0 + 8]))
    seg = db[pk + int(0.08 * fps): pk + int(0.45 * fps)]
    return float(np.polyfit(np.arange(len(seg)) / fps, seg, 1)[0])


def main(apply=False):
    d = np.load(RF.DATA)
    ok = RF.select_mask()
    midi, r1 = d["midi"][ok], d["r1"][ok]
    keys = np.arange(36, 96)
    with Pool(14) as p:
        mine = dict(zip(keys.tolist(), p.map(inst_slope, [(int(k), 0.5) for k in keys])))
    print("register     notes   recordings dB/s   instrument dB/s   ratio")
    ratios = np.full(len(F.KEYS), np.nan)
    for lo, hi in BANDS:
        sel = (midi >= lo) & (midi <= hi) & np.isfinite(r1)
        if sel.sum() < 6:
            print(f"{lo}-{hi}   too few ({int(sel.sum())})"); continue
        real = np.median(r1[sel]); inst = np.median([mine[k] for k in range(lo, hi + 1)])
        ratio = float(np.clip(inst / real, 0.5, 2.0))                     # real falls faster -> ratio < 1 -> shorter t1
        print(f"{lo:3d}-{hi:3d}   {int(sel.sum()):5d}   {real:10.1f}      {inst:10.1f}      {inst / real:5.2f}")
        ratios[(lo + hi) // 2 - 21] = ratio
    if not apply:
        return
    good = np.isfinite(ratios)
    r = np.interp(F.KEYS, F.KEYS[good], np.log(ratios[good]))
    r = np.convolve(np.pad(r, 6, mode="edge"), np.ones(13) / 13, "valid")
    P = dict(np.load(RF.PARAMS))
    P["t1"] = P["t1"] * np.exp(0.5 * r); P["t2"] = np.maximum(P["t2"] * np.exp(0.25 * r), 1.5 * P["t1"])
    np.savez(RF.PARAMS, **P)
    F.write_lib(P); RF.fix_header()
    print("applied (half-way); run again to check")


if __name__ == "__main__":
    main("apply" in sys.argv)
