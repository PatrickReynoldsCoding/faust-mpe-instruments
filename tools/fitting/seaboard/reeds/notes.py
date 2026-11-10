"""Per-note measurements of a Seaboard demo clip (polyphonic): for each Basic Pitch note, the
level of its harmonics (in a window inside the note), its left/right balance, and whether a
harmonic is shared with another note sounding at the same time (then it is not trusted).

    python notes.py rise-cello-clarinet-oboe 17 [minmidi maxmidi]

Prints one line per note: onset, length, name, level, L/R balance (dB), harmonics 1..10 in dB
re the strongest (x = shared with another note).
"""
import json, os, sys
import numpy as np
import soundfile as sf

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
REFS = os.path.join(ROOT, "refs", "roli-seaboard")
NAMES = "C C# D D# E F F# G G# A A# B".split()


def name(m):
    return f"{NAMES[m % 12]}{m // 12 - 1}"


def load_clip(clip):
    x, sr = sf.read(os.path.join(REFS, clip + ".wav"), dtype="float64", always_2d=True)
    return x, sr


def clip_notes(video, t0, t1, minamp=0.25):
    n = json.load(open(os.path.join(REFS, video + ".basic-pitch-notes.json")))
    return [(a - t0, b - t0, int(m), amp) for a, b, m, amp in sorted(n) if t0 <= a < t1 and amp >= minamp]


def harmonics_at(x, sr, a, b, f0, K=10, nfft=16384):
    """Levels (linear) of harmonics 1..K of f0 in x[a:b] (stereo), plus L and R totals."""
    seg = x[int(a * sr):int(b * sr)]
    if len(seg) < 2048:
        return None
    w = np.hanning(len(seg))[:, None]
    n = max(nfft, 1 << int(np.ceil(np.log2(len(seg)))))
    S = np.abs(np.fft.rfft(seg * w, n, axis=0))
    fr = np.fft.rfftfreq(n, 1 / sr)
    H = np.zeros((K, 2))
    for k in range(1, K + 1):
        f = f0 * k
        if f > sr / 2 - 500:
            break
        bw = max(f0 * 0.12, 6.0)
        sel = (fr > f - bw) & (fr < f + bw)
        H[k - 1] = np.sqrt((S[sel] ** 2).sum(axis=0))
    return H


def main():
    clip = sys.argv[1]
    off = float(sys.argv[2])
    lo, hi = (int(sys.argv[3]), int(sys.argv[4])) if len(sys.argv) > 4 else (0, 127)
    video = clip.split("-")[0]
    x, sr = load_clip(clip)
    dur = len(x) / sr
    notes = clip_notes(video, off, off + dur)
    for a, b, m, amp in notes:
        if not (lo <= m <= hi) or b - a < 0.18:
            continue
        f0 = 440 * 2 ** ((m - 69) / 12)
        # the middle of the note, away from its attack
        aa, bb = a + min(0.08, (b - a) * 0.25), b - min(0.05, (b - a) * 0.15)
        H = harmonics_at(x, sr, aa, bb, f0)
        if H is None:
            continue
        others = [n for n in notes if n[2] != m and n[0] < bb and n[1] > aa]
        shared = []
        for k in range(1, 11):
            s = any(abs(12 * np.log2(k * f0 / (j * 440 * 2 ** ((o[2] - 69) / 12)))) < 0.4
                    for o in others for j in range(1, 13))
            shared.append(s)
        tot = H.sum(axis=1)
        ref = tot.max() + 1e-12
        lr = 20 * np.log10((H[:, 0].sum() + 1e-12) / (H[:, 1].sum() + 1e-12))
        cells = []
        for k in range(10):
            d = 20 * np.log10(tot[k] / ref + 1e-9)
            cells.append(("x" if shared[k] else " ") + f"{d:5.0f}")
        print(f"{a:6.2f} {b - a:5.2f} {name(m):4s} {20 * np.log10(ref):6.1f} {lr:5.1f} |" + "".join(cells))


if __name__ == "__main__":
    main()
