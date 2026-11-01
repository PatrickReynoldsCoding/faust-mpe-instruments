"""Measuring tools for comparing a synthetic bowed string with a recording.

The same code measures both sides, so the numbers can be compared directly:
  track_f0     pitch, how periodic the sound is, and level, every 5 ms (YIN)
  harmonics    level of each harmonic (and the noise between them) per frame
  envelope     the average harmonic envelope (level against frequency), the
               main thing that makes a violin sound like a violin
"""
import numpy as np
import soundfile as sf

SR = 48000
HOP = 240                      # 5 ms


def load(path, sr=SR):
    if path.endswith(".f32"):
        return np.fromfile(path, dtype=np.float32).astype(np.float64)
    x, r = sf.read(path, dtype="float64", always_2d=True)
    if r != sr:
        raise ValueError(f"{path}: {r} Hz, want {sr}")
    return x.mean(axis=1)


def save(path, x, sr=SR):
    sf.write(path, np.asarray(x, dtype=np.float32), sr, subtype="FLOAT")


def frames(x, length, hop):
    n = 1 + max(0, (len(x) - length) // hop)
    idx = np.arange(length)[None, :] + hop * np.arange(n)[:, None]
    return x[idx]


def track_f0(x, fmin, fmax, hop=HOP, thresh=0.12, chunk=1500):
    """YIN. Returns times (centre of frame), f0 (Hz), periodicity (0..1, 1 = perfectly
    periodic) and frame rms. f0 is 0 where nothing periodic was found."""
    tmax = int(np.ceil(SR / fmin)) + 2
    tmin = max(2, int(SR / fmax))
    w = max(int(2.5 * SR / fmin), 512)                 # integration window
    L = w + tmax
    nfft = 1 << int(np.ceil(np.log2(L + w)))
    xp = np.concatenate([np.zeros(L // 2), x, np.zeros(L)])
    F = frames(xp, L, hop)
    times = (np.arange(len(F)) * hop) / SR
    f0 = np.zeros(len(F)); per = np.zeros(len(F)); rms = np.zeros(len(F))
    taus = np.arange(tmax)
    for s in range(0, len(F), chunk):
        fr = F[s:s + chunk]
        a = fr[:, :w]
        # d(tau) = sum (x_j - x_{j+tau})^2 = E0 + E_tau - 2 r(tau)
        A = np.fft.rfft(a, nfft); B = np.fft.rfft(fr, nfft)
        r = np.fft.irfft(np.conj(A) * B, nfft)[:, :tmax]
        e0 = np.sum(a * a, axis=1)
        c = np.cumsum(np.concatenate([np.zeros((len(fr), 1)), fr * fr], axis=1), axis=1)
        et = c[:, taus + w] - c[:, taus]
        d = e0[:, None] + et - 2 * r
        d[:, 0] = 0
        cm = np.cumsum(d[:, 1:], axis=1)
        cmnd = np.ones_like(d)
        cmnd[:, 1:] = d[:, 1:] * taus[None, 1:] / np.maximum(cm, 1e-20)
        rms[s:s + chunk] = np.sqrt(e0 / w)
        for i in range(len(fr)):
            row = cmnd[i]
            below = np.nonzero(row[tmin:] < thresh)[0]
            if len(below):
                t = tmin + below[0]
                while t + 1 < tmax and row[t + 1] < row[t]:
                    t += 1
            else:
                t = tmin + int(np.argmin(row[tmin:]))
            if 1 <= t < tmax - 1:
                y0, y1, y2 = row[t - 1], row[t], row[t + 1]
                den = y0 - 2 * y1 + y2
                dt = 0.5 * (y0 - y2) / den if abs(den) > 1e-12 else 0.0
                tt = t + float(np.clip(dt, -1, 1))
            else:
                tt = float(t)
            f0[s + i] = SR / tt
            per[s + i] = max(0.0, 1 - row[t])
    return times, f0, per, rms


def voiced_mask(f0, per, rms, fmin, fmax, min_per=0.85, min_db=-45):
    db = 20 * np.log10(rms + 1e-12)
    ref = np.percentile(db[db > -100], 95) if np.any(db > -100) else 0
    return (per >= min_per) & (f0 >= fmin) & (f0 <= fmax) & (db > ref + min_db)


def harmonics(x, times, f0, mask, kmax=60, fmax=16000, periods=8):
    """Level (dB, power summed in a band of +-f0/2 around k*f0) of harmonics 1..kmax for
    the frames in mask, plus the level of what lies between harmonics (dB, the band
    (k+0.5)*f0 +- f0/6 scaled to a full harmonic band: noise, reverb of earlier notes).
    Returns (idx, H, N) with H, N of shape (n, kmax), NaN above fmax."""
    idx = np.nonzero(mask)[0]
    H = np.full((len(idx), kmax), np.nan)
    N = np.full((len(idx), kmax), np.nan)
    nfft = 16384
    hz = SR / nfft
    k = np.arange(1, kmax + 1)
    wins = {}
    for j, i in enumerate(idx):
        f = f0[i]
        L = int(np.clip(periods * SR / f, 1024, 6144)) // 64 * 64
        c = int(times[i] * SR)
        a, b = c - L // 2, c - L // 2 + L
        if a < 0 or b > len(x):
            continue
        if L not in wins:
            w = np.hanning(L); wins[L] = (w, 4 / np.sum(w) ** 2)
        w, g = wins[L]
        P = np.abs(np.fft.rfft(x[a:b] * w, nfft)) ** 2 * g
        cs = np.concatenate([[0], np.cumsum(P)])
        ok = k * f + f / 2 <= fmax
        lo = ((k - 0.5) * f / hz).astype(int); hi = ((k + 0.5) * f / hz).astype(int)
        lo = np.clip(lo, 0, len(P)); hi = np.clip(hi, 0, len(P))
        H[j, ok] = 10 * np.log10(cs[hi[ok]] - cs[lo[ok]] + 1e-20)
        nlo = ((k + 0.5 - 1 / 6) * f / hz).astype(int); nhi = ((k + 0.5 + 1 / 6) * f / hz).astype(int)
        nlo = np.clip(nlo, 0, len(P)); nhi = np.clip(nhi, 0, len(P))
        nb = np.maximum(nhi - nlo, 1)
        N[j, ok] = 10 * np.log10((cs[nhi[ok]] - cs[nlo[ok]]) / nb[ok] * (hi[ok] - lo[ok]) + 1e-20)
    return idx, H, N


def octave_grid(lo=80, hi=16000, per_oct=24):
    n = int(np.round(np.log2(hi / lo) * per_oct)) + 1
    return lo * 2 ** (np.arange(n) / per_oct)


def envelope(f0s, H, grid, weights=None, norm="frame"):
    """Average harmonic envelope on a log-frequency grid. Each frame is first normalised
    to its own total power (so loud and soft notes count the same), then every harmonic
    lands in the nearest grid bin. Returns (mean dB per bin, count per bin)."""
    lg = np.log2(grid)
    step = lg[1] - lg[0]
    acc = np.zeros(len(grid)); cnt = np.zeros(len(grid))
    for j in range(len(f0s)):
        h = H[j]
        ok = np.isfinite(h)
        if not ok.any():
            continue
        tot = 10 * np.log10(np.sum(10 ** (h[ok] / 10)))
        k = np.arange(1, len(h) + 1)[ok]
        b = np.round((np.log2(k * f0s[j]) - lg[0]) / step).astype(int)
        good = (b >= 0) & (b < len(grid))
        w = 1.0 if weights is None else weights[j]
        np.add.at(acc, b[good], w * (h[ok][good] - tot))
        np.add.at(cnt, b[good], w)
    with np.errstate(invalid="ignore"):
        return acc / cnt, cnt


def smooth_log(y, cnt, width_bins=2):
    """Fill gaps and smooth a binned envelope (gaussian over bins, weighted by count)."""
    n = len(y)
    out = np.full(n, np.nan)
    ok = np.isfinite(y) & (cnt > 0)
    yy = np.where(ok, y, 0)
    ww = np.where(ok, cnt, 0)
    k = np.arange(-4 * width_bins, 4 * width_bins + 1)
    g = np.exp(-0.5 * (k / max(width_bins, 1e-3)) ** 2)
    num = np.convolve(yy * ww, g, mode="same")
    den = np.convolve(ww, g, mode="same")
    with np.errstate(invalid="ignore", divide="ignore"):
        out = num / den
    out[den < 1e-6] = np.nan
    return out


def analyse_file(path, fmin, fmax, max_frames=None, every=1):
    x = load(path)
    t, f0, per, rms = track_f0(x, fmin, fmax)
    m = voiced_mask(f0, per, rms, fmin, fmax)
    if every > 1:
        sel = np.zeros_like(m); sel[::every] = True; m &= sel
    if max_frames and m.sum() > max_frames:
        keep = np.nonzero(m)[0]
        drop = np.random.default_rng(0).choice(keep, m.sum() - max_frames, replace=False)
        m[drop] = False
    idx, H, N = harmonics(x, t, f0, m)
    return dict(x=x, t=t, f0=f0, per=per, rms=rms, mask=m, idx=idx, H=H, N=N)
