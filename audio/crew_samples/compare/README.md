# Kokoro vs Chatterbox comparison set (audition)

The same 8 lines rendered by the approved Kokoro pipeline (copied unchanged from the parent folder) and by Chatterbox (Resemble AI, MIT) at three expressiveness levels. Michael = gun crew, Lewis = squad. Voice identity comes from a synthetic Kokoro reference clip (am_michael, bm_lewis); no real person is cloned.

| Level | exaggeration | cfg_weight | speed-up | finish |
|---|---|---|---|---|
| `_kokoro` | n/a | n/a | approved set | shout chain, as approved |
| `_cb_calm` | 0.40 | 0.55 | 1.00 | light compression only |
| `_cb_urgent` | 0.70 | 0.40 | 1.10 | mild presence + saturation |
| `_cb_shout` | 1.10 | 0.25 | 1.15 | full shout chain (same as Kokoro set) |

Release handling: each segment is cut right after the last consonant burst (-26 dB below the segment peak; 'Up!' uses -14 dB with a 6 ms fade). 'Ready to fire' is rendered as 'Ready to' + 'fire' (fire time-compressed 1.35x, 45 ms gap). Each segment is the best of 4 Chatterbox takes chosen by measurement (short, short low-energy tail, no runaway babble). Nobody listened to these before writing this table: the numbers are duration, tail and spectral centroid only. Mono 44.1 kHz Ogg q4, decoded peak about -2.1 to -2.4 dBFS, every file under 18 KB.

| Voice / line | Kokoro dur | Kokoro centroid | calm dur / KB | urgent dur / KB | shout dur / KB | shout rms dB (Kokoro rms) |
|---|---|---|---|---|---|---|
| michael `up` | 0.22 s | 776 Hz | 0.14 s / 5.6 | 0.17 s / 6.2 | 0.12 s / 6.5 | -10.2 (-13.1) |
| michael `weaponup` | 0.63 s | 624 Hz | 0.38 s / 10.1 | 0.47 s / 11.4 | 0.41 s / 11.8 | -7.5 (-12.7) |
| michael `ready` | 0.38 s | 640 Hz | 0.28 s / 8.3 | 0.41 s / 10.3 | 0.28 s / 10.4 | -7.3 (-8.9) |
| michael `readytofire` | 0.80 s | 1057 Hz | 0.91 s / 13.1 | 1.12 s / 17.9 | 0.93 s / 15.3 | -12.5 (-11.9) |
| michael `loaded` | 0.41 s | 618 Hz | 0.33 s / 9.0 | 0.32 s / 8.0 | 0.49 s / 11.3 | -6.8 (-9.0) |
| lewis `contactfront` | 0.87 s | 1261 Hz | 0.72 s / 11.2 | 0.61 s / 11.1 | 0.60 s / 15.5 | -12.8 (-11.8) |
| lewis `takingfire` | 0.69 s | 1150 Hz | 0.68 s / 11.6 | 0.70 s / 11.8 | 0.91 s / 15.4 | -12.5 (-11.5) |
| lewis `mandown` | 0.56 s | 1030 Hz | 0.71 s / 13.3 | 0.65 s / 14.9 | 0.57 s / 11.6 | -11.0 (-11.6) |

Files are named `cmp_<voice>_<line>_<kokoro|cb_calm|cb_urgent|cb_shout>.ogg`. Regenerate: see `tools/voices/make_expressive.py compare`. Chatterbox output carries Resemble's Perth watermark.
