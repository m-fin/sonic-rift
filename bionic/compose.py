import numpy as np, json, soundfile as sf, subprocess
SR=44100; rng=np.random.default_rng(16)
d=json.load(open('data/bionic_tracker_data.json')); E=d['entries']
for e in E: e['lv']=int(e['level'])
order=sorted(E,key=lambda e:-e['lv'])   # most replaced enters first
BPM=100; beat=60/BPM; bar=4*beat
INTRO=4; PER=2; OUT=8
bars=INTRO+PER*len(order)+OUT; L=int(bars*bar*SR)+SR*3
mix=np.zeros(L)
def ld(p,res=True):
    a,sr=sf.read(p); a=a if a.ndim==1 else a.mean(1)
    if sr!=SR: a=np.interp(np.arange(int(len(a)*SR/sr))*sr/SR,np.arange(len(a)),a)
    return a
def add(x,t,g=1):
    i=int(t*SR); j=min(L,i+len(x)); mix[i:j]+=x[:j-i]*g
def lp(x,k):
    y=np.empty_like(x);s=0.
    for i in range(len(x)): s+=k*(x[i]-s);y[i]=s
    return y
def tt(s): return np.arange(int(s*SR))/SR
def robot(x,amt):  # ring mod + bitcrush, amt 0..1
    t=np.arange(len(x))/SR; rm=x*np.sin(2*np.pi*70*t)
    y=(1-amt)*x+amt*rm; q=2**int(8-5*amt); y=np.round(y*q)/q
    return y
S='../sounds/'
hb=ld(S+'heartbeat.wav'); br=ld(S+'mech_breath.wav'); servo=ld(S+'servo_whir.wav')
metal=ld(S+'metal_hit.wav'); hum=ld(S+'machine_hum.wav'); glitch=ld(S+'circuit_glitch.wav')
# A minor-ish scale degrees per system (16 voices)
scale=[45,48,52,55,57,60,62,64,67,69,72,74,76,79,81,84]
wav=['sine','tri','saw','square']
def osc(f,n,w):
    t=np.arange(n)/SR; ph=(f*t)%1
    return {'sine':np.sin(2*np.pi*ph),'tri':4*np.abs(ph-.5)-1,'saw':2*ph-1,'square':np.sign(ph-.5)}[w]
mtof=lambda n:440*2**((n-69)/12)
# rhythmic patterns (16th steps over 1 bar) per voice
pats=[[k for k in range(16) if rng.random()<.25+.05*(i%3)] or [0] for i in range(16)]
entered=[]; endb=bars-OUT
for b in range(bars):
    t0=b*bar
    machine=min(1,max(0,(b-INTRO)/(PER*len(order))))   # 0 human -> 1 machine
    if b>=INTRO and (b-INTRO)%PER==0 and (b-INTRO)//PER<len(order):
        e=order[(b-INTRO)//PER]; entered.append(e)
        v=ld(f"vox_{e['id']}.wav"); add(robot(v,machine*.9),t0,.55)
        add(metal,t0,.12*e['lv']/5)
    # human layer fades: heartbeat & breath
    hg=1-machine*0.95
    if b<endb:
        add(hb,t0,.6*hg); add(hb,t0+2*beat,.6*hg)
        if b%2==0: add(br,t0,.35*hg)
    # machine pulse grows
    if machine>0 and b<endb:
        for q in range(4):
            n=int(.25*SR); x=tt(.25); add(np.sin(2*np.pi*(40+90*np.exp(-x*35))*x)*np.exp(-x*10),t0+q*beat,.7*machine)
        if b%4==0: add(hum,t0,.15*machine)
    # each entered system plays its voice, intensity = level/5
    if b<endb+4:
        fade=1 if b<endb else (endb+4-b)/4
        for i,e in enumerate(entered):
            idx=E.index(e); g=(e['lv']/5)**1.5*.12*fade
            if g==0: continue
            for s in pats[idx]:
                n=int(beat/4*SR*(1+e['lv']/2)); f=mtof(scale[idx])
                x=osc(f,n,wav[idx%4])*np.exp(-np.arange(n)/SR*(8-e['lv']))
                add(lp(x,.05+.03*e['lv']),t0+s*beat/4,g)
        if b%2==1 and b>=INTRO and b<endb: add(servo,t0+3*beat,.12*machine)
        if b%8==6 and machine>.5 and b<endb: add(glitch[:int(beat*SR)],t0+3*beat,.1)
# outro: Blake, fully robotic
add(robot(ld('vox_blake.wav'),1.0),endb*bar,.6)
add(robot(ld('vox_blake.wav'),.35),endb*bar+bar/2,.18)
d2=int(beat*.75*SR); out=mix.copy(); out[d2:]+=mix[:-d2]*.25
out=np.tanh(out*1.3); out/=np.max(np.abs(out))*1.05
sf.write('/tmp/bionic.wav',out,SR)
subprocess.run(['ffmpeg','-y','-loglevel','error','-i','/tmp/bionic.wav','-b:a','192k','bionic-body.mp3'],check=True)
json.dump([{'order':i+1,'system':e['system'],'level':e['lv'],'enters_sec':round((INTRO+PER*i)*bar,1)} for i,e in enumerate(order)],open('data/bionic_scores_used.json','w'),indent=1)
print(round(len(out)/SR,1))
