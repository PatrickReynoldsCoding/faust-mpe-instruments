"""The duduk line of blockm-duduk.wav: python measure_duduk.py out.npz (see the comment below)."""
# The duduk line in a polyphonic clip: per frame, the highest Basic Pitch note in 55..71 is the melody;
# refine its f0 by harmonic peak search, measure harmonics, mask ones colliding with other active notes.
import json, numpy as np, soundfile as sf
import os, sys
R=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', 'refs', 'roli-seaboard')+'/'
OFF=79.55; SR=48000; HOP=240
x,_=sf.read(R+'blockm-duduk.wav', always_2d=True); x=x.mean(1)
notes=[n for n in json.load(open(R+'blockm.basic-pitch-notes.json')) if OFF-1<n[0]<OFF+36]
nf=len(x)//HOP; t=np.arange(nf)*HOP/SR
K=30; nfft=16384; hz=SR/nfft
out_f0=np.zeros(nf); out_db=np.full(nf,-200.); H=np.full((nf,K),np.nan); N=np.full((nf,K),np.nan)
for i in range(nf):
    tt=t[i]+OFF
    act=[n for n in notes if n[0]+0.08<=tt<n[1]-0.05]
    mel=[n for n in act if 55<=n[2]<=71]
    if not mel: continue
    m=max(mel,key=lambda n:n[2]); others=[n[2] for n in act if n is not m]
    L=4096; c=int(t[i]*SR); a=c-L//2
    if a<0 or a+L>len(x): continue
    w=np.hanning(L); P=np.abs(np.fft.rfft(x[a:a+L]*w,nfft))**2*4/np.sum(w)**2
    f0n=440*2**((m[2]-69)/12)
    # refine f0: maximise summed power at k*f0 for k=1..6 over +-80 cents
    cands=f0n*2**(np.linspace(-0.8,0.8,81)/12)
    sc=[sum(P[int(round(k*f/hz))-1:int(round(k*f/hz))+2].sum() for k in range(1,7)) for f in cands]
    f0=cands[int(np.argmax(sc))]
    cs=np.concatenate([[0],np.cumsum(P)])
    oth=np.array([440*2**((o-69)/12)*k for o in others for k in range(1,25)]) if others else np.array([])
    for k in range(1,K+1):
        if (k+0.5)*f0>16000: break
        lo=int((k-0.4)*f0/hz); hi=int((k+0.4)*f0/hz)
        if len(oth) and np.min(np.abs(oth-k*f0))<0.35*f0: continue
        H[i,k-1]=10*np.log10(cs[hi]-cs[lo]+1e-20)
        nlo=int((k+0.5-1/6)*f0/hz); nhi=int((k+0.5+1/6)*f0/hz)
        N[i,k-1]=10*np.log10((cs[nhi]-cs[nlo])/(nhi-nlo)*(hi-lo)+1e-20)
    out_f0[i]=f0; out_db[i]=10*np.log10(np.mean(x[a:a+L]**2)+1e-20)
np.savez(sys.argv[1], t=t, f0=out_f0, db=out_db, H=H, N=N)
ok=out_f0>0; print('melody frames', ok.sum())
mid=12*np.log2(out_f0[ok]/440)+69
for lo,hi in [(55,60),(60,65),(65,72)]:
    s=(mid>=lo)&(mid<hi); h=H[ok][s]; h1=h[:,0:1]
    print(lo,hi,s.sum(),' '.join('%4.0f'%v for v in np.nanmedian(h-h1,0)[:16]), '| N-H', ' '.join('%4.0f'%v for v in np.nanmedian((N-H)[ok][s],0)[:8]))
