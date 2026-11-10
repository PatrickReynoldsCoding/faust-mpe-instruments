"""Fit the upright bass's / jazz guitar's body (lib/upright_fit.lib, lib/jazzgtr_fit.lib: 24
third-octave peaking gains and the output level) by playing the Seaboard player's own phrase
(refs/roli-seaboard/blockm-*.wav, notes from Basic Pitch, the bass's pitch curves from YIN)
through the instrument and moving the gains by the difference in the long-term spectrum.

    python fit.py bass [rounds]      rounds 0: just score
    python fit.py guitar [rounds]
    python fit.py bass 0 --wav OUT   also write the render (and the reference) to listen to

Prints, before and after: the third-octave difference (ref - model, dB, level removed) over the
whole phrase, in the first 60 ms of the notes (the attack) and later (the ring), and how fast
the notes fall from 50 ms to 250 ms.
"""
import argparse, json, os, re, subprocess, sys, tempfile
import numpy as np
import scipy.signal as ss

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "fitting", "timbre"))
import analysis as A  # noqa: E402

SR, BLK, NB, Q = 48000, 64, 24, 2.2
REFS = os.path.join(ROOT, "refs", "roli-seaboard")
RENDER = os.path.join(ROOT, "build", "render_curves")

INST = {
    "bass": dict(dsp="instruments/plucked/upright-bass.dsp", lib="lib/upright_fit.lib", f1=25,
                 wav="blockm-upright-bass.wav", t0=0.0, t1=23.6, mono=True, fmin=30, fmax=200, lag=0.129, trim=-6,
                 press=0.7),
    "guitar": dict(dsp="instruments/plucked/jazz-guitar.dsp", lib="lib/jazzgtr_fit.lib", f1=63,
                   wav="blockm-jazz-guitar.wav", t0=26.0, t1=63.0, mono=False, press=0.75, lag=0.332, trim=2),
}


def bands(f1):
    return f1 * 2 ** (np.arange(NB) / 3)


def peq_db(g, fc, f):
    A_ = 10 ** (g / 40); w = 2 * np.pi * min(fc, 0.45 * SR) / SR; al = np.sin(w) / (2 * Q)
    b = np.array([1 + al * A_, -2 * np.cos(w), 1 - al * A_]); a = np.array([1 + al / A_, -2 * np.cos(w), 1 - al / A_])
    z = np.exp(-1j * 2 * np.pi * f / SR)
    return 20 * np.log10(np.abs((b[0] + b[1] * z + b[2] * z * z) / (a[0] + a[1] * z + a[2] * z * z)))


def body_db(eq, f1, f):
    return sum(peq_db(g, fc, f) for g, fc in zip(eq, bands(f1)))


def read_fit(lib):
    s = open(os.path.join(ROOT, lib)).read()
    eq = np.array([float(v) for v in re.search(r"eq = \(([^)]*)\)", s).group(1).split(",")])
    out = float(re.search(r"^out = ([-0-9.e]+);", s, re.M).group(1))
    return eq, out


def write_fit(lib, eq, out):
    p = os.path.join(ROOT, lib)
    s = open(p).read()
    s = re.sub(r"eq = \([^)]*\)", "eq = (" + ",".join(f"{g:.2f}" for g in eq) + ")", s)
    s = re.sub(r"^out = [-0-9.e]+;", f"out = {out:.3f};", s, flags=re.M)
    open(p, "w").write(s)


def build(inst):
    so = "build/" + inst["dsp"][len("instruments/"):-4] + ".so"
    subprocess.run(["make", "-s", so], cwd=ROOT, check=True)
    return os.path.join(ROOT, so)


