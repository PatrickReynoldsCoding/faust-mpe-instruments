"""Compare a render with the reference: python compare.py ref.npz render.npz ref.wav render.wav"""
# Compare two measured frame sets (ref, render): harmonic levels (rel. to frame total) by loudness
# tercile, and long-term third-octave spectra of the two wavs (normalised).
import sys, numpy as np, soundfile as sf, scipy.signal as ss
a, b, wa, wb = sys.argv[1:5]
def load(p):
    d=np.load(p); 
    if 'idx' in d: i=d['idx']; f0=d['f0'][i]; H=d['H']
    else: f0=d['f0']; H=d['H']
    tot=10*np.log10(np.nansum(10**(H/10),1)); return f0, H-tot[:,None], tot
errs=[]
A=load(a); B=load(b)
print('loud  k:  ' + ' '.join('%4d'%k for k in range(1,17)))
for name, q in [('soft',(0,33)),('mid',(33,66)),('loud',(66,100))]:
    rows=[]
    for f0,Hr,tot in (A,B):
        lo,hi=np.percentile(tot[np.isfinite(tot)],q); s=(tot>=lo)&(tot<=hi)
        rows.append(np.nanmedian(Hr[s],0)[:16])
    e=rows[1]-rows[0]; errs.append(e)
    print(f'{name:4s} ref ', ' '.join('%4.0f'%v for v in rows[0])); print(f'{name:4s} ren ', ' '.join('%4.0f'%v for v in rows[1]))
E=np.array(errs); print('harmonic error rms (k1-16, 3 loudness) %.2f dB' % np.sqrt(np.nanmean(E**2)))
def third(p):
    x,_=sf.read(p, always_2d=True); x=x.mean(1)
    f,P=ss.welch(x,48000,nperseg=8192)
    c=100*2**(np.arange(0,22)/3); out=[]
    for fc in c:
        m=(f>=fc*2**-(1/6))&(f<fc*2**(1/6)); out.append(10*np.log10(P[m].sum()+1e-20))
    out=np.array(out); return c, out-10*np.log10(np.sum(10**(out/10)))
c,ta=third(wa); _,tb=third(wb)
print('third-oct Hz ', ' '.join('%5.0f'%v for v in c))
print('ref         ', ' '.join('%5.1f'%v for v in ta)); print('render      ', ' '.join('%5.1f'%v for v in tb))
print('third-octave error rms 200-10k: %.2f dB' % np.sqrt(np.mean((tb-ta)[(c>=200)&(c<=10000)]**2)))
