#!/usr/bin/env python3
"""Zoom seco por grupos de frase direto num projeto do CapCut já montado (Dra. Luciana, "16 - Suspenção de
medicações antes da cirurgia", 2026-11-01: "refaça ... os zoom in e zoom out de acordo com as nossas últimas
atualizações").

- Divide o take onde um grupo começa no meio dele, sem mexer no áudio. Ponha o tempo no silêncio entre as frases.
- Cada grupo leva a escala do plano e o rosto centrado, com a regra do capcut_pedacos.py: até 1,2 o rosto fica
  na altura em que está; acima disso vai a 1/3 da altura.
- `uniform_scale` fica em 1,0 e não há keyframes.

grupos.json: [[t na timeline, escala], ...]; o primeiro em 0. CapCut FECHADO; backup em ~/Desktop/Concat/backup-capcut.
Uso: capcut_zoom_grupos.py <pasta do projeto no CapCut> <grupos.json>
"""
import copy
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

import cv2
import numpy as np
P, grupos_arq = os.path.abspath(sys.argv[1]), sys.argv[2]
if subprocess.run(["pgrep", "-x", "CapCut"], capture_output=True).returncode == 0:
    sys.exit("feche o CapCut antes (ele regrava o projeto aberto por cima)")
grupos = json.load(open(grupos_arq))   # [[t_timeline, escala], ...]
ALVO_Y = 0.33
novo_id = lambda: str(uuid.uuid4()).upper()
alvos = [p for p in [os.path.join(P, "draft_info.json"), os.path.join(P, "template-2.tmp")] + glob.glob(os.path.join(P, "Timelines", "*", "draft_info.json")) if os.path.exists(p)]
d = json.load(open(alvos[0], encoding="utf-8"))
copia = os.path.expanduser(f"~/Desktop/Concat/backup-capcut/{os.path.basename(P)} {time.strftime('%Y-%m-%d %H%M%S')} (antes do zoom por frase)")
for p in alvos + glob.glob(os.path.join(P, "*.json")):
    dest = os.path.join(copia, os.path.relpath(p, P)); os.makedirs(os.path.dirname(dest), exist_ok=True); shutil.copy2(p, dest)
mats = {}
for k, v in d["materials"].items():
    if isinstance(v, list):
        for m in v:
            if isinstance(m, dict) and "id" in m: mats[m["id"]] = (k, m)
def copiar_refs(seg):
    ids = []
    for r in seg.get("extra_material_refs", []):
        k, m = mats.get(r, (None, None))
        if m is None: continue
        m2 = dict(copy.deepcopy(m), id=novo_id()); d["materials"][k].append(m2); mats[m2["id"]] = (k, m2); ids.append(m2["id"])
    return ids
t = next(t for t in d["tracks"] if t["type"] == "video")
q = lambda x: int(round(round(x * 30) / 30 * 1e6))
# 1) divide os takes onde um grupo começa no meio deles
for tg, _ in grupos[1:]:
    T = q(tg)
    for i, s in enumerate(t["segments"]):
        a, D = s["target_timerange"]["start"], s["target_timerange"]["duration"]
        if a + 200000 < T < a + D - 200000:
            v = s.get("speed", 1.0); dt = T - a
            s2 = copy.deepcopy(s); s2.update(id=novo_id(), extra_material_refs=copiar_refs(s))
            s["target_timerange"] = {"start": a, "duration": dt}
            ss, sd = s["source_timerange"]["start"], s["source_timerange"]["duration"]
            s["source_timerange"] = {"start": ss, "duration": int(round(dt * v))}
            s2["target_timerange"] = {"start": T, "duration": D - dt}
            s2["source_timerange"] = {"start": ss + int(round(dt * v)), "duration": sd - int(round(dt * v))}
            t["segments"].insert(i + 1, s2)
            print(f"dividido em {T/1e6:.3f}s")
            break
# 2) rosto de cada grupo e escala/posição
raw = d["materials"]["videos"][0]["path"].replace("/Library/Containers/com.lemon.lvoverseas/Data", "")
cas = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
tmp = tempfile.mkdtemp()
def rosto(src):
    png = os.path.join(tmp, "q.png")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{src:.3f}", "-i", raw, "-frames:v", "1", "-vf", "scale=540:-2", png], check=True)
    img = cv2.imread(png); h, w = img.shape[:2]
    fs = [f for f in cas.detectMultiScale(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 1.1, 5, minSize=(int(w * .12), int(w * .12))) if 0.1 * h < f[1] + f[3] / 2 < 0.6 * h]
    if not len(fs): return None
    x, y, fw, fh = max(fs, key=lambda f: f[2]); return (x + fw / 2) / w, (y + fh / 2) / h
def grupo(s):
    a = s["target_timerange"]["start"] / 1e6; g = 0
    for i, (tg, _) in enumerate(grupos):
        if tg <= a + 0.2: g = i
    return g
por_grupo = {}
for s in t["segments"]: por_grupo.setdefault(grupo(s), []).append(s)
for g, segs in sorted(por_grupo.items()):
    esc = grupos[g][1]
    srcs = [(s["source_timerange"]["start"] + s["source_timerange"]["duration"] / 2) / 1e6 for s in segs]
    if len(srcs) > 5: srcs = [srcs[int(i * (len(srcs) - 1) / 4)] for i in range(5)]
    rs = [r for r in (rosto(x) for x in srcs) if r]
    fx, fy = np.median(np.array(rs), 0) if rs else (0.5, 0.4)
    folga = esc - 1
    tx = max(-folga, min(folga, -2 * (fx - 0.5) * esc))
    ty = max(-folga, min(folga, 2 * (0.5 + (fy - 0.5) * esc - (fy if esc < 1.2 else ALVO_Y))))
    for s in segs:
        s["clip"]["scale"] = {"x": esc, "y": esc}
        s["clip"]["transform"] = {"x": round(tx, 4), "y": round(ty, 4)}
        if isinstance(s.get("uniform_scale"), dict): s["uniform_scale"].update(on=True, value=1.0)
    print(f"grupo {g} ({grupos[g][0]}s) x{esc}: {len(segs)} takes, rosto ({fx:.3f},{fy:.3f}) -> ({tx:.3f},{ty:.3f})")
if d.get("render_index_track_mode_on"):
    for i, tr in enumerate(d["tracks"]):
        for s in tr["segments"]: s["track_render_index"] = i
texto = json.dumps(d, ensure_ascii=False, separators=(",", ":"))
for p in alvos: open(p, "w", encoding="utf-8").write(texto)
print(f"{len(t['segments'])} takes; backup em {copia}")