def ref_notes(inst):
    """Basic Pitch's notes in the clip, times from the clip's start. The bass is one line: where
    two overlap, the weaker goes (Basic Pitch hears the second harmonic as a note too)."""
    ns = json.load(open(os.path.join(REFS, "blockm.basic-pitch-notes.json")))
    ns = sorted([n for n in ns if inst["t0"] <= n[0] < inst["t1"]])
    # Basic Pitch's times are late against these clips (the bass by 129 ms: cross-correlating the
    # onsets of the reference with a render); `lag` takes it off.
    lag = inst.get("lag", 0.0)
    ns = [[max(0, n[0] - inst["t0"] - lag), n[1] - inst["t0"] - lag, n[2], n[3]] for n in ns]
    if inst["mono"]:
        keep = []
        for n in ns:
            if keep and n[0] < keep[-1][1] - 0.03:
                if n[3] < 0.42 or n[3] < keep[-1][3] - 0.2:
                    continue
                keep[-1][1] = n[0]
            keep.append(list(n))
        ns = keep
    return ns


def controls(inst, notes, total, x=None, voices=8):
    nb = int(total * SR / BLK)
    ctl = np.zeros((nb, voices, 6), np.float32)
    ctl[:, :, 0] = 110; ctl[:, :, 3] = 0.5; ctl[:, :, 4] = 0.5
    busy = np.zeros(voices)
    if inst["mono"] and x is not None:
        t, f0, per, _ = A.track_f0(x, inst["fmin"], inst["fmax"])
    for n in notes:
        a, b = int(n[0] * SR / BLK), int(n[1] * SR / BLK)
        b = min(max(b, a + 4), nb)
        if b <= a + 1:
            continue
        v = int(np.argmin(busy)) if not inst["mono"] else 0
        if not inst["mono"]:
            free = [i for i in range(voices) if busy[i] < a]
            v = free[0] if free else int(np.argmin(busy))
        hz = 440 * 2 ** ((n[2] - 69) / 12) * np.ones(b - a)
        if inst["mono"] and x is not None:
            tb = (np.arange(a, b) + 0.5) * BLK / SR
            ff = np.interp(tb, t, np.where(per > 0.8, f0, 0))
            ok = (ff > 0) & (np.abs(12 * np.log2(np.maximum(ff, 1) / hz)) < 7)
            # keep the measured pitch where it is clean, else the note's
            hz = np.where(ok, ff, hz)
            hz = ss.medfilt(hz, 5)
        ctl[a:b, v, 0] = hz
        ctl[a:b - 1, v, 1] = 1               # lift one block early so the next note re-plucks
        ctl[a:b, v, 2] = inst["press"]
        ctl[a:b, v, 4] = np.clip(0.25 + 0.7 * n[3], 0, 1)
        if b < nb:
            ctl[b:min(nb, b + int(0.5 * SR / BLK)), v, 0] = hz[-1]
        busy[v] = b + 2
    return ctl


def render(so, ctl):
    with tempfile.TemporaryDirectory() as d:
        c, o = os.path.join(d, "c.f32"), os.path.join(d, "o.f32")
        np.ascontiguousarray(ctl, np.float32).tofile(c)
        subprocess.run([RENDER, so, c, str(ctl.shape[1]), o], check=True, stdout=subprocess.DEVNULL)
        return np.fromfile(o, np.float32).astype(np.float64)


def third_oct(x, f1, sel=None):
    """Mean power (dB) in the 24 bands, over STFT frames (sel: which frames)."""
    f, t, S = ss.stft(x, SR, nperseg=8192, noverlap=8192 - 480)
    P = np.abs(S) ** 2
    if sel is not None:
        P = P[:, sel(t)]
    P = P.mean(1)
    out = []
    for fc in bands(f1):
        m = (f >= fc * 2 ** (-1 / 6)) & (f < fc * 2 ** (1 / 6))
        out.append(10 * np.log10(P[m].sum() + 1e-20))
    return np.array(out), t


def masks(notes):
    on = np.array([n[0] for n in notes])
    def attack(t):
        d = t[:, None] - on[None, :]
        return ((d > -0.01) & (d < 0.07)).any(1)
    def ring(t):
        d = t[:, None] - on[None, :]
        inn = ((d > 0.12) & (t[:, None] < np.array([n[1] for n in notes])[None, :])).any(1)
        return inn & ~attack(t)
    return attack, ring


