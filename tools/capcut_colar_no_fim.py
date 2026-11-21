#!/usr/bin/env python3
"""Cola a timeline inteira de um projeto do CapCut no fim de outro, sem mudar nada do que já existe no destino
(pedido de 2026-11-17: juntar os Papo Sem Vergonha 1, 2 e 3 da Dra. Larissa num vídeo só).

- Cada trilha da origem vai para a trilha equivalente do destino: a principal na principal; trilha com nome na de
  mesmo tipo e nome; trilha sem nome na n-ésima sem nome do mesmo tipo (se ela já terminou antes do ponto de colagem);
  senão, uma trilha nova.
- Todos os clipes, materiais e keyframes copiados ganham ids novos (referências entre eles trocadas junto).
- O ponto de colagem é o fim da trilha principal do destino. A origem só é lida.
CapCut FECHADO. Backup do destino em ~/Desktop/Claude Code Skills/backup-capcut.
Uso: capcut_colar_no_fim.py <pasta do destino> <pasta da origem>"""
import copy
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid

P1, P2 = sys.argv[1:3]
if subprocess.run(["pgrep", "-x", "CapCut"], capture_output=True).returncode == 0:
    sys.exit("feche o CapCut")
alvos = [p for p in [os.path.join(P1, "draft_info.json"), os.path.join(P1, "template-2.tmp")] + glob.glob(os.path.join(P1, "Timelines", "*", "draft_info.json"))
         + glob.glob(os.path.join(P1, "Timelines", "*", "template-2.tmp")) if os.path.exists(p)]
bk = os.path.expanduser(f"~/Desktop/Claude Code Skills/backup-capcut/{os.path.basename(P1)} {time.strftime('%Y-%m-%d %H%M%S')} (antes de colar {os.path.basename(P2)[:30]})")
for p in alvos + glob.glob(os.path.join(P1, "*.json")):
    dst = os.path.join(bk, os.path.relpath(p, P1))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(p, dst)
A = json.load(open(alvos[0], encoding="utf-8"))
B = json.load(open(os.path.join(P2, "draft_info.json"), encoding="utf-8"))


def fim(t):
    return max((s["target_timerange"]["start"] + s["target_timerange"]["duration"] for s in t["segments"]), default=0)


mainA = next(t for t in A["tracks"] if t["type"] == "video")
mainB = next(t for t in B["tracks"] if t["type"] == "video")
OFF = fim(mainA)
MB = {m["id"]: (k, m) for k, v in B["materials"].items() if isinstance(v, list) for m in v if isinstance(m, dict) and "id" in m}
usados = {r for t in B["tracks"] for s in t["segments"] for r in [s["material_id"]] + s.get("extra_material_refs", [])}
mudou = True
while mudou:   # materiais citados por outros materiais (ex.: video_id do áudio extraído)
    mudou = False
    txt = json.dumps([MB[i][1] for i in usados if i in MB])
    for i in MB:
        if i not in usados and i in txt:
            usados.add(i)
            mudou = True
usados = {i for i in usados if i in MB}
ids = set(usados)
for t in B["tracks"]:
    for s in t["segments"]:
        ids.add(s["id"])
        for k in s.get("common_keyframes") or []:
            ids.add(k["id"])
            ids.update(kf["id"] for kf in k.get("keyframe_list", []))
mapa = {i: (str(uuid.uuid4()).upper() if "-" in i else uuid.uuid4().hex) for i in ids if i}
pat = re.compile("|".join(re.escape(i) for i in sorted(mapa, key=len, reverse=True)))


def troca(o):
    return json.loads(pat.sub(lambda m: mapa[m.group(0)], json.dumps(o, ensure_ascii=False)))


for i in usados:
    k, m = MB[i]
    A["materials"].setdefault(k, []).append(troca(m))


def destino(tb, n):
    if tb is mainB:
        return mainA
    nome = tb.get("name", "")
    if nome:
        c = [t for t in A["tracks"] if t["type"] == tb["type"] and t.get("name", "") == nome]
        if c:
            return c[0]
    else:
        c = [t for t in A["tracks"] if t["type"] == tb["type"] and not t.get("name", "") and t is not mainA]
        if n < len(c) and fim(c[n]) <= OFF + 1:
            return c[n]
    novo = dict(copy.deepcopy({k: v for k, v in tb.items() if k != "segments"}), id=str(uuid.uuid4()).upper(), segments=[])
    A["tracks"].append(novo)
    return novo


cont = {}
for tb in B["tracks"]:
    ch = (tb["type"], tb.get("name", ""))
    n = cont.get(ch, 0)
    cont[ch] = n + 1
    td = destino(tb, n)
    for s in tb["segments"]:
        s2 = troca(s)
        s2["target_timerange"]["start"] += OFF
        td["segments"].append(s2)
    print(f"  {tb['type']:6s} {tb.get('name', '')[:24]:24s} {len(tb['segments']):3d} clipes -> trilha {A['tracks'].index(td)} {td.get('name', '')}")
total = max(fim(t) for t in A["tracks"])
A["duration"] = total
if A.get("render_index_track_mode_on"):
    for i, t in enumerate(A["tracks"]):
        for s in t["segments"]:
            s["track_render_index"] = i
# cada take com o seu material (senão "Extrair áudio" num take emudece todos os que dividem o material, 2026-11-17)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capcut_materiais_unicos  # noqa: E402
capcut_materiais_unicos.unicos(A)
txt = json.dumps(A, ensure_ascii=False, separators=(",", ":"))
for p in alvos:
    open(p, "w", encoding="utf-8").write(txt)
mp = os.path.join(P1, "draft_meta_info.json")
m = json.load(open(mp, encoding="utf-8"))
m["tm_duration"] = total
json.dump(m, open(mp, "w", encoding="utf-8"), ensure_ascii=False)
rp = os.path.join(os.path.dirname(P1), "root_meta_info.json")
r = json.load(open(rp, encoding="utf-8"))
for x in r["all_draft_store"]:
    if os.path.realpath(x["draft_fold_path"]) == os.path.realpath(P1):
        x["tm_duration"] = total
json.dump(r, open(rp, "w", encoding="utf-8"), ensure_ascii=False)
print(f"colado em {OFF / 1e6:.3f} s; nova duração {total / 1e6:.3f} s; {len(usados)} materiais; backup {bk}")
