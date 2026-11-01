"""Is the string in Helmholtz motion? Counts stick-to-slip changes per period and how long
each stick lasts, from the voice's own stick/slip state (the lab instrument's debugStuck).
Helmholtz motion: 1 slip per period, stuck for (1 - beta) of it.
   python slips.py cello 65,73,98,147 [name=value ...]"""
import sys, numpy as np
import synth as S

def stats(st, f):
    P = S.SR / f
    tr = np.nonzero((st[:-1] > 0.5) & (st[1:] < 0.5))[0]
    if len(tr) < 3: return 0.0, 0.0
    return len(tr) / (len(st) / P), float(np.median(np.diff(tr)) / P)

if __name__ == "__main__":
    inst = sys.argv[1]; freqs = [float(v) for v in sys.argv[2].split(",")]
    extra = dict((a.split("=")[0], float(a.split("=")[1])) for a in sys.argv[3:])
    so = S.build(f"lab/{inst}-lab.dsp")
    print("slips per period (1.00 = Helmholtz); columns pressure/slide")
    combos = [(p, s) for p in (0.15, 0.5, 0.9) for s in (0.0, 0.5, 1.0)]
    print("          " + " ".join(f"{p:.2f}/{s:.1f}" for p, s in combos))
    for f in freqs:
        row = []
        for p, s in combos:
            st = S.note(so, f, p, s, 0.6, hold=1.4, total=1.4, extra={**extra, "debugStuck": 1})[int(0.6 * S.SR):]
            n, _ = stats(st, f)
            row.append(f"{n:8.2f}")
        print(f"{f:7.1f}  " + " ".join(row))
