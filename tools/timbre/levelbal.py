"""Loudness balance across the range: the player's median level per pitch band (from all the
reference recordings) against the instrument's level at pressure 0.6. Prints the correction
(dB at log-spaced pitches) for the instrument's levelPoints / levelDb settings.
   python levelbal.py violin [--dsp ...]"""
import os, sys, numpy as np
import synth as S, evaluate as E

def main(inst, dsp=None, pressure=0.6):
    c = E.CFG[inst]
    d = np.load(os.path.join(E.ROOT, "refs", c["who"] + ".npz"))
    lo, hi = (196, 1760) if inst == "violin" else (65.4, 700)
    pts = np.geomspace(lo, hi, 8)
    so = S.build(os.path.join(E.ROOT, dsp or c["dsp"]))
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
    tgt = np.where(np.isfinite(tgt), tgt, np.interp(np.arange(len(tgt)), np.nonzero(np.isfinite(tgt))[0], tgt[np.isfinite(tgt)]))
    corr = (tgt - tgt.mean()) - (ins - ins.mean())
    corr = np.clip(corr, -10, 10)
    for f, a, b, cc in zip(pts, tgt, ins, corr):
        print(f"  {f:7.1f} Hz  player {a - tgt.mean():+5.1f}  instrument {b - ins.mean():+5.1f}  -> correction {cc:+5.1f} dB")
    print("levelPoints = (" + ", ".join(f"{f:.1f}" for f in pts) + ");")
    print("levelDb = (" + ", ".join(f"{v:.1f}" for v in corr) + ");")
    return pts, corr


def apply(inst, pts, corr):
    """Add the correction to the levelDb already in the instrument file (or create the setting)."""
    import re
    path = os.path.join(E.ROOT, E.CFG[inst]["dsp"])
    src = open(path).read()
    m_p = re.search(r"levelPoints = \(([^)]*)\);", src); m_d = re.search(r"levelDb = \(([^)]*)\);", src)
    if m_p and m_d:
        old_p = np.array([float(v) for v in m_p.group(1).split(",")]); old_d = np.array([float(v) for v in m_d.group(1).split(",")])
        base = np.interp(np.log2(pts), np.log2(old_p), old_d)
        new = np.clip(base + 0.9 * corr, -15, 15)
        src = src.replace(m_p.group(0), "levelPoints = (" + ", ".join(f"{f:.1f}" for f in pts) + ");")
        src = src.replace(m_d.group(0), "levelDb = (" + ", ".join(f"{v:.1f}" for v in new) + ");")
    else:
        new = 0.9 * corr
        src = src.replace("    outGain =", "    levelPoints = (" + ", ".join(f"{f:.1f}" for f in pts) + ");\n"
                          "    levelDb = (" + ", ".join(f"{v:.1f}" for v in new) + ");     // tools/timbre/levelbal.py\n    outGain =", 1)
    open(path, "w").write(src)
    print("updated", path)

if __name__ == "__main__":
    a = sys.argv
    pts, corr = main(a[1], os.path.join("tools", "timbre", a[a.index("--dsp") + 1]) if "--dsp" in a else None)
    if "--apply" in a:
        apply(a[1], pts, corr)
