import sys, numpy as np, soundfile as sf
from scipy.signal import butter, sosfiltfilt
sys.path.insert(0,'.'); from yin import yin
x,sr=sf.read(sys.argv[1]); x=x.mean(1) if x.ndim>1 else x
lo=sosfiltfilt(butter(4,700,fs=sr,output='sos'),x)
for a in sys.argv[2:]:
    t0,t1=map(float,a.split(':'))
    row=[]
    for t in np.arange(t0,t1,0.01):
        i=int(t*sr); seg=lo[i:i+int(0.06*sr)]
        f0,q=yin(seg,sr,38,500,0.026)
        row.append('%4.0f'%(69+12*np.log2(f0/440)) if q<0.35 else '   .')
    print(a,' '.join(row))
