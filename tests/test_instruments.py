"""Checks every compiled instrument by rendering notes offline.

An instrument may declare, in its .dsp:
    declare range   "lo hi";   playable range in Hz (default "130 520")
    declare pitched "no";      skip the pitch check (noisy or inharmonic sounds)
    declare ringout "6";       seconds it may keep ringing after release (default 3)

Run:  python3 tests/test_instruments.py [name-filter]
"""
import glob, os, re, subprocess, sys, tempfile
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))
from pitch import cents_off

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RENDER = os.path.join(ROOT, "build", "render")
SR = 48000


def declared(dsp_path):
    src = open(dsp_path).read()
    return {k: v for k, v in re.findall(r'declare\s+(\w+)\s+"([^"]*)"', src)}


def render(so, freq, pressure, slide, velocity, hold, total):
    with tempfile.NamedTemporaryFile(suffix=".f32") as f:
        subprocess.run([RENDER, so, f.name, str(freq), str(pressure), str(slide), str(velocity),
                        str(hold), str(total)], check=True, capture_output=True)
        return np.fromfile(f.name, dtype=np.float32)


def rms(x):
    return float(np.sqrt(np.mean(x ** 2))) if len(x) else 0.0


failures, rows = [], []


def check(inst, label, ok, detail):
    rows.append((inst, label, ok, detail))
    if not ok:
        failures.append(f"{inst}: {label}: {detail}")


def test_instrument(dsp_path, so):
    inst = os.path.relpath(so, os.path.join(ROOT, "build"))[:-3]
    meta = declared(dsp_path)
    lo, hi = (float(v) for v in meta.get("range", "130 520").split())
    ringout = float(meta.get("ringout", 3))
    win_lo, win_hi = (float(v) for v in meta.get("window", "0.6 1.4").split())   # where a note is judged
    pitched = meta.get("pitched", "yes") != "no"
    hold = 1.5
    total = hold + ringout + 0.5

    notes = [lo, (lo * hi) ** 0.5, hi]
    for f in notes:
        x = render(so, f, 0.7, 0.5, 0.7, hold, total)
        if not np.isfinite(x).all():
            check(inst, f"{f:.0f} Hz finite", False, "NaN or Inf in output"); continue
        peak = float(np.abs(x).max())
        held = x[int(win_lo * SR):int(win_hi * SR)]
        tail = x[-int(0.3 * SR):]
        check(inst, f"{f:.0f} Hz not too loud", peak <= 1.5, f"peak {peak:.2f}")
        check(inst, f"{f:.0f} Hz audible", rms(held) > 0.005, f"rms while held {rms(held):.4f}")
        check(inst, f"{f:.0f} Hz stops", rms(tail) < max(0.005, 0.05 * rms(held)),
              f"rms in last 0.3 s {rms(tail):.4f} vs {rms(held):.4f} while held")
        if pitched and rms(held) > 0.005:
            cents = cents_off(held, f)
            check(inst, f"{f:.0f} Hz in tune", abs(cents) <= 30, f"{cents:+.0f} cents off")

    mid = notes[1]
    for p in (0.0, 1.0):
        for s in (0.0, 1.0):
            x = render(so, mid, p, s, 0.7, hold, hold + 1.0)
            ok = np.isfinite(x).all() and float(np.abs(x).max()) <= 2.0
            check(inst, f"touch extremes p={p:.0f} s={s:.0f}", ok,
                  "NaN" if not np.isfinite(x).all() else f"peak {np.abs(x).max():.2f}")


def main():
    want = sys.argv[1] if len(sys.argv) > 1 else ""
    if not os.path.exists(RENDER):
        sys.exit("build/render missing: run `make` first")
    found = 0
    for dsp_path in sorted(glob.glob(os.path.join(ROOT, "instruments", "*", "*.dsp"))):
        so = dsp_path.replace(os.path.join(ROOT, "instruments"), os.path.join(ROOT, "build"))[:-4] + ".so"
        if want not in dsp_path:
            continue
        if not os.path.exists(so):
            failures.append(f"{dsp_path}: not built"); continue
        found += 1
        test_instrument(dsp_path, so)

    by = {}
    for inst, label, ok, detail in rows:
        by.setdefault(inst, []).append((label, ok, detail))
    for inst, rs in by.items():
        bad = [r for r in rs if not r[1]]
        print(f"{'PASS' if not bad else 'FAIL'}  {inst}  ({len(rs) - len(bad)}/{len(rs)})")
        for label, _, detail in bad:
            print(f"        - {label}: {detail}")
    print(f"\n{found} instruments, {len(failures)} failed checks")
    sys.exit(1 if failures else 0)


main()
