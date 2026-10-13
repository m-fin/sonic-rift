import numpy as np
import os
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','game','premiere','make.py')).read().split('# (1) theme')[0])
def echo(x,d,fb,n=5):
    y=x.copy(); k=int(d*SR)
    for r in range(1,n): y+=np.roll(x,k*r)*fb**r
    return y
def build(name,bpm,prog,base,theme,seed):
    global rng; rng=np.random.default_rng(seed)
    b4=4*60/bpm*4  # 4-bar chord length
    L=int(b4*len(prog)*SR); t=tt(L)
    P=place(L,[(pad([mtof(x) for x in c],b4+3),i*b4,1) for i,c in enumerate(prog)])
    sub=np.sin(2*np.pi*mtof(base)*t)*(0.7+.3*np.sin(2*np.pi*t*2/(L/SR)))  # integer cycles -> seamless
    air=lp(rng.standard_normal(L),.004)*(0.6+.4*np.sin(2*np.pi*t*3/(L/SR)))
    g=[]
    for _ in range(int(L/SR/2.5)):
        n=rng.choice(theme); g.append((mbox(mtof(n),3.0),rng.uniform(0,L/SR),rng.uniform(.08,.22)))
    X=echo(place(L,g),60/bpm*1.5,.5,7)
    mix=echo(P,60/bpm*2,.4,5)*.55+sub*.12+air*1.2+X*.5
    # seamless: crossfade tail into head handled by place wrap; normalize
    out(name,mix,.8); return L/SR
a=build('space_drift',60,[[50,57,64,69],[47,54,62,66],[43,50,57,64],[45,52,57,61],[50,57,62,69],[52,59,64,68],[43,50,55,62],[45,52,57,64]],38,[74,76,78,81,83,86],11)
b=build('machine_sleep',54,[[45,52,57,60],[41,48,53,57],[43,50,55,59],[40,47,52,55],[45,52,57,64],[38,45,50,53],[41,48,53,60],[40,47,52,56]],33,[69,71,72,76,79,81],12)
print(a,b)
