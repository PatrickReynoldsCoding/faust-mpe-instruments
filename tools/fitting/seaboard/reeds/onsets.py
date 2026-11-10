"""Attacks and releases of the reference's notes and of the model playing them (fit.py's render):
10-90 % rise time of each note's level, split into tongued (after a gap) and slurred notes, and
the release (time to fall 30 dB after the last note of a phrase).   python onsets.py sax"""
import sys
import numpy as np
import fit
import analysis as A


def env(x, ms=3):
    n = int(48 * ms)
    e = np.sqrt(np.convolve(x ** 2, np.ones(n) / n, "same"))
    return 20 * np.log10(e + 1e-9)


def rise(e, t0, t1):
    a, b = max(0, int((t0 - 0.06) * 48000)), int(min(t1, t0 + 0.4) * 48000)
    seg = e[a:b]
    top = np.percentile(seg, 95); bot = seg[:int(0.03 * 48000)].min()
    lo_, hi_ = bot + 0.1 * (top - bot), bot + 0.9 * (top - bot)
    i = np.argmax(seg > lo_); j = i + np.argmax(seg[i:] > hi_)
    return (j - i) / 48000


inst = fit.INST[sys.argv[1]]
so = fit.build(inst)
x, y, notes, ref = fit.sax_data(inst, so)
ex, ey = env(x), env(y)
for kind in ("tongued", "slurred"):
    rx, ry = [], []
    for k, nt in enumerate(notes):
        gap = nt["start"] - notes[k - 1]["end"] if k else 1
        if (gap > 0.05) != (kind == "tongued"):
            continue
        rx.append(rise(ex, nt["start"], nt["end"])); ry.append(rise(ey, nt["start"], nt["end"]))
    print(f"{kind:8s} n={len(rx):2d}  rise ref {np.median(rx)*1000:5.0f} ms   model {np.median(ry)*1000:5.0f} ms")
rx, ry = [], []
for k, nt in enumerate(notes):
    nxt = notes[k + 1]["start"] if k + 1 < len(notes) else 99
    if nxt - nt["end"] > 0.3:
        for e, out in ((ex, rx), (ey, ry)):
            i = int(nt["end"] * 48000); lvl = np.median(e[i - 2400:i])
            out.append(np.argmax(e[i - 2400:] < lvl - 30) / 48000 - 0.05)
print(f"release (-30 dB) ref {np.median(rx)*1000:.0f} ms  model {np.median(ry)*1000:.0f} ms  (n={len(rx)})")
