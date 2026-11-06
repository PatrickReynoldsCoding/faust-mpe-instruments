"""Measure single piano notes (refs/iowa-piano/<dyn>.<note><oct>.wav, or a rendered note).

For each note: the real f0 and how stretched the overtones are (inharmonicity B, from
f_n = n f0 sqrt(1 + B n^2)), the level of each partial just after the strike, and how each
partial decays (an early and a late rate, since piano notes fall fast then ring on).
The same code measures the instrument, so the two can be compared.

   python notes.py                 measure all Iowa notes -> refs/iowa-piano.npz
"""
import glob, os, re, sys
import numpy as np
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "timbre"))
from analysis import load, SR                                          # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
NP = 40                       # partials measured
FMAX = 16000                  # ... below this
ENV_HOP = 0.01                # envelope step, s
NAMES = {"C": 0, "Db": 1, "D": 2, "Eb": 3, "E": 4, "F": 5, "Gb": 6, "G": 7, "Ab": 8, "A": 9, "Bb": 10, "B": 11}
DYN = {"pp": 0, "mf": 1, "ff": 2}


def midi_of(name):
    m = re.match(r"([A-G]b?)(\d)$", name)
    return 12 * (int(m.group(2)) + 1) + NAMES[m.group(1)]


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def onset(x):
    """First sample where the note (1 ms rms) is within 20 dB of its peak: a little before the
    strike. (The recordings have a hiss floor near -66 dB, so a lower threshold finds the hiss.)"""
    e = np.sqrt(np.convolve(x * x, np.ones(48) / 48, "same"))
    i = int(np.argmax(e > e.max() * 0.1))
    return max(0, i - int(0.002 * SR))


def peak_near(spec, df, f, width):
    lo = max(1, int((f - width) / df)); hi = min(len(spec) - 2, int((f + width) / df) + 1)
    if hi <= lo:
        return None
    k = lo + int(np.argmax(spec[lo:hi]))
    a, b, c = np.log(spec[k - 1] + 1e-30), np.log(spec[k] + 1e-30), np.log(spec[k + 1] + 1e-30)
    d = 0.5 * (a - c) / (a - 2 * b + c) if (a - 2 * b + c) < 0 else 0.0
    return (k + d) * df, spec[k]


def fit_partials(x, f_nom):
    """f0 and B from the peaks of a long spectrum taken just after the strike."""
    seg = x[int(0.03 * SR): int(0.03 * SR) + int(min(2.0, max(0.5, 40 / f_nom)) * SR)]
    nfft = 1 << int(np.ceil(np.log2(len(seg) * 4)))
    spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), nfft))
    df = SR / nfft
    f0, B = f_nom, 0.0
    found = []
    # widen the search a few partials at a time, refitting f0 and B as it goes, so the
    # prediction for the next partials is always close (high partials sit far sharp)
    for nmax in (4, 7, 10, 14, 20, 28, NP, NP):
        found = []
        for n in range(1, nmax + 1):
            fp = n * f0 * np.sqrt(1 + B * n * n)
            if fp > FMAX:
                break
            p = peak_near(spec, df, fp, width=0.2 * f0)
            if p is None:
                continue
            floor = np.median(spec[max(0, int((fp - f0 / 2) / df)): int((fp + f0 / 2) / df) + 1])
            if p[1] > 4 * floor:
                found.append((n, p[0]))
        if len(found) >= 3:
            n_ = np.array([a for a, _ in found], float); f_ = np.array([b for _, b in found])
            y = (f_ / n_) ** 2
            A = np.stack([np.ones_like(n_), n_ ** 2], 1)
            a_, b_ = np.linalg.lstsq(A, y, rcond=None)[0]
            if a_ > 0:
                f0, B = np.sqrt(a_), max(b_ / a_, 0.0)
    return f0, B, len(found)


def envelope(x, f, f0):
    """Amplitude of the component at f, every ENV_HOP s (heterodyne, then a box filter whose
    length is a whole number of f0 periods near 20 ms, so the neighbours cancel)."""
    t = np.arange(len(x)) / SR
    z = x * np.exp(-2j * np.pi * f * t)
    L = int(round(np.ceil(0.02 * f0) / f0 * SR))
    c = np.cumsum(np.concatenate([[0], z]))
    hop = int(ENV_HOP * SR)
    idx = np.arange(0, len(x) - L, hop)
    return 2 * np.abs(c[idx + L] - c[idx]) / L


