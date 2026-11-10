# Play the funk-berlin clip's own notes (Basic Pitch) through sync-funk (left, < MIDI 50) and berlin (right).
# Funk: onsets snapped to the low-band attacks; notes that dive in are struck hard (velocity 0.9).
# Pressure from each zone's band level. Writes funk.wav, berlin.wav, mix.wav (mono).
import sys, json, subprocess, numpy as np, soundfile as sf
from scipy.signal import butter, sosfiltfilt
sys.path.insert(0,'.'); from yin import yin
import os; S=os.environ.get('SCRATCH','/tmp/seaboard-synths'); os.makedirs(S, exist_ok=True)
M=__import__('os').path.abspath(__import__('os').path.join(__import__('os').path.dirname(__file__),'../../../..'))
R=M+'/refs/roli-seaboard/'
x,sr=sf.read(R+'rise-funk-berlin.wav'); x=x.mean(1); T=len(x)/sr
notes=[(o-62,e-62,m,a) for o,e,m,a in json.load(open(R+'rise.basic-pitch-notes.json')) if 62<=o<62+T]
lo=sosfiltfilt(butter(4,200,fs=sr,output='sos'),x); lp=sosfiltfilt(butter(4,700,fs=sr,output='sos'),x)
hi=sosfiltfilt(butter(4,[250,3000],btype='band',fs=sr,output='sos'),x)
H=int(0.005*sr)
def env(y): return 20*np.log10(np.array([np.sqrt(np.mean(y[i:i+H]**2)) for i in range(0,len(y)-H,H)])+1e-6)
elo=env(lo); ehi=env(hi)
on=[k for k in range(4,len(elo)) if elo[k]-elo[k-4]>12 and elo[k]>-35]
on2=[]
for k in on:
    if not on2 or k-on2[-1]>20: on2.append(k)
onT=np.array(on2)*H/sr
BLK=64; nb=int(T*sr/BLK)+1; tb=np.arange(nb)*BLK/sr
def press(e, lo_, hi_):
    v=np.interp(tb, np.arange(len(e))*H/sr+H/2/sr, e); return np.clip((v-lo_)/(hi_-lo_),0,1)*0.75+0.1
def build(sel, vels, pr, nv):
    ctl=np.zeros((nb,nv,6),np.float32); ctl[:,:,0]=440; ctl[:,:,3]=0.5
    free=[0.0]*nv
    for (o,e,m),v in zip(sel,vels):
        k=min(range(nv),key=lambda i: free[i]) 
        a=int(o*sr/BLK); b=max(a+2,int(e*sr/BLK))
        ctl[a:,k,0]=440*2**((m-69)/12); ctl[a:b,k,1]=1; ctl[b:,k,1]=0; ctl[a:,k,2]=pr[a:]; ctl[a:,k,4]=v
        ctl[a:,k,5]=1 if any(abs(f-o)<0.06 for f in free) else 0
        free[k]=e+0.3
    return ctl
# funk: mono line
fsel=[]; fv=[]
for j,o in enumerate(onT):
    nxt=onT[j+1] if j+1<len(onT) else T
    k=int(o*sr/H); pk=elo[k:k+20].max(); 
    endk=next((i for i in range(k+8,min(len(elo),int(nxt*sr/H))) if elo[i]<pk-18), int(nxt*sr/H))
    e=endk*H/sr
    def f0at(t):
        i=int(t*sr); f,q=yin(lp[i:i+int(0.075*sr)],sr,30,500,0.034); return f if q<0.35 else None
    fs=[f0at(t) for t in np.arange(o+0.12,max(o+0.13,e-0.04),0.02)]; fs=[f for f in fs if f]
    if not fs: fs=[f0at(min(e-0.05,o+0.05)) or 43.65]
    m=round(69+12*np.log2(np.median(fs)/440))
    if m>50: m-=12
    st=[f0at(o+t) for t in (0.0,0.02,0.04)]; st=[f for f in st if f]
    dive=bool(st) and 12*np.log2(max(st)/(440*2**((m-69)/12)))>7
    fsel.append((o,e,m)); fv.append(0.9 if dive else 0.45)
# truncate overlaps (mono)
for i in range(len(fsel)-1):
    if fsel[i][1]>fsel[i+1][0]-0.005: fsel[i]=(fsel[i][0],fsel[i+1][0]-0.005,fsel[i][2])
print(len(fsel),'funk notes,',sum(v>0.5 for v in fv),'dive in')
bk=sorted([(o,e,m) for o,e,m,a in notes if m>=50])
print(len(bk),'berlin notes')
pf=press(elo,-30,-12); pb=press(ehi,-38,-18)
for name,sel,vel,pr,nv in [('sync-funk',fsel,fv,pf,1),('berlin',bk,[0.6]*len(bk),pb,8)]:
    ctl=build(sel,vel,pr,nv); ctl.tofile(S+'/ctl.f32')
    subprocess.run([M+'/build/render_curves',M+'/build/synths/'+name+'.so',S+'/ctl.f32',str(nv),S+'/out.f32'],check=True)
    y=np.fromfile(S+'/out.f32',np.float32); sf.write(S+'/'+name+'-phrase.wav',y,sr)
a,_=sf.read(S+'/sync-funk-phrase.wav'); b,_=sf.read(S+'/berlin-phrase.wav'); n=min(len(a),len(b))
sf.write(S+'/mix-phrase.wav',a[:n]+b[:n],sr)
