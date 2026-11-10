"""Harmonic profile of one line in a stretch of a recording where it holds a steady note.

    python profile.py file.wav t0 t1 note [note ...]

For each note (name like G#4, or Hz) finds its exact frequency (largest peak within 40 cents) and
prints harmonics 1..16 in dB re the strongest. '*' marks a harmonic within 15 Hz of a harmonic of
another listed note (not to be trusted)."""
import sys
import numpy as np
import soundfile as sf

NAMES = "C C# D D# E F F# G G# A A# B".split()


def hz(s):
    try:
        return float(s)
    except ValueError:
        n = s[:-1]; o = int(s[-1])
        m = NAMES.index(n) + 12 * (o + 1)
        return 440 * 2 ** ((m - 69) / 12)


def spectrum(path, t0, t1):
    x, sr = sf.read(path, dtype="float64", always_2d=True)
    seg = x[int(t0 * sr):int(t1 * sr)].mean(axis=1)
    n = 1 << 18
    S = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), n))
    return np.fft.rfftfreq(n, 1 / sr), S, sr


def peak(fr, S, f, bw):
    s = (fr > f - bw) & (fr < f + bw)
    i = np.argmax(S[s])
    return fr[s][i], S[s][i]


def profiles(path, t0, t1, notes, K=16):
    fr, S, sr = spectrum(path, t0, t1)
    f0s = []
    for nm in notes:
        f = hz(nm)
        f0s.append(peak(fr, S, f, f * 0.023)[0])
    out = []
    for j, f0 in enumerate(f0s):
        lv, bad = [], []
        for k in range(1, K + 1):
            if f0 * k > sr / 2 - 200:
                lv.append(np.nan); bad.append(False); continue
            fk, a = peak(fr, S, f0 * k, max(3.0, 0.004 * f0 * k))
            lv.append(20 * np.log10(a + 1e-12))
            bad.append(any(abs(f0 * k - g * i) < max(25, 0.02 * f0 * k) for jj, g in enumerate(f0s) if jj != j for i in range(1, 40)))
        out.append((notes[j], f0, np.array(lv), np.array(bad)))
    return out


if __name__ == "__main__":
    path, t0, t1 = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
    for nm, f0, lv, bad in profiles(path, t0, t1, sys.argv[4:]):
        ref = np.nanmax(lv)
        print(f"{nm:4s} {f0:7.1f} {ref:5.0f} |" + "".join(f"{v - ref:5.0f}{'*' if b else ' '}" for v, b in zip(lv, bad)))
