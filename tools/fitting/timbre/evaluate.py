"""Compare an instrument with a player's recordings, note for note.

The player's own performance (notes, pitch curve with vibrato, loudness) is taken from
each cached passage (passages.py) and played on the instrument. The result, with a room
added, is measured exactly like the recording, frame by frame, and the two are compared:

  envelope   the average harmonic envelope (body + bridge) difference, dB rms 200 Hz-10 kHz
  timbre     per frame, harmonic levels 1..20 relative to the frame total, median |diff| dB
  noise      level between harmonics relative to the harmonics (harmonics 1-3, 4-10, 11-30)
  vib-AM     how much each harmonic's level wobbles inside a long note (the body's peaks
             and valleys seen through vibrato), dB, harmonics 1-3, 4-10, 11-30
  bright     how much brighter the sound gets per 10 dB louder (harmonic centroid)
  mrstft     multi-resolution log-spectrogram distance (lower is closer)

   python evaluate.py violin [--dsp lab/violin-lab.dsp] [--wav] [--correction] [name=value ...]
--wav writes A/B files to refs/ab/<instrument>/, --correction saves the envelope difference
for makebody.py --apply-diff."""
import os, sys, pickle, json, numpy as np
import analysis as A, perform as P, synth as S, body

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
CFG = {
    "violin": dict(who="hahn", fmin=180, fmax=3000, dsp="instruments/strings/violin.dsp", env=(200, 10000),
                   cal=(196, 330, 523, 880, 1400)),
    "cello": dict(who="ma", fmin=60, fmax=1100, dsp="instruments/strings/cello.dsp", env=(70, 8000),
                  cal=(65.4, 110, 196, 330, 523)),
}
ROOM = dict(wet_db=float(os.environ.get("ROOM_WET", -12.0)), rt60=float(os.environ.get("ROOM_RT60", 2.0)))
PRESSURES = np.array([0.0, 0.05, 0.1, 0.2, 0.3, 0.45, 0.6, 0.8, 1.0])


def calibrate(so, cal, extra):
    """Steady level (dB) of the instrument for each calibration pitch and pressure."""
    L = np.zeros((len(cal), len(PRESSURES)))
    for i, f in enumerate(cal):
        for j, p in enumerate(PRESSURES):
            x = S.note(so, f, p, 0.5, 0.5, hold=1.2, total=1.2, extra=extra)
            L[i, j] = 20 * np.log10(np.sqrt(np.mean(x[int(0.6 * S.SR):] ** 2)) + 1e-9)
    return L


def level_map(L, cal, ref_db, top_db):
    """Function (recording level dB, Hz) -> pressure. The recording's top level maps to the
    instrument at full pressure; quieter playing maps dB for dB as far as the instrument goes."""
    Lm = np.maximum.accumulate(L, axis=1)            # make each row monotonic for inversion
    lc = np.log2(cal)

    def fn(db, hz):
        want = db - top_db                           # dB below the player's loudest
        out = np.empty_like(db)
        li = np.clip(np.interp(np.log2(hz), lc, np.arange(len(cal))), 0, len(cal) - 1)
        for n in range(len(db)):
            a = int(min(li[n], len(cal) - 2)); w = li[n] - a
            row = Lm[a] * (1 - w) + Lm[a + 1] * w
            row = row - Lm[:, -1].mean()             # 0 dB = full pressure, average pitch
            out[n] = np.interp(want[n], row + np.arange(len(row)) * 1e-6, PRESSURES)
        return out
    return fn


def frame_stats(x, t, f0, mask):
    idx, H, N = A.harmonics(x, t, f0, mask, kmax=40, fmax=14000)
    return idx, H, N


def centroid(H):
    p = 10 ** (H / 10)
    k = np.arange(1, H.shape[1] + 1)
    with np.errstate(invalid="ignore"):
        return np.nansum(p * k, 1) / np.nansum(p, 1)


def vib_am(H, idx, groups, min_len=80):
    """Std (dB) of harmonic levels inside runs of consecutive frames, after removing a
    slow trend (0.2 s). idx are 5 ms frame numbers."""
    runs, start = [], 0
    for i in range(1, len(idx) + 1):
        if i == len(idx) or idx[i] != idx[i - 1] + 1:
            if i - start >= min_len: runs.append((start, i))
            start = i
    out = []
    for lo, hi in groups:
        vals = []
        for a, b in runs:
            h = H[a:b, lo - 1:hi]
            k = np.ones(41) / 41
            for c in range(h.shape[1]):
                col = h[:, c]
                if not np.isfinite(col).all(): continue
                tr = np.convolve(np.pad(col, 20, mode="edge"), k, "valid")
                vals.append(np.std(col - tr))
        out.append(float(np.median(vals)) if vals else float("nan"))
    return out


