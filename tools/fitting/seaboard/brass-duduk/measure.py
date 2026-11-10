"""Measure a solo line (the trumpet clip, or a render): f0, level and harmonics 1..40 per voiced frame.
   python measure.py in.wav out.npz fmin fmax"""
# measure harmonic levels per voiced frame of a mono line: f0, level, H (k=1..40), N
import sys, numpy as np
import os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'fitting', 'timbre'))
import analysis as A
src, out, fmin, fmax = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
x = A.load(src)
t, f0, per, rms = A.track_f0(x, fmin, fmax)
m = A.voiced_mask(f0, per, rms, fmin, fmax, min_per=0.9, min_db=-30)
# stable pitch: within 30 cents of neighbours
c = 1200*np.log2(np.maximum(f0,1))
st = np.zeros_like(m)
st[2:-2] = (np.abs(c[2:-2]-c[:-4])<30)&(np.abs(c[2:-2]-c[4:])<30)
m &= st
idx, H, N = A.harmonics(x, t, f0, m, kmax=40, fmax=16000, periods=6)
np.savez(out, t=t, f0=f0, per=per, rms=rms, mask=m, idx=idx, H=H, N=N)
print('voiced frames', m.sum(), 'of', len(m))
