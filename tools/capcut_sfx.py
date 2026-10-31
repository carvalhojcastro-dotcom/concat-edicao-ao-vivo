#!/usr/bin/env python3
"""Põe efeitos sonoros (arquivos de áudio nossos) num projeto do CapCut, cada um como um clipe editável,
em trilhas próprias (uma nova trilha só quando dois se sobrepõem). Rodar de novo troca as trilhas com o
mesmo nome; o resto do projeto (o que a usuária mexeu) fica como está.

Pedido de 2026-10-30 (Sabrina, vídeo 24/11): efeitos profissionais e sutis em cada elemento que entra nos
motions. Os WAV vêm de tools/sfx_sintese.py e ficam numa pasta que o CapCut (sandbox) lê:
~/Movies/CapCut/User Data/SFX Concat/..., escritos no plano com o caminho como ele vê
(~/Library/Containers/com.lemon.lvoverseas/Data/Movies/CapCut/User Data/...).

Plano: {"trilha": "SFX motions (Concat)", "efeitos": [{"arquivo": "...wav", "em": s, "duracao": s,
         "nome": "...", "volume": 1.0}, ...]}
O projeto precisa ter ao menos um clipe de áudio (o molde do segmento e do material). CapCut FECHADO.
Uso: capcut_sfx.py <pasta do projeto no CapCut> <plano.json> [--trocar]
  --trocar: só troca o arquivo (e a duração) de cada clipe já posto, achado pelo nome do efeito; posição,
  volume e clipes apagados pela usuária ficam como ela deixou (pedido de 2026-10-30: trocar as notas por cliques).
"""
import copy
import glob
import json
import os
import shutil
import subprocess
import sys
import time
import uuid

novo_id = lambda: str(uuid.uuid4()).upper()  # noqa: E731
us = lambda s: int(round(s * 1e6))  # noqa: E731


def material(d, mid):
    for k, v in d["materials"].items():
        if isinstance(v, list):
            for m in v:
                if isinstance(m, dict) and m.get("id") == mid:
                    return k, m
    return None, None


def copiar_refs(seg, d):
    """Referências do segmento molde (velocidade, canal de som...) copiadas com ids novos."""
    ids = []
    for r in seg.get("extra_material_refs", []):
        k, m = material(d, r)
        if m is None:
            continue
        m = dict(copy.deepcopy(m), id=novo_id())
        d["materials"][k].append(m)
        ids.append(m["id"])
    return ids


def aplicar(d, plano):
    nome = plano.get("trilha", "SFX (Concat)")
    # tira as trilhas de uma rodada anterior, com os materiais delas
    velhas = [t for t in d["tracks"] if t.get("name", "").startswith(nome)]
    ids = {s["material_id"] for t in velhas for s in t["segments"]} | {r for t in velhas for s in t["segments"] for r in s.get("extra_material_refs", [])}
    d["tracks"] = [t for t in d["tracks"] if t not in velhas]
    for k, v in d["materials"].items():
        if isinstance(v, list):
            d["materials"][k] = [m for m in v if not (isinstance(m, dict) and m.get("id") in ids)]
    trilha_molde = next(t for t in d["tracks"] if t["type"] == "audio" and t["segments"])
    seg_molde = trilha_molde["segments"][0]
    _, mat_molde = material(d, seg_molde["material_id"])
    trilhas = []   # [fim, trilha]
    for e in sorted(plano["efeitos"], key=lambda e: e["em"]):
        caminho = e["arquivo"]
        local = caminho.replace("/Library/Containers/com.lemon.lvoverseas/Data", "")
        if not os.path.exists(local):
            sys.exit(f"não existe: {local}")
        dur = e.get("duracao") or float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", local],
                                                       capture_output=True, text=True).stdout)
        m = copy.deepcopy(mat_molde)
        m.update(id=novo_id(), path=caminho, name=e.get("nome", os.path.splitext(os.path.basename(caminho))[0]), duration=us(dur),
                 type="extract_music", category_name="local", category_id="", music_id=novo_id(), unique_id=uuid.uuid4().hex,
                 resource_id="", third_resource_id="", effect_id="", source_platform=0, wave_points=[], check_flag=1,
                 local_material_id="", copyright_limit_type="none")
        d["materials"]["audios"].append(m)
        s = copy.deepcopy(seg_molde)
        s.update(id=novo_id(), material_id=m["id"], extra_material_refs=copiar_refs(seg_molde, d),
                 source_timerange={"start": 0, "duration": us(dur)}, target_timerange={"start": us(e["em"]), "duration": us(dur)},
                 volume=e.get("volume", 1.0), speed=1.0, common_keyframes=[], keyframe_refs=[])
        livre = next((k for k, (fim, _) in enumerate(trilhas) if fim <= e["em"] + 1e-6), None)
        if livre is None:
            t = dict(copy.deepcopy({k: v for k, v in trilha_molde.items() if k != "segments"}), id=novo_id(), segments=[],
                     name=f"{nome} {len(trilhas) + 1}")
            trilhas.append([0.0, t])
            livre = len(trilhas) - 1
        trilhas[livre][0] = e["em"] + dur
        trilhas[livre][1]["segments"].append(s)
    d["tracks"] += [t for _, t in trilhas]
    return len(plano["efeitos"]), len(trilhas)


