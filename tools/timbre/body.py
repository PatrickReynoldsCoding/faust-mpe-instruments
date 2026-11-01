"""Separate the harmonic levels of a recording into a per-frame level and one shared
frequency response B(f) (body + bridge + room + microphone), assuming the string itself
gives harmonics that fall at `slope` dB per octave of harmonic number:
    level[i, k] = g[i] + slope*log2(k) + B(k*f0[i])
B is found on a 1/48-octave grid by alternating least squares, with a little smoothing."""
import numpy as np

def fit_body(f0, H, slope=-6.0, grid=None, iters=12, smooth_bins=1.0, fmax=14000):
    if grid is None:
        grid = 60 * 2 ** (np.arange(0, int(np.log2(fmax / 60) * 48) + 1) / 48)
    lg = np.log2(grid); step = lg[1] - lg[0]
    n, K = H.shape
    k = np.arange(1, K + 1)
    F = f0[:, None] * k[None, :]
    ok = np.isfinite(H) & (F < fmax) & (F >= grid[0])
    b = np.clip(np.round((np.log2(np.where(ok, F, grid[0])) - lg[0]) / step).astype(int), 0, len(grid) - 1)
    src = slope * np.log2(k)[None, :]
    A = np.where(ok, H - src, 0.0)
    B = np.zeros(len(grid)); g = np.zeros(n)
    kern = np.exp(-0.5 * (np.arange(-4, 5) / max(smooth_bins, 1e-3)) ** 2)
    for _ in range(iters):
        r = np.where(ok, A - B[b], 0.0)
        g = r.sum(1) / np.maximum(ok.sum(1), 1)
        r = np.where(ok, A - g[:, None], 0.0)
        acc = np.bincount(b[ok], r[ok], len(grid)); cnt = np.bincount(b[ok], None, len(grid)).astype(float)
        num = np.convolve(acc, kern, "same"); den = np.convolve(cnt, kern, "same")
        B = np.where(den > 0.5, num / np.maximum(den, 1e-9), np.nan)
        # fill gaps by interpolation, normalise to 0 dB mean over 300 Hz..5 kHz
        good = np.isfinite(B)
        B = np.interp(lg, lg[good], B[good])
        B -= B[(grid > 300) & (grid < 5000)].mean()
    resid = np.where(ok, A - g[:, None] - B[b], np.nan)
    return grid, B, g, resid, cnt
