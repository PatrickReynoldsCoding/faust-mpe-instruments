"""The strings fitted to ROLI's Seaboard demos (SWAM viola and cello), using the strings fitting
tools in tools/fitting/timbre/ unchanged: this module only tells them about the new players and
instruments, then runs the same steps.

References (git-ignored, never committed): refs/swam-viola/blockm-viola.wav and
refs/swam-cello/blockm-cello.wav, the solo clips of the BLOCK M video trimmed to the playing
(see refs/roli-seaboard/SOURCES.md).

   python swam.py stats viola|cello         measure the clips (refstats) and cut passages
   python swam.py body viola|cello [--correct]   first body fit (or with the correction)
   python swam.py eval viola|cello [--wav] [--correction] [name=value ...]
   python swam.py round viola|cello [n]     n rounds of evaluate --correction + body --apply-diff
   python swam.py level viola|cello [--apply]  loudness balance across the range
   python swam.py vib viola|cello           the player's vibrato
   python swam.py reg viola|cello [pressure=0.5]   brightness by register"""
import os, sys, pickle, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "fitting", "timbre"))
import analysis as A, perform as P, synth as S, evaluate as E, makebody as MB, body

# who: refs/<who>/; inst names are kept apart from the old violin/cello fits (their files in refs/).
CFG = {
    "viola": dict(who="swam-viola", fmin=250, fmax=1500, dsp="instruments/strings/viola.dsp", env=(130, 9000),
                  cal=(131, 220, 330, 523, 880), lo=120, poles=(42, 30, 14), out="viola_body.lib",
                  level=(130.8, 1047), bands=[120, 200, 290, 400, 550, 750, 1050]),
    "cello": dict(who="swam-cello", fmin=60, fmax=900, dsp="instruments/strings/cello.dsp", env=(70, 8000),
                  cal=(65.4, 110, 196, 330, 523), lo=60, poles=(54, 24, 12), out="cello_body.lib",
                  level=(65.4, 700), bands=[60, 85, 120, 170, 240, 340, 480]),
}
KEY = {"viola": "swam-viola", "cello": "swam-cello"}     # name used by the timbre tools (refs/<name>-*.npz)

def register():
    for inst, c in CFG.items():
        k = KEY[inst]
        E.CFG[k] = dict(who=c["who"], fmin=c["fmin"], fmax=c["fmax"], dsp=c["dsp"], env=c["env"], cal=c["cal"])
        MB.CFG[k] = dict(who=c["who"], lo=c["lo"], poles=c["poles"])
register()

def lib_response(path, f):
    """Magnitude (dB) of a body made by makebody.py (parallel fi.tf2 sections plus a gain)."""
    import re, bodyfit as BF
    secs, fir = [], 0.0
    for l in open(path):
        m = re.search(r"fi.tf2\(([^)]*)\)", l)
        if m:
            v = [float(a) for a in m.group(1).split(",")]; secs.append((v[0], v[1], v[3], v[4]))
        m = re.search(r"^\s*\*\(([-0-9.e]+)\)", l)
        if m: fir = float(m.group(1))
    return 20 * np.log10(np.abs(BF.response(secs, [fir], f)) + 1e-12)

_target = MB.target
def target(inst):
    """The viola clips only go down to D4, so below about 300 Hz there is nothing to fit: there the
    viola takes the shape of the fitted violin body (lib/body_violin.lib), its modes scaled down by
    the viola's larger size (x0.85: the A0 air mode near 230 Hz instead of 275), joined smoothly."""
    g, B = _target(inst)
    if inst == "swam-viola":
        vs = lib_response(os.path.join(ROOT, "lib", "body_violin.lib"), g / 0.85)
        a = (g > 300) & (g < 420)
        vs = vs + (B[a].mean() - vs[a].mean())
        w = np.clip((np.log2(g) - np.log2(260)) / np.log2(320 / 260), 0, 1)
        B = w * B + (1 - w) * vs
    return g, B
MB.target = target

