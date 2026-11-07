"""Fit keys/max-richter (lib/richter_fit.lib) to the single notes measured in the Richter albums.

The piano engine is the Steinway's (lib/piano.lib). What changes is its tables: tuning, stiffness, hammer
softness and level by key and dynamic, and the body (the shape of the sound by frequency: felt, upright or
grand, microphone, room). The recordings' notes (richter_notes.py) and the instrument's own notes are
measured the same way (the spectrum a strike adds in its first 0.3 s), compared key by key, and the tables
are moved by the difference, a few rounds: as fit.py does for the Iowa notes.

   python richter_fit.py select     choose the tracks and notes that are solo piano -> refs/richter/selected.txt
   python richter_fit.py init       start from the Steinway's tables
   python richter_fit.py refit [n] [levels]   n rounds (levels: only the loudness of each key)
   python richter_fit.py refit [n]  n rounds of render, measure, correct (default 4)
   python richter_fit.py anchor     (after the rounds) keys few notes support fall back on the Steinway's tables
   python richter_fit.py level      (after the rounds and richter_tone.py) every key as loud as the Steinway's
   python richter_fit.py report     how far the instrument still is from the recordings
"""
import os, shutil, subprocess, sys, tempfile
import numpy as np
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, "..", "timbre"))
import fit as F                                                           # noqa: E402
import notes as N                                                         # noqa: E402
import richter_notes as RN                                                # noqa: E402
import richter_transcribe as T                                            # noqa: E402

ROOT = F.ROOT
REFS = F.REFS
PARAMS = os.path.join(REFS, "richter-params.npz")
LIB = os.path.join(ROOT, "lib", "richter_fit.lib")
SO = os.path.join(ROOT, "build", "keys", "max-richter.so")
DATA = os.path.join(REFS, "richter-piano.npz")
SELECTED = os.path.join(REFS, "richter", "selected.txt")
SR = F.SR
KEYS, DYNS, VEL = F.KEYS, F.DYNS, F.VEL
hz = F.hz
F.PARAMS, F.LIB, F.SO = PARAMS, LIB, SO


# ---------------------------------------------------------------- which notes

def select_mask():
    """The selected notes of richter-piano.npz, as a boolean mask (no printing)."""
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()):
        return select()


def select():
    """Tracks whose single notes are piano (stiff-string overtones like the Steinway's, and decaying), then notes."""
    d = np.load(DATA)
    tr, mid = d["track"], d["midi"]
    ratio = d["B"] / np.load(os.path.join(REFS, "piano-params.npz"))["B"][mid - 21]
    keep_tracks = []
    for t in sorted(set(tr)):
        m = (tr == t) & (d["nfound"] >= 7)
        dec = np.nanmedian(d["r1"][tr == t]) if np.isfinite(d["r1"][tr == t]).any() else np.nan
        if m.sum() >= 15 and 0.8 <= np.median(ratio[m]) <= 1.4 and not (dec > -3):
            keep_tracks.append(t)
    ok = np.isin(tr, keep_tracks) & (ratio > 0.5) & (ratio < 2.0) & ~(d["r1"] > -1)
    names = {}
    for line in open(os.path.join(REFS, "richter", "tracklist.txt")):
        a, n, b = line.strip().split("|"); names[f"{a}_{n[:2]}.wav"] = b.split(" - ", 1)[-1]
    with open(SELECTED, "w") as f:
        for t in keep_tracks:
            f.write(f"{t}\t{int((ok & (tr == t)).sum())}\t{names.get(t, '')}\n")
    print(f"{len(keep_tracks)} tracks, {int(ok.sum())} notes")
    for t in keep_tracks:
        print(f"  {t}  {int((ok & (tr == t)).sum()):4d}  {names.get(t, '')}")
    return ok


