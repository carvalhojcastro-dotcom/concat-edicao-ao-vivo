#!/usr/bin/env python3
"""Ajusta os B-rolls de imagem de um projeto: entram e saem junto com os cortes do vídeo e
ganham um movimento lento (aproximar, afastar, deslizar), alternando de uma imagem para outra.

Uso: broll_animar.py <projeto>
Regra de tempo: início no corte mais próximo do início atual (se o mais próximo estiver a mais
de 0,5 s, o corte anterior, desde que a até 1,6 s); fim no corte mais próximo do fim atual;
no mínimo 1 s, sem encostar na imagem seguinte.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from concat_api import Concat, timeline

SUAVE = [0.25, 0.1, 0.25, 1.0]
# (escala início, escala fim, offsetX início, fim, offsetY início, fim)
MOVIMENTOS = [
    (1.00, 1.12, 0.0, 0.0, 0.0, 0.0),        # aproxima
    (1.14, 1.02, 0.0, 0.0, 0.0, 0.0),        # afasta
    (1.10, 1.10, 0.0, 0.0, 0.03, -0.03),     # sobe
    (1.08, 1.16, -0.025, 0.025, 0.0, 0.0),   # aproxima indo para a direita
    (1.10, 1.10, 0.03, -0.03, 0.0, 0.0),     # desliza para a esquerda
    (1.16, 1.06, 0.0, 0.0, -0.02, 0.02),     # afasta descendo
]

path = sys.argv[1]
api = Concat(path); api.sock.settimeout(180)
api.call("project.open", path=path)
tl = timeline(api.view())
v = sorted([c for c in tl["clips"] if c["kind"] == "video"], key=lambda c: c["start"])
cortes = sorted({c["start"] for c in v} | {v[-1]["start"] + v[-1]["duration"]})
imgs = sorted([c for c in tl["clips"] if c["kind"] == "image"], key=lambda c: c["start"])

novos = []
for k, c in enumerate(imgs):
    s, e = c["start"], c["start"] + c["duration"]
    ini = min(cortes, key=lambda x: abs(x - s))
    if abs(ini - s) > 0.5:
        antes = [x for x in cortes if x <= s and s - x <= 1.6]
        ini = antes[-1] if antes else min([x for x in cortes if x >= s])
    fim = min(cortes, key=lambda x: abs(x - e))
    if fim - ini < 1.0:
        fim = min(x for x in cortes if x - ini >= 1.0)
    if novos and ini < novos[-1][2]:
        ini = novos[-1][2]
    novos.append((c, ini, fim))

cmds = []
for c, ini, fim in novos:  # encurta primeiro, move, depois acerta a duração
    cmds.append({"op": "trimClip", "clipId": c["id"], "edge": "end", "delta": min(0.0, (fim - ini) - c["duration"]), "ripple": False})
cmds.append({"op": "moveClips", "moves": [{"clipId": c["id"], "start": ini, "trackId": c["trackId"]} for c, ini, _ in novos]})
api.batch([x for x in cmds if not (x["op"] == "trimClip" and abs(x["delta"]) < 1e-9)])
tl = timeline(api.view())
por_id = {c["id"]: c for c in tl["clips"]}
cmds = []
for k, (c, ini, fim) in enumerate(novos):
    atual = por_id[c["id"]]
    delta = (fim - ini) - atual["duration"]
    if abs(delta) > 1e-6:
        cmds.append({"op": "trimClip", "clipId": c["id"], "edge": "end", "delta": delta, "ripple": False})
    # Limpa as keys de um movimento anterior: sobra de outra propriedade (ex.: offsetX de um
    # deslize) somada ao novo movimento pode mostrar borda preta.
    for key in atual.get("keys") or []:
        if key["property"] in ("scale", "offsetX", "offsetY"):
            cmds.append({"op": "clearClipKey", "clipId": c["id"], "property": key["property"], "at": key["at"]})
    s0, s1, x0, x1, y0, y1 = MOVIMENTOS[k % len(MOVIMENTOS)]
    for prop, a, b in (("scale", s0, s1), ("offsetX", x0, x1), ("offsetY", y0, y1)):
        if a == b == (1.0 if prop == "scale" else 0.0):
            continue
        cmds.append({"op": "setClipKey", "clipId": c["id"], "property": prop, "at": 0.0, "value": a, "ease": SUAVE})
        cmds.append({"op": "setClipKey", "clipId": c["id"], "property": prop, "at": 1.0, "value": b, "ease": SUAVE})
api.batch(cmds)
api.call("project.save", path=path)
for k, (c, ini, fim) in enumerate(novos):
    print(f"{c['id']}: {ini:6.2f}-{fim:6.2f}s ({fim-ini:.2f}s)  movimento {k % len(MOVIMENTOS) + 1}")