def falls(x, notes):
    """How much each (long enough) note falls from 50 ms to 250 ms after its onset (dB)."""
    out = []
    for n in notes:
        if n[1] - n[0] < 0.3:
            continue
        a = int((n[0] + 0.05) * SR); b = int((n[0] + 0.25) * SR); w = 1200
        r = lambda i: 20 * np.log10(np.sqrt(np.mean(x[i:i + w] ** 2)) + 1e-9)
        out.append(r(a) - r(b))
    return np.median(out) if out else np.nan


def report(name, x, y, notes, f1):
    at, ri = masks(notes)
    res = {}
    for lab, sel in (("all", None), ("attack", at), ("ring", ri)):
        R, _ = third_oct(x, f1, sel); M, _ = third_oct(y, f1, sel)
        w = 10 ** ((R - R.max()) / 20)
        d = R - M
        d -= np.sum(d * w) / np.sum(w)
        res[lab] = (d, w)
        err = np.sqrt(np.sum(w * d ** 2) / np.sum(w))
        print(f"  {lab:6s} rms {err:4.1f} dB | " + " ".join(f"{v:+.0f}" for v in d))
    # how loud the attack is next to the ring (ref minus model), and the fall
    def lv(z, s): return 10 * np.log10(np.sum(10 ** (third_oct(z, f1, s)[0] / 10)))
    print(f"  attack-ring balance ref-model {((lv(x, at) - lv(x, ri)) - (lv(y, at) - lv(y, ri))):+.1f} dB;"
          f" fall 50->250 ms: ref {falls(x, notes):.1f} model {falls(y, notes):.1f} dB")
    print("  bands: " + " ".join(f"{b:.0f}" for b in bands(f1)))
    return res


def solve(F, D, W, eq, f1, lam=0.3, step=0.8):
    J = np.zeros((len(F), NB))
    base = body_db(eq, f1, F)
    for i in range(NB):
        e = eq.copy(); e[i] += 1
        J[:, i] = body_db(e, f1, F) - base
    Dm = np.diff(np.eye(NB), 2, axis=0)
    Aa = np.vstack([J * W[:, None], lam * Dm, 0.1 * np.eye(NB)])
    bb = np.concatenate([D * W, -lam * Dm @ eq, np.zeros(NB)])
    return np.clip(eq + step * np.linalg.lstsq(Aa, bb, rcond=None)[0], -30, 30)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inst"); ap.add_argument("rounds", nargs="?", type=int, default=3)
    ap.add_argument("--wav")
    a = ap.parse_args()
    inst = INST[a.inst]
    x = A.load(os.path.join(REFS, inst["wav"]))
    x = x[:int((inst["t1"] - inst["t0"] + 0.5) * SR)]
    notes = ref_notes(inst)
    ctl = controls(inst, notes, len(x) / SR, x)
    f1 = inst["f1"]
    for r in range(a.rounds + 1):
        so = build(inst)
        y = render(so, ctl)[:len(x)]
        eq, out = read_fit(inst["lib"])
        print(f"round {r}: {len(notes)} notes")
        res = report(a.inst, x, y, notes, f1)
        if r == a.rounds:
            break
        d, w = res["all"]
        fc = bands(f1)
        # the target at each band centre, the bands' own shapes in between
        eq = solve(fc, d, w ** 0.25, eq, f1)
        eq -= eq.max() if eq.max() > 12 else 0
        # level: the model's rms re the reference's, then `trim` (dB) to sit with odo's other sounds
        lvl = 20 * np.log10(np.sqrt(np.mean(x ** 2)) / (np.sqrt(np.mean(y ** 2)) + 1e-12)) + inst.get("trim", 0)
        write_fit(inst["lib"], eq, out + lvl)
    if a.wav:
        A.save(a.wav, y / max(1e-9, np.abs(y).max()) * 0.5)
        A.save(a.wav.replace(".wav", ".ref.wav"), x / np.abs(x).max() * 0.5)


if __name__ == "__main__":
    main()
