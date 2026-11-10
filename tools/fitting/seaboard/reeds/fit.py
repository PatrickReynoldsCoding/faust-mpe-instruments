"""Fit a reed's body (lib/<inst>_fit.lib: 24 third-octave peaking gains, output level, and for
the sax the brightness) to the SWAM references in refs/roli-seaboard/.

    python fit.py sax [rounds]        the solo tenor sax: its own phrase played through the model
    python fit.py clarinet [rounds]   held notes picked out of the three-zone split (NOTES below)
    python fit.py oboe [rounds]
    python fit.py sax 0               just score the current fit

Each round: build the instrument, play the reference's notes through it (render_curves, same
pitch curve and a pressure from the reference's level), measure the harmonics of both the same
way, and move the body gains by the difference (least squares over the bands' exact responses,
smoothed). Prints the error (rms dB over harmonics, per-note level removed) before and after.
"""
import os, re, subprocess, sys, tempfile
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "fitting", "timbre"))
sys.path.insert(0, HERE)
import analysis as A          # noqa: E402
import perform as P           # noqa: E402
import harmprofile as PR      # noqa: E402

SR, BLK = 48000, 64
REFS = os.path.join(ROOT, "refs", "roli-seaboard")
RENDER = os.environ.get("RENDER_CURVES", os.path.join(ROOT, "build", "render_curves"))
NB = 24
BANDS = 100 * 2 ** (np.arange(NB) / 3)
Q = 2.2
K = 24                                    # harmonics compared

INST = {
    "sax": dict(dsp="instruments/winds/tenor-sax.dsp", lib="lib/sax_fit.lib", wav="blockm-tenor-sax.wav",
                fmin=90, fmax=900),
    # (t0, t1, the note, every note sounding then) from the rise split; see the report
    "clarinet": dict(dsp="instruments/winds/clarinet.dsp", lib="lib/clarinet_fit.lib", lam=0.2,
                     wav="rise-cello-clarinet-oboe.wav", notes=[
                         (2.3, 3.9, "E5", "E5 G4 C4 G3"), (6.6, 7.4, "B4", "B4 G#4 B2 E3 F#3"),
                         (9.2, 11.2, "B4", "E4 G#4 B4"), (11.35, 11.75, "B4", "G#4 B4"),
                         (2.3, 3.9, "C4", "E5 G4 C4 G3")]),
    "oboe": dict(dsp="instruments/winds/oboe.dsp", lib="lib/oboe_fit.lib",
                 wav="rise-cello-clarinet-oboe.wav", notes=[
                     (6.6, 7.4, "G#4", "B4 G#4 B2 E3 F#3"), (9.2, 11.2, "G#4", "E4 G#4 B4"),
                     (11.35, 11.75, "G#4", "G#4 B4"), (4.1, 5.2, "B4", "D5 B4 D4 G2"),
                     (2.3, 3.9, "G4", "E5 G4 C4 G3")]),
}


# -- the fit file -----------------------------------------------------------------------------
def read_fit(lib):
    s = open(os.path.join(ROOT, lib)).read()
    eq = np.array([float(v) for v in re.search(r"eq = \(([^)]*)\)", s).group(1).split(",")])
    vals = {k: float(v) for k, v in re.findall(r"^(\w+) = ([-0-9.e]+);", s, re.M)}
    return s, eq, vals


def write_fit(lib, eq, vals):
    s = open(os.path.join(ROOT, lib)).read()
    s = re.sub(r"eq = \([^)]*\)", "eq = (" + ",".join(f"{g:.2f}" for g in eq) + ")", s)
    for k, v in vals.items():
        s = re.sub(rf"^{k} = [-0-9.e]+;", f"{k} = {v:.3f};", s, flags=re.M)
    open(os.path.join(ROOT, lib), "w").write(s)


# -- the bands' response ----------------------------------------------------------------------
def peq_db(g, fc, f):
    A_ = 10 ** (g / 40); w = 2 * np.pi * fc / SR; al = np.sin(w) / (2 * Q)
    b = np.array([1 + al * A_, -2 * np.cos(w), 1 - al * A_]); a = np.array([1 + al / A_, -2 * np.cos(w), 1 - al / A_])
    z = np.exp(-1j * 2 * np.pi * f / SR)
    return 20 * np.log10(np.abs((b[0] + b[1] * z + b[2] * z * z) / (a[0] + a[1] * z + a[2] * z * z)))


def body_db(eq, f):
    return sum(peq_db(g, fc, f) for g, fc in zip(eq, BANDS) if fc < SR / 2.2)


