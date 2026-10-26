"""Show what an instrument does on one note: loudness over time and strongest partials.
   python3 tools/inspect_note.py winds/flute 440 [pressure=0.7] [slide=0.5] [velocity=0.7] [hold=1.5]
"""
import os, subprocess, sys, tempfile
import numpy as np
SR = 48000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
inst, freq = sys.argv[1], float(sys.argv[2])
p, s, v, hold = (float(a) for a in (sys.argv[3:7] + ["0.7", "0.5", "0.7", "1.5"][len(sys.argv[3:7]):]))
with tempfile.NamedTemporaryFile(suffix=".f32") as t:
    subprocess.run([os.path.join(ROOT, "build/render"), os.path.join(ROOT, "build", inst + ".so"), t.name,
                    str(freq), str(p), str(s), str(v), str(hold), str(hold + 2)], check=True, capture_output=True)
    x = np.fromfile(t.name, dtype=np.float32)
print(f"{inst} at {freq:g} Hz  (pressure {p}, slide {s}, velocity {v}, held {hold}s)   peak {np.abs(x).max():.3f}   finite {np.isfinite(x).all()}")
print("loudness (rms) per 0.25 s:  " + " ".join(f"{np.sqrt(np.mean(x[int(i*SR*.25):int((i+1)*SR*.25)]**2)):.4f}" for i in range(int(len(x)/SR/.25))))
seg = x[int(0.3*SR):int(min(1.3, hold-0.1)*SR)]
sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), len(seg) * 4)); fr = np.fft.rfftfreq(len(seg) * 4, 1 / SR)
pk = [i for i in range(2, len(sp) - 2) if sp[i] > sp[i-1] and sp[i] > sp[i+1] and fr[i] < 5000]
top = sorted(pk, key=lambda i: -sp[i])[:8]
if top:
    print("strongest partials (Hz: level, as multiple of target):  " + "  ".join(f"{fr[i]:.0f}:{sp[i]/sp[top[0]]:.2f} (x{fr[i]/freq:.2f})" for i in sorted(top)))
