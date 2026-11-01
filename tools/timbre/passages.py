"""Pick the stretches of the reference recordings that are a clear single line (few chords),
split them into notes and cache them: refs/<who>-passages.npz.
   python passages.py hahn"""
import os, sys, pickle, glob, numpy as np
import analysis as A, perform as P

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RANGES = {"hahn": (180, 3000), "ma": (60, 1100)}

def main(who, win=15.0, keep=10):
    fmin, fmax = RANGES[who]
    cands = []
    for path in sorted(glob.glob(os.path.join(ROOT, "refs", who, "*.wav"))):
        x = A.load(path)
        for a in np.arange(0, len(x) / A.SR - win, win):
            seg = x[int(a * A.SR):int((a + win) * A.SR)]
            notes, tr = P.notes_from(seg, fmin, fmax, min_per=0.75)
            cover = sum(n["end"] - n["start"] for n in notes) / win
            cands.append((cover, os.path.basename(path)[:-4], float(a), notes))
        print(path, max(c[0] for c in cands if c[1] == os.path.basename(path)[:-4]), flush=True)
    cands.sort(key=lambda c: -c[0])
    best, used = [], {}
    for c in cands:                      # at most 2 windows per movement, for variety
        if used.get(c[1], 0) >= 2: continue
        used[c[1]] = used.get(c[1], 0) + 1
        best.append(c)
        if len(best) == keep: break
    for c in best:
        print(f"  {c[1]:20s} {c[2]:6.1f}s  coverage {c[0]:.2f}  notes {len(c[3])}")
    with open(os.path.join(ROOT, "refs", f"{who}-passages.pkl"), "wb") as f:
        pickle.dump([dict(file=c[1], start=c[2], dur=win, cover=c[0], notes=c[3]) for c in best], f)

if __name__ == "__main__":
    main(sys.argv[1])
