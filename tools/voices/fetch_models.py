"""Download TTS models into tools/voices/models (git-ignored). Official sources only."""
import os, sys, urllib.request
import truststore; truststore.inject_into_ssl()
M = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
os.makedirs(M, exist_ok=True)
K = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
P = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/"
files = [
 (K+"kokoro-v1.0.onnx", "kokoro-v1.0.onnx"),
 (K+"voices-v1.0.bin", "voices-v1.0.bin"),
]
for v in ["en_US/ryan/medium/en_US-ryan-medium", "en_US/joe/medium/en_US-joe-medium", "en_GB/alan/medium/en_GB-alan-medium"]:
    n = v.split("/")[-1]
    files += [(P+v+".onnx", n+".onnx"), (P+v+".onnx.json", n+".onnx.json"), (P+v.rsplit("/",1)[0]+"/MODEL_CARD", n+".MODEL_CARD")]
for url, name in files:
    dst = os.path.join(M, name)
    if os.path.exists(dst) and os.path.getsize(dst) > 0: continue
    print("GET", url, flush=True)
    try: urllib.request.urlretrieve(url, dst)
    except Exception as e: print("FAIL", url, e, flush=True); continue
    print("  ->", name, os.path.getsize(dst), flush=True)
