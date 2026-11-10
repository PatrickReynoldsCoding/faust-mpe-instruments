import sys,numpy as np, soundfile as sf
from scipy.signal import butter, sosfiltfilt
x,sr=sf.read(sys.argv[1]); x=x.mean(1) if x.ndim>1 else x
t0,t1=float(sys.argv[2]),float(sys.argv[3]); step=float(sys.argv[4]) if len(sys.argv)>4 else 0.02
bs=[(200,400),(500,1000),(1000,3000),(3000,8000)]
fl=[sosfiltfilt(butter(4,b,btype='band',fs=sr,output='sos'),x) for b in bs]
H=int(step*sr)
for i in range(int(t0*sr),int(t1*sr),H):
    print('%.2f'%(i/sr),' '.join('%5.1f'%(20*np.log10(np.sqrt(np.mean(f[i:i+H]**2))+1e-9)) for f in fl))
