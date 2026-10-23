#!/usr/bin/env python3
"""Headline de abertura: caixa branca com letra preta no centro da tela, com o hook do vídeo.

Pedido de 2026-10-23 (CAPs do Dr. Leonardo, versão 2): "uma headline no centro da tela (fundo branco
letra preta) com algum hook escrito para segurar a atenção". Fica só na abertura: até o fim do 1º
conjunto de zoom (aberto), entre 2 e 5 s, para não cobrir o rosto nos closes. Entra de baixo para cima
como as legendas. Rodar de novo troca a headline anterior.

Uso: headline.py <projeto> "Linha 1|Linha 2" [--fim=s] [--altura=0.0] [--tamanho=0.044]
  "|" quebra a linha; --altura é o deslocamento do centro (0 = meio da tela, positivo = para baixo).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from concat_api import Concat, timeline  # noqa: E402

args = [a for a in sys.argv[1:] if not a.startswith("--")]
opc = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
path, texto = args[0], args[1].replace("|", "\n")
ALTURA, TAMANHO = float(opc.get("altura", 0.0)), float(opc.get("tamanho", 0.044))
NOME = "headline"
ESTILO = {"content": texto, "fontFamily": "Helvetica", "fontWeight": 700.0, "italic": False, "fontSize": TAMANHO,
          "color": "#000000", "background": "#ffffff", "backgroundPaddingX": 0.035, "backgroundPaddingY": 0.022,
          "backgroundRadius": 0.012, "align": "center", "lineHeight": 1.12, "tracking": -0.03 * TAMANHO,
          "shadow": False, "strokeWidth": 0.0, "strokeColor": "#000000", "opacity": 1.0, "maxWidth": 0.0, "maxHeight": 0.0}
ENTRADA, DESLIZE = 0.25, 0.012
EASE_OUT, LINEAR = [0.0, 0.0, 0.58, 1.0], [0.0, 0.0, 1.0, 1.0]

api = Concat(path)
api.sock.settimeout(300)
try:
    api.call("project.get", path=path)
except RuntimeError:
    api.call("project.open", path=path)
tl = timeline(api.view())
velhas = [c["id"] for c in tl["clips"] if c["kind"] == "text" and c.get("name") == NOME]
if velhas:
    api.edit({"op": "removeClips", "clipIds": velhas})
    tl = timeline(api.view())
fps = 30
if "fim" in opc:
    fim = float(opc["fim"])
else:   # fim do 1º conjunto de zoom (takes seguidos com a mesma escala)
    vs = sorted([c for c in tl["clips"] if c["kind"] == "video"], key=lambda c: c["start"])
    k = 0
    while k + 1 < len(vs) and abs(vs[k + 1].get("scale", 1) - vs[0].get("scale", 1)) < 1e-3:
        k += 1
    fim = vs[k]["start"] + vs[k]["duration"]
    fim = min(max(fim, 2.0), 5.0)
fim = round(fim * fps) / fps
antes = {t["id"] for t in tl["tracks"]}
tl = timeline(api.edit({"op": "addTrack"}))   # por cima de tudo
trilha = next(t["id"] for t in tl["tracks"] if t["id"] not in antes)
antes_c = {c["id"] for c in tl["clips"]}
tl = timeline(api.edit({"op": "addTextClip", "trackId": trilha, "start": 0.0, "duration": fim, "offsetY": ALTURA, "style": ESTILO}))
cid = next(c["id"] for c in tl["clips"] if c["id"] not in antes_c)
a, s = min(ENTRADA / fim, 0.5), 1 - min((2 / fps) / fim, 0.2)
api.batch([{"op": "updateClip", "clipId": cid, "patch": {"name": NOME}},
           {"op": "setClipKey", "clipId": cid, "property": "offsetY", "at": 0.0, "value": ALTURA + DESLIZE, "ease": LINEAR},
           {"op": "setClipKey", "clipId": cid, "property": "offsetY", "at": a, "value": ALTURA, "ease": EASE_OUT},
           {"op": "setClipKey", "clipId": cid, "property": "opacity", "at": 0.0, "value": 0.0, "ease": LINEAR},
           {"op": "setClipKey", "clipId": cid, "property": "opacity", "at": a * 0.7, "value": 1.0, "ease": EASE_OUT},
           {"op": "setClipKey", "clipId": cid, "property": "opacity", "at": s, "value": 1.0, "ease": LINEAR},
           {"op": "setClipKey", "clipId": cid, "property": "opacity", "at": 1.0, "value": 0.0, "ease": LINEAR}])
api.call("project.save", path=path)
print(f"headline \"{texto.replace(chr(10), ' / ')}\" em {trilha}, 0-{fim:.2f}s")
