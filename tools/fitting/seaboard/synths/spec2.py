import sys, numpy as np, soundfile as sf, json
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from scipy.signal import stft
f=sys.argv[1]; t0=float(sys.argv[2]); t1=float(sys.argv[3]); out=sys.argv[4]
flo=float(sys.argv[5]); fhi=float(sys.argv[6]); n=int(sys.argv[7]); hop=int(sys.argv[8])
x,sr=sf.read(f,start=int(t0*48000),stop=int(t1*48000)); 
if x.ndim>1: x=x.mean(1)
fr,tt,Z=stft(x,sr,nperseg=n,noverlap=n-hop)
S=20*np.log10(np.abs(Z)+1e-7)
k=(fr>=flo)&(fr<=fhi)
fig,ax=plt.subplots(figsize=(16,8))
ax.pcolormesh(tt+t0,fr[k],S[k],vmin=S[k].max()-70,vmax=S[k].max(),shading='auto',cmap='magma')
if len(sys.argv)>9 and sys.argv[9]=='log': ax.set_yscale('log')
ax.set_xticks(np.arange(np.ceil(t0*10)/10,t1,0.1),minor=True); ax.grid(axis='x',which='both',alpha=0.3)
ax.grid(axis='y',alpha=0.3)
plt.tight_layout(); plt.savefig(out,dpi=70)
