import sys, numpy as np, soundfile as sf
from scipy.signal import butter, sosfiltfilt
def yin(x,sr,fmin,fmax,win,thr=0.15):
    W=int(win*sr); tmin=int(sr/fmax); tmax=int(sr/fmin)
    d=np.array([np.sum((x[:W]-x[t:t+W])**2) for t in range(tmax+1)])
    c=d[1:]*np.arange(1,tmax+1)/np.maximum(np.cumsum(d[1:]),1e-12); c=np.r_[1,c]
    cand=np.where(c[tmin:]<thr)[0]
    if len(cand)==0: t=tmin+np.argmin(c[tmin:])
    else:
        t=tmin+cand[0]
        while t+1<len(c) and c[t+1]<c[t]: t+=1
    if 1<=t<len(c)-1:
        a,b,g=c[t-1],c[t],c[t+1]; p=0.5*(a-g)/(a-2*b+g+1e-12)
    else: p=0
    return sr/(t+p), c[t]
if __name__=='__main__':
    f=sys.argv[1]; t0=float(sys.argv[2]); t1=float(sys.argv[3]); lpf=float(sys.argv[4]); fmin=float(sys.argv[5]); fmax=float(sys.argv[6])
    x,sr=sf.read(f); x=x.mean(1)
    x=sosfiltfilt(butter(4,lpf,fs=sr,output='sos'),x)
    W=1.2/fmin
    for t in np.arange(t0,t1,0.01):
        i=int(t*sr); seg=x[i:i+int((W+1/fmin)*sr)+10]
        rms=np.sqrt(np.mean(seg[:int(W*sr)]**2))
        f0,q=yin(seg,sr,fmin,fmax,W)
        print('%.2f f0 %6.1f midi %5.1f q %.2f rms %.3f'%(t,f0,69+12*np.log2(f0/440),q,rms))