def trocar(d, plano):
    """Troca o arquivo dos clipes das trilhas do plano, pelo nome do efeito; o resto do clipe fica."""
    nome = plano.get("trilha", "SFX (Concat)")
    por_nome = {e["nome"]: e for e in plano["efeitos"]}
    n = 0
    for t in d["tracks"]:
        if not t.get("name", "").startswith(nome):
            continue
        for seg in t["segments"]:
            _, m = material(d, seg["material_id"])
            e = por_nome.get(m.get("name")) if m else None
            if not e or m["path"] == e["arquivo"]:
                continue
            local = e["arquivo"].replace("/Library/Containers/com.lemon.lvoverseas/Data", "")
            if not os.path.exists(local):
                sys.exit(f"não existe: {local}")
            dur = us(e["duracao"])
            m.update(path=e["arquivo"], duration=dur, unique_id=uuid.uuid4().hex)
            seg["source_timerange"] = {"start": 0, "duration": dur}
            seg["target_timerange"] = dict(seg["target_timerange"], duration=dur)
            n += 1
    return n


def main():
    pasta, plano_arq = os.path.abspath(sys.argv[1]), sys.argv[2]
    if subprocess.run(["pgrep", "-x", "CapCut"], capture_output=True).returncode == 0:
        sys.exit("feche o CapCut antes (ele regrava o projeto aberto por cima)")
    plano = json.load(open(plano_arq, encoding="utf-8"))
    alvos = [p for p in [os.path.join(pasta, "draft_info.json"), os.path.join(pasta, "template-2.tmp")]
             + glob.glob(os.path.join(pasta, "Timelines", "*", "draft_info.json")) if os.path.exists(p)]
    copia = os.path.expanduser(f"~/Desktop/Concat/backup-capcut/{os.path.basename(pasta)} {time.strftime('%Y-%m-%d %H%M%S')}")
    while os.path.exists(copia):
        copia += "+"
    for p in glob.glob(os.path.join(pasta, "*.json")) + glob.glob(os.path.join(pasta, "*.tmp")) + glob.glob(os.path.join(pasta, "Timelines", "**", "*"), recursive=True):
        if os.path.isfile(p):
            destino = os.path.join(copia, os.path.relpath(p, pasta))
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            shutil.copy2(p, destino)
    for p in alvos:
        d = json.load(open(p, encoding="utf-8"))
        if not any(t["type"] == "audio" and t["segments"] for t in d["tracks"]):
            continue   # linha do tempo sem áudio (outra timeline do projeto): não mexe
        if "--trocar" in sys.argv:
            n, nt = trocar(d, plano), None
        else:
            n, nt = aplicar(d, plano)
        open(p, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, separators=(",", ":")))
    if nt is None:
        print(f"{n} clipes com arquivo novo; backup em {copia}")
    else:
        print(f"{n} efeitos em {nt} trilhas \"{plano.get('trilha')}\"; backup em {copia}")


if __name__ == "__main__":
    main()
