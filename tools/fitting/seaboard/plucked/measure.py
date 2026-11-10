"""Measure the plucked notes of a Seaboard demo clip (or a render of ours), note by note.

    python measure.py CLIP.wav [--t0 S] [--fmin HZ --fmax HZ] [--json OUT] [--mono]

For each note (onsets from a spectral flux, pitch from YIN):
  f0, how much it moves (slides / vibrato), the level of harmonics 1..K 30-60 ms after the
  onset (the attack spectrum, relative to the strongest), each harmonic's decay in dB/s over the
  note, the inharmonicity B (partial k sits at k f0 sqrt(1 + B k^2)), the noise in the first
  20 ms (finger / pick) and the spectral centroid.
The same code measures the reference and our renders, so the numbers compare directly.
"""
import argparse
import json
import os
import sys

import numpy as np
import scipy.signal as ss

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "timbre"))
import analysis as an  # noqa: E402

SR = 48000


def onsets(x, min_gap=0.09, thresh=1.5):
    """Onset times (s) from a log spectral flux (positive part), peaks above a running median."""
    n, hop = 1024, 240
    f, t, S = ss.stft(x, SR, nperseg=n, noverlap=n - hop, boundary=None)
    L = np.log1p(1000 * np.abs(S))
    sel = f > 150                       # the thump of a bass note moves the low bins a lot anyway
    fl = np.maximum(0, np.diff(L[sel], axis=1)).sum(0)
    fl = np.concatenate([[0], fl])
    med = ss.medfilt(fl, 41) + 1e-9
    r = fl / med
    pk, _ = ss.find_peaks(r, height=thresh, distance=int(min_gap * SR / hop))
    keep = [p for p in pk if fl[p] > 0.15 * np.percentile(fl, 99)]
    return t[keep] - n / 2 / SR * 0.5


def partial_peaks(seg, f0, K, nfft=1 << 16):
    """Exact frequency and level (dB) of partials 1..K in seg (hann window), searching +-3% around
    k f0 (inharmonic partials drift sharp)."""
    w = np.hanning(len(seg))
    P = np.abs(np.fft.rfft(seg * w, nfft)) * 2 / w.sum()
    hz = SR / nfft
    fr, lv = np.full(K, np.nan), np.full(K, -120.0)
    for k in range(1, K + 1):
        c = k * f0
        if c > SR / 2 - 500:
            break
        lo, hi = int(c * 0.97 / hz), int(c * 1.03 / hz) + 1
        lo = max(lo, int((c - f0 * 0.45) / hz)); hi = min(hi, int((c + f0 * 0.45) / hz) + 1)
        i = lo + int(np.argmax(P[lo:hi]))
        if 1 <= i < len(P) - 1:
            a, b, g = np.log(P[i - 1] + 1e-12), np.log(P[i] + 1e-12), np.log(P[i + 1] + 1e-12)
            d = 0.5 * (a - g) / (a - 2 * b + g) if (a - 2 * b + g) != 0 else 0
            fr[k - 1] = (i + np.clip(d, -1, 1)) * hz
        lv[k - 1] = 20 * np.log10(P[i] + 1e-12)
    return fr, lv


