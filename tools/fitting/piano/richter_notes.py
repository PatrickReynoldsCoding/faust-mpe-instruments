"""Measure the notes of the Richter albums that are struck one at a time.

Every track is cut into one-minute pieces. In each, a jump in the whole spectrum is an event; where exactly
one key rises (a melody note or one note of an arpeggio; chords and echoes of a lower key are left out) the
note is measured from what appears in the 0.3 s after the strike minus what was already sounding just
before it. That "rise spectrum" is the new note alone even when older notes are still ringing, so it works
in flowing music. From it: the key's real pitch and stretch, its inharmonicity B, the level of each partial
(hammer and body), and which channel it sits in. The fundamental's early decay is also measured when the
next 0.45 s is free of events.

   python richter_notes.py       -> refs/richter-piano.npz, and a count by key
(LAION CLAP was tried first, to find the solo-piano stretches; its embeddings did not tell music apart.)
"""
import os, sys
import numpy as np
import soundfile as sf
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "timbre"))
import notes as N                                                         # noqa: E402
import richter_transcribe as T                                            # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
WAV = os.path.join(ROOT, "refs", "richter", "wav")
SR = N.SR
NP = N.NP
PRIOR = dict(np.load(os.path.join(ROOT, "refs", "piano-params.npz")))           # the Steinway: stretch (cents) and B per key


def segments():
    segs = []
    for f in sorted(os.listdir(WAV)):
        n = sf.info(os.path.join(WAV, f)).duration
        for a in np.arange(0, n - 5, 60.0):
            segs.append([f, float(a), float(min(n, a + 60.0))])
    return segs


def rise_spectrum(m, t, w):
    """Magnitude spectrum of what the strike at t adds: the w seconds from 20 ms after it, minus the same
    length from just before (negative parts, a decaying older note, are zero)."""
    n = int(w * SR)
    a0 = int((t + 0.02) * SR); b0 = int(t * SR) - n - int(0.01 * SR)
    if b0 < 0 or a0 + n > len(m):
        return None, None
    win = np.hanning(n)
    nfft = 1 << int(np.ceil(np.log2(n * 4)))
    A = np.abs(np.fft.rfft(m[a0:a0 + n] * win, nfft)); B = np.abs(np.fft.rfft(m[b0:b0 + n] * win, nfft))
    return np.maximum(A - 1.0 * B, 0), SR / nfft


def partials(D, df, key):
    """f0, B and the partials' levels from the rise spectrum, widening the search as N.fit_partials does."""
    k = key - 21
    f0 = N.hz(key) * 2 ** (PRIOR["stretch"][k] / 1200); B = float(PRIOR["B"][k])
    found = []
    for nmax in (4, 7, 10, 14, 20, 28, NP, NP):
        found = []
        for n in range(1, nmax + 1):
            fp = n * f0 * np.sqrt(1 + B * n * n)
            if fp > N.FMAX:
                break
            p = N.peak_near(D, df, fp, width=0.2 * f0)
            if p is None:
                continue
            floor = np.median(D[max(0, int((fp - f0 / 2) / df)): int((fp + f0 / 2) / df) + 1])
            if p[1] > 6 * floor:
                found.append((n, p[0], p[1]))
        if len(found) >= 3:
            n_ = np.array([a for a, _, _ in found], float); f_ = np.array([b for _, b, _ in found])
            A_ = np.stack([np.ones_like(n_), n_ ** 2], 1)
            a_, b_ = np.linalg.lstsq(A_, (f_ / n_) ** 2, rcond=None)[0]
            if a_ > 0:
                f0, B = np.sqrt(a_), max(b_ / a_, 0.0)
    return f0, B, found


def clean_notes(seg):
    f, a, b = seg
    x, sr = sf.read(os.path.join(WAV, f), start=int(a * SR), stop=int(b * SR), dtype="float32")
    m = x.mean(axis=1)
    db = T.semis(T.cqt_db(m))
    fps = SR / T.HOP
    ev, _ = T.events(db)
    out = []
    for i, t in enumerate(ev):
        tt = t / fps
        nxt = ev[i + 1] / fps if i + 1 < len(ev) else tt + 5
        prv = ev[i - 1] / fps if i > 0 else tt - 5
        w = min(0.3, nxt - tt - 0.03)
        if w < 0.1 or tt - prv < 0.12 or tt < 0.5:
            continue
        before = db[:, max(0, t - 8):max(1, t - 2)].min(axis=1)
        after = db[:, t + 1:t + 8].max(axis=1)
        top = [k for k in range(88) if after[k] - before[k] >= 8]
        keys = []
        for k in top:
            nb = max(after[k - 1] if k > 0 else -200, after[k + 1] if k < 87 else -200)
            if after[k] - nb < 3 or any((k - j) in (12, 19, 24, 28, 31, 34, 36, 38, 40) and after[k] < after[j] + 1 for j in top if j < k):
                continue
            keys.append(k)
        if len(keys) != 1 or after[keys[0]] - before[keys[0]] < 12:
            continue
        key = 21 + keys[0]
        D, df = rise_spectrum(m, tt, w)
        if D is None:
            continue
        f0, B, found = partials(D, df, key)
        if len(found) < 5 or abs(1200 * np.log2(f0 * np.sqrt(1 + B) / N.hz(key))) > 40:
            continue
        L = np.full(NP, np.nan); Fp = np.full(NP, np.nan)
        scale = 2 / np.sum(np.hanning(int(w * SR)))
        for n, fq, amp in found:
            L[n - 1] = 20 * np.log10(amp * scale + 1e-12); Fp[n - 1] = fq
        # early decay of the fundamental (dB/s from 0.08 s to 0.45 s after the peak), if nothing else happens
        r1 = np.nan
        if nxt - tt > 0.55:
            kk = keys[0]; pk = t + int(np.argmax(db[kk, t:t + 8]))
            seg_db = db[kk, pk + int(0.08 * fps): pk + int(0.45 * fps)]
            if len(seg_db) > 8:
                r1 = float(np.polyfit(np.arange(len(seg_db)) / fps, seg_db, 1)[0])
        seg_lr = x[int(tt * SR):int((tt + 0.3) * SR)]
        el = float(np.sum(seg_lr[:, 0] ** 2)) + 1e-20; er = float(np.sum(seg_lr[:, 1] ** 2)) + 1e-20
        out.append(dict(midi=key, f0=f0, B=B, nfound=len(found), L=L, Fp=Fp, level=float(after[keys[0]]), r1=r1,
                        lr_db=10 * np.log10(el / er), t=a + tt, file=f, rms=20 * np.log10(np.sqrt(np.mean(seg_lr ** 2)) + 1e-12)))
    return out


def main():
    segs = segments()
    print(len(segs), "pieces,", sum(s[2] - s[1] for s in segs) / 60, "minutes", flush=True)
    with Pool(14) as p:
        res = [n for part in p.map(clean_notes, segs, chunksize=1) for n in part]
    print(len(res), "single notes")
    out = {k: np.array([r[k] for r in res]) for k in ("midi", "f0", "B", "nfound", "level", "r1", "lr_db", "t", "rms")}
    out["track"] = np.array([r["file"] for r in res])
    out["L"] = np.stack([r["L"] for r in res]); out["Fp"] = np.stack([r["Fp"] for r in res])
    np.savez(os.path.join(ROOT, "refs", "richter-piano.npz"), **out)
    keys, counts = np.unique(out["midi"], return_counts=True)
    print("notes per key:", dict(zip(keys.tolist(), counts.tolist())))


if __name__ == "__main__":
    main()