def reference():
    """Pooled per (key, dynamic): the recordings' notes within two keys (four if sparse), the dynamic being the
    note's loudness third within its register. Same fields as the Iowa measurements."""
    d = np.load(DATA)
    ok = select()
    midi = d["midi"][ok]; L = d["L"][ok]; Fp = d["Fp"][ok]; B = d["B"][ok]
    f0 = d["f0"][ok]
    peak = np.nanmax(L, axis=1)
    cents = 1200 * np.log2(f0 * np.sqrt(1 + B) / hz(midi))
    dyn = np.zeros(len(midi), int)
    for lo in range(21, 109, 12):
        sel = (midi >= lo) & (midi < lo + 12)
        if sel.sum() >= 6:
            q1, q2 = np.percentile(peak[sel], [33.3, 66.7])
            dyn[sel] = np.where(peak[sel] < q1, 0, np.where(peak[sel] < q2, 1, 2))
    # registers with too few notes borrow the thirds of the nearest band
    ref = {k: [] for k in ("midi", "dyn", "f0", "B", "nfound", "rms")}
    Ls, Fs = [], []
    counts = {}
    for k in KEYS:
        for dy in DYNS:
            for width in (2, 4):
                sel = (np.abs(midi - k) <= width) & (dyn == dy)
                if sel.sum() >= 3:
                    break
            if sel.sum() < 3:
                continue
            Lm = np.nanmedian(L[sel], axis=0); Fm = np.nanmedian(Fp[sel], axis=0)
            Bm = float(np.median(B[sel])); cm = float(np.median(cents[sel] - 0 * k))
            ref["midi"].append(k); ref["dyn"].append(dy); ref["B"].append(Bm); ref["nfound"].append(10)
            ref["f0"].append(hz(k) * 2 ** (cm / 1200) / np.sqrt(1 + Bm))
            ref["rms"].append(float(np.nanmax(Lm)))
            Ls.append(Lm); Fs.append(Fm); counts[(k, dy)] = int(sel.sum())
    out = {k: np.array(v) for k, v in ref.items()}
    out["L"] = np.array(Ls); out["Fp"] = np.array(Fs)
    nanw = np.full_like(out["L"], np.nan)
    out["R1"] = out["R2"] = out["I2"] = nanw
    out["count"] = np.array([counts[(m, dd)] for m, dd in zip(out["midi"], out["dyn"])])
    return out


# ---------------------------------------------------------------- the instrument, measured the same way

def render_one(args):
    k, dy = args
    with tempfile.NamedTemporaryFile(suffix=".f32") as f:
        subprocess.run([os.path.join(ROOT, "build", "render"), SO, f.name, f"{hz(k):.4f}", "0", "0.5", f"{VEL[dy]}", "1.2", "1.2"],
                       check=True, capture_output=True)
        x = np.fromfile(f.name, dtype=np.float32).astype(np.float64)
    m = np.concatenate([np.zeros(int(0.5 * SR)), x])
    D, df = RN.rise_spectrum(m, 0.5, 0.3)
    f0, B, found = RN.partials(D, df, k)
    L = np.full(N.NP, np.nan); Fp = np.full(N.NP, np.nan)
    scale = 2 / np.sum(np.hanning(int(0.3 * SR)))
    for n, fq, amp in found:
        L[n - 1] = 20 * np.log10(amp * scale + 1e-12); Fp[n - 1] = fq
    return dict(midi=k, dyn=dy, f0=f0, B=B, nfound=len(found), L=L, Fp=Fp, rms=float(np.nanmax(L)) if found else -120.0)


def measure_instrument(pairs):
    with Pool(14) as p:
        res = p.map(render_one, pairs)
    out = {k: np.array([r[k] for r in res]) for k in ("midi", "dyn", "f0", "B", "nfound", "rms")}
    out["L"] = np.stack([r["L"] for r in res]); out["Fp"] = np.stack([r["Fp"] for r in res])
    out["R1"] = out["R2"] = out["I2"] = np.full_like(out["L"], np.nan)
    return out


def rebuild():
    subprocess.run(["make", "-s", "build/keys/max-richter.so", "build/render"], cwd=ROOT, check=True)


# ---------------------------------------------------------------- the rounds

def init():
    shutil.copy(os.path.join(REFS, "piano-params.npz"), PARAMS)
    P = dict(np.load(PARAMS))
    F.write_lib(P)
    fix_header()
    print("started from the Steinway tables")


def fix_header():
    t = open(LIB).read().replace("// Piano, fitted to the University of Iowa single notes (Steinway B) by tools/fitting/piano/fit.py.",
                                 "// Max Richter piano: tables fitted to single notes in the Richter albums, from a start at the Steinway's,\n// by tools/fitting/piano/richter_fit.py.")
    open(LIB, "w").write(t)


