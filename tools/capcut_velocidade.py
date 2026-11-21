#!/usr/bin/env python3
"""Troca a velocidade da trilha principal de um projeto do CapCut já editado, sem refazer nada: cada take fica com
o mesmo trecho do bruto, e todo o resto (legendas, motions, efeitos, música) vai junto para os tempos novos.

Pedido de 2026-11-09 (Dra. Larissa): "a doutora já fala rápido, então não coloque velocidade 1.1 no vídeo, deixe
1.0x mesmo". Os projetos já tinham zoom, legendas e ajustes dela; refazer com as ferramentas de trilha inteira
desfaria o que ela mudou (capcut-edicao-dela-entre-passos), então este script só reescala os tempos.

- Takes: speed nova, duração = trecho do bruto / speed, arredondada à grade de quadros do projeto (o fim do trecho
  do bruto anda menos de meio quadro para isso), na mesma ordem e com as mesmas folgas entre eles.
- Outras trilhas: início e fim levados pela mesma conta (tempo dentro de cada take reescalado); clipe com trecho de
  fonte (áudio, vídeo) ganha o trecho que cabe na duração nova, sem passar do fim da mídia.
- Keyframes: o tempo de cada um reescala junto com o clipe.
CapCut FECHADO. Backup em ~/Desktop/Claude Code Skills/backup-capcut/. Uso: capcut_velocidade.py <pasta do projeto> <velocidade>
"""
import glob
import json
import os
import shutil
import subprocess
import sys
import time

P, V = os.path.abspath(sys.argv[1]), float(sys.argv[2])
if subprocess.run(["pgrep", "-x", "CapCut"], capture_output=True).returncode == 0:
    sys.exit("feche o CapCut antes (ele regrava o projeto aberto por cima)")
alvos = [p for p in [os.path.join(P, "draft_info.json"), os.path.join(P, "template-2.tmp")]
         + glob.glob(os.path.join(P, "Timelines", "*", "draft_info.json")) + glob.glob(os.path.join(P, "Timelines", "*", "template-2.tmp"))
         if os.path.exists(p)]
copia = os.path.expanduser(f"~/Desktop/Claude Code Skills/backup-capcut/{os.path.basename(P)} {time.strftime('%Y-%m-%d %H%M%S')} (antes da velocidade {V})")
for p in alvos + glob.glob(os.path.join(P, "*.json")):
    d = os.path.join(copia, os.path.relpath(p, P))
    os.makedirs(os.path.dirname(d), exist_ok=True)
    shutil.copy2(p, d)

d = json.load(open(alvos[0], encoding="utf-8"))
quadro = 1e6 / float(d.get("fps") or 30.0)
mats = {m["id"]: (k, m) for k, v in d["materials"].items() if isinstance(v, list) for m in v if isinstance(m, dict) and "id" in m}
principal = next(t for t in d["tracks"] if t["type"] == "video")
segs = sorted(principal["segments"], key=lambda s: s["target_timerange"]["start"])

# mapa velho -> novo, take a take (folgas entre takes ficam iguais)
mapa, fim_novo, fim_velho = [], 0, 0
for s in segs:
    S, D = s["target_timerange"]["start"], s["target_timerange"]["duration"]
    F = s["source_timerange"]["duration"]
    S2 = fim_novo + (S - fim_velho)
    D2 = int(round(round(F / V / quadro) * quadro))
    mapa.append((S, D, S2, D2))
    for k in (s.get("common_keyframes") or []):
        for kf in k.get("keyframe_list", []):
            kf["time_offset"] = int(round(kf["time_offset"] * D2 / D))
    s["target_timerange"] = {"start": S2, "duration": D2}
    s["source_timerange"]["duration"] = int(round(D2 * V))
    s["speed"] = V
    for r in s.get("extra_material_refs", []):
        if r in mats and mats[r][0] == "speeds":
            mats[r][1]["speed"] = V
    fim_novo, fim_velho = S2 + D2, S + D


def leva(t):
    for S, D, S2, D2 in mapa:
        if t <= S + D:
            return S2 + max(0, t - S) * D2 / D if t >= S else S2 - (S - t)
    S, D, S2, D2 = mapa[-1]
    return S2 + D2 + (t - S - D)


MIDIA_CURTA = 12e6   # vídeo/áudio de até 12 s fora da trilha principal = motion ou SFX (mantém a duração); mais longo = música
outros = 0
for t in d["tracks"]:
    if t is principal:
        continue
    for s in t["segments"]:
        tr = s["target_timerange"]
        a, b = int(round(leva(tr["start"]))), int(round(leva(tr["start"] + tr["duration"])))
        if s.get("source_timerange") and s["material_id"] in mats and t["type"] in ("video", "audio") and tr["duration"] <= MIDIA_CURTA:
            # motion pronto (ProRes) e SFX: andam com a fala, mas tocam inteiros (encurtar cortaria a saída/a cauda)
            dur = min(tr["duration"], fim_novo - a) if a < fim_novo else tr["duration"]   # não passa do fim da fala
            s["target_timerange"] = {"start": a, "duration": dur}
            s["source_timerange"]["duration"] = int(round(dur * s.get("speed", 1.0)))
            outros += 1
            continue
        for k in (s.get("common_keyframes") or []):
            for kf in k.get("keyframe_list", []):
                kf["time_offset"] = int(round(kf["time_offset"] * (b - a) / max(1, tr["duration"])))
        if s.get("source_timerange") and s["material_id"] in mats:
            m = mats[s["material_id"]][1]
            src = s["source_timerange"]
            dur_src = int(round((b - a) * s.get("speed", 1.0)))
            if m.get("duration") and src["start"] + dur_src > m["duration"]:
                dur_src = m["duration"] - src["start"]
                b = a + int(dur_src / s.get("speed", 1.0))
            src["duration"] = dur_src
        s["target_timerange"] = {"start": a, "duration": b - a}
        outros += 1

total = max(s["target_timerange"]["start"] + s["target_timerange"]["duration"] for t in d["tracks"] for s in t["segments"])
d["duration"] = total
texto = json.dumps(d, ensure_ascii=False, separators=(",", ":"))
for p in alvos:
    open(p, "w", encoding="utf-8").write(texto)
meta_p = os.path.join(P, "draft_meta_info.json")
meta = json.load(open(meta_p, encoding="utf-8"))
meta["tm_duration"] = total
json.dump(meta, open(meta_p, "w", encoding="utf-8"), ensure_ascii=False)
raiz_p = os.path.join(os.path.dirname(P), "root_meta_info.json")
raiz = json.load(open(raiz_p, encoding="utf-8"))
for x in raiz["all_draft_store"]:
    if os.path.realpath(x["draft_fold_path"]) == os.path.realpath(P):
        x["tm_duration"] = total
json.dump(raiz, open(raiz_p, "w", encoding="utf-8"), ensure_ascii=False)
print(f"{len(segs)} takes a {V}x, {outros} clipes de outras trilhas levados junto; {mapa[-1][2] / 1e6 + mapa[-1][3] / 1e6:.3f}s "
      f"(antes {fim_velho / 1e6:.3f}s); backup em {copia}")
