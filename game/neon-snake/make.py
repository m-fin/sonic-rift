import numpy as np, soundfile as sf, subprocess
SR=44100; BPM=150; st=60/BPM/4
mtof=lambda n:440*2**((n-69)/12)
def sq(f,n,d=.5): ph=(f*np.arange(n)/SR)%1; return np.where(ph<d,1.,-1.)
def tri(f,n): ph=(f*np.arange(n)/SR)%1; return np.round((4*np.abs(ph-.5)-1)*8)/8
def env(n,k): return np.exp(-np.arange(n)/SR*k)
rng=np.random.default_rng(3); noise=rng.choice([-1.,1.],SR)
def ogg(name,x):
    x=x/np.max(np.abs(x))*0.9; sf.write(name+'.wav',x,SR)
    subprocess.run(['ffmpeg','-y','-loglevel','error','-i',name+'.wav','-c:a','libvorbis','-q:a','6',name+'.ogg'],check=True)
# ---- level 1 loop: 48 bars (Am Am F G | Am Am C E) x6 with A/B/C sections
prog=[57,57,53,55,57,57,48,52]
mels={0:[69,None,72,69,74,None,72,None,69,72,76,None,74,72,69,None],
      1:[76,76,None,79,77,None,76,74,None,72,74,None,76,None,None,None],
      2:[81,None,79,None,76,None,74,76,None,None,72,None,69,None,71,72]}
bars=48; L=int(bars*16*st*SR); mix=np.zeros(L)
def put(x,s,g):
    i=int(s*st*SR); j=min(L,i+len(x)); mix[i:j]+=x[:j-i]*g
    if i+len(x)>L: mix[:i+len(x)-L]+=x[L-i:]*g
for b in range(bars):
    s0=b*16; root=prog[b%8]; sec=(b//16)  # A,B,C 16 bars each
    mel=mels[sec] if b%2==0 else mels[(sec+1)%3]
    for k,n in enumerate(mel):
        if n is None: continue
        if root in(53,48) : n-=0
        put(sq(mtof(n),int(st*SR*1.5),.25)*env(int(st*SR*1.5),5),s0+k,.15)
    ch=[root+12,root+15 if root in(57,) else root+16,root+19]
    for k in range(16):
        put(sq(mtof(ch[k%3]),int(st*SR*.8),.125)*env(int(st*SR*.8),14),s0+k,.06)
    for k in range(16):  # driving 16th-ish bass
        if k%2==0 or sec==2: put(tri(mtof(root-12+(12 if k%4==2 else 0)),int(st*SR*.95)),s0+k,.26)
    for k in range(16):
        if k%4==0: x=noise[:int(.1*SR)]; x=np.repeat(x[::10],10)[:len(x)]*env(len(x),28); put(x,s0+k,.3)
        if k%8==4: put(noise[:int(.1*SR)]*env(int(.1*SR),30),s0+k,.2)
        if k%2==1: put(noise[:int(.025*SR)]*env(int(.025*SR),140),s0+k,.06)
ogg('level1_loop',mix)
# ---- SFX
def seq(notes,dur,d=.5,dec=6,gap=0):
    out=[]
    for n in notes: m=int(dur*SR); out.append(sq(mtof(n),m,d)*env(m,dec)); 
    return np.concatenate(out)
ogg('speedup',seq([57,60,64,69,72,76,81],.045,.25,8))
t=np.arange(int(.5*SR))/SR; f=880*np.exp(-t*5); ph=np.cumsum(f)/SR
ogg('death',np.where(ph%1<.5,1.,-1.)*np.exp(-t*4))
ogg('pickup',np.concatenate([sq(mtof(83),int(.05*SR),.5),sq(mtof(88),int(.18*SR),.5)*env(int(.18*SR),10)]))
ogg('win',np.concatenate([seq([69,73,76],.09,.25,4),sq(mtof(81),int(.6*SR),.25)*env(int(.6*SR),3)]))
x=noise[:int(.04*SR)]*env(int(.04*SR),90)+sq(mtof(96),int(.04*SR))*env(int(.04*SR),120)*.5
ogg('attempt',x)
print(L/SR)
