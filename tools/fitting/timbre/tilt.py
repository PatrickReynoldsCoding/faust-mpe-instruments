"""How the tone colour changes with loudness, recording against instrument (same notes):
the level of harmonics 6-15 relative to harmonics 1-3 (dB) per +10 dB of loudness, within
half-octave pitch bands. Positive = brighter when louder.
   python tilt.py violin [--dsp lab/violin-lab.dsp] [name=value ...]"""
import os, sys, numpy as np
import diag

def tilt_slope(H, f0, Hlevel=None):
    """Hlevel: whose loudness to use as the x axis (default: H's own)."""
    p = 10 ** (H / 10)
    lo = 10 * np.log10(np.nansum(p[:, 0:3], 1)); hi = 10 * np.log10(np.nansum(p[:, 5:15], 1))
    lv = 10 * np.log10(np.nansum(10 ** ((H if Hlevel is None else Hlevel) / 10), 1))
    t = hi - lo
    # average over ~0.3 s so the vibrato's own level/colour flicker does not count, only dynamics
    k = np.ones(31) / 31
    lv = np.convolve(np.nan_to_num(lv, nan=np.nanmedian(lv)), k, "same")
    t = np.convolve(np.nan_to_num(t, nan=np.nanmedian(t)), k, "same")
    band = np.floor(2 * np.log2(f0 / 50)).astype(int)
    x, y = lv.copy(), t.copy()
    ok = np.isfinite(x) & np.isfinite(y)
    for b in np.unique(band):
        m = (band == b) & ok
        if m.sum() < 30: ok &= ~(band == b); continue
        x[m] -= x[m].mean(); y[m] -= y[m].mean()
    return float(np.sum(x[ok] * y[ok]) / np.sum(x[ok] ** 2) * 10), float(np.nanmedian(t))

if __name__ == "__main__":
    inst = sys.argv[1]; args = sys.argv[2:]
    dsp = os.path.join("tools", "fitting", "timbre", args[args.index("--dsp") + 1]) if "--dsp" in args else None
    extra = dict((a.split("=")[0], float(a.split("=")[1])) for a in args if "=" in a)
    d = diag.collect(inst, dsp, extra, max_passages=int(os.environ.get("EVAL_N", 10)))
    ok = np.isfinite(d["Hs"]).any(1) & (np.nansum(10 ** (d["Hs"] / 10), 1) > 1e-12)
    st, mt = tilt_slope(d["Ht"][ok], d["f0"][ok]); ss, ms = tilt_slope(d["Hs"][ok], d["f0"][ok])
    s2, _ = tilt_slope(d["Hs"][ok], d["f0"][ok], d["Ht"][ok])
    print(f"upper/lower harmonics: recording {mt:+.1f} dB, slope {st:+.2f} dB per +10 dB;  instrument {ms:+.1f} dB, slope {ss:+.2f}"
          f" (against the player's loudness: {s2:+.2f})")