def mrstft(a, b):
    """Mean |log power difference| over three STFT sizes, on loudness-matched signals."""
    d = []
    for n in (512, 2048, 8192):
        def spec(x):
            F = A.frames(x, n, n // 4) * np.hanning(n)
            return np.log10(np.abs(np.fft.rfft(F, axis=1)) ** 2 + 1e-9)
        sa, sb = spec(a), spec(b)
        m = min(len(sa), len(sb))
        sa, sb = sa[:m], sb[:m]
        act = sa.max(1) > sa.max() - 6                   # frames with sound in the recording
        d.append(np.mean(np.abs(sa[act] - sb[act])))
    return float(np.mean(d))


def run(inst, dsp=None, extra=None, wav=False, correction=False, quiet=False):
    c = CFG[inst]
    extra = extra or {}
    so = S.build(os.path.join(ROOT, dsp or c["dsp"]))
    passages = pickle.load(open(os.path.join(ROOT, "refs", f"{c['who']}-passages.pkl"), "rb"))[:int(os.environ.get("EVAL_N", 99))]
    L = calibrate(so, c["cal"], extra)
    all_db = np.concatenate([n["db"] for p in passages for n in p["notes"]])
    top = np.percentile(all_db, 95)
    lmap = level_map(L, np.array(c["cal"]), None, top)
    T, Sy = dict(H=[], N=[], f0=[], db=[], idx=[]), dict(H=[], N=[], db=[])
    mr = []
    if wav:
        abdir = os.path.join(ROOT, "refs", "ab", inst, os.environ.get("AB_TAG", "current"))
        os.makedirs(abdir, exist_ok=True)
    for pi, p in enumerate(passages):
        x = A.load(os.path.join(ROOT, "refs", c["who"], p["file"] + ".wav"))
        x = x[int(p["start"] * A.SR):int((p["start"] + p["dur"]) * A.SR)]
        ctl = P.controls(p["notes"], p["dur"] + 0.5, lmap)
        y = S.render(so, ctl, extra)[:len(x)]
        y = np.pad(y, (0, len(x) - len(y)))
        yr = P.add_room(y, **ROOM)
        # same frames, same f0 (the recording's) for both
        t, f0, per, rms = A.track_f0(x, c["fmin"], c["fmax"])
        mask = np.zeros(len(t), bool)
        for n in p["notes"]:
            mask[n["i0"] + 4:n["i1"] - 2] = True         # skip the first 20 ms of each note
        mask &= np.arange(len(t)) % 2 == 0
        fs = np.zeros(len(t))
        for n in p["notes"]:
            fs[n["i0"]:n["i1"]] = n["hz"]
        it, Ht, Nt = frame_stats(x, t, fs, mask)
        _, Hs, Ns = frame_stats(yr, t, fs, mask)
        T["H"].append(Ht); T["N"].append(Nt); T["f0"].append(fs[it]); T["idx"].append(it + pi * 100000)
        Sy["H"].append(Hs); Sy["N"].append(Ns)
        T["db"].append(20 * np.log10(rms[it] + 1e-12))
        g = np.sqrt(np.mean(x ** 2) / max(np.mean(yr ** 2), 1e-20))
        mr.append(mrstft(x, yr * g))
        if wav:
            base = os.path.join(abdir, f"{pi:02d}-{p['file']}")
            peak = max(np.abs(x).max(), np.abs(yr * g).max())
            A.save(base + "-1-recording.wav", x / peak * 0.9)
            A.save(base + "-2-instrument-in-room.wav", yr * g / peak * 0.9)
            A.save(base + "-3-instrument-dry.wav", y / np.abs(y).max() * 0.9)
    Ht = np.concatenate(T["H"]); Hs = np.concatenate(Sy["H"]); Nt = np.concatenate(T["N"]); Ns = np.concatenate(Sy["N"])
    f0 = np.concatenate(T["f0"]); idx = np.concatenate(T["idx"]); dbt = np.concatenate(T["db"])
    ok = np.isfinite(Hs).any(1) & np.isfinite(Ht).any(1) & (np.nansum(10 ** (Hs / 10), 1) > 1e-12)
    Ht, Hs, Nt, Ns, f0, idx, dbt = Ht[ok], Hs[ok], Nt[ok], Ns[ok], f0[ok], idx[ok], dbt[ok]

    res = {}
    # envelope
    grid = 60 * 2 ** (np.arange(0, int(np.log2(14000 / 60) * 24) + 1) / 24)
    g1, Bt, *_ = body.fit_body(f0, Ht, grid=grid, smooth_bins=1.5)
    g2, Bs, *_ = body.fit_body(f0, Hs, grid=grid, smooth_bins=1.5)
    lo, hi = c["env"]
    m = (grid > lo) & (grid < hi)
    diff = Bt - Bs
    diff -= diff[m].mean()
    res["envelope"] = float(np.sqrt(np.mean(diff[m] ** 2)))
    # per-frame timbre
    def rel(H):
        tot = 10 * np.log10(np.nansum(10 ** (H / 10), 1))
        return H - tot[:, None]
    rt, rs = rel(Ht)[:, :20], rel(Hs)[:, :20]
    res["timbre"] = float(np.nanmedian(np.abs(rt - rs)))
    groups = [(1, 3), (4, 10), (11, 30)]
    res["noise_t"] = [float(np.nanmedian(Ht[:, a - 1:b] - Nt[:, a - 1:b])) for a, b in groups]
    res["noise_s"] = [float(np.nanmedian(Hs[:, a - 1:b] - Ns[:, a - 1:b])) for a, b in groups]
    res["vibam_t"] = vib_am(Ht, idx // 2, groups)
    res["vibam_s"] = vib_am(Hs, idx // 2, groups)
    ct, cs = centroid(Ht), centroid(Hs)
    dbs = 10 * np.log10(np.nansum(10 ** (Hs / 10), 1))
    # within half-octave pitch bands, so that "loud notes are often high notes" does not count
    band = np.floor(2 * np.log2(f0 / 50)).astype(int)
    def slope(lv, cc):
        x, y = lv.copy(), cc.copy()
        for b in np.unique(band):
            m = band == b
            x[m] -= x[m].mean(); y[m] -= y[m].mean()
        ok = np.isfinite(x) & np.isfinite(y)
        return float(np.sum(x[ok] * y[ok]) / np.sum(x[ok] ** 2) * 10)
    res["bright_t"] = slope(dbt, ct)
    res["bright_s"] = slope(dbs, cs)
    res["centroid_t"] = float(np.median(ct)); res["centroid_s"] = float(np.median(cs))
    res["level_corr"] = float(np.corrcoef(dbt, dbs)[0, 1])
    res["mrstft"] = float(np.mean(mr))
    if correction:
        np.savez(os.path.join(ROOT, "refs", f"{inst}-lastdiff.npz"), f=grid, db=np.where(m | (grid > hi), diff, diff[m][0]))
    if not quiet:
        print(f"{inst}: {len(passages)} passages, {len(f0)} frames compared")
        print(f"  envelope error   {res['envelope']:.2f} dB rms ({lo}-{hi} Hz)")
        print(f"  timbre error     {res['timbre']:.2f} dB median per harmonic (1-20)")
        print(f"  noise (harm/between, dB)   recording {fmt(res['noise_t'])}   instrument {fmt(res['noise_s'])}")
        print(f"  vibrato AM (dB)            recording {fmt(res['vibam_t'])}   instrument {fmt(res['vibam_s'])}")
        print(f"  centroid (harmonic no.)    recording {res['centroid_t']:.2f}   instrument {res['centroid_s']:.2f}")
        print(f"  brighter per +10 dB        recording {res['bright_t']:+.2f}   instrument {res['bright_s']:+.2f}")
        print(f"  level correlation {res['level_corr']:.2f}    mrstft {res['mrstft']:.3f}")
        print("  envelope diff by band (recording - instrument, dB): " +
              " ".join(f"{int(a)}-{int(b)}:{np.mean(diff[(grid >= a) & (grid < b)]):+.1f}" for a, b in
                       ((lo, 400), (400, 800), (800, 1600), (1600, 3200), (3200, 6400), (6400, hi))))
    return res


def fmt(v):
    return " ".join(f"{x:5.1f}" for x in v)


if __name__ == "__main__":
    inst = sys.argv[1]
    dsp = None; extra = {}
    args = sys.argv[2:]
    if "--dsp" in args:
        dsp = os.path.join("tools", "fitting", "timbre", args[args.index("--dsp") + 1]);
    extra = dict((a.split("=")[0], float(a.split("=")[1])) for a in args if "=" in a)
    r = run(inst, dsp, extra, wav="--wav" in args, correction="--correction" in args)
    if "--json" in args:
        print(json.dumps(r))
