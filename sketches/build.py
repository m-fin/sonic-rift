import numpy as np, json, wave, subprocess
SR=44100
def mtof(n): return 440*2**((n-69)/12)
SONGS={
 "01-circuit-wake":dict(title="Circuit Wake",bpm=124,bars=36,
   bass=[45,45,57,45, 45,48,45,43],      # 8th notes, 1 bar loop pattern x2 bars
   lead=[69,None,72,None,76,None,74,72, 69,None,None,67,69,None,None,None],
   chords=[[57,60,64],[53,57,60],[55,59,62],[52,55,59]], wave="saw"),
 "02-servo-pulse":dict(title="Servo Pulse",bpm=132,bars=40,
   bass=[38,38,50,38, 41,38,50,36],
   lead=[74,77,81,77,74,None,72,None, 74,77,79,None,77,None,None,None],
   chords=[[50,53,57],[46,50,53],[48,52,55],[45,48,52]], wave="square"),
 "03-bionic-dawn":dict(title="Bionic Dawn",bpm=110,bars=30,
   bass=[40,None,40,52, 43,None,43,47],
   lead=[64,None,67,71,None,None,69,None, 67,None,64,None,62,None,None,None],
   chords=[[52,55,59,62],[48,52,55,59],[43,47,50,54],[45,48,52,55]], wave="tri"),
}
def osc(f,n,w,t0=0):
  t=np.arange(n)/SR; ph=(f*t)%1
  if w=="saw": return 2*ph-1
  if w=="square": return np.sign(ph-.5)
  if w=="tri": return 4*np.abs(ph-.5)-1
  return np.sin(2*np.pi*f*t)
def env(n,a=.005,r=.1):
  e=np.ones(n); ai=int(a*SR); ri=min(int(r*SR),n)
  e[:ai]=np.linspace(0,1,ai) if ai else 1; e[n-ri:]*=np.linspace(1,0,ri); return e
def lp(x,k): # one-pole lowpass
  y=np.empty_like(x); s=0.
  for i in range(len(x)): s+=k*(x[i]-s); y[i]=s
  return y
def render(s):
  beat=60/s['bpm']; bar=4*beat; L=int(s['bars']*bar*SR)+SR*2
  mix=np.zeros(L); bars=s['bars']
  def add(sig,start):
    i=int(start*SR); j=min(L,i+len(sig)); mix[i:j]+=sig[:j-i]
  for b in range(bars):
    sec=b//4 # sections of 4 bars
    intro=b<4; brk=16<=b<20; outro=b>=bars-4
    for q in range(4):
      t=b*bar+q*beat
      if not brk:  # kick
        n=int(.3*SR); tt=np.arange(n)/SR
        add(np.sin(2*np.pi*(45+120*np.exp(-tt*30))*tt)*np.exp(-tt*9)*.9,t)
      if q in(1,3) and not intro: # clap
        n=int(.15*SR); add(np.random.randn(n)*np.exp(-np.arange(n)/SR*25)*.25,t)
      for h in (0,1): # hats on offbeats
        if h==1 and not intro or (intro and b>=2 and h==1):
          n=int(.05*SR); add(np.diff(np.random.randn(n+1))*np.exp(-np.arange(n)/SR*80)*.08,t+h*beat/2)
    # bass 8ths
    if not intro or b>=2:
      for k in range(8):
        nt=s['bass'][k]
        if nt is None or brk: continue
        n=int(beat/2*SR*.9); sig=osc(mtof(nt-12),n,"saw")*env(n,.003,.05)
        add(lp(sig,.08)*.45,b*bar+k*beat/2)
    # pad chords
    ch=s['chords'][b%4]; n=int(bar*SR)
    pad=sum(osc(mtof(c)*(1+d),n,"saw") for c in ch for d in(-.003,.003))/len(ch)/2
    add(lp(pad*env(n,.4,.4),.02)*(.35 if brk or intro else .2),b*bar)
    # lead 16th grid over 2 bars, from bar 8, not outro
    if b>=8 and not outro:
      for k in range(8):
        idx=(b%2)*8+k; nt=s['lead'][idx]
        if nt is None: continue
        n=int(beat/2*SR*1.6); sig=osc(mtof(nt),n,s['wave'])*env(n,.01,.2)
        add(lp(sig,.15)*.22,b*bar+k*beat/2)
  # simple echo
  d=int(beat*.75*SR); out=mix.copy(); out[d:]+=mix[:-d]*.3; out[2*d:]+=mix[:-2*d]*.12
  out=np.tanh(out*1.2); out/=np.max(np.abs(out))*1.05
  return out
pages=[]
for slug,s in SONGS.items():
  a=render(s); pcm=(a*32767).astype('<i2')
  with wave.open(slug+'.wav','wb') as w: w.setnchannels(1);w.setsampwidth(2);w.setframerate(SR);w.writeframes(pcm.tobytes())
  subprocess.run(['ffmpeg','-y','-loglevel','error','-i',slug+'.wav','-b:a','192k',slug+'.mp3'],check=True)
  subprocess.run(['rm',slug+'.wav'])
  dur=len(a)/SR; pages.append((slug,s['title'],dur))
  html=open('template.html').read().replace('__TITLE__',s['title']).replace('__DATA__',json.dumps(s))
  open(slug+'.html','w').write(html)
  print(slug,round(dur,1),'s')
idx="<html><body style='background:#000;color:#f7931a;font-family:monospace'><h1>Sonic Rift: code sketches</h1>"+"".join(f"<p><a style='color:#f7931a' href='{p}.html'>{t}</a></p>" for p,t,_ in pages)+"</body></html>"
open('index.html','w').write(idx)
