"""Take the performance out of a recording (notes, pitch curve with vibrato, loudness) and
play it on an instrument, so the instrument can be compared with the recording note for note.

Each note goes to its own voice, as on the Seaboard (one finger per note)."""
import os
import numpy as np
import analysis as A
import synth as S

BLK = S.BLK


def notes_from(x, fmin, fmax, min_note=0.06, min_per=0.8, jump_st=0.6):
    """Split a solo line into notes. Returns (notes, track); a note is
    dict(start, end) in seconds plus the 5 ms pitch (Hz) and level (dB) curves."""
    t, f0, per, rms = A.track_f0(x, fmin, fmax)
    db = 20 * np.log10(rms + 1e-12)
    ref = np.percentile(db, 97)
    v = (per >= min_per) & (f0 >= fmin) & (f0 <= fmax) & (db > ref - 40)
    st = 12 * np.log2(np.maximum(f0, 1) / 440)
    # close 1-3 frame dropouts so a note is not cut by a single bad frame
    vv = v.copy()
    for gap in (1, 2, 3):
        for i in range(1, len(v) - gap):
            if v[i - 1] and not v[i:i + gap].any() and v[i + gap] and abs(st[i + gap] - st[i - 1]) < jump_st:
                vv[i:i + gap] = True
                st[i:i + gap] = np.linspace(st[i - 1], st[i + gap], gap + 2)[1:-1]
    v = vv
    # a 7-frame median of the pitch in semitones shows note steps but not vibrato
    pad = np.pad(st, 3, mode="edge")
    med = np.median(np.lib.stride_tricks.sliding_window_view(pad, 7), axis=1)
    notes = []
    i, n = 0, len(t)
    while i < n:
        if not v[i]:
            i += 1; continue
        j = i
        while j + 1 < n and v[j + 1] and abs(med[j + 1] - np.median(med[i:j + 1][-8:])) < jump_st:
            j += 1
        if (j - i + 1) * A.HOP / A.SR >= min_note:
            notes.append(dict(start=t[i], end=t[j] + A.HOP / A.SR, i0=i, i1=j + 1,
                              hz=440 * 2 ** (st[i:j + 1] / 12), db=db[i:j + 1]))
        i = j + 1
    return notes, dict(t=t, f0=f0, per=per, db=db, voiced=v)


def controls(notes, total, level_to_pressure, slide=0.5, velocity=0.7, voices=6, legato_overlap=0.01):
    """Control curves (blocks, voices, 5) that play the notes. level_to_pressure maps the
    recording's level (dB) to the instrument's pressure, per note frame."""
    nb = int(total * S.SR / BLK) + 1
    ctl = np.zeros((nb, voices, 5))
    ctl[:, :, 0] = 440; ctl[:, :, 3] = slide; ctl[:, :, 4] = velocity
    tb = np.arange(nb) * BLK / S.SR
    free_at = np.zeros(voices)
    for k, nt in enumerate(notes):
        vi = int(np.argmin(free_at))                       # the voice that went quiet longest ago
        a = int(nt["start"] * S.SR / BLK); b = min(nb, int((nt["end"] + legato_overlap) * S.SR / BLK))
        tt = nt["start"] + np.arange(len(nt["hz"])) * A.HOP / A.SR
        ctl[a:b, vi, 0] = np.interp(tb[a:b], tt, nt["hz"])
        ctl[a:b, vi, 1] = 1
        # a player's pressure does not follow the recording's vibrato flicker: smooth ~60 ms
        sm = int(os.environ.get("PRESS_SMOOTH", 12))
        dbs = nt["db"] if sm <= 1 or len(nt["db"]) < 3 else \
            np.convolve(np.pad(nt["db"], sm // 2, mode="edge"), np.ones(sm) / sm, "valid")[:len(nt["db"])]
        ctl[a:b, vi, 2] = level_to_pressure(np.interp(tb[a:b], tt, dbs), np.interp(tb[a:b], tt, nt["hz"]))
        # keep pitch and pressure after the release so the tail rings at the right pitch
        e = min(nb, b + int(3 * S.SR / BLK))
        ctl[b:e, vi, 0] = ctl[b - 1, vi, 0]; ctl[b:e, vi, 2] = ctl[b - 1, vi, 2]
        free_at[vi] = nt["end"] + 3.0 if False else nt["end"]
    return ctl


def reverb_ir(rt60=2.0, sr=S.SR, predelay=0.012, seed=1, length=None):
    """A plain hall impulse response: exponentially decaying noise, darker as it decays.
    Unit energy. Used only to compare a dry instrument with a recording made in a room."""
    rng = np.random.default_rng(seed)
    n = int((length or rt60 * 1.2) * sr)
    t = np.arange(n) / sr
    bands = [(0, 500, 1.15), (500, 2000, 1.0), (2000, 6000, 0.8), (6000, 24000, 0.55)]
    ir = np.zeros(n)
    noise = rng.standard_normal(n)
    spec = np.fft.rfft(noise); fr = np.fft.rfftfreq(n, 1 / sr)
    for lo, hi, k in bands:
        sb = np.where((fr >= lo) & (fr < hi), spec, 0)
        ir += np.fft.irfft(sb, n) * np.exp(-6.9 * t / (rt60 * k))
    ir *= np.clip(t / 0.02, 0, 1)                       # build-up of the diffuse field
    ir = np.concatenate([np.zeros(int(predelay * sr)), ir])
    return ir / np.sqrt(np.sum(ir ** 2))


def add_room(x, wet_db=-6.0, rt60=2.0):
    """Dry + reverb, with the reverb energy wet_db relative to the dry energy."""
    from scipy.signal import fftconvolve
    w = fftconvolve(x, reverb_ir(rt60))[:len(x)]
    return x + w * 10 ** (wet_db / 20)
