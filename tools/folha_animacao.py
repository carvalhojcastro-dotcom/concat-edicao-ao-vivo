#!/usr/bin/env python3
"""Folha de conferência: uma linha por animação, quadros em vários instantes depois do início,
recortados na faixa da legenda. Use o projeto real (aberto na janela ou não), nunca uma cópia.

Uso: folha_animacao.py <projeto> <saida.jpg> <t0,t0,...> [--offs=0.03,0.1,...] [--faixa=0.45,0.8]
"""
import os, sys, subprocess, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from concat_api import Concat
from PIL import Image, ImageDraw

path, out = os.path.abspath(sys.argv[1]), sys.argv[2]
t0s = [float(x) for x in sys.argv[3].split(",")]
opc = dict(a[2:].split("=", 1) for a in sys.argv[4:] if a.startswith("--"))
offs = [float(x) for x in opc.get("offs", "0.03,0.1,0.2,0.35,0.6,1.0,1.6").split(",")]
y0, y1 = [float(x) for x in opc.get("faixa", "0.45,0.8").split(",")]
api = Concat(path); api.sock.settimeout(600)
try:
    api.call("project.get", path=path); janela = True
except RuntimeError:
    api.call("project.open", path=path); janela = False
d = tempfile.mkdtemp(dir=os.path.expanduser("~/Desktop/Concat/ferramentas/dist/verificacao"))
w, h = 540, 960
cw, ch = w, int(h * (y1 - y0))
folha = Image.new("RGB", (cw * len(offs), ch * len(t0s)))
dr = ImageDraw.Draw(folha)
for r, t0 in enumerate(t0s):
    for c, o in enumerate(offs):
        f = os.path.join(d, "q.png")
        api.call("preview.frame", path=path, time=t0 + o, output=f, width=w, height=h)
        im = Image.open(f).convert("RGB").crop((0, int(h * y0), w, int(h * y1)))
        folha.paste(im, (c * cw, r * ch))
        dr.text((c * cw + 4, r * ch + 2), f"+{o:.2f}s", fill="yellow")
if not janela:
    api.call("project.close", path=path, save=False)
folha.save(out)
os.remove(os.path.join(d, "q.png")); os.rmdir(d)
print(out)
