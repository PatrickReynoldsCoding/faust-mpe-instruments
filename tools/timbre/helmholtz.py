"""Map where the bare string gives clean Helmholtz motion (a sawtooth at the bridge).
For each pitch, bow speed and bow position, try a range of bow forces and print a quality
mark per force:  # clean   + nearly   - weak fundamental / multiple slips   r raucous   s silent
   python helmholtz.py lab/violin-lab.dsp 196,440,880 0.1,0.3 0.05,0.08,0.12,0.18 [k=v...]"""
import sys, numpy as np
import analysis as A, synth as S

FORCES = [0.05, 0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 6.4]

def quality(x, f):
    seg = x[int(0.7 * S.SR):int(1.3 * S.SR)]
    if np.sqrt(np.mean(seg ** 2)) < 1e-4: return "s", 99
    t, f0, per, rms = A.track_f0(seg, f / 2.2, f * 2.2)
    if np.median(per) < 0.8 or abs(1200 * np.log2(np.median(f0) / f)) > 50: return "r", 99
    idx, H, N = A.harmonics(seg, t, np.full_like(f0, f), np.ones(len(f0), bool), kmax=6)
    h = np.nanmedian(H, 0); h = h - h[0]
    err = np.sqrt(np.mean((h[1:4] + 20 * np.log10([2, 3, 4])) ** 2))
    return ("#" if err < 2 else "+" if err < 4 else "-"), err

def main():
    dsp = sys.argv[1]
    freqs = [float(v) for v in sys.argv[2].split(",")]
    vbs = [float(v) for v in sys.argv[3].split(",")]
    betas = [float(v) for v in sys.argv[4].split(",")]
    fixed = dict(a.split("=") for a in sys.argv[5:])
    so = S.build(dsp)
    print("forces:", FORCES)
    for f in freqs:
        for vb in vbs:
            for be in betas:
                marks = []
                for F in FORCES:
                    x = S.note(so, f, 0, 0, 0.5, hold=1.4, total=1.5,
                               extra={**fixed, "bowSpeedMin": vb, "bowForceMin": F, "bowPosNear": be})
                    marks.append(quality(x, f)[0])
                print(f"{f:6g} Hz  vb {vb:<5g} beta {be:<5g}  " + " ".join(marks))

if __name__ == "__main__":
    main()
