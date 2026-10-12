import numpy as np, soundfile as sf, subprocess
SR=44100; BPM=75; beat=60/BPM; bar=4*beat
mtof=lambda n:440*2**((n-69)/12)
rng=np.random.default_rng(5)
THEME=[62,69,66,64,62,71]          # D5 A5 F#5 E5 D5 B5  (D major)
THEME_RES=THEME+[69,74]            # resolves: A5 -> D6
def tt(n): return np.arange(n)/SR
def mbox(f,d=1.6):
    t=tt(int(d*SR)); return sum(a*np.sin(2*np.pi*f*m*t)*np.exp(-t*k) for m,a,k in[(1,1,3),(2.01,.4,6),(3.98,.25,9),(5.43,.1,14)])
def pad(fs,d):
    t=tt(int(d*SR)); x=sum(np.sin(2*np.pi*f*(1+dt)*t+np.sin(2*np.pi*f*.5*t)*.3) for f in fs for dt in(-.002,0,.002))
    a=int(min(1.5,d/3)*SR); e=np.ones(len(t)); e[:a]=np.linspace(0,1,a); e[-a:]=np.linspace(1,0,a); return x*e/len(fs)/3
def lp(x,k):
    y=np.empty_like(x);s=0.
    for i in range(len(x)): s+=k*(x[i]-s);y[i]=s
    return y
def out(name,x,peak=.9):
    x=x/np.max(np.abs(x))*peak; sf.write(name+'.wav',x,SR)
    subprocess.run(['ffmpeg','-y','-loglevel','error','-i',name+'.wav','-c:a','libvorbis','-q:a','6',name+'.ogg'],check=True)
def place(L,items,wrap=True):
    m=np.zeros(L)
    for x,t,g in items:
        i=int(t*SR); j=min(L,i+len(x)); m[i:j]+=x[:j-i]*g
        if wrap and i+len(x)>L: m[:i+len(x)-L]+=x[L-i:]*g
    return m
def echo(x,d,fb,n=5):
    y=x.copy(); k=int(d*SR)
    for r in range(1,n): y[k*r:]+=x[:-k*r]*fb**r
    return y
# (1) theme
mb=[];step=beat/2
for i,n in enumerate(THEME_RES[:6]): mb.append((mbox(mtof(n+12)),i*step,1))
out('theme_musicbox',echo(place(int((6*step+2)*SR),mb,False),beat*.75,.3))
L=int((8*beat+4)*SR); items=[]
for i,n in enumerate(THEME_RES):
    d=beat*(2 if i==7 else 1); t=i*beat
    items.append((pad([mtof(n)],d*1.5+1.5)*1.0,t,1)); items.append((mbox(mtof(n)),t,.6))
for c,t in[([50,57,62,66],0),([47,54,59,62],2*bar/2),([43,50,55,59],bar),([45,52,57,61],1.5*bar)]:
    items.append((pad([mtof(x) for x in c],bar/2+1.5),t,.5))
items.append((pad([mtof(x) for x in[50,57,62,66,69]],5),2*bar,.7))
full=place(L,items,False); out('theme_full',echo(full,beat*.75,.25))
# (2) cabin loop: 45 bars, D Bm G A
bars=45; L=int(bars*bar*SR); prog=[[50,57,62,66],[47,54,59,62],[43,50,55,59],[45,52,57,61]]
t=tt(L); hum=(np.sin(2*np.pi*55*t)+.5*np.sin(2*np.pi*110.3*t)+.2*np.sin(2*np.pi*165*t))*(1+.15*np.sin(2*np.pi*t/bar/4))
pads=[];beatl=[];boxl=[]
for b in range(bars):
    c=prog[(b//2)%4]; pads.append((pad([mtof(x) for x in c],2*bar+1.5),b*bar,1) if b%2==0 else (np.zeros(1),0,0))
    for q in range(4):  # soft heartbeat-ish pulse
        k=tt(int(.4*SR)); beatl.append((np.sin(2*np.pi*(48+30*np.exp(-k*20))*k)*np.exp(-k*7),b*bar+q*beat,.35 if q%2==0 else .15))
        if q%2==1: n=rng.standard_normal(int(.05*SR)); beatl.append((lp(n,.2)*np.exp(-tt(len(n))*60),b*bar+q*beat+beat/2,.08))
    if b%8==4:
        for i,n in enumerate(THEME): boxl.append((mbox(mtof(n+12)),b*bar+i*beat/2,.35))
P=place(L,pads); B=place(L,beatl); X=echo(place(L,boxl),beat*.75,.35)
H=hum*.12
cabin=P*.5+B+X*.6+H; out('cabin_loop',cabin)
zp=echo(P,beat*1.5,.45,6); zx=echo(place(L,boxl),beat*1.5,.5,6)
zero=zp*.6+zx*.5+H*.5+lp(rng.standard_normal(L),.01)*.4
out('zero_g_layer',zero)
# (3) events
w=tt(int(2.5*SR)); f=110*2**(w/2.5*2); wake=np.sin(2*np.pi*np.cumsum(f)/SR)*np.minimum(w/2,1)*np.exp(-np.maximum(w-2,0)*6)
wake=wake+place(len(w),[(mbox(mtof(74+12)),2.0,.5)],False); out('wake',wake)
fs=tt(int(2*SR)); fl=place(len(fs),[(pad([mtof(x) for x in[62,69,74,78]],2),0,1)],False)
fl+=lp(rng.standard_normal(len(fs)),.03)*np.sin(np.pi*fs/2)*2; out('float_start',echo(fl,.3,.4))
cr=place(int(1.2*SR),[(mbox(mtof(n+12),1),i*.08,1) for i,n in enumerate([62,66,69])]+[(np.sign(np.sin(2*np.pi*1200*tt(int(.03*SR))))*.3,0,1)],False)
out('cockpit_reach',cr)
out('window_look',full)
print('cabin',L/SR)