def refit(rounds=4, levels_only=False):
    ref = reference()
    for rnd in range(rounds + 1):
        P = dict(np.load(PARAMS))
        rebuild()
        ins = measure_instrument([(k, d) for k in KEYS for d in DYNS])
        rows = F.compare(ref, ins)
        print(f"--- round {rnd}: {len(rows)} (key, dynamic) pairs")
        F.report(ref, ins, rows)
        if rnd == rounds:
            break
        by = lambda dy, fn, sigma=2, cap=None: np.clip(F.smooth_keys([np.nanmedian([fn(x) for x in rows if x["key"] == k and x["dyn"] == dy] or [np.nan])
                                         for k in KEYS], sigma=sigma), -cap if cap else -1e9, cap if cap else 1e9)
        mid = np.median([x["lvl"] for x in rows if 54 <= x["key"] <= 66 and x["dyn"] == 1])
        for dy, tag in zip(DYNS, ("PP", "MF", "FF")):
            P["lv" + tag] = P["lv" + tag] + 0.5 * (by(dy, lambda x: x["lvl"], 6, cap=15) - mid)

            def best_th(x, tag=tag):
                th0 = P["th" + tag][x["key"] - 21]
                f, dl, n = x["f"], x["dl"], x["n"]
                wt = 1 / np.sqrt(n)
                errs = []
                for t in F.TH_GRID:
                    r = dl - (F.hammer_db(f, t) - F.hammer_db(f, th0))
                    r = r - np.sum(wt * r) / wt.sum()
                    errs.append(np.sum(wt * r * r))
                return np.log10(F.TH_GRID[int(np.argmin(errs))] / th0)
            if not levels_only:
                P["th" + tag] = np.clip(P["th" + tag] * 10 ** (0.5 * np.nan_to_num(by(dy, best_th, 2, cap=0.5))), 0.12, 10)
        if levels_only:                                   # the loudness of every key, leaving the tone as it is
            np.savez(PARAMS, **P); F.write_lib(P); fix_header()
            print(f"round {rnd + 1} done (levels only)")
            continue
        P["thMF"] = np.minimum(P["thMF"], P["thPP"] * 0.97); P["thFF"] = np.minimum(P["thFF"], P["thMF"] * 0.97)
        grid, bd = P["bodyGrid"], P["bodyDb"]
        lg = np.log2(grid)
        Fq = np.concatenate([x["f"] for x in rows]); S = np.concatenate([x["shape"] for x in rows])
        b = np.clip(np.round((np.log2(Fq) - lg[0]) / (lg[1] - lg[0])).astype(int), 0, len(grid) - 1)
        acc = np.bincount(b, S, len(grid)); cnt = np.bincount(b, None, len(grid)).astype(float)
        kern = np.exp(-0.5 * (np.arange(-8, 9) / 2.0) ** 2)
        num = np.convolve(acc, kern, "same"); den = np.convolve(cnt, kern, "same")
        good = den > 3
        corr = np.interp(lg, lg[good], num[good] / den[good])
        sel = (grid > 100) & (grid < 6000)
        corr -= np.polyval(np.polyfit(lg[sel], corr[sel], 1), lg)
        P["bodyDb"] = np.clip(bd + 0.7 * corr, -25, 15)
        dc = by(1, lambda x: 1200 * np.log2(ref["f0"][x["r"]] * np.sqrt(1 + ref["B"][x["r"]]) / (ins["f0"][x["i"]] * np.sqrt(1 + ins["B"][x["i"]]))), 3, cap=15)
        P["stretch"] = P["stretch"] + 0.8 * np.nan_to_num(dc)
        dB = by(1, lambda x: np.log10(ref["B"][x["r"]] / ins["B"][x["i"]]) if ref["B"][x["r"]] > 0 and ins["B"][x["i"]] > 0 else np.nan, 3, cap=0.5)
        P["B"] = P["B"] * 10 ** (0.7 * np.nan_to_num(dB))
        for i, k in enumerate(KEYS):
            err, M, a = F.fit_dispersion(hz(k) * 2 ** (P["stretch"][i] / 1200), P["B"][i])
            P["apM"][i], P["apA"][i], P["apErr"][i] = M, a, err
        np.savez(PARAMS, **P)
        F.write_lib(P); fix_header()
        print(f"round {rnd + 1} done")


