#!/usr/bin/env python3
"""Enquadra cada take do projeto: pessoa centralizada, margem entre o topo e a cabeça, zoom por conjunto.

Regras do usuário (2026-10-21, Ozempic):
  - a pessoa sempre centralizada, em todo take, inclusive nos abertos (por isso o aberto não é 100%: com
    --aberto=1.08 sobra imagem para mover o quadro);
  - sempre uma margem entre o topo do vídeo e a cabeça: a cabeça fica em --topo (0,13) e nunca acima de
    --topo-min (0,10), para a margem não pular de um take para o outro;
  - o zoom de cada conjunto vem do plano (zoom_cortes.py): clipes seguidos com a mesma escala.
Com --estampa (camiseta com estampa clara no peito), a estampa nunca desce abaixo de 0,745 (ou do valor
dado), para não cair sobre a legenda; se cabeça e estampa não cabem juntas, o zoom do conjunto diminui.

As medidas vêm de quadros que o próprio Concat renderiza com os takes a 100% (a cor do bruto HLG não
serve para achar a estampa). O centro da pessoa é o rosto; quando o rosto não aparece, o peito (estampa).

Uso: centralizar_zoom.py <projeto> [--aberto=1.08] [--topo=0.13] [--topo-min=0.10] [--estampa[=0.745]]
"""
import os
import shutil
import sys
import tempfile

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from concat_api import Concat, timeline  # noqa: E402
from render_projeto import projeto_para_render  # noqa: E402

args = [a for a in sys.argv[1:] if not a.startswith("--")]
opc = dict(a[2:].split("=", 1) if "=" in a else (a[2:], "") for a in sys.argv[1:] if a.startswith("--"))
path = args[0]
ABERTO = float(opc.get("aberto", 1.08))
TOPO = float(opc.get("topo", 0.13))
TOPO_MIN = float(opc.get("topo-min", 0.10))
EST_MAX = float(opc["estampa"] or 0.745) if "estampa" in opc else None
cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


def natural(doc):
    """Cópia para medir: todos os takes a 100% e no lugar, sem legendas por cima."""
    for t in doc["timelines"]:
        for c in t["clips"]:
            if c["kind"] == "video":
                c["scale"], c["offsetX"], c["offsetY"] = 1.0, 0.0, 0.0
                c["keys"] = [k for k in c.get("keys", []) if k.get("property") not in ("scale", "offsetX", "offsetY")]
            elif c["kind"] in ("text", "image"):
                c["opacity"] = 0.0


