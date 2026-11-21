#!/usr/bin/env python3
"""Dá a cada clipe de vídeo o seu próprio material (id único), sem mudar nada do que se vê ou ouve.

Por quê (2026-11-17, Dra. Larissa, Papo Sem Vergonha 1): as nossas ferramentas punham vários takes no MESMO material
de vídeo, e o CapCut grava esse material repetido com o mesmo id. Quando ela usa "Extrair áudio" num take, o CapCut
marca has_sound_separated nesse id, e TODOS os takes que o compartilham ficam mudos (12 takes perderam o áudio).

O que faz:
- tira cópias repetidas de material com o mesmo id;
- descobre os takes que ela de fato extraiu (um áudio video_original_sound com video_id = material do take e o mesmo
  deslocamento fonte-timeline); esses ficam no material separado, como ela deixou;
- todo outro clipe que divide material com alguém ganha uma cópia com id novo; se o material estava marcado como
  separado sem ser um take extraído, a cópia volta a ter som (has_sound_separated false, extra_type_option 0).
Uso: capcut_materiais_unicos.py <pasta do projeto> [...]   (CapCut FECHADO; backup em backup-capcut)
Também importável: unicos(d) -> número de clipes que ganharam material próprio."""
import collections
import copy
import glob
import json
import os
import shutil
import subprocess
import sys
import time
import uuid


def unicos(d):
    mats = d["materials"]
    # 1. cópias repetidas do mesmo id: fica a primeira
    for k, v in mats.items():
        if isinstance(v, list):
            vistos, nova = set(), []
            for m in v:
                if isinstance(m, dict) and "id" in m:
                    if m["id"] in vistos:
                        continue
                    vistos.add(m["id"])
                nova.append(m)
            mats[k] = nova
    videos = {m["id"]: m for m in mats.get("videos", [])}
    # 2. takes realmente extraídos: (material, deslocamento fonte - timeline) dos áudios video_original_sound
    audios = {m["id"]: m for m in mats.get("audios", []) if isinstance(m, dict)}
    extraidos = set()
    for t in d["tracks"]:
        if t["type"] != "audio":
            continue
        for s in t["segments"]:
            a = audios.get(s["material_id"])
            if a and a.get("type") == "video_original_sound" and a.get("video_id"):
                extraidos.add((a["video_id"], s["source_timerange"]["start"] - s["target_timerange"]["start"]))
    # 3. um material por clipe
    uso = collections.Counter(s["material_id"] for t in d["tracks"] if t["type"] == "video" for s in t["segments"])
    feitos = 0
    ja = collections.Counter()
    for t in d["tracks"]:
        if t["type"] != "video":
            continue
        for s in sorted(t["segments"], key=lambda s: s["target_timerange"]["start"]):
            mid = s["material_id"]
            m = videos.get(mid)
            if m is None or uso[mid] < 2:
                continue
            desl = s["source_timerange"]["start"] - s["target_timerange"]["start"]
            extraido = any(v == mid and abs(dd - desl) < 2000 for v, dd in extraidos)
            if extraido or (not m.get("has_sound_separated") and ja[mid] == 0):
                ja[mid] += 1      # fica no material original
                continue
            m2 = copy.deepcopy(m)
            m2["id"] = str(uuid.uuid4()).upper()
            if m.get("has_sound_separated"):
                m2["has_sound_separated"] = False
                m2["extra_type_option"] = 0
            mats["videos"].append(m2)
            videos[m2["id"]] = m2
            s["material_id"] = m2["id"]
            feitos += 1
    return feitos


def projeto(P):
    alvos = [p for p in [os.path.join(P, "draft_info.json"), os.path.join(P, "template-2.tmp")] + glob.glob(os.path.join(P, "Timelines", "*", "draft_info.json"))
             + glob.glob(os.path.join(P, "Timelines", "*", "template-2.tmp")) if os.path.exists(p)]
    d = json.load(open(alvos[0], encoding="utf-8"))
    n = unicos(d)
    if n == 0:
        return 0
    bk = os.path.expanduser(f"~/Desktop/Claude Code Skills/backup-capcut/{os.path.basename(P)} {time.strftime('%Y-%m-%d %H%M%S')} (antes de materiais únicos)")
    for p in alvos:
        dst = os.path.join(bk, os.path.relpath(p, P))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(p, dst)
    txt = json.dumps(d, ensure_ascii=False, separators=(",", ":"))
    for p in alvos:
        open(p, "w", encoding="utf-8").write(txt)
    return n


if __name__ == "__main__":
    if subprocess.run(["pgrep", "-x", "CapCut"], capture_output=True).returncode == 0:
        sys.exit("feche o CapCut")
    for P in sys.argv[1:]:
        print(f"{os.path.basename(P)}: {projeto(os.path.abspath(P))} clipe(s) com material próprio")
