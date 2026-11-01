"""Pitch measurement shared by the tests and the scan tools."""
import numpy as np

SR = 48000
PAD = 8                 # zero-padding factor for a fine frequency grid


def _spectrum(x):
    x = (x - x.mean()) * np.hanning(len(x))
    n = len(x) * PAD
    return np.abs(np.fft.rfft(x, n)), SR / n


def _peak_near(mag, bin_hz, f, window_cents):
    """(frequency, level) of the strongest peak within +-window_cents of f."""
    lo = int(f * 2 ** (-window_cents / 1200) / bin_hz)
    hi = int(f * 2 ** (window_cents / 1200) / bin_hz) + 1
    i = lo + int(np.argmax(mag[lo:hi + 1]))
    if 0 < i < len(mag) - 1:                                   # parabolic refine
        a, b, c = np.log(mag[i - 1:i + 2] + 1e-12)
        i = i + 0.5 * (a - c) / (a - 2 * b + c + 1e-12)
    return i * bin_hz, float(mag[int(round(i))])


def cents_off(x, target):
    """How many cents the played note `x` is from `target` Hz.

    0 = in tune; small numbers = detuned.
    -1200 = an octave low: there is real energy at half the target.
    +1200 = the fundamental is missing and so are the odd harmonics (the sound is
            something else, e.g. the string sounding an octave up).

    Looks for the fundamental directly instead of guessing a pitch from the
    whole signal, because a body resonance (one loud overtone) or a sound with
    few partials fools every guess-the-pitch method."""
    mag, bin_hz = _spectrum(x)
    f0, a0 = _peak_near(mag, bin_hz, target, 60)
    loud = mag[int(target * 0.45 / bin_hz):int(target * 2.2 / bin_hz)].max()   # strongest partial in the band
    _, a_half = _peak_near(mag, bin_hz, target / 2, 60)
    if a0 < 0.08 * loud:
        # A weak fundamental is normal low on a violin or cello: the body hardly radiates it.
        # The note is still right if odd harmonics are there (a string sounding an octave up
        # has only even ones). Then judge the pitch from the 3rd harmonic.
        _, a2 = _peak_near(mag, bin_hz, 2 * target, 40)
        f3, a3 = _peak_near(mag, bin_hz, 3 * target, 40)
        _, a5 = _peak_near(mag, bin_hz, 5 * target, 40)
        if max(a3, a5) < 0.1 * max(a2, loud) or a_half > 0.3 * loud:
            return 1200.0
        return 1200 * np.log2(f3 / 3 / target)
    if a_half > 0.3 * a0:
        return -1200.0
    return 1200 * np.log2(f0 / target)
