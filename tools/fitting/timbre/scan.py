"""Scan a lab instrument over settings and grade each note:
   .  Helmholtz motion, in tune      X  wrong note (octave or other mode)
   r  raucous (not periodic)         s  silent        number = cents off when > 15
   python scan.py lab/violin-lab.dsp 196,440,880 bowForceMin=0.2,0.5,1,2 bowPosNear=0.04,0.08,0.15 [fixed=..]"""
import sys, numpy as np
import analysis as A, synth as S
sys.path.insert(0, "../..")
from pitch import cents_off

def grade(x, f):
    seg = x[int(0.5 * S.SR):int(1.3 * S.SR)]
    if np.sqrt(np.mean(seg ** 2)) < 1e-4: return "s"
    if not np.isfinite(seg).all(): return "N"
    t, f0, per, rms = A.track_f0(seg, f / 2.2, f * 2.2)
    if np.median(per) < 0.8: return "r"
    c = cents_off(seg, f)
    if abs(c) > 100: return "X"
    return "." if abs(c) <= 15 else f"{c:+.0f}"

def main():
    dsp = sys.argv[1]; freqs = [float(v) for v in sys.argv[2].split(",")]
    k1, v1 = sys.argv[3].split("="); v1 = [float(v) for v in v1.split(",")]
    k2, v2 = sys.argv[4].split("="); v2 = [float(v) for v in v2.split(",")]
    fixed = dict(a.split("=") for a in sys.argv[5:])
    press = float(fixed.pop("pressure", 0.0)); slide = float(fixed.pop("slide", 0.0))
    so = S.build(dsp)
    for f in freqs:
        print(f"\n{f:g} Hz   rows {k1}, columns {k2} = {v2}")
        for a in v1:
            row = []
            for b in v2:
                x = S.note(so, f, press, slide, 0.5, hold=1.4, total=1.5, extra={**fixed, k1: a, k2: b})
                row.append(grade(x, f))
            print(f"  {a:<8g}" + "".join(f"{r:>6}" for r in row))

if __name__ == "__main__":
    main()
