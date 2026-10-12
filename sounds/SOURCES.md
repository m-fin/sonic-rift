# Sonic Rift sound palette: sources and licenses

Every file here was generated from scratch by `make_sounds.py`, with no third-party samples. Frog owns these sounds outright and can use them freely.

| File | How it was made | Source / license |
|---|---|---|
| servo_whir.wav | FM motor sweep plus gear buzz | Original synthesis, Frog's own |
| machine_hum.wav | 60 Hz harmonic stack with wobble | Original synthesis, Frog's own |
| heartbeat.wav | Synthesized lub-dub thumps (not a recording) | Original synthesis, Frog's own |
| mech_breath.wav | Filtered noise swell | Original synthesis, Frog's own |
| metal_hit.wav | Inharmonic FM bell partials | Original synthesis, Frog's own |
| circuit_glitch.wav | Bitcrushed square glitch bursts | Original synthesis, Frog's own |
| granular_cloud.wav | Granular resynthesis of the metal tones | Original synthesis, Frog's own |
| btc_blocks_melody.wav | Sonification of Bitcoin blocks 971051–971065 (transaction count sets pitch, block size sets note length) | Public block data from mempool.space API (blockchain data is public facts); sound is Frog's own |

## Not yet added
- **Freesound CC0 samples:** Freesound's API requires a free account and API key, and there isn't one on my computer. If Frog makes a free Freesound account and adds a key in a 1:1 chat with me, I'll pull CC0-only sounds and log each sound's ID, author and URL here.
- **Field recordings:** Frog can record on his phone (car interior, engine, turn signal, city ambience, rain, elevator, vending machines), with no passengers or other voices. Drop them in `sounds/field/` and I'll log them as Frog's own.

## Bionic Body piece (bionic/bionic-body.mp3), Oct 12 2026
- **Data:** readiness scores (0–5) for all 16 systems from Frog's own tracker, https://m-fin.github.io/bionic-body/tracker/data.json (tracker last updated: 2026-10-12). Snapshot in bionic_tracker_data.json; the entry order and timings are in bionic_scores_used.json.
- **Voice (AI):** Kokoro v1.0 text-to-speech (open model, Apache 2.0), voice am_michael, run locally through kokoro-onnx. It reads the 16 system names, plus the opening lines of William Blake's "Auguries of Innocence" (public domain). This is an **AI-generated voice**, so label it that way on any release.
- **Everything else:** synthesized in Python/numpy by bionic/compose.py, using the palette above. No third-party samples.
- **Tools not installed:** SuperCollider, Csound, Pure Data and sox all need system admin rights, which I don't have on this computer. MusicGen was skipped because it's too heavy without a graphics card and its model license doesn't allow commercial use.
