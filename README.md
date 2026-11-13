# sonicrift

sonicrift is Matthew "Frog" Finley's electronic music project: https://soundcloud.com/sonicrift

This repo holds music made with code: the scripts that build the sounds, sketches and tracks, plus small previews.

## Folders

- `sketches/` – short music sketches that play in the browser (`index.html` lists them), and the script that builds them (plus MP3 previews when you rebuild).
- `sounds/` – the sound palette (servo whir, machine hum, heartbeat and more) and the script that makes it.
- `bionic/` – the code for the track **Bionic Body**. Each of the 16 body systems on the Bionic Body tracker (https://m-fin.github.io/bionic-body) becomes an instrument, and its 0–5 readiness score sets how loud it is.
  - `bionic/data/` – the tracker data and the scores the track used.
- `game/` – game music and sound effects: the title loop, Neon Snake, and the DRIFTHOME cabin scene. The scripts render the OGG loops/sounds and MP3 previews.
- `ambient/` – `make.py` builds the seamless ambient loops for **Space Drift** (D major, 60 BPM) and **Machine Sleep** (A minor, 54 BPM). It reuses the synth helpers in `game/premiere/make.py`.

## Rebuild the audio

You need Python 3 with `numpy` and `soundfile` (`pip install -r requirements.txt`) and `ffmpeg`. Every script
can be run from anywhere and writes its output next to itself, for example `python3 sketches/build.py`.
Run `sounds/make_sounds.py` first, since other scripts reuse its WAVs. The audio files (WAV/OGG/MP3) are
build output and aren't committed. CI renders everything on each pull request.

`bionic/vox.py` also needs `kokoro-onnx` and the Kokoro model files. Set `KOKORO_DIR` to the folder with
`kokoro-v1.0.onnx` and `voices-v1.0.bin`, then run `bionic/compose.py`.

## How the sounds are made

All the sounds are made with code. No outside samples are used. See [`sounds/SOURCES.md`](sounds/SOURCES.md) for how each one was made.

## AI voice

The Bionic Body track uses Kokoro, an AI text-to-speech voice, to read the system names and lines from William Blake's "Auguries of Innocence" (public domain). The release is labeled as using an AI voice.

## Listen in the browser

Once GitHub Pages is turned on: https://m-fin.github.io/sonic-rift/sketches/
