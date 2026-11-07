"""Turn a measured body response (dB against frequency) into a Faust filter.

The filter is a bank of parallel two-pole resonators with fixed, log-spaced poles
(Bank, "Perceptually motivated audio equalization using fixed-pole parallel second-order
filters", 2008). Only the numerators are fitted, by linear least squares, to the
minimum-phase version of the response, so the fit is fast and always stable.
The pole spacing can be finer where the body has sharp modes."""
import numpy as np

SR = 48000


def extend(freqs, db, lo_slope=12.0, f_lo=None, f_hi=None, nfft=16384):
    """Response on the FFT grid 0..SR/2. Below f_lo it falls at lo_slope dB/octave, above
    f_hi it keeps the slope of the last octave."""
    fr = np.fft.rfftfreq(nfft, 1 / SR)
    f_lo = f_lo or freqs[0]; f_hi = f_hi or freqs[-1]
    lg = np.log2(np.maximum(fr, 1.0))
    out = np.interp(lg, np.log2(freqs), db)
    d_lo = np.interp(np.log2(f_lo), np.log2(freqs), db)
    out = np.where(fr < f_lo, d_lo - lo_slope * (np.log2(f_lo) - lg), out)
    d_hi = np.interp(np.log2(f_hi), np.log2(freqs), db)
    slope = d_hi - np.interp(np.log2(f_hi / 2), np.log2(freqs), db)          # dB per octave
    out = np.where(fr > f_hi, d_hi + slope * (lg - np.log2(f_hi)), out)
    return fr, out


def min_phase(db):
    """Minimum-phase complex response from a magnitude in dB on an rfft grid."""
    n = 2 * (len(db) - 1)
    logmag = np.log(10 ** (db / 20))
    c = np.fft.irfft(logmag, n)
    w = np.zeros(n); w[0] = 1; w[1:n // 2] = 2; w[n // 2] = 1
    return np.exp(np.fft.rfft(c * w))


def poles(f_points):
    """Pole pairs at the given frequencies, each as wide as the gap to its neighbours."""
    th = 2 * np.pi * np.asarray(f_points) / SR
    d = np.empty_like(th)
    d[1:-1] = (th[2:] - th[:-2]) / 2; d[0] = th[1] - th[0]; d[-1] = th[-1] - th[-2]
    return np.exp(-d / 2) * np.exp(1j * th)


def fit(fr, target, p, weight=None, fir=1):
    """Least-squares numerators for poles p (one of each conjugate pair) against the
    complex target on grid fr. Returns sections [(b0, b1, a1, a2)] and FIR taps."""
    z1 = np.exp(-1j * 2 * np.pi * fr / SR)
    cols = []
    secs_a = []
    for pk in p:
        a1, a2 = -2 * pk.real, abs(pk) ** 2
        den = 1 + a1 * z1 + a2 * z1 ** 2
        cols += [1 / den, z1 / den]
        secs_a.append((a1, a2))
    for m in range(fir):
        cols.append(z1 ** m)
    M = np.stack(cols, axis=1)
    w = np.ones(len(fr)) if weight is None else weight
    Mw = M * w[:, None]; tw = target * w
    A = np.concatenate([Mw.real, Mw.imag]); y = np.concatenate([tw.real, tw.imag])
    x, *_ = np.linalg.lstsq(A, y, rcond=None)
    secs = [(x[2 * i], x[2 * i + 1], a1, a2) for i, (a1, a2) in enumerate(secs_a)]
    return secs, x[2 * len(p):], M @ x


def design(freqs, db, pole_freqs, lo_slope=12.0, f_lo=None, f_hi=None, fit_lo=None, fit_hi=20000):
    fr, full = extend(freqs, db, lo_slope, f_lo, f_hi)
    target = min_phase(full)
    fit_lo = fit_lo or max(20, pole_freqs[0] / 2)
    m = (fr >= fit_lo) & (fr <= fit_hi)
    w = 1 / np.sqrt(np.maximum(fr[m], fit_lo))          # equal weight per octave (power ~ 1/f)
    secs, firt, resp = fit(fr[m], target[m], poles(pole_freqs), w)
    err = 20 * np.log10(np.abs(resp) + 1e-9) - full[m]
    return secs, firt, fr[m], err, full


def response(secs, firt, fr):
    z1 = np.exp(-1j * 2 * np.pi * fr / SR)
    h = sum(b0 / (1 + a1 * z1 + a2 * z1 ** 2) + b1 * z1 / (1 + a1 * z1 + a2 * z1 ** 2) for b0, b1, a1, a2 in secs)
    return h + sum(c * z1 ** m for m, c in enumerate(firt))


def faust(name, secs, firt, comment=""):
    """A Faust function `name` = the filter, as parallel fi.tf2 sections."""
    lines = [f"// {comment}" if comment else "", f"// {len(secs)} parallel resonators, fitted by tools/fitting/timbre/bodyfit.py.",
             f"{name} = _ <: ("]
    terms = [f"    fi.tf2({b0:.9g}, {b1:.9g}, 0, {a1:.12g}, {a2:.12g})" for b0, b1, a1, a2 in secs]
    terms.append(f"    *({firt[0]:.9g})")
    lines.append(",\n".join(terms))
    lines.append(") :> _;")
    return "\n".join(l for l in lines if l != "") + "\n"