def stats(inst):
    c = CFG[inst]; who = c["who"]
    allf0, allH, allN, alldb, allfile, out = [], [], [], [], [], {}
    files = sorted(f for f in os.listdir(os.path.join(ROOT, "refs", who)) if f.endswith(".wav"))
    for n, f in enumerate(files):
        r = A.analyse_file(os.path.join(ROOT, "refs", who, f), c["fmin"], c["fmax"], every=1)
        db = 20 * np.log10(r["rms"] + 1e-12)
        print(f"{f:28s} frames {len(r['t'])}  voiced {r['mask'].mean():.2f}  analysed {len(r['idx'])}")
        allf0.append(r["f0"][r["idx"]]); allH.append(r["H"]); allN.append(r["N"]); alldb.append(db[r["idx"]])
        allfile.append(np.full(len(r["idx"]), n)); out[f"track_{n}"] = np.stack([r["t"], r["f0"], r["per"], r["rms"]])
        del r
    np.savez_compressed(os.path.join(ROOT, "refs", who + ".npz"), f0=np.concatenate(allf0), H=np.concatenate(allH),
                        N=np.concatenate(allN), db=np.concatenate(alldb), fileno=np.concatenate(allfile), **out)
    # passages: the clips are short, so cut them into overlapping 6 s windows (passages.py uses 15 s)
    win, ps = 6.0, []
    for f in files:
        x = A.load(os.path.join(ROOT, "refs", who, f))
        for a in sorted(set(list(np.arange(0, len(x) / A.SR - win + 0.01, 3.0)) + [len(x) / A.SR - win])):
            seg = x[int(a * A.SR):int((a + win) * A.SR)]
            notes, _ = P.notes_from(seg, c["fmin"], c["fmax"], min_per=0.75)
            cover = sum(n["end"] - n["start"] for n in notes) / win
            ps.append(dict(file=f[:-4], start=float(a), dur=win, cover=cover, notes=notes))
            print(f"  passage {f[:-4]} {a:5.1f}s  coverage {cover:.2f}  notes {len(notes)}")
    pickle.dump(ps, open(os.path.join(ROOT, "refs", f"{who}-passages.pkl"), "wb"))

def levelbal(inst, apply=False, pressure=0.5):
    """As timbre/levelbal.py, over this instrument's range."""
    import re
    c = CFG[inst]
    d = np.load(os.path.join(ROOT, "refs", c["who"] + ".npz"))
    pts = np.geomspace(*c["level"], 8)
    so = S.build(os.path.join(ROOT, c["dsp"]))
    tgt, ins = [], []
    for f in pts:
        m = (d["f0"] > f / 2 ** (1 / 6)) & (d["f0"] < f * 2 ** (1 / 6))
        tgt.append(np.median(d["db"][m]) if m.sum() > 50 else np.nan)
        lv = []
        for ff in (f / 2 ** (1 / 12), f, f * 2 ** (1 / 12)):
            x = S.note(so, ff, pressure, 0.5, 0.5, hold=1.5, total=1.5)
            lv.append(20 * np.log10(np.sqrt(np.mean(x[36000:] ** 2))))
        ins.append(np.mean(lv))
    tgt, ins = np.array(tgt), np.array(ins)
    ok = np.isfinite(tgt)
    # where the player never went, ask for an even level (no data, no correction to the shape)
    tgt = np.where(ok, tgt, np.nan)
    corr = (tgt - np.nanmean(tgt)) - (ins - ins[ok].mean())
    corr = np.where(ok, corr, np.nan)
    if (~ok).any():
        first, last = np.nonzero(ok)[0][[0, -1]]
        corr[:first] = corr[first]; corr[last + 1:] = corr[last]
        # outside the recorded notes keep the instrument's own balance relative to the ends
        corr[:first] = -(ins[:first] - ins[first]) + corr[first] * 0 + corr[first]
        corr[last + 1:] = -(ins[last + 1:] - ins[last]) + corr[last]
    corr = np.clip(corr, -10, 10)
    for f, a, b, cc in zip(pts, tgt, ins, corr):
        print(f"  {f:7.1f} Hz  player {a - np.nanmean(tgt):+5.1f}  instrument {b - ins.mean():+5.1f}  -> correction {cc:+5.1f} dB")
    if apply:
        path = os.path.join(ROOT, c["dsp"]); src = open(path).read()
        m_p = re.search(r"levelPoints = \(([^)]*)\);", src); m_d = re.search(r"levelDb = \(([^)]*)\);", src)
        old_p = np.array([float(v) for v in m_p.group(1).split(",")]); old_d = np.array([float(v) for v in m_d.group(1).split(",")])
        new = np.clip(np.interp(np.log2(pts), np.log2(old_p), old_d) + 0.9 * corr, -15, 15)
        new -= new.mean()
        src = src.replace(m_p.group(0), "levelPoints = (" + ", ".join(f"{f:.1f}" for f in pts) + ");")
        src = src.replace(m_d.group(0), "levelDb = (" + ", ".join(f"{v:.1f}" for v in new) + ");")
        open(path, "w").write(src); print("updated", path)