# -- rendering --------------------------------------------------------------------------------
def build(inst):
    so = os.path.join(ROOT, "build", inst["dsp"][len("instruments/"):-4] + ".so")
    subprocess.run(["make", "-s", os.path.relpath(so, ROOT)], cwd=ROOT, check=True)
    return so


def render(so, ctl):
    ctl = np.ascontiguousarray(ctl, dtype=np.float32)
    with tempfile.TemporaryDirectory() as d:
        c, o = os.path.join(d, "c.f32"), os.path.join(d, "o.f32")
        ctl.tofile(c)
        subprocess.run([RENDER, so, c, str(ctl.shape[1]), o], check=True)
        return np.fromfile(o, dtype=np.float32).astype(np.float64)


# -- measurements -----------------------------------------------------------------------------
def note_harmonics(x, notes, k=K):
    """Mean harmonic levels (dB) of each note, from 5 ms frames inside it (after its first 60 ms)."""
    out = []
    for nt in notes:
        t = nt["start"] + 0.06 + np.arange(0, max(0.0, nt["end"] - nt["start"] - 0.1), 0.02)
        if len(t) < 3:
            out.append(None); continue
        f0 = np.interp(t, nt["start"] + np.arange(len(nt["hz"])) * A.HOP / A.SR, nt["hz"])
        _, H, _ = A.harmonics(x, t, f0, np.ones(len(t), bool), kmax=k, fmax=12000)
        P_ = 10 ** (H / 10)
        out.append((np.nanmedian(f0), 10 * np.log10(np.nanmean(P_, axis=0) + 1e-20),
                    10 * np.log10(np.nansum(np.nanmean(P_, axis=0)) + 1e-20)))
    return out


def sax_data(inst, so):
    x = A.load(os.path.join(REFS, inst["wav"]))
    notes, tr = P.notes_from(x, inst["fmin"], inst["fmax"])
    notes = [n for n in notes if n["end"] - n["start"] > 0.15]
    ref = np.percentile(tr["db"][tr["voiced"]], 95)
    l2p = lambda db, hz: np.clip(10 ** ((db - ref) / (20 * 1.35)) * 0.95, 0.03, 1)
    ctl = P.controls(notes, len(x) / SR + 0.5, l2p)
    y = render(so, ctl)
    return x, y, notes, ref


def compare(href, hmod, mask=None):
    """Per-note differences ref - model (dB) at harmonic frequencies, per-note level removed."""
    F, D, W = [], [], []
    for j, (r, m) in enumerate(zip(href, hmod)):
        if r is None or m is None:
            continue
        f0 = r[0]
        ok = np.isfinite(r[1]) & np.isfinite(m[1]) & (r[1] > r[1].max() - 45)
        if mask is not None:
            ok &= mask[j][:len(ok)]
        d = r[1] - m[1]
        if ok.sum() < 3:
            continue
        w = 10 ** ((r[1] - r[1].max()) / 20)
        d = d - np.sum(d[ok] * w[ok]) / np.sum(w[ok])
        F += list(f0 * np.arange(1, K + 1)[ok]); D += list(d[ok]); W += list(np.sqrt(w[ok]))
    return np.array(F), np.array(D), np.array(W)


def solve(F, D, W, eq, lam=0.6, step=0.8):
    """Gain changes so that the body's change matches D at F (weighted), smooth across bands."""
    J = np.zeros((len(F), NB))
    base = body_db(eq, F)
    for i in range(NB):
        e = eq.copy(); e[i] += 1
        J[:, i] = body_db(e, F) - base
    Dm = np.diff(np.eye(NB), 2, axis=0)
    Aa = np.vstack([J * W[:, None], lam * Dm, 0.15 * np.eye(NB)])
    bb = np.concatenate([D * W, -lam * Dm @ eq, np.zeros(NB)])
    dg = np.linalg.lstsq(Aa, bb, rcond=None)[0]
    return np.clip(eq + step * dg, -24, 24)


def err(F, D, W):
    return float(np.sqrt(np.sum(W * D ** 2) / np.sum(W)))


def bands_report(F, D, W):
    edges = [0, 400, 800, 1600, 3200, 6400, 20000]
    return " ".join(f"{a}-{b}:{np.average(D[(F >= a) & (F < b)], weights=W[(F >= a) & (F < b)]):+.1f}"
                    for a, b in zip(edges, edges[1:]) if ((F >= a) & (F < b)).any())


def tilt(h):
    """Brightness: level of harmonics above 1 kHz re the total (dB)."""
    f0, lv, tot = h
    f = f0 * np.arange(1, len(lv) + 1)
    p = 10 ** (lv / 10)
    return 10 * np.log10(np.nansum(p[f > 1000]) + 1e-20) - tot


