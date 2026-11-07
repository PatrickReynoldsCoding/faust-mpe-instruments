import os, sys, subprocess, tempfile
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_pitch import cents, SR, ROOT
def render(f, vel, press, pos):
    with tempfile.NamedTemporaryFile(suffix=".f32") as t:
        subprocess.run([os.path.join(ROOT, "build/render"), os.path.join(ROOT, "build-lab/lab.so"), t.name, str(f), "0", "0", "0", "1.5", "1.8",
                        f"vel={vel}", f"press={press}", f"pos={pos}"], check=True, capture_output=True)
        return np.fromfile(t.name, dtype=np.float32)[int(0.6*SR):int(1.4*SR)]
freqs = [float(v) for v in sys.argv[1].split(",")]
pos = float(sys.argv[2]) if len(sys.argv) > 2 else 0.15
vels = [0.1, 0.2, 0.3, 0.45, 0.6, 0.8]
presses = [0.1, 0.3, 0.5, 0.7, 0.9]
print(f"bow position {pos}.  columns = bow speed {vels};  rows = bow force.   . ok   X wrong note   s silent")
for f in freqs:
    print(f"\n{f:g} Hz")
    for p in presses:
        row = ""
        for v in vels:
            x = render(f, v, p, pos)
            if np.sqrt(np.mean(x**2)) < 0.01: row += "  s"; continue
            row += "  ." if abs(cents(x, f)) < 30 else "  X"
        print(f"  force {p:<4g}{row}")
