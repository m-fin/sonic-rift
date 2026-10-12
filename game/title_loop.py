import numpy as np, soundfile as sf, subprocess
SR=44100; BPM=150; st=60/BPM/4   # 16th step
mtof=lambda n:440*2**((n-69)/12)
def sq(f,n,duty=.5):
    ph=(f*np.arange(n)/SR)%1; return np.where(ph<duty,1.,-1.)
def tri(f,n):
    ph=(f*np.arange(n)/SR)%1; return np.round((4*np.abs(ph-.5)-1)*8)/8  # 4-bit stepped like NES
def env(n,dec): return np.exp(-np.arange(n)/SR*dec)
# 16 bars, A minor: Am F C G | Am F G E
prog=[(57,[69,72,76]),(53,[65,69,72]),(48,[67,72,76]),(55,[67,71,74])]*2+[(57,[69,72,76]),(53,[65,69,72]),(55,[67,71,74]),(52,[64,68,71])]*2
melA=[76,None,74,76,None,72,None,69, 71,None,72,74,None,None,76,None]
melB=[81,None,79,77,None,76,None,74, 76,None,None,72,74,None,71,None]
STEPS=16*len(prog); L=int(STEPS*st*SR)
mix=np.zeros(L)
def put(x,step,g):
    i=int(step*st*SR); j=min(L,i+len(x)); mix[i:j]+=x[:j-i]*g
    if i+len(x)>L: mix[:i+len(x)-L]+=x[L-i:]*g   # wrap tail -> seamless loop
rng=np.random.default_rng(1); noise=rng.choice([-1.,1.],SR)
for b,(root,ch) in enumerate(prog):
    s0=b*16; sec=b//8
    # pulse 1: melody (2nd half of each 8-bar uses B phrase)
    mel=melA if b%2==0 else melB
    for k,n in enumerate(mel):
        if n is None: continue
        if sec==1: n+= (0 if b%4<3 else -2)
        x=sq(mtof(n),int(st*SR*2),.25)*env(int(st*SR*2),3); put(x,s0+k,.16)
    # pulse 2: arpeggio 50% duty
    for k in range(16):
        n=ch[k%3]+(12 if k%6>=3 else 0)
        x=sq(mtof(n-12),int(st*SR*.9),.125)*env(int(st*SR*.9),12); put(x,s0+k,.07)
    # triangle bass: root octave bounce 8ths
    for k in range(0,16,2):
        n=root-12+(12 if k%4==2 else 0); put(tri(mtof(n),int(st*SR*1.8)),s0+k,.28)
    # noise drums
    for k in range(16):
        if k%8==0: x=noise[:int(.12*SR)]*env(int(.12*SR),25); x=np.repeat(x[::8],8)[:len(x)]; put(x,s0+k,.3)  # low-ish kick-ish
        elif k%8==4: put(noise[:int(.1*SR)]*env(int(.1*SR),30),s0+k,.22)
        elif k%2==0: put(noise[:int(.03*SR)]*env(int(.03*SR),120),s0+k,.07)
mix/=np.max(np.abs(mix))*1.1
sf.write('title_loop.wav',mix,SR)
subprocess.run(['ffmpeg','-y','-loglevel','error','-i','title_loop.wav','-c:a','libvorbis','-q:a','6','title_loop.ogg'],check=True)
prev=np.concatenate([mix,mix]); n=int(3*SR); prev[-n:]*=np.linspace(1,0,n)
sf.write('/tmp/p.wav',prev,SR)
subprocess.run(['ffmpeg','-y','-loglevel','error','-i','/tmp/p.wav','-b:a','192k','title_loop_preview.mp3'],check=True)
print(round(L/SR,2))
