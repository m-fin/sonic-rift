import numpy as np, wave, subprocess, sys
sys.path.insert(0,'/workspace/sonic-rift/sketches')
import importlib.util
spec=importlib.util.spec_from_file_location("b","/workspace/sonic-rift/sketches/build.py")
src=open(spec.origin).read().split("pages=[]")[0]; g={}; exec(src,g)
SR=44100; S=g['SONGS']['02-servo-pulse']; base=g['render'](S)
def ld(n):
    with wave.open(f'/workspace/sonic-rift/sounds/{n}.wav') as w: return np.frombuffer(w.readframes(w.getnframes()),'<i2')/32767
snd={k:ld(k) for k in['servo_whir','machine_hum','heartbeat','mech_breath','metal_hit','circuit_glitch','granular_cloud','btc_blocks_melody']}
mix=base*0.8; beat=60/S['bpm']; bar=4*beat
def add(x,t,g):
    i=int(t*SR); j=min(len(mix),i+len(x)); 
    if i<len(mix): mix[i:j]+=x[:j-i]*g
for b in range(S['bars']):
    t=b*bar
    if b<4: add(snd['heartbeat'],t,.5); add(snd['heartbeat'],t+2*beat,.5)
    if b%4==0: add(snd['machine_hum'],t,.12)
    if b%2==1 and 4<=b<36: add(snd['servo_whir'],t+3*beat,.18)
    if b%8==7: add(snd['metal_hit'],t,.3)
    if 8<=b<36 and b%4==2: add(snd['circuit_glitch'][:int(beat*SR)],t+3*beat,.15)
    if 16<=b<20: add(snd['granular_cloud'],t,.25) if b==16 else None; add(snd['heartbeat'],t,.6)
add(snd['mech_breath'],15*bar,.35)
add(snd['btc_blocks_melody'],20*bar,.18)
add(snd['granular_cloud'],(S['bars']-4)*bar,.3)
mix=np.tanh(mix*1.1); mix/=np.max(np.abs(mix))*1.05
with wave.open('/tmp/sp2.wav','wb') as w: w.setnchannels(1);w.setsampwidth(2);w.setframerate(SR);w.writeframes((mix*32767).astype('<i2').tobytes())
subprocess.run(['ffmpeg','-y','-loglevel','error','-i','/tmp/sp2.wav','-b:a','192k','/workspace/sonic-rift/sketches/02-servo-pulse-v2.mp3'],check=True)
print(len(mix)/SR)