def medir(img):
    """(centro x do rosto, topo da cabeça), (centro x da estampa, fim da estampa) - em fração do quadro."""
    h, w = img.shape[:2]
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = [f for f in cascade.detectMultiScale(g, 1.1, 5, minSize=(w // 8, w // 8))
             if 0.15 * h < f[1] + f[3] / 2 < 0.55 * h and 0.2 * w < f[0] + f[2] / 2 < 0.8 * w]
    rosto = None
    if faces:
        x, y, fw, fh = max(faces, key=lambda f: f[2])
        col = g[:, x + fw // 4:x + 3 * fw // 4]
        cabelo = np.nonzero((col < 90).mean(1) > 0.3)[0]
        cabelo = cabelo[cabelo < y]
        rosto = ((x + fw / 2) / w, (cabelo.min() / h) if len(cabelo) else (y - 0.35 * fh) / h)
    estampa = None
    if EST_MAX is not None:
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        escuro = cv2.blur(((hsv[..., 2] < 150) & (hsv[..., 1] > 40)).astype(np.float32), (31, 31)) > 0.35
        m = (hsv[..., 2] > 170) & (hsv[..., 1] < 70) & escuro
        # só a faixa do peito: tira chão, parede dos lados e mãos lá embaixo
        m[:int(0.5 * h)] = False
        m[int(0.82 * h):] = False
        m[:, :int(0.25 * w)] = False
        m[:, int(0.75 * w):] = False
        linhas = np.nonzero(m.sum(1) > 6)[0]
        if len(linhas):
            blocos = np.split(linhas, np.nonzero(np.diff(linhas) > 12)[0] + 1)
            bloco = max(blocos, key=lambda b: int(m[b[0]:b[-1] + 1].sum()))   # o de mais "letra"
            ys, xs = np.nonzero(m[bloco[0]:bloco[-1] + 1])
            estampa = ((np.percentile(xs, 5) + np.percentile(xs, 95)) / 2 / w, bloco[-1] / h)
    return rosto, estampa


api = Concat(path)
api.sock.settimeout(600)
medidas = []
with projeto_para_render(path, transformar=natural) as (api_r, alvo):
    takes_r = sorted([c for c in timeline(api_r.call("project.get", path=alvo))["clips"] if c["kind"] == "video"],
                     key=lambda c: c["start"])
    tmp = tempfile.mkdtemp(dir=os.path.expanduser("~"), prefix=".concat-medidas-")  # o Concat só grava na pasta do usuário
    for k, c in enumerate(takes_r):
        rs, es = [], []
        for f in (0.2, 0.5, 0.8):
            png = os.path.join(tmp, f"q{k}_{f}.png")
            api_r.call("preview.frame", path=alvo, time=c["start"] + c["duration"] * f, output=png, width=540, height=960)
            r, e = medir(cv2.imread(png))
            rs += [r] if r else []
            es += [e] if e else []
        medidas.append({"fx": float(np.median([r[0] for r in rs])) if rs else None,
                        "topo": float(min(r[1] for r in rs)) if rs else None,
                        "ex": float(np.median([e[0] for e in es])) if es else None,
                        "est": float(max(e[1] for e in es)) if es else None})

shutil.rmtree(tmp, ignore_errors=True)
# o que um take não mostrou vem do vizinho mais próximo
for chave in ("topo", "est"):
    for k, m in enumerate(medidas):
        if m[chave] is None:
            viz = [medidas[j][chave] for j in sorted(range(len(medidas)), key=lambda j: abs(j - k))
                   if medidas[j][chave] is not None]
            m[chave] = viz[0] if viz else (0.18 if chave == "topo" else EST_MAX or 0.7)

clips = sorted([c for c in timeline(api.call("project.open", path=path))["clips"] if c["kind"] == "video"],
               key=lambda c: c["start"])
# conjuntos: clipes seguidos com a mesma escala do plano
conjuntos = []
for k, c in enumerate(clips):
    s = c.get("scale", 1.0)
    if conjuntos and abs(conjuntos[-1][0] - s) < 1e-6:
        conjuntos[-1][1].append(k)
    else:
        conjuntos.append((s, [k]))

cl = lambda v, f: max(-f, min(f, v))  # noqa: E731
cmds, log, finais = [], [], []
for s_plano, ks in conjuntos:
    s = max(s_plano, ABERTO)
    if EST_MAX is not None:  # cabeça a TOPO_MIN do topo e estampa até EST_MAX só cabem até esta escala
        s = min(s, min((EST_MAX - TOPO_MIN) / max(medidas[k]["est"] - medidas[k]["topo"], 1e-3) for k in ks))
    s = round(max(1.0, s), 3)
    f = (s - 1) / 2
    for k in ks:
        m = medidas[k]
        cx = m["fx"] if m["fx"] is not None else (m["ex"] if m["ex"] is not None else 0.5)   # rosto; peito se não houver
        ox = cl(-(cx - 0.5) * s, f)
        y = lambda v, o: 0.5 + (v - 0.5) * s + o  # noqa: E731
        oy = TOPO - y(m["topo"], 0.0)
        oy = max(oy, TOPO_MIN - y(m["topo"], 0.0))
        if EST_MAX is not None and y(m["est"], oy) > EST_MAX:
            oy = EST_MAX - y(m["est"], 0.0)
        oy = cl(oy, f)
        cmds.append({"op": "setClipTransform", "clipId": clips[k]["id"], "scale": s,
                     "offsetX": round(ox, 4), "offsetY": round(oy, 4)})
        finais.append((k, 0.5 + (cx - 0.5) * s + ox, y(m["topo"], oy)))
    log.append(f"{clips[ks[0]]['start']:6.2f}s  takes {ks[0] + 1}-{ks[-1] + 1}: {round(s * 100)}%"
               + ("" if abs(s - max(s_plano, ABERTO)) < 1e-3 else f" (plano {round(s_plano * 100)}%: limitado)"))
api.batch(cmds)
api.call("project.save", path=path)
print("\n".join(log))
print("centro da pessoa entre %.2f e %.2f | cabeça entre %.2f e %.2f do topo" % (
    min(f[1] for f in finais), max(f[1] for f in finais), min(f[2] for f in finais), max(f[2] for f in finais)))
for k, cx, _ in finais:
    if abs(cx - 0.5) > 0.03:
        print(f"  take {k + 1}: centro em {cx:.2f} (a pessoa está muito de lado; o zoom não dá folga para mais)")
