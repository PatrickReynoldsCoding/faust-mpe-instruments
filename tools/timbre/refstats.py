"""Analyse every reference recording of one player and save the measurements.
   python refstats.py hahn  ->  refs/hahn.npz"""
import glob, os, sys, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analysis as A

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RANGES = {"hahn": (180, 3000), "ma": (60, 1100)}

def main(who):
    fmin, fmax = RANGES[who]
    out = {}
    allf0, allH, allN, alldb, allfile = [], [], [], [], []
    for n, path in enumerate(sorted(glob.glob(os.path.join(ROOT, "refs", who, "*.wav")))):
        r = A.analyse_file(path, fmin, fmax, every=2)
        db = 20 * np.log10(r["rms"] + 1e-12)
        print(f"{os.path.basename(path):24s} frames {len(r['t'])}  voiced {r['mask'].mean():.2f}  analysed {len(r['idx'])}", flush=True)
        allf0.append(r["f0"][r["idx"]]); allH.append(r["H"]); allN.append(r["N"]); alldb.append(db[r["idx"]])
        allfile.append(np.full(len(r["idx"]), n))
        out[f"track_{n}"] = np.stack([r["t"], r["f0"], r["per"], r["rms"]])
    np.savez_compressed(os.path.join(ROOT, "refs", who + ".npz"), f0=np.concatenate(allf0), H=np.concatenate(allH),
                        N=np.concatenate(allN), db=np.concatenate(alldb), fileno=np.concatenate(allfile), **out)

main(sys.argv[1])
