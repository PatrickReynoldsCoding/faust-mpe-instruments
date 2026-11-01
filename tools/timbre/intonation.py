"""Intonation over the whole range: cents off for every semitone at several pressures and
slide positions (steady notes, the instrument's own vibrato averaged out).
   python intonation.py violin [lo hi]"""
import os, sys, numpy as np
import synth as S
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from pitch import cents_off
ROOT = S.ROOT

def main(inst, lo, hi):
    so = S.build(os.path.join(ROOT, "instruments", "strings", inst + ".dsp"))
    worst = []
    notes = lo * 2 ** (np.arange(0, int(round(12 * np.log2(hi / lo))) + 1) / 12)
    for f in notes:
        row = []
        for p in (0.15, 0.5, 0.9):
            for s in (0.0, 0.5, 1.0):
                x = S.note(so, f, p, s, 0.6, hold=1.6, total=1.6)[int(0.6 * S.SR):int(1.6 * S.SR)]
                c = cents_off(x, f)
                row.append(c); worst.append((abs(c), f, p, s, c))
        print(f"{f:7.1f} Hz  " + " ".join(f"{c:+4.0f}" for c in row))
    worst.sort(reverse=True)
    print("worst:", ", ".join(f"{f:.0f} Hz p={p} s={s}: {c:+.0f}" for _, f, p, s, c in worst[:6]))
    a = np.array([w[0] for w in worst])
    print(f"{np.mean(a <= 10) * 100:.0f}% within 10 cents, {np.mean(a <= 20) * 100:.0f}% within 20, max {a.max():.0f}")

if __name__ == "__main__":
    inst = sys.argv[1]
    lo, hi = (float(sys.argv[2]), float(sys.argv[3])) if len(sys.argv) > 3 else ((196, 1760) if inst == "violin" else (65.41, 880))
    main(inst, lo, hi)
