import sys,numpy as np, soundfile as sf, scipy.signal as ss
ref,ren=sys.argv[1],sys.argv[2]; t0=float(sys.argv[3]) if len(sys.argv)>3 else 0
def ld(p):
    x,sr=sf.read(p); x=x.mean(1) if x.ndim>1 else x; return x
a=ld(ref); b=ld(ren); n=min(len(a),len(b)); a=a[:n]; b=b[:n]
def third(x):
    f,P=ss.welch(x,48000,nperseg=16384); c=31.5*2**(np.arange(0,27)/3); o=[]
    for fc in c:
        m=(f>=fc*2**-(1/6))&(f<fc*2**(1/6)); o.append(10*np.log10(P[m].sum()+1e-20))
    o=np.array(o); return c,o-10*np.log10(np.sum(10**(o/10)))
c,ta=third(a); _,tb=third(b)
print('Hz   ',' '.join('%5.0f'%v for v in c)); print('ref  ',' '.join('%5.1f'%v for v in ta)); print('ren  ',' '.join('%5.1f'%v for v in tb))
print('diff ',' '.join('%5.1f'%v for v in tb-ta)); print('third-oct err rms 40-8k: %.2f dB'%np.sqrt(np.mean((tb-ta)[(c>=40)&(c<=8000)]**2)))
H=int(0.02*48000)
for lo,hi in [(30,200),(250,1000),(1000,4000)]:
    s=ss.butter(4,[lo,hi],btype='band',fs=48000,output='sos')
    ea=[20*np.log10(np.sqrt(np.mean(v**2))+1e-6) for v in np.array_split(ss.sosfilt(s,a),n//H)]
    eb=[20*np.log10(np.sqrt(np.mean(v**2))+1e-6) for v in np.array_split(ss.sosfilt(s,b),n//H)]
    ea=np.maximum(ea,max(ea)-40); eb=np.maximum(eb,max(eb)-40)
    print('band %d-%d env corr %.2f'%(lo,hi,np.corrcoef(ea,eb)[0,1]))
print('level ref %.1f ren %.1f dBFS'%(20*np.log10(np.sqrt(np.mean(a**2))),20*np.log10(np.sqrt(np.mean(b**2)))))
