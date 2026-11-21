#!/usr/bin/env python3
"""Zoom in / zoom out seco ao longo de um corte de podcast já montado no CapCut, dividindo os takes nos começos de frase.

Pedido de 2026-11-14 (JFIT C04 em diante): "adicione cortes para poder dar zoom in e zoom out ao longo de todo o
video ... Esse vai e volta é bom pra dar dinamicidade". Os cortes de podcast têm takes longos (uma câmera falando por
30 s ou mais) com o bruto 16:9 ampliado (escala ~3,2) e o X fixo por pessoa. Este script:
  - divide cada take longo em trechos de ~4,5 s (entre --min e --max), sempre no começo de uma frase (depois de
    ponto, ?, ! ou vírgula, ou numa pausa), sem mexer no áudio: as duas metades seguem coladas no bruto;
  - alterna os trechos entre o enquadramento dela (normal) e zoom (escala x --zoom, padrão 1,18), sem keyframe e sem
    animação ("No animated zooms"); trecho curto (< 1,2 s) acompanha o seguinte, para não piscar;
  - no zoom, o rosto fica no mesmo lugar da tela (o zoom "entra" no rosto): mediana de 3 quadros com o detector de
    rosto do OpenCV; o rosto escolhido é o mais perto do centro da tela; sem rosto, o zoom vai para o terço de cima;
  - o quadro nunca mostra borda (a posição é limitada pela folga da escala);
  - take com keyframes de X (a pessoa se desloca; capcut_podcast.py) também é dividido: os keyframes têm o tempo
    absoluto do bruto, então cada metade fica com os dela mais um keyframe interpolado na emenda; no zoom, X, Y e
    escala dos keyframes passam pela mesma conta (o X do rosto já segue a pessoa, então o zoom é no centro).
Os tempos das frases vêm de words.json com tempos da TIMELINE (capcut/transcrever_timeline.py). Rode UMA vez por
projeto: de novo, o zoom multiplica a escala outra vez (para refazer, volte o backup antes).
CapCut FECHADO. Backup em ~/Desktop/Claude Code Skills/backup-capcut/.
Uso: capcut_zoom_podcast.py <pasta do projeto> <words.json> [--zoom=1.18] [--alvo=4.5] [--min=3] [--max=7] [--teste]
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

args = [a for a in sys.argv[1:] if not a.startswith("--")]
op = {a[2:].split("=")[0]: (a.split("=", 1)[1] if "=" in a else True) for a in sys.argv[1:] if a.startswith("--")}
P, words = os.path.abspath(args[0]), json.load(open(args[1]))
Z, ALVO = float(op.get("zoom", 1.18)), float(op.get("alvo", 4.5))
MIN, MAX = float(op.get("min", 3.0)), float(op.get("max", 7.0))
CURTO = 1.2
if not op.get("teste") and subprocess.run(["pgrep", "-x", "CapCut"], capture_output=True).returncode == 0:
    sys.exit("feche o CapCut antes (ele regrava o projeto aberto por cima)")
novo_id = lambda: str(uuid.uuid4()).upper()  # noqa: E731
alvos = [p for p in [os.path.join(P, "draft_info.json"), os.path.join(P, "template-2.tmp")]
         + glob.glob(os.path.join(P, "Timelines", "*", "draft_info.json")) + glob.glob(os.path.join(P, "Timelines", "*", "template-2.tmp"))
         if os.path.exists(p)]
d = json.load(open(alvos[0], encoding="utf-8"))
copia = os.path.expanduser(f"~/Desktop/Claude Code Skills/backup-capcut/{os.path.basename(P)} {time.strftime('%Y-%m-%d %H%M%S')} (antes do zoom por frase)")
for p in alvos + glob.glob(os.path.join(P, "*.json")):
    dest = os.path.join(copia, os.path.relpath(p, P))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copy2(p, dest)
quadro = 1e6 / float(d.get("fps") or 30.0)
q = lambda us: int(round(round(us / quadro) * quadro))  # noqa: E731
mats = {m["id"]: (k, m) for k, v in d["materials"].items() if isinstance(v, list) for m in v if isinstance(m, dict) and "id" in m}
trilha = next(t for t in d["tracks"] if t["type"] == "video")
trilha["segments"].sort(key=lambda s: s["target_timerange"]["start"])
canvas = d.get("canvas_config", {"width": 1080, "height": 1920})
CW, CH = canvas["width"], canvas["height"]


def interp(lista, t):
    lista = sorted(lista, key=lambda k: k["time_offset"])
    if t <= lista[0]["time_offset"]:
        return lista[0]["values"][0]
    for a, b in zip(lista, lista[1:]):
        if a["time_offset"] <= t <= b["time_offset"]:
            f = (t - a["time_offset"]) / max(1, b["time_offset"] - a["time_offset"])
            return a["values"][0] + f * (b["values"][0] - a["values"][0])
    return lista[-1]["values"][0]


def dividir_kf(kfs, t):
    """Keyframes (tempo do bruto em us) partidos em t: cada lado ganha um keyframe interpolado em t."""
    um, dois = [], []
    for k in kfs:
        lista = k["keyframe_list"]
        v = interp(lista, t)
        novo = lambda: dict(copy.deepcopy(lista[0]), id=novo_id(), time_offset=int(t), values=[v])  # noqa: E731
        um.append(dict(copy.deepcopy(k), keyframe_list=[copy.deepcopy(x) for x in lista if x["time_offset"] < t] + [novo()]))
        dois.append(dict(copy.deepcopy(k), id=novo_id(), keyframe_list=[novo()] + [dict(copy.deepcopy(x), id=novo_id()) for x in lista if x["time_offset"] > t]))
    return um, dois


def copiar_refs(seg):
    ids = []
    for r in seg.get("extra_material_refs", []):
        k, m = mats.get(r, (None, None))
        if m is None:
            continue
        m2 = dict(copy.deepcopy(m), id=novo_id())
        d["materials"][k].append(m2)
        mats[m2["id"]] = (k, m2)
        ids.append(m2["id"])
    return ids


# começos de frase (tempo do corte na timeline, nota)
cand = []
for i in range(1, len(words)):
    ant, w = words[i - 1], words[i]
    pausa = w["start"] - ant["end"]
    fim = ant["word"].strip()[-1:]
    nota = 3 if fim in ".?!" else 2 if fim in ",;:" else 0
    nota += 1 if pausa >= 0.25 else 0
    if nota:
        cand.append((w["start"] - min(0.08, max(0.0, pausa) / 2), nota))

# 1) divide os takes longos nos começos de frase
avisos, cortes = [], 0
novos = []
for s in trilha["segments"]:
    a, D = s["target_timerange"]["start"], s["target_timerange"]["duration"]
    pedacos, cur, fim = [], a / 1e6, (a + D) / 1e6
    while fim - cur > MAX:
        ok = [(t, n) for t, n in cand if cur + MIN <= t <= cur + MAX and fim - t >= MIN * 0.8]
        t = max(ok, key=lambda c: c[1] - abs(c[0] - (cur + ALVO)) * 0.6)[0] if ok else cur + ALVO
        pedacos.append(t)
        cur = t
    resto = s
    for t in pedacos:
        T = q(t * 1e6)
        ra, rD = resto["target_timerange"]["start"], resto["target_timerange"]["duration"]
        if not (ra + 0.5e6 < T < ra + rD - 0.5e6):
            continue
        v = resto.get("speed", 1.0)
        dt = T - ra
        s2 = copy.deepcopy(resto)
        s2.update(id=novo_id(), extra_material_refs=copiar_refs(resto))
        ss, sd = resto["source_timerange"]["start"], resto["source_timerange"]["duration"]
        dsrc = int(round(dt * v))
        resto["target_timerange"] = {"start": ra, "duration": dt}
        resto["source_timerange"] = {"start": ss, "duration": dsrc}
        s2["target_timerange"] = {"start": T, "duration": rD - dt}
        s2["source_timerange"] = {"start": ss + dsrc, "duration": sd - dsrc}
        if resto.get("common_keyframes"):
            resto["common_keyframes"], s2["common_keyframes"] = dividir_kf(resto["common_keyframes"], ss + dsrc)
        novos.append(resto)
        resto = s2
        cortes += 1
    novos.append(resto)
trilha["segments"] = novos

# 2) grupos (trecho curto acompanha o seguinte) e alternância
segs = trilha["segments"]
grupos, pend = [], []
for s in segs:
    pend.append(s)
    if s["target_timerange"]["duration"] / 1e6 >= CURTO:
        grupos.append(pend)
        pend = []
if pend:
    if grupos:
        grupos[-1] += pend
    else:
        grupos.append(pend)

# rosto na tela: x em metades da largura, y em metades da altura (para cima), como o transform do CapCut
fonte = {m["id"]: m for m in d["materials"]["videos"]}
tmp = tempfile.mkdtemp()
cas = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


def caminho(m):
    p = m["path"]
    return p if os.path.exists(p) else p.replace("/Library/Containers/com.lemon.lvoverseas/Data", "")


def rosto_tela(s):
    m = fonte[s["material_id"]]
    sw, sh = m.get("width") or 1920, m.get("height") or 1080
    esc, tx, ty = s["clip"]["scale"]["x"], s["clip"]["transform"]["x"], s["clip"]["transform"]["y"]
    alt = CW / sw * sh / CH            # altura do vídeo na escala 1, em fração da altura da tela
    ss, sd = s["source_timerange"]["start"] / 1e6, s["source_timerange"]["duration"] / 1e6
    pts = []
    for f in (0.25, 0.5, 0.75):
        png = os.path.join(tmp, "q.png")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{ss + sd * f:.3f}", "-i", caminho(m), "-frames:v", "1",
                        "-vf", "scale=960:-2", png], check=True)
        img = cv2.imread(png)
        h, w = img.shape[:2]
        fs = cas.detectMultiScale(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 1.1, 6, minSize=(int(w * .035), int(w * .035)))
        tela = []
        for x, y, fw, fh in fs:
            fx, fy = (x + fw / 2) / w, (y + fh / 2) / h
            px, py = tx + (fx - 0.5) * 2 * esc, ty - (fy - 0.5) * 2 * esc * alt
            if abs(px) < 0.8 and -0.9 < py < 0.95:
                tela.append((abs(px), px, py))
        if tela:
            pts.append(min(tela)[1:])
    return (float(np.median([p[0] for p in pts])), float(np.median([p[1] for p in pts]))) if pts else None


zooms = 0
for k, g in enumerate(grupos):
    if k % 2 == 0:
        continue
    for s in g:
        m = fonte[s["material_id"]]
        sw, sh = m.get("width") or 1920, m.get("height") or 1080
        alt = CW / sw * sh / CH
        esc, tx, ty = s["clip"]["scale"]["x"], s["clip"]["transform"]["x"], s["clip"]["transform"]["y"]
        r = rosto_tela(s)
        px, py = r if r else (0.0, 0.33)
        if s.get("common_keyframes"):
            px = 0.0   # o X dos keyframes já segue a pessoa
        e2 = esc * Z
        tx2, ty2 = px - Z * (px - tx), py - Z * (py - ty)
        fx, fy = max(0.0, e2 - 1), max(0.0, e2 * alt - 1)      # folga para não aparecer borda
        tx2, ty2 = max(-fx, min(fx, tx2)), max(-fy, min(fy, ty2))
        s["clip"]["scale"] = {"x": round(e2, 4), "y": round(e2, 4)}
        s["clip"]["transform"] = {"x": round(tx2, 4), "y": round(ty2, 4)}
        for k in s.get("common_keyframes") or []:
            for kf in k["keyframe_list"]:
                v = kf["values"][0]
                if k["property_type"] == "KFTypePositionX":
                    kf["values"] = [round(max(-fx, min(fx, px - Z * (px - v))), 4)]
                elif k["property_type"] == "KFTypePositionY":
                    kf["values"] = [round(max(-fy, min(fy, py - Z * (py - v))), 4)]
                elif k["property_type"] in ("KFTypeScaleX", "KFTypeScaleY"):
                    kf["values"] = [round(v * Z, 4)]
        zooms += 1
        print(f"  zoom {s['target_timerange']['start'] / 1e6:7.2f}s +{s['target_timerange']['duration'] / 1e6:5.2f}s "
              f"escala {esc:.2f}->{e2:.2f} rosto {'(%.2f, %.2f)' % r if r else 'não achado'} pos ({tx:.3f},{ty:.3f})->({tx2:.3f},{ty2:.3f})")

if d.get("render_index_track_mode_on"):
    for i, tr in enumerate(d["tracks"]):
        for s in tr["segments"]:
            s["track_render_index"] = i
texto = json.dumps(d, ensure_ascii=False, separators=(",", ":"))
for p in alvos:
    open(p, "w", encoding="utf-8").write(texto)
for a in avisos:
    print("!!", a)
print(f"{cortes} cortes novos, {len(segs)} takes em {len(grupos)} trechos, {zooms} takes com zoom x{Z}; backup em {copia}")