def decay_rates(env_db, floor_db):
    """Peak level, early rate (dB/s, from 30 ms to 0.5 s after the peak), late rate (the rest,
    while the level is 10 dB above the floor) and the late line's level at the peak time
    (how strong the slow 'aftersound' is). NaN where it can't be measured."""
    pk = int(np.argmax(env_db[:int(0.3 / ENV_HOP)]))
    t = np.arange(len(env_db)) * ENV_HOP
    live = env_db > floor_db + 10
    out, icpt = [], np.nan
    for a, b in ((pk + 3, pk + int(0.5 / ENV_HOP)), (pk + int(0.6 / ENV_HOP), len(env_db))):
        m = np.zeros(len(env_db), bool); m[a:b] = True; m &= live
        if m.sum() < 8:
            out.append(np.nan); continue
        p = np.polyfit(t[m], env_db[m], 1)
        out.append(p[0]); icpt = np.polyval(p, t[pk])
    return env_db[pk], out[0], out[1], icpt


def measure(x, f_nom, seconds=12.0):
    x = x[onset(x):]
    x = x[:int(seconds * SR)]
    f0, B, nfound = fit_partials(x, f_nom)
    L = np.full(NP, np.nan); R1 = np.full(NP, np.nan); R2 = np.full(NP, np.nan); I2 = np.full(NP, np.nan)
    Fp = np.full(NP, np.nan)
    noise = x[-int(0.5 * SR):] if len(x) > 6 * SR else None
    total = None
    for n in range(1, NP + 1):
        fp = n * f0 * np.sqrt(1 + B * n * n)
        if fp > FMAX or fp > 0.45 * SR:
            break
        e = 20 * np.log10(envelope(x, fp, f0) + 1e-12)
        fl = np.percentile(e[-50:], 50) if len(e) > 300 else -120
        pk, r1, r2, i2 = decay_rates(e, fl)
        L[n - 1], R1[n - 1], R2[n - 1], I2[n - 1], Fp[n - 1] = pk, r1, r2, i2, fp
        if n == 1:
            total = e
    rms = 20 * np.log10(np.sqrt(np.mean(x[:int(0.2 * SR)] ** 2)) + 1e-12)
    return dict(f0=f0, B=B, nfound=nfound, L=L, R1=R1, R2=R2, I2=I2, Fp=Fp, rms=rms, env1=total[:int(8 / ENV_HOP)])


def one(path):
    m = re.match(r"(pp|mf|ff)\.([A-G]b?\d)\.wav$", os.path.basename(path))
    dyn, note = m.group(1), m.group(2)
    midi = midi_of(note)
    r = measure(load(path), hz(midi))
    r.update(midi=midi, dyn=DYN[dyn])
    return r


def main():
    files = sorted(glob.glob(os.path.join(ROOT, "refs", "iowa-piano", "*.wav")))
    with Pool(4) as p:
        res = p.map(one, files)
    out = {k: np.array([r[k] for r in res]) for k in ("midi", "dyn", "f0", "B", "nfound", "rms")}
    for k in ("L", "R1", "R2", "I2", "Fp"):
        out[k] = np.stack([r[k] for r in res])
    E = np.full((len(res), int(8 / ENV_HOP)), np.nan)
    for i, r in enumerate(res):
        E[i, :len(r["env1"])] = r["env1"]
    out["env1"] = E
    np.savez(os.path.join(ROOT, "refs", "iowa-piano.npz"), **out)
    o = np.lexsort((out["dyn"], out["midi"]))
    for i in o[::9]:
        print(f"midi {out['midi'][i]:3d} dyn {out['dyn'][i]}  f0 {out['f0'][i]:8.2f} (nom {hz(out['midi'][i]):8.2f})"
              f"  B {out['B'][i]:.2e}  n {out['nfound'][i]:2d}  rms {out['rms'][i]:6.1f}"
              f"  T60 early/late h1 {-60/out['R1'][i,0]:5.1f}/{-60/out['R2'][i,0]:5.1f} s")


if __name__ == "__main__":
    main()
