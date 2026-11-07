"""Fit the piano (lib/piano.lib) to the Iowa single notes and write lib/piano_fit.lib.

Every parameter is a table with one value per key (A0..C8), smoothed across the keyboard:
  stretch   cents the fundamental sits from equal temperament (pianos are tuned stretched)
  B         inharmonicity, realised as a cascade of first-order allpasses in the string loop
            (apM stages of coefficient apA; fitted here so the loop's partials land on
            n f0 sqrt(1 + B n^2))
  t1, p1    the prompt sound: T60 at the fundamental and the pole of the loss lowpass
  t2, p2    the aftersound (the slow second stage of a piano note), same
  after     level of the aftersound against the prompt sound, dB
  th*       hammer contact time (ms) at pp, mf, ff: shorter = brighter
  lv*       level at pp, mf, ff, dB
The body (soundboard + microphones) is a bank of resonators fitted to what the partial
levels have in common across all the notes.

   python fit.py init        first fit, straight from refs/iowa-piano.npz (notes.py)
   python fit.py refit [n]   n rounds of: render every note, measure it with notes.py,
                             correct the tables by the difference (default 3)
   python fit.py report      how far the instrument is from the recordings now
"""
import os, subprocess, sys, tempfile
import numpy as np
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "timbre"))
import notes                                                             # noqa: E402
import body as BODY                                                      # noqa: E402
import bodyfit as BF                                                     # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
REFS = os.path.join(ROOT, "refs")
PARAMS = os.path.join(REFS, "piano-params.npz")
LIB = os.path.join(ROOT, "lib", "piano_fit.lib")
SO = os.path.join(ROOT, "build", "keys", "piano.so")
RENDER = os.path.join(ROOT, "build", "render")
SR = 48000
KEYS = np.arange(21, 109)
NAP = 16                                   # allpass stages available in the string loop
VEL = {0: 0.15, 1: 0.5, 2: 0.9}            # the velocity that plays pp, mf, ff (lib/piano.lib)
DYNS = (0, 1, 2)
TOPFIT = 100                               # keys above this are extrapolated, not fitted


def hz(m):
    return 440.0 * 2 ** ((np.asarray(m, float) - 69) / 12)


def smooth_keys(v, w=None, sigma=2.5, deg_out=1):
    """Gaussian-weighted smoothing across keys of per-key values with NaNs; outside the
    measured keys the trend of the nearest 10 measured keys is carried on (linear)."""
    v = np.asarray(v, float); w = np.ones_like(v) if w is None else np.asarray(w, float)
    ok = np.isfinite(v) & (w > 0)
    out = np.full(len(KEYS), np.nan)
    for i, k in enumerate(KEYS):
        g = np.exp(-0.5 * ((KEYS[ok] - k) / sigma) ** 2) * w[ok]
        if g.sum() > 0.3:
            out[i] = (g * v[ok]).sum() / g.sum()
    good = np.where(np.isfinite(out))[0]
    lo, hi = good[0], good[-1]
    for side, idx in (("lo", range(lo)), ("hi", range(hi + 1, len(KEYS)))):
        ref = good[:10] if side == "lo" else good[-10:]
        p = np.polyfit(KEYS[ref], out[ref], deg_out)
        for i in idx:
            out[i] = np.polyval(p, KEYS[i])
    return out


# ---------------------------------------------------------------- dispersion

def ap_phase_delay(a, w):
    return 1 - 2 * np.arctan2(a * np.sin(w), 1 + a * np.cos(w)) / w


def loop_partials(f1, M, a, nmax):
    """Partial frequencies of a loop: a delay set so the loop is in tune at f1, then M
    allpasses of coefficient a. Returns (freqs, D) or (None, D) if D is too short."""
    w1 = 2 * np.pi * f1 / SR
    D = SR / f1 - M * ap_phase_delay(a, w1)                 # all the rest of the loop
    if D < 4:
        return None, D
    w = np.linspace(1e-4, np.pi * 0.98, 20000)
    theta = w * D + M * w * ap_phase_delay(a, w)            # total phase round the loop
    n = np.arange(1, nmax + 1)
    wn = np.interp(2 * np.pi * n, theta, w, right=np.nan)
    return wn * SR / (2 * np.pi), D


