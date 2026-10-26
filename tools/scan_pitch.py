"""Map where an instrument plays in tune across pitch, pressure and slide.
   python3 tools/scan_pitch.py strings/cello 65,98,130,196,262,330 "0.2,0.5,0.8" "0.2,0.5,0.8"
Prints cents error per (pressure, slide) for each pitch. '--' = octave or worse off."""
import os, sys, subprocess, tempfile
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
SR = 48000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def render(so, f, p, s, v=0.7, hold=1.5, total=2.0):
    with tempfile.NamedTemporaryFile(suffix=".f32") as t:
        subprocess.run([os.path.join(ROOT, "build/render"), so, t.name, str(f), str(p), str(s), str(v), str(hold), str(total)],
                       check=True, capture_output=True)
        return np.fromfile(t.name, dtype=np.float32)

from pitch import cents_off as cents

if __name__ == "__main__":
    inst = sys.argv[1]
    freqs = [float(v) for v in sys.argv[2].split(",")]
    ps = [float(v) for v in (sys.argv[3] if len(sys.argv) > 3 else "0.2,0.5,0.8").split(",")]
    ss = [float(v) for v in (sys.argv[4] if len(sys.argv) > 4 else "0.2,0.5,0.8").split(",")]
    so = os.path.join(ROOT, "build", inst + ".so")
    print("cents error;  rows = pressure, columns = slide;  '--' = octave or worse off, 'sil' = silent")
    for f in freqs:
        print(f"\n{f:g} Hz        " + "".join(f"s={s:<5g}" for s in ss))
        for p in ps:
            row = []
            for s in ss:
                x = render(so, f, p, s)[int(0.6 * SR):int(1.4 * SR)]
                if np.sqrt(np.mean(x ** 2)) < 0.003: row.append("sil"); continue
                c = cents(x, f)
                row.append("--" if abs(c) > 100 else f"{c:+.0f}")
            print(f"  p={p:<4g}        " + "".join(f"{r:<7}" for r in row))
