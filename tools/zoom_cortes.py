#!/usr/bin/env python3
"""Zoom seco por frase (punch-in, sem animação): muda o enquadramento do vídeo em trechos.

Uso: zoom_cortes.py <projeto> <legendas_ref.json> <plano.json>
  legendas_ref: o concat.json com as legendas simples (dá o início de cada palavra).
  plano: {"rosto": [0.48, 0.34], "trechos": [[indice_palavra_inicial, escala], ...]}
    Cada trecho vale da palavra indicada até o próximo trecho. A troca cai na emenda
    existente mais próxima (até 0,4 s) ou num corte novo no início da palavra.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from concat_api import Concat, timeline, fps_de

FPS = fps_de(sys.argv[1])  # o fps do projeto (24 ou 30)
path, ref, plano = sys.argv[1], json.load(open(sys.argv[2])), json.load(open(sys.argv[3]))
fx, fy = plano["rosto"]
words = sorted([c for c in ref["timelines"][0]["clips"] if c["kind"] == "text"], key=lambda c: c["start"])
api = Concat(path); api.sock.settimeout(180)
api.call("project.open", path=path)

def videos():
    return sorted([c for c in timeline(api.view())["clips"] if c["kind"] == "video"], key=lambda c: c["start"])

# 1. Pontos de troca.
trocas = []
for i, escala in plano["trechos"]:
    t = words[i]["start"]
    if t < 1e-6:
        trocas.append((0.0, escala)); continue
    emendas = [c["start"] for c in videos()]
    perto = min(emendas, key=lambda e: abs(e - t))
    if abs(perto - t) <= 0.4:
        t = perto
    else:
        t = round(t * FPS) / FPS
        clip = next(c for c in videos() if c["start"] + 1e-6 < t < c["start"] + c["duration"] - 1e-6)
        api.edit({"op": "splitClips", "clipIds": [clip["id"]], "time": t})
    trocas.append((t, escala))

# 2. Escala de cada clipe de vídeo pelo trecho onde ele começa, com o rosto parado no lugar.
cmds = []
for c in videos():
    escala = [e for t, e in trocas if t <= c["start"] + 1e-6][-1]
    cmds.append({"op": "setClipTransform", "clipId": c["id"], "scale": escala,
                 "offsetX": (fx - 0.5) * (1 - escala), "offsetY": (fy - 0.5) * (1 - escala)})
api.batch(cmds)
api.call("project.save", path=path)
for t, e in trocas: print(f"{int(t//60)}:{t%60:05.2f}  {round(e*100)}%")
print(f"pronto: {len(videos())} clipes de vídeo")
