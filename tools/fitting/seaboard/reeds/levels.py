"""Set a reed's loudness: the slope across its range (`lvl` in lib/<inst>_fit.lib, so the
middle of the range is even within a few dB) and the output level (`out`: -11.5 dB rms for a
held note at pressure 0.8 in the middle of the range).   python levels.py clarinet"""
import sys
import numpy as np
import fit

TARGET = -11.5
nm = sys.argv[1]
inst = fit.INST[nm]
lo, hi = {"clarinet": (147, 1568), "oboe": (233, 1568), "sax": (104, 880)}[nm]


def level(so, f, p=0.8):
    n = int(1.5 * 48000 / 64); ctl = np.zeros((n, 1, 6))
    ctl[:, 0, 0] = f; ctl[:, 0, 1] = np.arange(n) < 900; ctl[:, 0, 2] = p; ctl[:, 0, 3] = 0.5; ctl[:, 0, 4] = 0.7
    y = fit.render(so, ctl)
    return 20 * np.log10(np.sqrt(np.mean(y[24000:48000] ** 2)))


for it in range(3):
    so = fit.build(inst)
    fs = np.geomspace(lo, hi, 7)
    L = np.array([level(so, f) for f in fs])
    slope = np.polyfit(np.log2(fs), L, 1)[0]                 # dB per octave
    s, eq, vals = fit.read_fit(inst["lib"])
    print(f"levels {' '.join(f'{v:.1f}' for v in L)}  slope {slope:+.1f} dB/oct  lvl {vals['lvl']:.2f} out {vals['out']:.1f}")
    # leave a gentle rise of 1 dB an octave, as players do
    vals["lvl"] = vals["lvl"] + (slope - 1.0) / 6.02
    vals["out"] = vals["out"] + TARGET - np.median(L)
    fit.write_fit(inst["lib"], eq, vals)
