import numpy as np, soundfile as sf, subprocess
exec(open('make.py').read().split('# ---- level 1')[0])
def build(name,bars,prog,mels,lead_d,arp,bassmode,drums,lg=.15):
    L=int(bars*16*st*SR); mix=np.zeros(L)
    def put(x,s,g):
        i=int(s*st*SR); j=min(L,i+len(x)); mix[i:j]+=x[:j-i]*g
        if i+len(x)>L: mix[:i+len(x)-L]+=x[L-i:]*g
    for b in range(bars):
        s0=b*16; root=prog[b%len(prog)]; mel=mels[(b//8)%len(mels)] if b%2==0 else mels[(b//8+1)%len(mels)]
        for k,n in enumerate(mel):
            if n is not None: put(sq(mtof(n),int(st*SR*2),lead_d)*env(int(st*SR*2),4),s0+k,lg)
        ch=[root+12,root+15,root+19]
        for k in range(0,16,arp): put(sq(mtof(ch[(k//arp)%3]),int(st*SR*.8),.125)*env(int(st*SR*.8),14),s0+k,.06)
        for k in range(16):
            if bassmode=='half' and k in(0,6,10): put(tri(mtof(root-12),int(st*SR*3)),s0+k,.3)
            if bassmode=='drive': put(tri(mtof(root-12+(12 if k%2 else 0)),int(st*SR*.9)),s0+k,.24)
        for k in range(16):
            kick=noise[:int(.1*SR)]; kick=np.repeat(kick[::10],10)[:len(kick)]*env(len(kick),28)
            if drums=='half':
                if k in(0,10): put(kick,s0+k,.3)
                if k==8: put(noise[:int(.12*SR)]*env(int(.12*SR),25),s0+k,.22)
                if k%4==2: put(noise[:int(.025*SR)]*env(int(.025*SR),140),s0+k,.05)
            else:
                if k%4==0: put(kick,s0+k,.3)
                if k%8==4: put(noise[:int(.1*SR)]*env(int(.1*SR),30),s0+k,.22)
                put(noise[:int(.02*SR)]*env(int(.02*SR),160),s0+k,.06)
    ogg(name,mix); return L/SR
d=build('level2_loop',48,[57,62,64,53,57,62,52,52],
  [[69,None,None,None,72,None,71,None,None,None,69,None,64,None,None,None],
   [76,None,None,74,None,None,72,None,71,None,None,None,None,None,None,None],
   [None]*16],.5,2,'half','half',.13)
m=build('montage_loop',16,[57,53,48,55],
  [[81,79,76,79,81,84,81,79,76,74,76,79,76,74,72,74],[76,72,69,72,76,79,76,72,74,71,67,71,74,76,74,71]],.25,1,'drive','fast',.12)
print(d,m)
for n in('level2_loop','montage_loop'): subprocess.run(['ffmpeg','-y','-loglevel','error','-i',n+'.wav','-b:a','192k',n.split('_')[0]+'_preview.mp3'])
