#!/usr/bin/env python3
"""Cortes do `reel.py cortes` -> pedaços do plano do capcut_montar.py, com zoom seco por grupos de frases e o
rosto centrado (Sabrina, vídeos 24/11 e 01/12, 2026-10-30).

- Cada grupo (`[t no bruto, escala]`, o começo da frase) vale até o próximo. Se a frase começa no meio de fala
  contínua, o pedaço se divide logo antes dela, para a troca de zoom cair no começo da frase.
- Rosto: mediana de até 5 quadros do grupo (detector de rosto do OpenCV). Na escala até 1,2, o rosto fica na
  altura em que está; acima disso vai a `alvo_y` (~1/3 da altura). Sempre centrado na horizontal, dentro da folga.
- Se o plano de saída já existe, só troca "pedacos" e "velocidade" (música, efeitos e B-roll ficam).

zoom.json: {"velocidade": 1.02, "alvo_y": 0.33, "grupos": [[0, 1.1], [16.2, 1.5], [17.42, 1.1], ...]}
Uso: capcut_pedacos.py <trabalho do reel.py> <vídeo bruto> <zoom.json> <plano.json>
"""
import json
import os
import subprocess
import sys
import tempfile

import cv2
import numpy as np
trab, video, zoomf, saida = sys.argv[1:5]
z = json.load(open(zoomf))
vel = z.get("velocidade", 1.02)
grupos = sorted(z["grupos"])
alvo_y = z.get("alvo_y", 0.31)
cortes = json.load(open(os.path.join(trab, "cortes.json")))
dur = json.load(open(os.path.join(trab, "info.json")))["duracao"]
keep, prev = [], 0.0
for a, b in cortes:
    if a - prev > 0.05:
        keep.append((prev, a))
    prev = b
if dur - prev > 0.05:
    keep.append((prev, dur))
# troca de zoom no meio de fala contínua: o pedaço se divide logo antes da palavra que abre o grupo
for tg, _ in grupos[1:]:
    for k, (s, e) in enumerate(keep):
        corte = tg - 0.04
        if s + 0.2 < corte < e - 0.2:
            keep[k:k + 1] = [(s, corte), (corte, e)]
            break
cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
tmp = tempfile.mkdtemp()


def rosto(t):
    png = os.path.join(tmp, f"q{t:.3f}.png")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1", "-vf", "scale=540:-2", png], check=True)
    img = cv2.imread(png)
    h, w = img.shape[:2]
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    fs = [f for f in cascade.detectMultiScale(g, 1.1, 5, minSize=(int(w * 0.12), int(w * 0.12)))
          if 0.1 * h < f[1] + f[3] / 2 < 0.6 * h]
    if not fs:
        return None
    x, y, fw, fh = max(fs, key=lambda f: f[2])
    return (x + fw / 2) / w, (y + fh / 2) / h, fh / h


def grupo_de(t):
    k = 0
    for i, (tg, _) in enumerate(grupos):
        if tg <= t + 0.2:   # o grupo que começa perto do início do pedaço é dele
            k = i
    return k


pedacos, ini = [], 0.0
for s, e in keep:
    d = round((e - s) / vel * 30) / 30
    pedacos.append({"fonte": round(s, 3), "fonte_dur": round(e - s, 3), "ini": round(ini, 6), "dur": d, "_g": grupo_de(s)})
    ini += d
# rosto por grupo: mediana de quadros no meio dos pedaços do grupo
medidas = {}
for g in sorted({p["_g"] for p in pedacos}):
    ps = [p for p in pedacos if p["_g"] == g]
    ts = [p["fonte"] + p["fonte_dur"] / 2 for p in ps]
    if len(ts) > 5:
        ts = [ts[int(i * (len(ts) - 1) / 4)] for i in range(5)]
    rs = [r for r in (rosto(t) for t in ts) if r]
    medidas[g] = tuple(np.median(np.array(rs), 0)) if rs else None
for p in pedacos:
    g = p.pop("_g")
    esc = grupos[g][1]
    p["escala"] = esc
    m = medidas[g]
    if m is None:
        p["tx"], p["ty"] = 0.0, 0.0
        continue
    fx, fy, fh = m
    folga = esc - 1
    tx = -2 * (fx - 0.5) * esc
    alvo = fy if esc < 1.2 else alvo_y
    ty = 2 * (0.5 + (fy - 0.5) * esc - alvo)
    p["tx"] = round(max(-folga, min(folga, tx)), 4)
    p["ty"] = round(max(-folga, min(folga, ty)), 4)
plano = {"pedacos": pedacos, "velocidade": vel}
if os.path.exists(saida):
    velho = json.load(open(saida))
    velho.update(plano)
    plano = velho
json.dump(plano, open(saida, "w"), ensure_ascii=False, indent=1)
for g, m in medidas.items():
    print(f"grupo {g} t={grupos[g][0]:.2f} x{grupos[g][1]}: rosto {None if m is None else tuple(round(v, 3) for v in m)}")
print(f"{len(pedacos)} pedaços, {ini:.2f}s na timeline a {vel}x")
