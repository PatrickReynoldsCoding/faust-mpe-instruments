"""Play an instrument across a grid of pitch x pressure x slide and list notes that
are not in tune (wrong mode, missing fundamental, or more than 30 cents off).
   python3 tools/grid.py strings/violin 196,262,330,440,523,698,880
"""
import os, subprocess, sys, tempfile
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pitch import cents_off, SR
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def render(so, f, p, s):
    with tempfile.NamedTemporaryFile(suffix=".f32") as t:
        subprocess.run([os.path.join(ROOT, "build/render"), so, t.name, str(f), str(p), str(s), "0.7", "1.5", "2"], check=True, capture_output=True)
        return np.fromfile(t.name, dtype=np.float32)[int(0.6 * SR):int(1.4 * SR)]

so = os.path.join(ROOT, "build", sys.argv[1] + ".so")
freqs = [float(v) for v in sys.argv[2].split(",")]
ps, ss = [0.0, 0.3, 0.6, 1.0], [0.0, 0.5, 1.0]
bad, total = [], 0
for f in freqs:
    for p in ps:
        for s in ss:
            x = render(so, f, p, s); total += 1
            if np.sqrt(np.mean(x ** 2)) < 0.003: bad.append(f"{f:g}Hz p{p} s{s}: silent"); continue
            c = cents_off(x, f)
            if abs(c) > 30: bad.append(f"{f:g}Hz p{p} s{s}: {c:+.0f}c")
print(f"{sys.argv[1]}: {len(bad)} bad of {total}")
for b in bad: print("  ", b)
