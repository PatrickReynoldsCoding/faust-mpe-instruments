"""How close is a rendered transcription to the recording it came from?

   python richter_compare.py recording.wav start end rendered.wav

  similarity   mean cosine of the semitone spectra frame by frame (1 = the same notes at the same times)
  tone         long-term spectrum, recording minus render, in 1/3-octave bands (dB), over the loud frames
"""
import sys
import numpy as np
import soundfile as sf
import richter_transcribe as T

SR = T.SR


def load(path, a=0, b=None):
    x, sr = sf.read(path, start=int(a * SR), stop=None if b is None else int(b * SR), dtype="float32")
    return x if x.ndim > 1 else np.stack([x, x], axis=1)


def band_edges():
    c = 31.5 * 2 ** (np.arange(0, 28) / 3)
    return c[c < 20000]


def ltas(x, nfft=8192):
    """Mean power spectrum (dB) in 1/3-octave bands, over frames within 25 dB of the loudest. The two channels'
    powers are added (what the ears get), not their mean signal: that would show notches where decorrelated
    channels cancel."""
    ch = [x[:, i] for i in range(x.shape[1])] if x.ndim > 1 else [x]
    hop = nfft // 2
    w = np.hanning(nfft)
    P = 0
    for m in ch:
        fr = np.array([m[i:i + nfft] * w for i in range(0, len(m) - nfft, hop)])
        P = P + np.abs(np.fft.rfft(fr, axis=1)) ** 2
    e = P.sum(axis=1)
    P = P[e > e.max() * 10 ** (-2.5)]
    f = np.fft.rfftfreq(nfft, 1 / SR)
    c = band_edges()
    out = []
    for fc in c:
        sel = (f >= fc / 2 ** (1 / 6)) & (f < fc * 2 ** (1 / 6))
        out.append(10 * np.log10(P[:, sel].sum(axis=1).mean() + 1e-20))
    return c, np.array(out)


def similarity(a, b):
    A = 10 ** (T.semis(T.cqt_db(a.mean(axis=1) if a.ndim > 1 else a)) / 20)
    B = 10 ** (T.semis(T.cqt_db(b.mean(axis=1) if b.ndim > 1 else b)) / 20)
    n = min(A.shape[1], B.shape[1])
    A, B = A[:, :n], B[:, :n]
    ea = np.linalg.norm(A, axis=0); eb = np.linalg.norm(B, axis=0)
    ok = ea > ea.max() * 0.05
    return float(np.mean(np.sum(A[:, ok] * B[:, ok], axis=0) / (ea[ok] * eb[ok] + 1e-12)))


if __name__ == "__main__":
    rec, a, b, ren = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
    r = load(rec, a, b); y = load(ren)
    print(f"similarity {similarity(r, y[:len(r)]):.3f}")
    c, lr = ltas(r); _, ly = ltas(y[:len(r)])
    lr -= lr.max(); ly -= ly.max()
    for fc, d1, d2 in zip(c, lr, ly):
        print(f"{fc:7.0f} Hz  rec {d1:6.1f}  render {d2:6.1f}  diff {d1 - d2:+5.1f}")
