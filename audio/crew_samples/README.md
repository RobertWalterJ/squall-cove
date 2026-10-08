# Crew and squad voice samples (audition set)

Rendered offline with TTS used purely as a tool. The models are NOT shipped
and are git-ignored (`tools/voices/models/`). Only these small ogg files are kept.

## Licences
- Kokoro-82M (hexgrad) via kokoro-onnx (thewh1teagle): Apache-2.0. Voices used: am_michael, am_adam, am_eric, bm_george (crew); am_liam, bm_lewis, am_onyx (squad).
- Piper (rhasspy/OHF-Voice): MIT.
- Piper voice `en_US-joe-medium`: dataset licence CC0 (per its MODEL_CARD). Used for crew "joe".
- Also downloaded but NOT used for any sample: `en_US-ryan-medium` (dataset CC BY-NC-SA 4.0, non-commercial, do not ship) and `en_GB-alan-medium` (model card says "License: See URL", unverified, do not ship).

## Files
- `crew_<voice>_<line>.ogg`: raw shouted delivery. Voices: michael, adam, george, eric (Kokoro), joe (Piper). Lines: up "Up!", weaponup "Weapon up!", ready "Ready!", readytofire "Ready to fire!", loaded "Loaded!" (40 mm loader).
- `crew_<voice>_<line>_hs.ogg`: same take through the aircraft intercom/headset chain.
- `squad_<voice>_<line>.ogg`: raw only. Voices liam, lewis, onyx; lines contactfront "Contact front!", movingup "Moving up!", coverme "Cover me!".

## Settings
- Text exactly as quoted above. Kokoro speed 1.15 (crew) / 1.1 (squad), lang en-us (en-gb for george, lewis). Piper joe: length_scale 1/1.15, noise_scale 0.8, noise_w 0.9.
- Shout chain: trim silence (-40 dB, 6 ms lead, 40 ms tail), +55% 1.2-4.2 kHz presence band, 110 Hz high-pass, feed-forward compressor (-22 dB, 3.5:1, 2/60 ms), normalise, tanh saturation (drive 2.6), x1.25 gain with hard clip at 0.92, 12 ms fade-out.
- Headset chain: 4th-order band-pass 300 Hz to 3.4 kHz, tanh distortion (drive 1.8), faint band-limited carrier hiss (about -27 dB), squelch click before (45 ms noise burst) and after (60 ms burst plus 1.1 kHz tick). No ring modulation.
- Output: mono, 44.1 kHz, Ogg Vorbis quality 0.4 (libsndfile, about q4), peak normalised to -2 dBFS and re-checked on the decoded file.

## Regenerate
```
py -3.11 -m venv tools/voices/.venv
tools/voices/.venv/Scripts/python -m pip install truststore kokoro-onnx piper-tts soundfile scipy numpy
tools/voices/.venv/Scripts/python tools/voices/fetch_models.py
tools/voices/.venv/Scripts/python tools/voices/make_samples.py [voice ids...]
tools/voices/.venv/Scripts/python tools/voices/verify_samples.py
```
Behind the corporate proxy, pip may need `--use-feature=truststore` (and a PEM export of the Windows cert store via `PIP_CERT` for the first bootstrap). Scripts call `truststore.inject_into_ssl()`.

## Revision 2 (owner feedback: trailing vowel, slow lines)
- Multi-word lines are rendered word by word (kept gap 45 ms for "Ready to"+"fire", 70 ms otherwise), without exclamation marks. For each word the generator renders three variants (text with period, bare text, Kokoro phoneme string for US voices), keeps the one with the shortest low-energy release tail, then cuts the tail after the last burst (threshold -24 dB below peak, 10 ms fade; for "up" -14 dB and 6 ms fade).
- "fire" is rendered at Kokoro speed 1.6 then WSOLA time-compressed 1.35x (pitch preserved). "Weapon" is compressed 1.25x. Single words use speed 1.25 to 1.3.
- `_alt` files are the second-best variant per line (Kokoro voices only). Previous versions are in `tools/voices/work/prev/` (git-ignored).
- `tools/voices/verify_tails.py` prints before/after durations and the tail measure.

## Revision 3 (owner listening verdict)
Kept only Michael (Kokoro am_michael, crew) and Lewis (Kokoro bm_lewis, UK squad). Rejected and deleted from this folder: onyx (sounds Chinese), adam (odd pause in "ready to ... fire", bad "weapon up", "up" ends as "upe"/"up-it"), eric ("up" ends with a trailing vowel), and george, joe, liam (not chosen). Processing for Michael and Lewis is unchanged from revision 2.
`lines.json` maps every file to its text, role (crew or squad), headset file, take (main or alt) and the matching `VLINES` key in index.html (null when none). Crew lines: up, weaponup, ready, readytofire, loaded, roundup, standingby, gunready, shotout, reloading (main, alt, and headset for both). Squad: 35 Lewis lines, main and alt.
