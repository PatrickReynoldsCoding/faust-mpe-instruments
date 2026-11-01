"""Vibrato of a player, from the long notes in the cached passages: rate (Hz), extent (cents,
half of peak-to-peak), how long after the note starts it reaches half its extent, and how much
rate and extent wander.   python vibstats.py hahn"""
import os, sys, pickle, numpy as np
import analysis as A

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def main(who):
    ps = pickle.load(open(os.path.join(ROOT, "refs", f"{who}-passages.pkl"), "rb"))
    rates, ext, onset, rate_sd, ext_sd = [], [], [], [], []
    for p in ps:
        for n in p["notes"]:
            if n["end"] - n["start"] < 0.5: continue
            c = 1200 * np.log2(n["hz"] / np.median(n["hz"]))
            fs = A.SR / A.HOP
            tr = np.convolve(np.pad(c, 25, mode="edge"), np.ones(51) / 51, "valid")    # 0.25 s trend
            v = c - tr
            # cycles from zero crossings (upward)
            z = np.nonzero((v[:-1] < 0) & (v[1:] >= 0))[0]
            if len(z) < 3: continue
            per = np.diff(z) / fs
            ok = (per > 1 / 9) & (per < 1 / 3.5)
            if ok.sum() < 2: continue
            rates.append(1 / np.median(per[ok])); rate_sd.append(np.std(1 / per[ok]) / rates[-1])
            amps = [0.5 * (v[a:b].max() - v[a:b].min()) for a, b in zip(z[:-1], z[1:])]
            ext.append(np.median(amps)); ext_sd.append(np.std(amps) / max(np.median(amps), 1e-6))
            env = np.array(amps); half = np.nonzero(env > 0.5 * env.max())[0]
            onset.append(z[half[0]] / fs if len(half) else np.nan)
    q = lambda v: f"median {np.nanmedian(v):.2f}  (quartiles {np.nanpercentile(v, 25):.2f}-{np.nanpercentile(v, 75):.2f})"
    print(f"{who}: {len(rates)} long notes")
    print("  rate Hz        ", q(rates))
    print("  extent cents   ", q(ext))
    print("  onset s        ", q(onset))
    print("  rate wander    ", q(rate_sd))
    print("  extent wander  ", q(ext_sd))

main(sys.argv[1])
