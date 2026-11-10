import sys, numpy as np, soundfile as sf
x,sr=sf.read(sys.argv[1]); x=x.mean(1) if x.ndim>1 else x
def f0of(seg):
    N=1<<17; sp=np.abs(np.fft.rfft(seg*np.hanning(len(seg)),N)); fr=np.fft.rfftfreq(N,1/sr)
    best=max(((sum(np.interp(f*k,fr,sp)**0.5 for k in range(1,7)),f) for f in np.arange(float(__import__("os").environ.get("F0LO",30)),float(__import__("os").environ.get("F0HI",140)),0.05)))
    return best[1],sp,fr
for a in sys.argv[2:]:
    t0,t1=map(float,a.split(':'))
    seg=x[int(t0*sr):int(t1*sr)]
    f0,sp,fr=f0of(seg)
    tot=20*np.log10(np.sqrt(np.mean(seg**2)))
    lv=[]
    for k in range(1,25):
        i=(fr>f0*k-f0*0.25)&(fr<f0*k+f0*0.25); a_=sp[i].max(); lv.append(a_)
    lv=20*np.log10(np.array(lv)/lv[0])
    print('%s f0 %.1f (midi %.1f) rms %.1f |'%(a,f0,69+12*np.log2(f0/440),tot),' '.join('%3.0f'%v for v in lv))