def anchor():
    """Where few Richter notes support a key, trust the Steinway's tables: tuning, stiffness and hammer are blended
    key by key, the weight being the number of selected notes within four keys over ten (1 = all Richter's).
    Without this the sparse top and bottom octaves drifted (stiffness 26 times too high, 57 cents flat at C8)."""
    d = np.load(DATA)
    ok = select_mask()
    midi = d["midi"][ok]
    S = dict(np.load(os.path.join(REFS, "piano-params.npz")))
    P = dict(np.load(PARAMS))
    w = np.array([min(1.0, np.sum(np.abs(midi - k) <= 4) / 10) for k in KEYS])
    P["stretch"] = w * P["stretch"] + (1 - w) * S["stretch"]
    P["B"] = 10 ** (w * np.log10(P["B"]) + (1 - w) * np.log10(S["B"]))
    for tag in ("thPP", "thMF", "thFF"):
        P[tag] = np.exp(w * np.log(P[tag]) + (1 - w) * np.log(S[tag]))
    for i, k in enumerate(KEYS):
        err, M, a = F.fit_dispersion(hz(k) * 2 ** (P["stretch"][i] / 1200), P["B"][i])
        P["apM"][i], P["apA"][i], P["apErr"][i] = M, a, err
    np.savez(PARAMS, **P); F.write_lib(P); fix_header()
    print("anchored; weight at keys 24, 36, 48, 60, 72, 84, 96, 108:", ", ".join(f"{w[k - 21]:.1f}" for k in (24, 36, 48, 60, 72, 84, 96, 108)))


def rms_one(args):
    so, k, dy = args
    with tempfile.NamedTemporaryFile(suffix=".f32") as f:
        subprocess.run([os.path.join(ROOT, "build", "render"), so, f.name, f"{hz(k):.4f}", "0", "0.5", f"{VEL[dy]}", "1.5", "1.5"],
                       check=True, capture_output=True, env=dict(os.environ, RENDER_STEREO="1"))
        x = np.fromfile(f.name, dtype=np.float32).reshape(-1, 2)
    return 10 * np.log10(np.mean(x[:int(0.5 * SR)] ** 2) * 2 + 1e-24)      # both ears' power


def level(rounds=3):
    """Make every key as loud as the Steinway's at the same velocity (the first half second, mono). The recordings'
    own balance across the keyboard is a performer's phrasing, the room and the pedal, not the instrument's: matched
    to it, the top octave was unplayably quiet. What stays Richter's is the tone and how it brightens with touch."""
    jobs = [(os.path.join(ROOT, "build", "keys", "piano.so"), k, d) for k in KEYS for d in DYNS]
    with Pool(14) as p:
        target = np.array(p.map(rms_one, jobs)).reshape(len(KEYS), len(DYNS))
    for rnd in range(rounds + 1):
        rebuild()
        with Pool(14) as p:
            mine = np.array(p.map(rms_one, [(SO, k, d) for k in KEYS for d in DYNS])).reshape(len(KEYS), len(DYNS))
        diff = target - mine
        print(f"round {rnd}: Steinway minus Richter, dB: mean {diff.mean():+.2f}, worst {np.abs(diff).max():.1f}")
        if rnd == rounds:
            break
        P = dict(np.load(PARAMS))
        for j, tag in enumerate(("PP", "MF", "FF")):
            P["lv" + tag] = P["lv" + tag] + F.smooth_keys(diff[:, j], sigma=1.5)
        np.savez(PARAMS, **P); F.write_lib(P); fix_header()


def report():
    ref = reference()
    rebuild()
    ins = measure_instrument([(k, d) for k in KEYS for d in DYNS])
    F.report(ref, ins, F.compare(ref, ins))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    if cmd == "select":
        select()
    elif cmd == "init":
        init()
    elif cmd == "anchor":
        anchor()
    elif cmd == "level":
        level()
    elif cmd == "refit":
        refit(int(sys.argv[2]) if len(sys.argv) > 2 else 4, "levels" in sys.argv)
    else:
        report()
