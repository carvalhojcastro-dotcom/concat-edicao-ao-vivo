#!/usr/bin/env python3
"""Sombra em degradê atrás das legendas: para legenda branca sobre roupa ou fundo claro.

A legenda branca some numa camiseta branca (Dr. Leonardo, 2026-10-22). Contorno grosso está vetado
("não use traços tão fortes") e placa atrás de cada palavra não serve para os blocos dinâmicos; então
uma imagem PNG transparente em cima, escurecendo de --inicio até --cheio (fração da altura) e
mantendo --forca de preto até a base, entra numa trilha entre o vídeo e as legendas, no vídeo todo.
Rodar de novo troca a sombra anterior.

Uso: sombra_legenda.py <projeto> [--forca=0.7] [--inicio=0.7] [--cheio=0.8]
"""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from concat_api import Concat, timeline  # noqa: E402

args = [a for a in sys.argv[1:] if not a.startswith("--")]
opc = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
path = args[0]
FORCA, INICIO, CHEIO = float(opc.get("forca", 0.7)), float(opc.get("inicio", 0.7)), float(opc.get("cheio", 0.8))
# nome muda com os parâmetros: o Concat guarda a imagem decodificada pelo caminho, e um PNG novo com o
# mesmo nome pode não aparecer
NOME = f"sombra_legenda_{FORCA:g}_{INICIO:g}_{CHEIO:g}.png"
eh_sombra = lambda caminho: os.path.basename(caminho or "").startswith("sombra_legenda")  # noqa: E731

W, H = 1080, 1920
y = np.linspace(0, 1, H)
t = np.clip((y - INICIO) / (CHEIO - INICIO), 0, 1)
# smoothstep: sem linha visível onde a sombra começa. O Concat aplica o alfa de imagem duas vezes
# (medido: alfa 0,55 escureceu só 28%), então o PNG leva a raiz para escurecer --forca de verdade
alfa = np.sqrt(FORCA * t * t * (3 - 2 * t))
png = np.zeros((H, W, 4), np.uint8)
png[..., :3] = 12
png[..., 3] = np.round(alfa * 255).astype(np.uint8)[:, None]
arq = os.path.join(path, "midia", NOME)
os.makedirs(os.path.dirname(arq), exist_ok=True)
cv2.imwrite(arq, png)

api = Concat(path)
api.sock.settimeout(300)
try:
    api.call("project.get", path=path)   # aberto na janela? então é ela que responde
except RuntimeError:
    api.call("project.open", path=path)
proj = api.view()["project"]
tl = timeline(api.view())
velhas = [c["id"] for c in tl["clips"] if c["kind"] == "image"
          and any(m["id"] == c.get("mediaId") and eh_sombra(m.get("path")) for m in proj["media"])]
if velhas:
    api.edit({"op": "removeClips", "clipIds": velhas})
    tl = timeline(api.view())
video = [c for c in tl["clips"] if c["kind"] == "video"]
fim = max(c["start"] + c["duration"] for c in video)
baixo = video[0]["trackId"]
ocupadas = {c["trackId"] for c in tl["clips"] if c["kind"] != "image" or c["id"] in velhas}
trilha = next((t["id"] for t in tl["tracks"] if t["id"] != baixo and t["id"] not in ocupadas), None)
if trilha is None:
    # as legendas ocupam todas as trilhas de cima: o vídeo desce para uma trilha nova embaixo e a sombra
    # fica na dele, entre o vídeo e as legendas
    antes = {t["id"] for t in tl["tracks"]}
    tl = timeline(api.edit({"op": "addTrack", "bottom": True}))
    nova = next(t["id"] for t in tl["tracks"] if t["id"] not in antes)
    api.edit({"op": "moveClips", "moves": [{"clipId": c["id"], "start": c["start"], "trackId": nova} for c in video]})
    trilha = baixo
    tl = timeline(api.view())

mid = next((m["id"] for m in proj["media"] if os.path.basename(m.get("path", "")) == NOME), None)
if mid is None:
    antes = {m["id"] for m in proj["media"]}
    api.call("media.import", path=path, file=os.path.abspath(arq))
    mid = next(m["id"] for m in api.view()["project"]["media"] if m["id"] not in antes)
antes_c = {c["id"] for c in tl["clips"]}
tl = timeline(api.edit({"op": "addClip", "mediaId": mid, "trackId": trilha, "start": 0.0}))
clip = next(c for c in tl["clips"] if c["id"] not in antes_c)
api.edit({"op": "trimClip", "clipId": clip["id"], "edge": "end", "delta": fim - clip["duration"], "ripple": False})
api.call("project.save", path=path)
print(f"sombra na trilha {trilha}, 0-{fim:.2f}s (forca {FORCA}, de {INICIO} a {CHEIO})")
