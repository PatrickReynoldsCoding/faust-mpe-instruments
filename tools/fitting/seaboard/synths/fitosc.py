import numpy as np
from scipy.optimize import minimize
N=4096; p=np.arange(N)/N
def harm(r, w_sq, w_saw, w_sync, fc, q, K):
    sync=2*((p*r)%1)-1
    sq=np.where(p<0.5,1,-1.0); saw=2*p-1
    y=w_sync*sync+w_sq*sq+w_saw*saw
    H=np.abs(np.fft.rfft(y))[1:K+1]
    k=np.arange(1,K+1); s=1j*k/fc
    Hf=np.abs(1/(s*s+s/q+1))
    H=H*Hf; return 20*np.log10(H/H[0]+1e-9)
def fit(tgt):
    tgt=np.array(tgt); K=len(tgt)
    best=None
    for r0 in np.arange(1.2,5,0.2):
        def cost(v):
            r,a,b,c,fc,q=v
            if fc<0.5 or q<0.3 or q>6 or r<1: return 1e3
            return np.mean((harm(r,abs(a),abs(b),abs(c),fc,q,K)-tgt)**2)
        res=minimize(cost,[r0,0.5,0.2,0.5,4,0.8],method='Nelder-Mead',options={'maxiter':3000})
        if best is None or res.fun<best.fun: best=res
    r,a,b,c,fc,q=best.x
    print('rms err %.2f dB  r %.2f sq %.2f saw %.2f sync %.2f fc %.2f*f0 q %.2f'%(np.sqrt(best.fun),r,abs(a),abs(b),abs(c),fc,q))
    print('tgt',' '.join('%4.0f'%v for v in tgt)); print('fit',' '.join('%4.0f'%v for v in harm(r,abs(a),abs(b),abs(c),fc,q,K)))
print('funk'); fit([0,-13,-7,-23,-17,-24,-21,-19,-25,-32,-23,-28])
print('berlin'); fit([0,-11,-8,-18,-16,-17,-25,-26,-20])
print('--- fixed r, sync weight >= square')
for name,tgt in [('funk',[0,-13,-7,-23,-17,-24,-21,-19,-25,-32,-23,-28]),('berlin',[0,-11,-8,-18,-16,-17,-25,-26,-20])]:
  tgt=np.array(tgt);K=len(tgt)
  for r in [1.5,2.0,2.5,3.0,3.5]:
    def cost(v):
        a,b,c,fc,q=v
        if fc<0.5 or q<0.3 or q>6 or abs(c)<abs(a): return 1e3
        return np.mean((harm(r,abs(a),abs(b),abs(c),fc,q,K)-tgt)**2)
    best=min((minimize(cost,[0.3,0.2,0.6,f,0.8],method='Nelder-Mead',options={'maxiter':3000}) for f in [3,6,12]),key=lambda z:z.fun)
    a,b,c,fc,q=best.x; print(name,'r %.1f err %.2f sq %.2f saw %.2f sync %.2f fc %.1f q %.2f'%(r,np.sqrt(best.fun),abs(a),abs(b),abs(c),fc,q))