def round_sax(name, inst, rounds):
    for r in range(rounds + 1):
        so = build(inst)
        x, y, notes, ref = sax_data(inst, so)
        hr, hm = note_harmonics(x, notes), note_harmonics(y, notes)
        F, D, W = compare(hr, hm)
        s, eq, vals = read_fit(inst["lib"])
        # brightness against loudness: tilt of loud and soft notes
        lv = np.array([h[2] if h else np.nan for h in hr])
        tr_ = np.array([tilt(h) if h else np.nan for h in hr]); tm = np.array([tilt(h) if h else np.nan for h in hm])
        ok = np.isfinite(lv) & np.isfinite(tr_) & np.isfinite(tm)
        loud = ok & (lv > np.nanmedian(lv[ok])); soft = ok & ~loud
        dl = np.nanmean(tr_[loud] - tm[loud]); ds = np.nanmean(tr_[soft] - tm[soft])
        f0n = np.array([h[0] if h else np.nan for h in hr])
        ok2 = ok & np.isfinite(f0n)
        so_r = np.polyfit(np.log2(f0n[ok2]), tr_[ok2], 1)[0]; so_m = np.polyfit(np.log2(f0n[ok2]), tm[ok2], 1)[0]
        lvl = 10 * np.log10(np.mean(y ** 2) + 1e-20) - 10 * np.log10(np.mean(x ** 2) + 1e-20)
        print(f"round {r}: err {err(F, D, W):.2f} dB  [{bands_report(F, D, W)}]  tilt diff loud {dl:+.1f} soft {ds:+.1f}"
              f"  level model-ref {lvl:+.1f} dB"
              f"  tilt/oct ref {so_r:+.1f} model {so_m:+.1f}", flush=True)
        if r == rounds:
            return x, y
        eq = solve(F, D, W, eq)
        # loud notes too dull/bright relative to soft: brightness span
        if "reg" in vals:
            vals["reg"] = float(np.clip(vals["reg"] + (so_m - so_r) / 15, -0.5, 1.0))
        vals["lo"] = float(np.clip(vals["lo"] * 10 ** (ds / 30), 1.2, 20))
        vals["hi"] = float(np.clip(vals["hi"] * 10 ** (dl / 30), vals["lo"] + 1, 60))
        write_fit(inst["lib"], eq - np.mean(eq), vals)


def round_split(name, inst, rounds, press=0.7):
    path = os.path.join(REFS, inst["wav"])
    href, masks, f0s = [], [], []
    for t0, t1, nm, alln in inst["notes"]:
        names = alln.split()
        pr = {n: (f0, lv, bad) for n, f0, lv, bad in PR.profiles(path, t0, t1, names, K)}
        f0, lv, bad = pr[nm]
        href.append((f0, lv, 10 * np.log10(np.nansum(10 ** (lv / 10)))))
        masks.append(~bad); f0s.append(f0)
    for r in range(rounds + 1):
        so = build(inst)
        # each note held 1.6 s alone; measured from 0.5 to 1.4 s like the reference
        hmod = []
        for f0 in f0s:
            n = int(2.0 * SR / BLK)
            ctl = np.zeros((n, 1, 6)); ctl[:, 0, 0] = f0; ctl[:, 0, 1] = np.arange(n) < int(1.6 * SR / BLK)
            ctl[:, 0, 2] = press; ctl[:, 0, 3] = 0.5; ctl[:, 0, 4] = 0.6
            y = render(so, ctl)
            with tempfile.NamedTemporaryFile(suffix=".wav") as tf:
                A.save(tf.name, y)
                (_, ff, lv, _), = PR.profiles(tf.name, 0.5, 1.4, [str(f0)], K)
            hmod.append((ff, lv, 10 * np.log10(np.nansum(10 ** (lv / 10)))))
        F, D, W = compare(href, hmod, masks)
        s, eq, vals = read_fit(inst["lib"])
        print(f"round {r}: err {err(F, D, W):.2f} dB  [{bands_report(F, D, W)}]", flush=True)
        for (t0, t1, nm, _), h, m in zip(inst["notes"], href, hmod):
            print(f"   {nm:4s} ref " + " ".join(f"{v - h[1].max():4.0f}" for v in h[1][:10]) +
                  "\n        mod " + " ".join(f"{v - m[1].max():4.0f}" for v in m[1][:10]))
        if r == rounds:
            return
        eq = solve(F, D, W, eq, lam=inst.get("lam", 0.6))
        write_fit(inst["lib"], eq - np.mean(eq), vals)


if __name__ == "__main__":
    name = sys.argv[1]
    rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    inst = INST[name]
    if name == "sax":
        x, y = round_sax(name, inst, rounds)
        if len(sys.argv) > 3:
            A.save(sys.argv[3], y)
    else:
        round_split(name, inst, rounds)
