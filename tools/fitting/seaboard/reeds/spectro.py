"""A log-frequency spectrogram of part of a wav, with note-name gridlines, to see the lines of a
split performance.   python spectro.py in.wav out.png [t0 t1 fmin fmax]"""
import sys
import numpy as np
import soundfile as sf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

x, sr = sf.read(sys.argv[1], dtype="float64", always_2d=True)
x = x.mean(axis=1)
t0, t1, fmin, fmax = (list(map(float, sys.argv[3:7])) + [None] * 4)[:4] if len(sys.argv) > 3 else (0, None, 60, 4000)
t1 = t1 or len(x) / sr
fmin = fmin or 60; fmax = fmax or 4000
x = x[int(t0 * sr):int(t1 * sr)]
n, hop = 8192, 480
w = np.hanning(n)
F = np.lib.stride_tricks.sliding_window_view(np.pad(x, n // 2), n)[::hop] * w
S = 20 * np.log10(np.abs(np.fft.rfft(F, axis=1)) + 1e-9)
fr = np.fft.rfftfreq(n, 1 / sr)
grid = np.geomspace(fmin, fmax, 600)
G = np.array([np.interp(grid, fr, s) for s in S])
G -= G.max()
fig, ax = plt.subplots(figsize=(max(12, (t1 - t0) * 1.2), 9), dpi=80)
ax.imshow(G.T, origin="lower", aspect="auto", vmin=-70, vmax=0, cmap="magma",
          extent=[t0, t1, 0, len(grid)])
names = "C C# D D# E F F# G G# A A# B".split()
for m in range(24, 110):
    f = 440 * 2 ** ((m - 69) / 12)
    if fmin < f < fmax and m % 12 in (0, 4, 7):
        y = np.interp(np.log(f), np.log(grid), np.arange(len(grid)))
        ax.axhline(y, color="c" if m % 12 == 0 else "w", lw=0.4, alpha=0.4)
ticks = [(np.interp(np.log(440 * 2 ** ((m - 69) / 12)), np.log(grid), np.arange(len(grid))), f"{names[m % 12]}{m // 12 - 1}")
         for m in range(24, 110) if fmin < 440 * 2 ** ((m - 69) / 12) < fmax]
ax.set_yticks([a for a, _ in ticks]); ax.set_yticklabels([b for _, b in ticks], fontsize=6)
ax.set_xticks(np.arange(np.ceil(t0), t1, 1))
ax.grid(axis="x", alpha=0.3)
plt.tight_layout()
plt.savefig(sys.argv[2])
