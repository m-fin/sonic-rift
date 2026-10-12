import json, soundfile as sf
from kokoro_onnx import Kokoro
k=Kokoro('/workspace/.tts-models/kokoro-v1.0.onnx','/workspace/.tts-models/voices-v1.0.bin')
d=json.load(open('data/bionic_tracker_data.json'))
for e in d['entries']:
    a,sr=k.create(e['system'].replace('/',', '),voice='am_michael',speed=0.9,lang='en-us'); sf.write(f"vox_{e['id']}.wav",a,sr)
blake="To see a world in a grain of sand. And a heaven in a wild flower. Hold infinity in the palm of your hand. And eternity in an hour."
a,sr=k.create(blake,voice='am_michael',speed=0.85,lang='en-us'); sf.write("vox_blake.wav",a,sr); print(sr)
