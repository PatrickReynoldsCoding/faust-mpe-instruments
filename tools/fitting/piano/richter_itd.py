"""Time and level difference between the two channels of each selected note, against its key.

A spaced microphone pair hears a bass string a little earlier on the left and a treble string a little earlier on
the right. For each selected note (richter_fit.select_mask) the first 0.4 s of the left and right channels, band-passed
to 150-2500 Hz, are cross-correlated within +-1.5 ms: the lag at the peak (positive = the right ear is later, i.e. the
source is to the left) and the correlation there. Then a straight line of lag, and of level difference, against key.
   python richter_itd.py        -> refs/richter/itd.npz and a printout
"""
import os, sys
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import richter_fit as RF                                                  # noqa: E402

SR, ROOT = 48000, RF.ROOT


def main():
    d = np.load(RF.DATA)
    idx = np.where(RF.select_mask())[0]
    sos = butter(2, [150, 2500], btype="band", fs=SR, output="sos")
    maxlag = int(0.0015 * SR)
    rows = []
    cache = {}
    for i in idx:
        tr = str(d["track"][i]); t = float(d["t"][i]); k = int(d["midi"][i])
        if tr not in cache:
            cache = {tr: sf.read(os.path.join(ROOT, "refs", "richter", "wav", tr), dtype="float32")[0]}
        seg = cache[tr][int(t * SR):int((t + 0.4) * SR)]
        if len(seg) < 0.3 * SR:
            continue
        L = sosfilt(sos, seg[:, 0]); R = sosfilt(sos, seg[:, 1])
        n = len(L)
        X = np.fft.irfft(np.fft.rfft(L, 2 * n) * np.conj(np.fft.rfft(R, 2 * n)))
        lags = np.arange(-maxlag, maxlag + 1)
        c = np.array([X[l] for l in lags]) / (np.sqrt(np.sum(L ** 2) * np.sum(R ** 2)) + 1e-20)
        j = int(np.argmax(np.abs(c)))
        rows.append((k, -lags[j] / SR * 1000, abs(c[j]), 10 * np.log10((np.sum(L ** 2) + 1e-20) / (np.sum(R ** 2) + 1e-20))))
    a = np.array(rows)
    print(len(a), "notes")
    for lo, hi in ((36, 47), (48, 59), (60, 71), (72, 83), (84, 100)):
        s = (a[:, 0] >= lo) & (a[:, 0] <= hi)
        if s.sum() >= 3:
            print(f"keys {lo:3d}-{hi:3d}  n {int(s.sum()):3d}  lag (ms, +: source on the left) median {np.median(a[s, 1]):+5.2f}  spread {np.std(a[s, 1]):4.2f}   peak correlation {np.median(a[s, 2]):.2f}   L-R {np.median(a[s, 3]):+5.1f} dB")
    ok = a[:, 2] > 0.5
    sl, ic = np.polyfit(a[ok, 0], a[ok, 1], 1)
    sd, idd = np.polyfit(a[ok, 0], np.clip(a[ok, 3], -12, 12), 1)
    print(f"lag against key: {sl:+.4f} ms per key ({sl * 12:+.3f} ms per octave), {ic + sl * 60:+.2f} ms at middle C (notes with correlation > 0.5: {int(ok.sum())})")
    print(f"level difference against key: {sd:+.3f} dB per key, {idd + sd * 60:+.1f} dB at middle C")
    np.savez(os.path.join(ROOT, "refs", "richter", "itd.npz"), rows=a, lag_slope=sl, lag_icpt=ic, lvl_slope=sd, lvl_icpt=idd)


if __name__ == "__main__":
    main()
