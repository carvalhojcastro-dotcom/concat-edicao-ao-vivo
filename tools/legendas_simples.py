#!/usr/bin/env python3
"""Legendas simples da Parte 1: uma palavra por vez, Helvetica, sem animação, sem ponto final.

Uso: legendas_simples.py <projeto> <words.json> [trilha=T4]
  words.json: palavras do Whisper com tempos da MÍDIA DE ORIGEM (start, end, word).
  Os tempos viram tempos da timeline pelos clipes de vídeo (cortes e velocidade incluídos).
Estilo aprovado: Helvetica 400, fontSize 0.04302, tracking -0.00224 (o "-0.3" do CapCut),
contorno preto 0.0006, sombra, branco, offsetY 0.104. Cada palavra vai até a seguinte (ou
até o fim dela, se vier uma pausa > 0,35 s); tudo na grade de quadros.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from concat_api import Concat, timeline, fps_de

FPS = fps_de(sys.argv[1])  # o fps do projeto (24 ou 30)
ESTILO = {"align": "center", "background": "", "backgroundPaddingX": 0.0315, "backgroundPaddingY": 0.018,
          "backgroundRadius": 0.0135, "color": "#ffffff", "fontFamily": "Helvetica", "fontSize": 0.04302,
          "fontWeight": 400.0, "italic": False, "lineHeight": 1.2, "maxHeight": 0.0, "maxWidth": 0.0,
          "opacity": 1.0, "shadow": True, "strokeColor": "#000000", "strokeWidth": 0.0006, "tracking": -0.00224}

path, words = sys.argv[1], json.load(open(sys.argv[2]))
args = [a for a in sys.argv[3:] if not a.startswith("--")]
trilha = args[0] if args else "T4"
if "--sem-contorno" in sys.argv:  # só a sombra leve, sem contorno
    ESTILO = dict(ESTILO, strokeWidth=0.0)
opc = dict(a[2:].split("=", 1) for a in sys.argv[3:] if a.startswith("--") and "=" in a)
ESCALA = float(opc.get("escala", 0.92))    # padrão do usuário: 92% do tamanho original
ALTURA = float(opc.get("altura", 0.17))  # padrão do usuário: abaixo do rosto (antes 0.104)
ESTILO = dict(ESTILO, fontSize=ESTILO["fontSize"] * ESCALA, tracking=ESTILO["tracking"] * ESCALA,
              strokeWidth=ESTILO["strokeWidth"] * ESCALA)
api = Concat(path); api.sock.settimeout(300)
api.call("project.open", path=path)
tl = timeline(api.view())
clips = sorted([c for c in tl["clips"] if c["kind"] == "video"], key=lambda c: c["start"])
segs = [(c["sourceStart"], c["sourceStart"] + c["duration"] * c["speed"], c["start"], c["speed"]) for c in clips]
fim_tl = segs[-1][2] + (segs[-1][1] - segs[-1][0]) / segs[-1][3]

def tmap(src, prefer):
    for a, b, st, sp in segs:
        if a - 1e-6 <= src <= b + 1e-6:
            return st + (src - a) / sp
    if prefer == "next":
        return next((st for a, b, st, sp in segs if a > src), fim_tl)
    return next((st + (b - a) / sp for a, b, st, sp in reversed(segs) if b < src), 0.0)

snap = lambda t: round(t * FPS) / FPS
itens = []
for i, w in enumerate(words):
    s = snap(tmap(w["start"], "next"))
    e_w = tmap(w["end"], "prev")
    if i + 1 < len(words):
        nxt = snap(tmap(words[i + 1]["start"], "next"))
        e = min(nxt if nxt - e_w < 0.35 else snap(max(e_w, s + 2 / FPS)), nxt)
    else:
        e = min(snap(max(e_w, s + 2 / FPS)), snap(fim_tl))
    itens.append([w["word"].strip().rstrip("."), s, e])
for k in range(len(itens)):
    if itens[k][2] - itens[k][1] < 1 / FPS - 1e-9:
        itens[k][2] = itens[k][1] + 1 / FPS
        if k + 1 < len(itens) and itens[k + 1][1] < itens[k][2]:
            itens[k + 1][1] = itens[k][2]
for k in range(0, len(itens), 50):
    api.batch([{"op": "addTextClip", "trackId": trilha, "start": s, "duration": round(e - s, 6),
                "offsetY": ALTURA, "style": dict(ESTILO, content=t)} for t, s, e in itens[k:k + 50]])
api.call("project.save", path=path)
print(f"{len(itens)} legendas em {trilha}, de {itens[0][1]:.2f} a {itens[-1][2]:.2f}s")
