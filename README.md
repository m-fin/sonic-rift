# Sonic Rift

Sonic Rift is Matthew "Frog" Finley's electronic music project: https://soundcloud.com/sonicrift

This repo holds music made with code: the scripts that build the sounds, sketches and tracks, plus small previews.

## Folders

- `sketches/` – short music sketches that play in the browser (`index.html` lists them), the script that builds them, and MP3 previews.
- `sounds/` – the sound palette (servo whir, machine hum, heartbeat and more) and the script that makes it.
- `bionic/` – the code for the track **Bionic Body**. Each of the 16 body systems on the Bionic Body tracker (https://m-fin.github.io/bionic-body) becomes an instrument, and its 0–5 readiness score sets how loud it is.
  - `bionic/data/` – the tracker data and the scores the track used.
- `game/` – game music and sound effects: the title loop, Neon Snake, and the DRIFTHOME cabin scene. Scripts plus OGG loops/sounds and MP3 previews.

## How the sounds are made

All the sounds are made with code. No outside samples are used. See [`sounds/SOURCES.md`](sounds/SOURCES.md) for how each one was made.

## AI voice

The Bionic Body track uses Kokoro, an AI text-to-speech voice, to read the system names and lines from William Blake's "Auguries of Innocence" (public domain). The release is labeled as using an AI voice.

## Listen in the browser

Once GitHub Pages is turned on: https://m-fin.github.io/sonic-rift/sketches/
