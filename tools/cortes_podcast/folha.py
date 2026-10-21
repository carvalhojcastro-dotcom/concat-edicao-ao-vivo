"""Folha de conferência do MP4 final: um quadro no meio de cada peça de enquadramento e um no fim
de cada composição de legenda. Uso: folha.py <dir do corte> <final.mp4> <saida.jpg>"""
import json, os, subprocess, sys, tempfile
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..")); import plataforma  # noqa: E401,E402 (acha o ffmpeg no Windows)
pasta, mp4, out = sys.argv[1:4]
cfg = json.load(open(os.path.join(pasta, "corte.json")))
plano = json.load(open(os.path.join(pasta, "plano.json")))
words = json.load(open(os.path.join(pasta, "words_leg.json")))
# tempo de saída de cada peça
segs = cfg["segmentos"]
def saida(t):
    off = 0
    for a, b in segs:
        if a - 1e-3 <= t <= b + 1e-3:
            return off + t - a
        off += b - a
    return None
ts = []
for p in cfg["pecas"]:
    m = saida((p["s"] + p["e"]) / 2)
    if m is not None and p["e"] - p["s"] > 0.5:
        ts.append(m)
for f in plano["frases"]:
    if f["preset"] != "linha":
        n = sum(len(l.split()) for l in f["linhas"])
        ts.append(words[f["de"] + n - 1]["end"] + 0.1)
ts = sorted(set(round(t, 2) for t in ts))
d = tempfile.mkdtemp()
arqs = []
for i, t in enumerate(ts):
    a = os.path.join(d, f"{i:03d}.jpg")
    subprocess.run(["ffmpeg", "-v", "fatal", "-y", "-ss", f"{t:.2f}", "-i", mp4, "-frames:v", "1", "-vf",
                    'scale=270:-1', '-pix_fmt', 'yuvj420p', a])
    arqs.append(a)
cols = 6
rows = (len(arqs) + cols - 1) // cols
subprocess.run(["ffmpeg", "-v", "error", "-y", "-pattern_type", "glob", "-i", os.path.join(d, "*.jpg"),
                "-vf", f"tile={cols}x{rows}:padding=3", "-frames:v", "1", out], check=True)
print(out, len(arqs), "quadros")
