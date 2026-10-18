#!/usr/bin/env python3
"""Escolhe a cor das palavras de destaque das Legendas Dinâmicas pelo fundo real atrás delas.

Para cada palavra colorida (cor diferente de branco), mede o brilho do que está atrás dela no
meio do tempo em que aparece, na posição dela: o B-roll de imagem, se houver um por cima do
vídeo nesse momento, ou o quadro do vídeo (com o zoom e o deslocamento do clipe). Fundo
escuro -> branco; fundo claro -> a cor escura de destaque.

Uso: contraste_destaques.py <projeto> [cor_escura=#1e40af] [limite=0.45]
"""
import os, subprocess, sys, tempfile
import numpy as np
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from concat_api import Concat, timeline

path = sys.argv[1]
ESCURA = sys.argv[2] if len(sys.argv) > 2 else "#1e40af"
LIMITE = float(sys.argv[3]) if len(sys.argv) > 3 else 0.45
CLARA = "#ffffff"
api = Concat(path); api.sock.settimeout(300)
try:
    v = api.call("project.get", path=path)
except RuntimeError:
    v = api.call("project.open", path=path)
media = {m["id"]: m for m in v["project"]["media"]}
tl = timeline(v)
imgs = [c for c in tl["clips"] if c["kind"] == "image"]
vids = [c for c in tl["clips"] if c["kind"] == "video"]
tmp = tempfile.mkdtemp()

def quadro_video(c, t):
    src = c["sourceStart"] + (t - c["start"]) * c.get("speed", 1.0)
    out = os.path.join(tmp, "q.png")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{src:.3f}", "-i", media[c["mediaId"]]["path"],
                    "-frames:v", "1", "-vf", "scale=540:-1", out], check=True)
    return Image.open(out).convert("L")

def brilho(img, c, x, y, w, h):
    """Média do brilho (0-1) da área (x, y, w, h) da tela, desfazendo zoom/deslocamento do clipe."""
    s, ox, oy = c.get("scale", 1.0), c.get("offsetX", 0.0), c.get("offsetY", 0.0)
    W, H = img.size
    def fonte(px, py):
        return ((0.5 + (px - 0.5 - ox) / s) * W, (0.5 + (py - 0.5 - oy) / s) * H)
    x0, y0 = fonte(x - w / 2, y - h / 2); x1, y1 = fonte(x + w / 2, y + h / 2)
    caixa = img.crop((max(0, int(x0)), max(0, int(y0)), min(W, int(x1) + 1), min(H, int(y1) + 1)))
    return float(np.asarray(caixa, dtype=np.float32).mean() / 255)

cmds = []
for c in sorted([c for c in tl["clips"] if c["kind"] == "text" and c["text"]["color"].lower() != CLARA],
                key=lambda c: c["start"]):
    t = c["start"] + c["duration"] / 2
    keys = c.get("keys") or []
    oy = next((k["value"] for k in sorted(keys, key=lambda k: -k["at"]) if k["property"] == "offsetY"), c.get("offsetY", 0.0))
    x, y = 0.5 + c.get("offsetX", 0.0), 0.5 + oy
    fs = c["text"]["fontSize"]
    w, h = min(0.9, 0.55 * fs * len(c["text"]["content"]) * 3840 / 2160), fs * 1.1
    img_sob = [i for i in imgs if i["start"] <= t < i["start"] + i["duration"]]
    if img_sob:
        i = img_sob[0]
        fundo, nome = Image.open(media[i["mediaId"]]["path"]).convert("L"), "B-roll " + os.path.basename(media[i["mediaId"]]["path"])
        clip = i
    else:
        clip = next(vv for vv in vids if vv["start"] <= t < vv["start"] + vv["duration"])
        fundo, nome = quadro_video(clip, t), "vídeo"
    b = brilho(fundo, clip, x, y, w, h)
    cor = CLARA if b < LIMITE else ESCURA
    muda = cor.lower() != c["text"]["color"].lower()
    print(f"{c['text']['content']:14s} {c['start']:6.2f}s  fundo={nome:24s} brilho={b:.2f} -> {cor}{'  (TROCA)' if muda else ''}")
    if muda:
        cmds.append({"op": "updateClip", "clipId": c["id"], "patch": {"text": dict(c["text"], color=cor)}})
if cmds:
    api.batch(cmds)
api.call("project.save", path=path)
print(f"pronto: {len(cmds)} palavra(s) trocada(s)")
