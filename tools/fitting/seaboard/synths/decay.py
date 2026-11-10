import sys,numpy as np, soundfile as sf
from scipy.signal import stft
x,sr=sf.read(sys.argv[1]); x=x.mean(1) if x.ndim>1 else x
f,t,Z=stft(x,sr,nperseg=8192,noverlap=8192-2400); A=20*np.log10(np.abs(Z)+1e-9)
for spec in sys.argv[2:]:
    f0,a,b,name=spec.split(':'); f0=float(f0);a=float(a);b=float(b)
    w=max(0.03*f0,6); m=(f>f0-w)&(f<f0+w); k=(t>=a)&(t<b); tt=t[k]; v=A[m][:,k].max(0)
    i=np.argmax(v); p=np.polyfit(tt[i+2:],v[i+2:],1)
    print('%-8s peak %.1f at %.2f, slope %.1f dB/s :'%(name,v[i],tt[i],p[0]),' '.join('%.0f'%q for q in v[::2]))
