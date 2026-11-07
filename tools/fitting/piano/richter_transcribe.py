"""A rough transcription of solo piano from a recording: which keys were struck, when, how hard, how long.

It is for fitting statistics (what the player does, in which register, how loudly), not for making
sheet music. Per semitone it follows the constant-Q magnitude at the fundamental, calls a note where
that rises sharply, then throws out octave echoes (a struck note's second and third partials).

   python richter_transcribe.py refs/richter/wav/bn2_01.wav 20 40 out.npy     (start s, end s)
Writes an array of rows: onset s, midi key, onset level dB (re full scale, at the fundamental), length s.
"""
import sys
import numpy as np
import librosa
import soundfile as sf

SR = 48000
HOP = 512
BPO = 36                               # constant-Q bins per octave: three per semitone
FMIN = 27.5                            # A0
NBINS = BPO * 8 + 5


def cqt_db(x):
    c = np.abs(librosa.cqt(x, sr=SR, hop_length=HOP, fmin=FMIN, n_bins=NBINS, bins_per_octave=BPO, filter_scale=1.0))
    return 20 * np.log10(np.maximum(c, 1e-9))


def semis(db):
    """(88, frames): the loudest of the three bins at each semitone, key 21..108."""
    out = np.empty((88, db.shape[1]))
    for k in range(88):
        i = 3 * k
        out[k] = db[max(0, i - 1):i + 2].max(axis=0)
    return out


def events(db, min_gap=0.06):
    """Frames where the whole spectrum jumps: the times something is struck. Returns (frames, flux)."""
    fps = SR / HOP
    up = np.maximum(db[:, 3:] - db[:, :-3], 0)
    flux = np.concatenate([np.zeros(3), up.sum(axis=0)])
    thr = np.median(flux) + 3 * np.median(np.abs(flux - np.median(flux))) + 1e-9
    raw = [t for t in range(3, len(flux) - 8) if flux[t] > thr and flux[t] >= flux[t - 1] and flux[t] >= flux[t + 1:t + 5].max()]
    out = []
    for t in raw:
        if out and t - out[-1] < int(min_gap * fps):
            if flux[t] > flux[out[-1]]:
                out[-1] = t
        else:
            out.append(t)
    return out, flux


def transcribe(x, rise_db=8.0, peaky=3.0):
    """Rows: onset s, midi key, level dB at the fundamental, length s. At every event, the keys that rise
    sharply and stand out from their neighbours; echoes of a lower key (its partials) are dropped."""
    db = semis(cqt_db(x))
    fps = SR / HOP
    ev, _ = events(db)
    notes = []
    for t in ev:
        before = db[:, max(0, t - 8):max(1, t - 2)].min(axis=1)
        after = db[:, t + 1:t + 8].max(axis=1)
        top = [k for k in range(88) if after[k] - before[k] >= rise_db]
        keep = []
        for k in top:
            nb = max(after[k - 1] if k > 0 else -200, after[k + 1] if k < 87 else -200)
            if after[k] - nb < peaky:
                continue
            if any((k - j) in (12, 19, 24, 28, 31, 34, 36, 38, 40) and after[k] < after[j] + 1 for j in top if j < k):
                continue
            keep.append(k)
        for k in keep:
            notes.append([t / fps, 21 + k, after[k], 0.0])
    notes.sort()
    # length: until the fundamental has fallen 20 dB, or the key is struck again, at most 6 s
    for i, n in enumerate(notes):
        k = int(n[1]) - 21
        t0 = int(n[0] * fps)
        end = t0 + 1
        while end < db.shape[1] - 1 and db[k, end] > n[2] - 20 and end - t0 < 6 * fps:
            end += 1
        nxt = [m[0] for m in notes[i + 1:] if int(m[1]) == int(n[1]) and m[0] > n[0] + 0.05]
        if nxt:
            end = min(end, int(nxt[0] * fps))
        n[3] = max(0.1, (end - t0) / fps)
    return np.array(notes)


if __name__ == "__main__":
    path, a, b, out = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
    x, sr = sf.read(path, start=int(a * SR), stop=int(b * SR), dtype="float32")
    x = x.mean(axis=1) if x.ndim > 1 else x
    n = transcribe(x)
    np.save(out, n)
    print(f"{len(n)} notes, keys {int(n[:, 1].min())}-{int(n[:, 1].max())}, {len(n) / (b - a):.1f} per second" if len(n) else "no notes")
