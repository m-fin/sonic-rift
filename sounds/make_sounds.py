import numpy as np, wave, json, os
SR=44100; rng=np.random.default_rng(7)
D=os.path.dirname(os.path.abspath(__file__))
def save(name,x):
    x=x/ (np.max(np.abs(x))+1e-9)*0.9
    with wave.open(f"{D}/{name}.wav","wb") as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(SR);w.writeframes((x*32767).astype('<i2').tobytes())
t=lambda s:np.arange(int(s*SR))/SR
def lp(x,k):
    y=np.empty_like(x);s=0.
    for i in range(len(x)): s+=k*(x[i]-s);y[i]=s
    return y
# servo whir: rising/falling FM motor with gear buzz
tt=t(1.2); f=300+900*np.sin(np.pi*tt/1.2)**2
ph=2*np.pi*np.cumsum(f)/SR
save("servo_whir",(np.sin(ph+2*np.sin(ph*3.01))+.3*np.sign(np.sin(ph*0.5)))*np.sin(np.pi*tt/1.2)**.5)
# machine hum: 60Hz harmonics with slow wobble
tt=t(4); save("machine_hum",sum(np.sin(2*np.pi*60*h*tt)/h for h in range(1,9))*(1+.2*np.sin(2*np.pi*.5*tt))+.05*rng.standard_normal(len(tt)))
# synthetic heartbeat (lub-dub)
def thump(f,d): x=t(d); return np.sin(2*np.pi*f*x*(1-x))*np.exp(-x*18)
hb=np.zeros(int(SR*1.0)); l=thump(55,.25); hb[:len(l)]+=l; hb[int(.28*SR):int(.28*SR)+len(l)]+=.7*thump(48,.25)
save("heartbeat",hb)
# mechanical breath: filtered noise swell in/out
tt=t(3); e=np.sin(np.pi*tt/3)**2; save("mech_breath",lp(rng.standard_normal(len(tt)),.05)*e+.2*lp(rng.standard_normal(len(tt)),.3)*e*np.sin(2*np.pi*.0*tt+1))
# metal hit: inharmonic FM bell
tt=t(2); save("metal_hit",sum(np.sin(2*np.pi*f*tt)*np.exp(-tt*d) for f,d in[(220,3),(587,4),(1031,6),(1673,8),(2711,11)]))
# circuit noise: bitcrushed glitch bursts
tt=t(2); x=np.sin(2*np.pi*(800+600*np.sign(np.sin(2*np.pi*7*tt)))*tt)*(rng.random(len(tt))>.3)
save("circuit_glitch",np.round(x*4)/4*(np.sin(2*np.pi*3*tt)>0))
# granular cloud from metal hit
src=sum(np.sin(2*np.pi*f*t(2)) for f in(220,587,1031)); out=np.zeros(SR*4)
for _ in range(400):
    n=int(rng.uniform(.02,.08)*SR); s=rng.integers(0,len(src)-n); p=rng.integers(0,len(out)-n)
    out[p:p+n]+=src[s:s+n]*np.hanning(n)
save("granular_cloud",out)
# Bitcoin sonification: each recent block -> note (tx_count->pitch, size->length)
B=json.load(open(f"{D}/btc_blocks.json")); scale=[0,3,5,7,10]; seq=[]
for b in B:
    i=int(np.interp(b["tx_count"],[1000,8000],[0,14])); note=50+12*(i//5)+scale[i%5]
    d=np.interp(b["size"],[5e5,2.5e6],[.15,.6]); x=t(d)
    seq.append(np.sin(2*np.pi*440*2**((note-69)/12)*x+1.5*np.sin(2*np.pi*880*2**((note-69)/12)*x))*np.exp(-x*5))
save("btc_blocks_melody",np.concatenate(seq))
json.dump([(b["height"],b["tx_count"],b["size"]) for b in B],open(f"{D}/btc_blocks_used.json","w"))
print("blocks",[b["height"] for b in B])