def measure(x, fmin, fmax, K=16, t0=0.0, min_dur=0.12):
    t, f0, per, rms = an.track_f0(x, fmin, fmax)
    on = onsets(x)
    db = 20 * np.log10(rms + 1e-12)
    top = np.percentile(db, 95)
    notes = []
    bounds = list(on) + [len(x) / SR]
    for a, b in zip(bounds[:-1], bounds[1:]):
        # where it is still a note: periodic and loud
        sel = (t > a + 0.03) & (t < b - 0.01) & (per > 0.8) & (f0 > fmin) & (f0 < fmax) & (db > top - 35)
        if sel.sum() < 6 or b - a < min_dur:
            continue
        ft = f0[sel]
        fm = float(np.median(ft[: max(6, len(ft) // 2)]))
        cents = 1200 * np.log2(ft / fm)
        # the note ends when its level falls 30 dB below its peak, or at the next onset
        ia, ib = int(a * SR), int(b * SR)
        env = rms[(t >= a) & (t < b)]
        pkv = env.max()
        end = b
        below = np.nonzero(env[np.argmax(env):] < pkv * 10 ** (-30 / 20))[0]
        if len(below):
            end = a + (np.argmax(env) + below[0]) * an.HOP / SR
        # attack spectrum: 30-90 ms after the onset
        L = int(max(4 / fm, 0.06) * SR)
        s0 = ia + int(0.03 * SR)
        fr, lv0 = partial_peaks(x[s0:s0 + L], fm, K)
        k = np.arange(1, K + 1)
        ok = np.isfinite(fr) & (lv0 > lv0.max() - 50)
        B = np.nan
        if ok.sum() >= 5:
            # (f_k / (k f1))^2 = (1 + B k^2) / (1 + B): least squares on the measured ones
            r2 = (fr[ok] / (k[ok] * fr[0])) ** 2
            kk = k[ok] ** 2
            A = np.stack([kk - r2, np.ones_like(kk)], 1)   # B (k^2 - r2) = r2 - 1
            B = float(np.linalg.lstsq(A[:, :1], r2 - 1, rcond=None)[0][0])
        # decay of each partial, in frames of 4 periods (at least 40 ms), hop 20 ms
        dec = np.full(K, np.nan)
        Lw = int(max(4 / fm, 0.04) * SR)
        starts = np.arange(ia + int(0.04 * SR), int(min(end, b) * SR) - Lw, int(0.02 * SR))
        if len(starts) >= 4:
            M = np.array([partial_peaks(x[s:s + Lw], fm, K, nfft=1 << 15)[1] for s in starts])
            tt = (starts - ia) / SR
            for j in range(K):
                y = M[:, j]
                g = y > M[0].max() - 60
                if g.sum() >= 4:
                    dec[j] = float(np.polyfit(tt[g], y[g], 1)[0])
        # noise in the first 25 ms: what the harmonic comb does not explain
        seg = x[ia:ia + int(0.025 * SR)]
        Pf = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), 1 << 14)) ** 2
        hz = SR / (1 << 14)
        ff = np.arange(len(Pf)) * hz
        cen = float((ff * Pf).sum() / Pf.sum())
        # centroid of the attack frame (30-90 ms)
        sa = x[s0:s0 + L]
        Pa = np.abs(np.fft.rfft(sa * np.hanning(len(sa)), 1 << 15)) ** 2
        fa = np.arange(len(Pa)) * SR / (1 << 15)
        cen_a = float((fa * Pa).sum() / Pa.sum())
        hf = float(10 * np.log10(Pf[ff > 2000].sum() / Pf.sum()))
        notes.append(dict(
            onset=round(a + t0, 3), dur=round(min(end, b) - a, 3), gap=round(b - a, 3),
            f0=round(fm, 2), midi=round(69 + 12 * np.log2(fm / 440), 2),
            cents_range=[round(float(np.percentile(cents, 5)), 1), round(float(np.percentile(cents, 95)), 1)],
            level=round(float(20 * np.log10(pkv + 1e-12)), 1),
            attack=[round(float(v - lv0.max()), 1) for v in lv0],
            decay=[None if not np.isfinite(v) else round(v, 1) for v in dec],
            B=None if not np.isfinite(B) else float(B),
            centroid_onset=round(cen, 0), centroid_attack=round(cen_a, 0), hf_onset_db=round(hf, 1)))
    return notes


def summary(notes):
    import collections
    print(f"{len(notes)} notes")
    for n in notes:
        a = ' '.join('%4.0f' % v for v in n['attack'][:10])
        d = ' '.join('%4s' % ('' if v is None else '%.0f' % v) for v in n['decay'][:8])
        print(f"{n['onset']:6.2f} {n['dur']:.2f} {n['midi']:6.2f} c{n['cents_range']} L{n['level']:.0f} "
              f"| {a} | {d} | B={n['B'] if n['B'] is None else '%.1e' % n['B']} cen {n['centroid_attack']:.0f} hf {n['hf_onset_db']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("clip")
    ap.add_argument("--t0", type=float, default=0)
    ap.add_argument("--fmin", type=float, default=30)
    ap.add_argument("--fmax", type=float, default=400)
    ap.add_argument("--K", type=int, default=16)
    ap.add_argument("--json")
    a = ap.parse_args()
    x = an.load(a.clip)
    ns = measure(x, a.fmin, a.fmax, a.K, a.t0)
    summary(ns)
    if a.json:
        json.dump(ns, open(a.json, "w"), indent=1)