def vib(inst):
    ps = pickle.load(open(os.path.join(ROOT, "refs", f"{CFG[inst]['who']}-passages.pkl"), "rb"))
    rates, ext, onset = [], [], []
    seen = set()
    for p in ps:
        for n in p["notes"]:
            key = round(p["start"] + n["start"], 1)
            if n["end"] - n["start"] < 0.5 or key in seen: continue
            seen.add(key)
            c = 1200 * np.log2(n["hz"] / np.median(n["hz"])); fs = A.SR / A.HOP
            v = c - np.convolve(np.pad(c, 25, mode="edge"), np.ones(51) / 51, "valid")
            z = np.nonzero((v[:-1] < 0) & (v[1:] >= 0))[0]
            if len(z) < 3: continue
            per = np.diff(z) / fs; ok = (per > 1 / 9) & (per < 1 / 3.5)
            if ok.sum() < 2: continue
            amps = [0.5 * (v[a:b].max() - v[a:b].min()) for a, b in zip(z[:-1], z[1:])]
            rates.append(1 / np.median(per[ok])); ext.append(np.median(amps))
            env = np.array(amps); h = np.nonzero(env > 0.5 * env.max())[0]
            onset.append(z[h[0]] / fs if len(h) else np.nan)
            print(f"   note {key:5.1f}s {np.median(n['hz']):6.1f} Hz {n['end'] - n['start']:.2f}s  rate {rates[-1]:.2f}  extent {ext[-1]:5.1f} c  onset {onset[-1]:.2f}")
    q = lambda v: f"median {np.nanmedian(v):.2f} (quartiles {np.nanpercentile(v, 25):.2f}-{np.nanpercentile(v, 75):.2f})"
    print(f"{inst}: {len(rates)} long notes\n  rate {q(rates)}\n  extent {q(ext)}\n  onset {q(onset)}")

def reg(inst, extra):
    import regprofile as RP
    RP.BANDS[KEY[inst]] = CFG[inst]["bands"]
    p = extra.pop("pressure", 0.5)
    so = S.build(os.path.join(ROOT, CFG[inst]["dsp"]))
    T = RP.target_profiles(KEY[inst]); I = RP.inst_profiles(so, KEY[inst], extra, p)
    D = I - T; b = CFG[inst]["bands"]
    print("instrument - recording (dB), harmonics 1..12 | 13-20 mean;  rms")
    for i in range(len(b) - 1):
        print(f"  {b[i]:4d}-{b[i+1]:4d}: " + " ".join(f"{v:+5.1f}" for v in D[i, :12]) + f" | {np.nanmean(D[i, 12:20]):+5.1f}   {np.sqrt(np.nanmean(D[i] ** 2)):4.1f}")
    print(f"  overall rms {np.sqrt(np.nanmean(D ** 2)):.2f} dB")

if __name__ == "__main__":
    cmd, inst = sys.argv[1], sys.argv[2]
    args = sys.argv[3:]
    extra = dict((a.split("=")[0], float(a.split("=")[1])) for a in args if "=" in a)
    os.chdir(os.path.join(ROOT, "tools", "fitting", "timbre"))
    if cmd == "stats": stats(inst)
    elif cmd == "body":
        MB.main(KEY[inst], "--correct" in args, out_name=CFG[inst]["out"])
    elif cmd == "eval":
        E.run(KEY[inst], None, extra, wav="--wav" in args, correction="--correction" in args)
    elif cmd == "round":
        n = int(args[0]) if args and "=" not in args[0] else 2
        for i in range(n):
            E.run(KEY[inst], None, extra, correction=True)
            MB.apply_diff(KEY[inst]); MB.main(KEY[inst], True, out_name=CFG[inst]["out"])
        E.run(KEY[inst], None, extra)
    elif cmd == "level": levelbal(inst, "--apply" in args)
    elif cmd == "vib": vib(inst)
    elif cmd == "reg": reg(inst, extra)
