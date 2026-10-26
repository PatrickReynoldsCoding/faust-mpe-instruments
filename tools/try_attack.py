"""Rebuild the cello with different bow attack times and count wrong-mode notes."""
import os, re, subprocess, sys, tempfile
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pitch import cents_off, SR
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(ROOT, "instruments/strings/cello.dsp")).read()

def build(attack, posrange):
    dsp = re.sub(r"0\.09,\s*0\.15\);", f"{attack}, 0.15);", src)
    dsp = dsp.replace("0.08, 0.22,", f"0.08, {posrange},")
    d = os.path.join(ROOT, "build-lab"); base = os.path.join(d, f"cello_a{attack}_r{posrange}")
    open(base + ".dsp", "w").write(dsp)
    subprocess.run(["faust", "-I", os.path.join(ROOT, "lib"), "-lang", "cpp", "-i", "-cn", "Instrument", "-o", base + ".cpp", base + ".dsp"], check=True, capture_output=True)
    subprocess.run(["g++", "-O2", "-std=c++17", "-w", "-shared", "-fPIC", f'-DGEN="{base}.cpp"', "-o", base + ".so", os.path.join(ROOT, "src/entry.cpp")], check=True, capture_output=True)
    return base + ".so"

def render(so, f, p, s):
    with tempfile.NamedTemporaryFile(suffix=".f32") as t:
        subprocess.run([os.path.join(ROOT, "build/render"), so, t.name, str(f), str(p), str(s), "0.7", "1.5", "2"], check=True, capture_output=True)
        return np.fromfile(t.name, dtype=np.float32)[int(0.6 * SR):int(1.4 * SR)]

freqs = [65, 82, 98, 130, 165, 196, 262, 330, 440, 523]
ps, ss = [0.0, 0.3, 0.6, 1.0], [0.0, 0.5, 1.0]
for attack, posrange in [tuple(float(v) for v in pair.split(":")) for pair in sys.argv[1].split(",")]:
    so = build(attack, posrange)
    bad = []
    for f in freqs:
        for p in ps:
            for s in ss:
                x = render(so, f, p, s)
                if np.sqrt(np.mean(x ** 2)) < 0.003: continue
                c = cents_off(x, f)
                if abs(c) > 30: bad.append((f, p, s, round(c)))
    print(f"attack {attack:5.3f} s, bow pos range {posrange:4.2f} (max {0.08+posrange:.2f}): {len(bad):2d} bad of {len(freqs)*len(ps)*len(ss)}   " + " ".join(f"{f}Hz/p{p}/s{s}" for f, p, s, c in bad[:12]), flush=True)