def fit_dispersion(f1, B):
    """Allpass stages and coefficient that best give partials n f1 sqrt((1+Bn^2)/(1+B))."""
    nmax = int(min(40, max(4, 9000 // f1)))
    n = np.arange(1, nmax + 1)
    target = n * f1 * np.sqrt((1 + B * n * n) / (1 + B))
    wt = 1 / np.sqrt(n)
    best = (np.inf, 0, 0.0)
    for M in range(0, NAP + 1):
        for a in (np.linspace(-0.95, -0.01, 95) if M else [0.0]):
            fr, D = loop_partials(f1, M, a, nmax)
            if fr is None:
                continue
            ok = np.isfinite(fr)
            if ok.sum() < len(n):
                continue
            err = np.sqrt(np.sum(wt * (1200 * np.log2(fr / target)) ** 2) / wt.sum())
            if err < best[0]:
                best = (err, M, a)
    return best


# ---------------------------------------------------------------- losses

def fit_loss(f0, fp, rate):
    """T60 at the fundamental and pole p of the loop's one-pole loss filter, from decay rates
    (dB/s, negative) of partials at frequencies fp. Decay of a partial at f, one trip round
    the loop per period: rate(f) = 20 f0 log10 |H(f)|, H = g (1-p) / (1 - p e^-jw)."""
    ok = np.isfinite(rate) & (rate < -0.05) & np.isfinite(fp)
    if ok.sum() < 2:
        return np.nan, np.nan
    fp, rate = fp[ok], rate[ok]
    w = 2 * np.pi * fp / SR
    best = (np.inf, np.nan, np.nan)
    for p in np.linspace(0, 0.95, 96):
        shape = 20 * f0 * (np.log10(1 - p) - 0.5 * np.log10(1 - 2 * p * np.cos(w) + p * p))
        c = np.median(rate - shape)                      # = 20 f0 log10 g
        e = np.median(np.abs(rate - shape - c))
        if e < best[0]:
            w0 = 2 * np.pi * f0 / SR
            at_f0 = c + 20 * f0 * (np.log10(1 - p) - 0.5 * np.log10(1 - 2 * p * np.cos(w0) + p * p))
            best = (e, -60 / at_f0 if at_f0 < 0 else np.nan, p)
    return best[1], best[2]


# ---------------------------------------------------------------- hammer + body

def hammer_db(f, th_ms):
    """Spectrum (dB, 0 at DC) of a half-sine force pulse lasting th_ms."""
    T = th_ms / 1000
    x = 2 * f * T
    # |FT| of half-sine of length T, normalised: cos(pi f T) / (1 - (2 f T)^2)
    mag = np.abs(np.cos(np.pi * f * T) / np.where(np.abs(1 - x * x) < 1e-6, 1e-6, 1 - x * x))
    mag = np.where(np.abs(1 - x * x) < 1e-6, np.pi / 4, mag)
    return 20 * np.log10(np.maximum(mag, 1e-4))


def comb_db(n, beta):
    return 20 * np.log10(np.maximum(np.abs(2 * np.sin(np.pi * n * beta)), 0.05))


def beta_of(m):
    """Where along the string the hammer strikes, as a fraction of its length (typical
    grand: about 1/8 through the middle, nearer the end in the top octaves)."""
    return np.interp(m, [21, 70, 108], [0.122, 0.118, 0.06])


TH_GRID = np.geomspace(0.15, 12, 90)


def fit_hammer_body(d, rounds=8):
    """Alternate: per note, the contact time that best explains its partial levels given the
    body; then the body as what is left in common. Returns th[note], g[note], (grid, body)."""
    midi, L, Fp = d["midi"], d["L"], d["Fp"]
    n = np.arange(1, L.shape[1] + 1)
    grid = 40 * 2 ** (np.arange(0, int(np.log2(14000 / 40) * 48) + 1) / 48)
    lg = np.log2(grid)
    body = np.zeros(len(grid))
    th = np.full(len(midi), 2.0); g = np.zeros(len(midi))
    ok = np.isfinite(L) & np.isfinite(Fp) & (Fp < 12000)
    # partials more than 45 dB below the strongest are mostly noise at pp: leave them out
    ok &= L > (np.nanmax(L, 1, keepdims=True) - 45)
    for _ in range(rounds):
        bF = np.interp(np.log2(np.where(ok, Fp, 100)), lg, body)
        for i in range(len(midi)):
            o = ok[i]
            if o.sum() < 3:
                th[i] = np.nan; continue
            src = comb_db(n[o], beta_of(midi[i]))
            errs = []
            for t in TH_GRID:
                r = L[i, o] - src - bF[i, o] - hammer_db(Fp[i, o], t)
                errs.append(np.sum((r - r.mean()) ** 2 / n[o]))
            th[i] = TH_GRID[int(np.argmin(errs))]
            g[i] = np.mean(L[i, o] - src - bF[i, o] - hammer_db(Fp[i, o], th[i]))
        # body: smoothed average of what's left, by frequency
        res = np.full(L.shape, np.nan)
        for i in range(len(midi)):
            o = ok[i]
            if np.isfinite(th[i]):
                res[i, o] = L[i, o] - comb_db(n[o], beta_of(midi[i])) - hammer_db(Fp[i, o], th[i]) - g[i]
        okr = np.isfinite(res)
        b = np.clip(np.round((np.log2(Fp[okr]) - lg[0]) / (lg[1] - lg[0])).astype(int), 0, len(grid) - 1)
        acc = np.bincount(b, res[okr], len(grid)); cnt = np.bincount(b, None, len(grid)).astype(float)
        kern = np.exp(-0.5 * (np.arange(-8, 9) / 2.0) ** 2)
        num = np.convolve(acc, kern, "same"); den = np.convolve(cnt, kern, "same")
        good = den > 2
        body = np.interp(lg, lg[good], num[good] / den[good])
        # the hammer carries the overall tilt: take any straight-line trend out of the body
        sel = (grid > 100) & (grid < 6000)
        body -= np.polyval(np.polyfit(lg[sel], body[sel], 1), lg)
    return th, g, (grid, body)


# ---------------------------------------------------------------- init

def init():
    d = dict(np.load(os.path.join(REFS, "iowa-piano.npz")))
    midi, dyn = d["midi"], d["dyn"]
    P = {}

    # tuning: measured fundamental (partial 1 of the fit) against equal temperament
    f1 = d["f0"] * np.sqrt(1 + d["B"])
    cents = 1200 * np.log2(f1 / hz(midi))
    per = [np.nanmedian(np.where((midi == k) & (dyn > 0) & (d["nfound"] >= 4) & (np.abs(cents) < 50), cents, np.nan))
           if ((midi == k) & (dyn > 0)).any() else np.nan for k in KEYS]
    P["stretch"] = smooth_keys(per, sigma=4)

    # inharmonicity, in log
    lb = [np.nanmedian(np.where((midi == k) & (d["nfound"] >= 5) & (d["B"] > 0), np.log10(d["B"]), np.nan))
          for k in KEYS]
    P["B"] = 10 ** smooth_keys(lb, sigma=2.5)
    P["apM"] = np.zeros(len(KEYS)); P["apA"] = np.zeros(len(KEYS)); P["apErr"] = np.zeros(len(KEYS))
    for i, k in enumerate(KEYS):
        err, M, a = fit_dispersion(hz(k) * 2 ** (P["stretch"][i] / 1200), P["B"][i])
        P["apM"][i], P["apA"][i], P["apErr"][i] = M, a, err

    # losses, from the mf and ff notes (pp hits the hiss too soon)
    for tag, R in (("1", d["R1"]), ("2", d["R2"])):
        t, p = [], []
        for k in KEYS:
            tt, pp_ = [], []
            for i in np.where((midi == k) & (dyn > 0))[0]:
                a, b = fit_loss(f1[i], d["Fp"][i], R[i])
                if np.isfinite(a) and 0.2 < a < 120:
                    tt.append(np.log10(a)); pp_.append(b)
            t.append(np.mean(tt) if tt else np.nan); p.append(np.mean(pp_) if pp_ else np.nan)
        P["t" + tag] = 10 ** smooth_keys(t, sigma=3)
        P["p" + tag] = np.clip(smooth_keys(p, sigma=4), 0, 0.9)
    P["t2"] = np.maximum(P["t2"], 1.5 * P["t1"])

    # aftersound level: the late line at the peak time, against the peak (partials 1..3)
    aft = [np.nanmedian(np.where(((midi == k) & (dyn > 0))[:, None], d["I2"][:, :3] - d["L"][:, :3], np.nan))
           for k in KEYS]
    P["after"] = np.clip(smooth_keys(aft, sigma=4), -30, -3)

    # hammer contact time: start from typical grand-piano figures (about 4 ms in the low
    # bass to 0.6 ms at the top at mf; softer blows are longer), the render loop refits it
    base = 10 ** np.interp(KEYS, [21, 108], np.log10([4.0, 0.6]))
    for tag, fac in (("PP", 1.4), ("MF", 1.0), ("FF", 0.65)):
        P["th" + tag] = base * fac
    # target levels: the strongest partial of each note, by dynamic, relative to mf middle C
    Lmax = np.nanmax(d["L"], 1)
    for dy, tag in zip(DYNS, ("PP", "MF", "FF")):
        P["target" + tag] = smooth_keys([np.nanmedian(np.where((dyn == dy) & (midi == k), Lmax, np.nan)) for k in KEYS], sigma=2)
    ref = P["targetMF"][60 - 21]
    for tag in ("PP", "MF", "FF"):
        P["target" + tag] -= ref
        P["lv" + tag] = P["target" + tag].copy()
    grid = 40 * 2 ** (np.arange(0, int(np.log2(14000 / 40) * 48) + 1) / 48)
    body = np.zeros(len(grid))
    P["bodyGrid"], P["bodyDb"] = grid, body
    P["gainDb"] = np.zeros(1)
    np.savez(PARAMS, **P)
    write_lib(P)
    show(P)


def show(P):
    print(" key    Hz  stretch      B  M     a  err  T60:1   p1  T60:2   p2  after  th pp/mf/ff ms    lv pp/mf/ff")
    for i in range(0, len(KEYS), 4):
        k = KEYS[i]
        print(f"{k:4d} {hz(k):6.0f} {P['stretch'][i]:+6.1f} {P['B'][i]:.1e} {int(P['apM'][i]):2d} {P['apA'][i]:+.2f}"
              f" {P['apErr'][i]:4.1f} {P['t1'][i]:6.2f} {P['p1'][i]:.2f} {P['t2'][i]:6.1f} {P['p2'][i]:.2f}"
              f" {P['after'][i]:+6.1f}  {P['thPP'][i]:4.2f}/{P['thMF'][i]:4.2f}/{P['thFF'][i]:4.2f}"
              f"  {P['lvPP'][i]:+6.1f}/{P['lvMF'][i]:+5.1f}/{P['lvFF'][i]:+5.1f}")


# ---------------------------------------------------------------- the library

def write_lib(P):
    def wf(name, v, fmt="{:.6g}"):
        return f"{name} = waveform{{{', '.join(fmt.format(x) for x in v)}}};"
    grid, db = P["bodyGrid"], P["bodyDb"]
    lines = [
        "// Piano, fitted to the University of Iowa single notes (Steinway B) by tools/fitting/piano/fit.py.",
        "// One value per key, A0 (MIDI 21) to C8 (108). Generated: do not edit.",
        'import("stdfaust.lib");',
        wf("stretch", P["stretch"]), wf("apM", P["apM"], "{:.0f}"), wf("apA", P["apA"]),
        wf("t1", P["t1"]), wf("p1", P["p1"]), wf("t2", P["t2"]), wf("p2", P["p2"]),
        wf("after", P["after"]),
        wf("thPP", P["thPP"]), wf("thMF", P["thMF"]), wf("thFF", P["thFF"]),
        wf("lvPP", P["lvPP"]), wf("lvMF", P["lvMF"]), wf("lvFF", P["lvFF"]),
        f"gainDb = {float(P['gainDb'][0]):.3f};",
        body_lib(grid, db),
    ]
    open(LIB, "w").write("\n".join(lines) + "\n")


def body_lib(grid, db, lo=40):
    """The body as parallel resonators (tools/fitting/timbre/bodyfit.py), 0 dB on average over
    300 Hz - 5 kHz, as tools/fitting/timbre/makebody.py does for the strings."""
    pf = np.concatenate([np.geomspace(lo * 0.9, 1500, 36, endpoint=False),
                         np.geomspace(1500, 6000, 18, endpoint=False), np.geomspace(6000, 20000, 10)])
    secs, firt, fr, err, full = BF.design(grid, db, pf, f_lo=lo)
    m = (fr > 300) & (fr < 5000)
    k = 1 / np.sqrt(np.mean(np.abs(BF.response(secs, firt, fr[m])) ** 2))
    secs = [(b0 * k, b1 * k, a1, a2) for b0, b1, a1, a2 in secs]
    for a, b in ((lo, 600), (600, 1500), (1500, 4000), (4000, 12000)):
        mm = (fr > a) & (fr < b)
        print(f"  body fit error {a:5.0f}-{b:5.0f} Hz: {np.sqrt(np.mean(err[mm] ** 2)):.2f} dB")
    return BF.faust("body", secs, firt * k)


# ---------------------------------------------------------------- render + measure

def render_one(args):
    k, dy = args
    with tempfile.NamedTemporaryFile(suffix=".f32") as f:
        subprocess.run([RENDER, SO, f.name, f"{hz(k):.4f}", "0", "0.5", f"{VEL[dy]}", "13", "13"],
                       check=True, capture_output=True)
        x = np.fromfile(f.name, dtype=np.float32).astype(np.float64)
    r = notes.measure(x, hz(k))
    r.update(midi=k, dyn=dy)
    return r


def measure_instrument(pairs):
    with Pool(4) as p:
        res = p.map(render_one, pairs)
    out = {k: np.array([r[k] for r in res]) for k in ("midi", "dyn", "f0", "B", "nfound", "rms")}
    for k in ("L", "R1", "R2", "I2", "Fp"):
        out[k] = np.stack([r[k] for r in res])
    return out


def rebuild():
    subprocess.run(["make", "-s", "build/keys/piano.so", "build/render"], cwd=ROOT, check=True)


def table(ref, key):
    """ref[(midi, dyn)] -> index into the measurement arrays."""
    return {(int(m), int(d)): i for i, (m, d) in enumerate(zip(ref["midi"], ref["dyn"]))}


def compare(ref, ins):
    """Per (key, dyn) present in both: level, tilt, partial residuals, decay and tuning differences."""
    ri, ii = table(ref, None), table(ins, None)
    rows = []
    for kd in sorted(set(ri) & set(ii)):
        r, i = ri[kd], ii[kd]
        Lr, Li = ref["L"][r], ins["L"][i]
        top = np.nanmax(Lr)
        ok = np.isfinite(Lr) & np.isfinite(Li) & (Lr > top - 40) & (ref["Fp"][r] < 12000)
        if ok.sum() < 2:
            continue
        f = ref["Fp"][r][ok]
        dl = (Lr[ok] - np.nanmax(Lr)) - (Li[ok] - np.nanmax(Li))           # shape only
        slope = np.polyfit(np.log2(f), dl, 1)[0] if ok.sum() >= 3 else 0.0
        rows.append(dict(key=kd[0], dyn=kd[1], lvl=ref["rms"][r] - ins["rms"][i], slope=slope, f=f,
                         shape=dl - dl.mean() - slope * (np.log2(f) - np.log2(f).mean()),
                         dl=dl, n=np.where(ok)[0] + 1, r=r, i=i))
    return rows


def refit(rounds=3):
    ref = dict(np.load(os.path.join(REFS, "iowa-piano.npz")))
    for rnd in range(rounds):
        P = dict(np.load(PARAMS))
        rebuild()
        ins = measure_instrument([(k, d) for k in KEYS for d in DYNS])
        np.savez(os.path.join(REFS, "piano-inst.npz"), **ins)
        rows = compare(ref, ins)
        report(ref, ins, rows)
        rows = [x for x in rows if x["key"] <= TOPFIT]        # above, the recordings are mostly hiss
        if rnd == rounds:
            break
        by = lambda dy, fn, sigma=2: smooth_keys([np.nanmedian([fn(x) for x in rows if x["key"] == k and x["dyn"] == dy] or [np.nan])
                                         for k in KEYS], sigma=sigma)
        # level, relative to mf middle C (gainDb holds the absolute level)
        mid = np.median([x["lvl"] for x in rows if 54 <= x["key"] <= 66 and x["dyn"] == 1])
        for dy, tag in zip(DYNS, ("PP", "MF", "FF")):
            P["lv" + tag] = P["lv" + tag] + 0.5 * (by(dy, lambda x: x["lvl"], 6) - mid)
            # contact time: the one whose half-sine spectrum best turns the instrument's
            # partial levels into the recording's (level free, low partials count most)
            def best_th(x, tag=tag):
                th0 = P["th" + tag][x["key"] - 21]
                f, dl, n = x["f"], x["dl"], x["n"]
                wt = 1 / np.sqrt(n)
                errs = []
                for t in TH_GRID:
                    r = dl - (hammer_db(f, t) - hammer_db(f, th0))
                    r = r - np.sum(wt * r) / wt.sum()
                    errs.append(np.sum(wt * r * r))
                return np.log10(TH_GRID[int(np.argmin(errs))] / th0)
            P["th" + tag] = np.clip(P["th" + tag] * 10 ** (0.5 * np.nan_to_num(by(dy, best_th))), 0.12, 10)
        P["thMF"] = np.minimum(P["thMF"], P["thPP"] * 0.97); P["thFF"] = np.minimum(P["thFF"], P["thMF"] * 0.97)
        # body: what is left in common, by frequency
        grid, bd = P["bodyGrid"], P["bodyDb"]
        lg = np.log2(grid)
        F = np.concatenate([x["f"] for x in rows]); S = np.concatenate([x["shape"] for x in rows])
        b = np.clip(np.round((np.log2(F) - lg[0]) / (lg[1] - lg[0])).astype(int), 0, len(grid) - 1)
        acc = np.bincount(b, S, len(grid)); cnt = np.bincount(b, None, len(grid)).astype(float)
        kern = np.exp(-0.5 * (np.arange(-8, 9) / 2.0) ** 2)
        num = np.convolve(acc, kern, "same"); den = np.convolve(cnt, kern, "same")
        good = den > 3
        corr = np.interp(lg, lg[good], num[good] / den[good])
        sel = (grid > 100) & (grid < 6000)
        corr -= np.polyval(np.polyfit(lg[sel], corr[sel], 1), lg)
        P["bodyDb"] = np.clip(bd + 0.7 * corr, -15, 15)
        # decay: move each loop's rate curve by the measured difference and refit it
        for tag, R in (("1", "R1"), ("2", "R2")):
            tk, pk = [], []
            for k in KEYS:
                j = k - 21
                ests = []
                for x in rows:
                    if x["key"] != k or x["dyn"] == 0:
                        continue
                    f0 = hz(k)
                    fp = ins["Fp"][x["i"]]
                    w = 2 * np.pi * fp / SR
                    p = P["p" + tag][j]
                    own = -60 / P["t" + tag][j] + 20 * f0 * (np.log10(1 - p) - 0.5 * np.log10(1 - 2 * p * np.cos(w) + p * p)) \
                          - 20 * f0 * (np.log10(1 - p) - 0.5 * np.log10(1 - 2 * p * np.cos(2 * np.pi * f0 / SR) + p * p))
                    want = own + (ref[R][x["r"]] - ins[R][x["i"]])
                    want = want[:12]; fpp = fp[:12]
                    t_, p_ = fit_loss(f0, fpp, want)
                    if np.isfinite(t_) and 0.2 < t_ < 150:
                        ests.append((np.log10(t_), p_))
                tk.append(np.mean([e[0] for e in ests]) if ests else np.nan)
                pk.append(np.mean([e[1] for e in ests]) if ests else np.nan)
            newt = 10 ** smooth_keys(tk, sigma=3); newp = np.clip(smooth_keys(pk, sigma=4), 0, 0.9)
            P["t" + tag] = 10 ** (0.3 * np.log10(P["t" + tag]) + 0.7 * np.log10(newt))
            P["p" + tag] = 0.3 * P["p" + tag] + 0.7 * newp
        P["t2"] = np.maximum(P["t2"], 1.5 * P["t1"])
        # aftersound level
        da = by(1, lambda x: np.nanmedian((ref["I2"][x["r"]][:3] - ref["L"][x["r"]][:3]) - (ins["I2"][x["i"]][:3] - ins["L"][x["i"]][:3])))
        P["after"] = np.clip(P["after"] + 0.7 * np.nan_to_num(da), -35, -3)
        # tuning and stiffness
        dc = by(1, lambda x: 1200 * np.log2(ref["f0"][x["r"]] * np.sqrt(1 + ref["B"][x["r"]]) / (ins["f0"][x["i"]] * np.sqrt(1 + ins["B"][x["i"]]))))
        P["stretch"] = P["stretch"] + 0.8 * np.clip(np.nan_to_num(dc), -10, 10)
        dB = by(1, lambda x: np.log10(ref["B"][x["r"]] / ins["B"][x["i"]]) if ref["B"][x["r"]] > 0 and ins["B"][x["i"]] > 0
                and ref["nfound"][x["r"]] >= 5 else np.nan)
        P["B"] = P["B"] * 10 ** (0.7 * np.clip(np.nan_to_num(dB), -0.5, 0.5))
        for i, k in enumerate(KEYS):
            err, M, a = fit_dispersion(hz(k) * 2 ** (P["stretch"][i] / 1200), P["B"][i])
            P["apM"][i], P["apA"][i], P["apErr"][i] = M, a, err
        # absolute level: mf around middle C at -24 dB rms over its first 0.2 s
        mfmid = np.median([ins["rms"][i] for i in range(len(ins["midi"])) if 54 <= ins["midi"][i] <= 66 and ins["dyn"][i] == 1])
        P["gainDb"] = np.array([float(P["gainDb"][0]) + 0.8 * (-24 - mfmid)])
        np.savez(PARAMS, **P)
        write_lib(P)
        print(f"round {rnd + 1} done")


def report(ref, ins, rows):
    print("register  dyn   level  tilt dB/oct  shape rms   T60 early h1-3 ref/inst   late ref/inst   after ref/inst   cents")
    for lo in range(21, 109, 12):
        for dy in DYNS:
            rs = [x for x in rows if lo <= x["key"] < lo + 12 and x["dyn"] == dy]
            if not rs:
                continue
            t = lambda R, src, j: np.nanmedian([np.nanmedian(-60 / src[R][x[j]][:3]) for x in rs])
            aft = lambda src, j: np.nanmedian([np.nanmedian(src["I2"][x[j]][:3] - src["L"][x[j]][:3]) for x in rs])
            cents = np.nanmedian([1200 * np.log2(ref["f0"][x["r"]] * np.sqrt(1 + ref["B"][x["r"]]) / (ins["f0"][x["i"]] * np.sqrt(1 + ins["B"][x["i"]]))) for x in rs])
            print(f"{lo:3d}-{lo + 11:3d}  {('pp', 'mf', 'ff')[dy]}  {np.median([x['lvl'] for x in rs]):+6.1f}  {np.median([x['slope'] for x in rs]):+6.2f}"
                  f"      {np.sqrt(np.mean(np.concatenate([x['dl'] - x['dl'].mean() for x in rs]) ** 2)):5.1f}"
                  f"        {t('R1', ref, 'r'):5.1f}/{t('R1', ins, 'i'):5.1f}         {t('R2', ref, 'r'):5.1f}/{t('R2', ins, 'i'):5.1f}"
                  f"      {aft(ref, 'r'):+5.1f}/{aft(ins, 'i'):+5.1f}   {cents:+5.1f}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "init"
    if cmd == "init":
        init()
    elif cmd == "refit":
        refit(int(sys.argv[2]) if len(sys.argv) > 2 else 3)
    elif cmd == "report":
        ref = dict(np.load(os.path.join(REFS, "iowa-piano.npz")))
        rebuild()
        ins = measure_instrument([(k, d) for k in KEYS for d in DYNS])
        report(ref, ins, compare(ref, ins))
