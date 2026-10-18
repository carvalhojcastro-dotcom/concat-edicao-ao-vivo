#!/usr/bin/env python3
"""Centraliza a pessoa nos trechos com zoom (escala > 1) de um projeto do Concat.

Para cada trecho com zoom (clipes seguidos com a mesma escala), olha vários quadros, acha o
rosto (OpenCV) e usa a posição média dele no trecho inteiro: um enquadramento só por trecho,
que não pula de take para take. Ajusta offsetX para o rosto ficar no meio do quadro na horizontal, e offsetY para a
cabeça ficar na altura de sempre. O deslocamento nunca passa do que o zoom permite,
então não aparece borda.

Uso: centralizar_zoom.py <projeto> [altura_do_rosto=0.34]   (precisa de opencv-python-headless)
"""
import os, subprocess, sys, tempfile
import cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from concat_api import Concat, timeline

path = sys.argv[1]
alvo_y = float(sys.argv[2]) if len(sys.argv) > 2 else 0.34
api = Concat(path); api.sock.settimeout(180)
v = api.call("project.open", path=path)
media = {m["id"]: m["path"] for m in v["project"]["media"]}
cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
tmp = tempfile.mkdtemp()

def rosto(arquivo, t):
    png = os.path.join(tmp, "q.png")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", arquivo, "-frames:v", "1",
                    "-vf", "scale=540:-1", png], check=True)
    img = cv2.imread(png); h, w = img.shape[:2]
    faces = cascade.detectMultiScale(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 1.1, 6, minSize=(w // 8, w // 8))
    if len(faces) == 0:
        return None
    x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
    return ((x + fw / 2) / w, (y + fh / 2) / h)

cmds, log = [], []
clips = sorted([c for c in timeline(v)["clips"] if c["kind"] == "video"], key=lambda c: c["start"])
# Trechos: clipes seguidos com a mesma escala. Um enquadramento só por trecho, para o
# quadro não pular de um take para o outro dentro do mesmo zoom.
trechos = []
for c in clips:
    s = c.get("scale", 1.0)
    if trechos and abs(trechos[-1][0] - s) < 1e-6:
        trechos[-1][1].append(c)
    else:
        trechos.append((s, [c]))
for s, grupo in trechos:
    if s <= 1.001:
        continue
    pontos = []  # (fx, fy, peso)
    for c in grupo:
        span = c["duration"] * c.get("speed", 1.0)
        n = max(1, min(4, round(c["duration"] / 0.8)))
        for k in range(n):
            r = rosto(media[c["mediaId"]], c["sourceStart"] + (k + 0.5) / n * span)
            if r:
                pontos.append((r[0], r[1], c["duration"] / n))
    ini = grupo[0]["start"]
    if not pontos:
        log.append(f"{ini:6.2f}s: rosto não encontrado, mantido"); continue
    peso = sum(p[2] for p in pontos)
    fx = sum(p[0] * p[2] for p in pontos) / peso
    fy = sum(p[1] * p[2] for p in pontos) / peso
    folga = (s - 1) / 2
    # Depois do zoom o ponto fx vai para 0.5 + (fx-0.5)*s + offsetX; queremos 0.5 (e alvo_y na vertical).
    ox = max(-folga, min(folga, -(fx - 0.5) * s))
    oy = max(-folga, min(folga, alvo_y - 0.5 - (fy - 0.5) * s))
    for c in grupo:
        cmds.append({"op": "setClipTransform", "clipId": c["id"], "offsetX": ox, "offsetY": oy})
    xs = [p[0] for p in pontos]
    log.append(f"{ini:6.2f}s {round(s*100)}%: {len(grupo)} takes, rosto entre x={min(xs):.2f} e {max(xs):.2f}, média {fx:.3f} -> enquadramento fixo")
if cmds:
    api.batch(cmds)
api.call("project.save", path=path)
print("\n".join(log)); print(f"pronto: {sum(1 for t in log if 'fixo' in t)} trechos com zoom, um enquadramento fixo cada")
