"""Render SYNTHETIC reference clips (Kokoro-82M, Apache-2.0) used as zero-shot prompts for Chatterbox.

No real person's voice is used anywhere: every reference is Kokoro output.
Run with the Kokoro venv:  tools/voices/.venv/Scripts/python tools/voices/make_refs.py [ids...]
Output: tools/voices/work/refs/<id>.wav (24 kHz mono, git-ignored)
"""
import os, sys
import numpy as np
import soundfile as sf
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_samples as ms

OUT = os.path.join(HERE, "work", "refs")

REF_TEXT = ("Alright, listen up. We move on my signal, keep your spacing and watch your sectors. "
            "If anything changes, call it out, loud and clear. Stay low, stay together, and let's get this done.")

# id -> (kokoro voice, lang, speed)
REFS = {
    "michael": ("am_michael", "en-us", 1.0),
    "lewis":   ("bm_lewis", "en-gb", 1.0),
    "echo":    ("am_echo", "en-us", 1.05),
    "nicole":  ("af_nicole", "en-us", 1.05),
    "daniel":  ("bm_daniel", "en-gb", 0.97),
    "fable":   ("bm_fable", "en-gb", 0.92),
    "sarah":   ("af_sarah", "en-us", 1.0),
    "fenrir":  ("am_fenrir", "en-us", 1.0),
    "george":  ("bm_george", "en-gb", 0.97),
    "adam":    ("am_adam", "en-us", 0.97),
    "emma":    ("bf_emma", "en-gb", 1.0),
}

def main():
    os.makedirs(OUT, exist_ok=True)
    only = set(sys.argv[1:])
    for rid, (v, lang, sp) in REFS.items():
        if only and rid not in only:
            continue
        a, sr = ms.synth_kokoro(REF_TEXT, v, lang, sp)
        a = a / (np.abs(a).max() + 1e-9) * 0.8
        sf.write(os.path.join(OUT, rid + ".wav"), a, sr, subtype="PCM_16")
        print("ref", rid, v, f"{len(a)/sr:.1f}s", flush=True)

if __name__ == "__main__":
    main()
