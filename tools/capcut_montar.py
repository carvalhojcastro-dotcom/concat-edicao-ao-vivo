#!/usr/bin/env python3
"""Monta a edição de um projeto do CapCut a partir de um plano, copiando o jeito de editar da usuária de
um projeto que ela já editou (o "modelo").

Pedido de 2026-10-27: "aprenda com a edição do primeiro e replique no segundo: velocidade, cortes no
momento certo, zoom in, zoom out, legendas, efeitos sonoros (da minha lista no CapCut), estilo de música
e volume dela ... me entregue pronto e editável no CapCut". O que vem do modelo (copiado, não inventado):
  - em cada pedaço de fala: velocidade, volume da voz, redução de ruído do CapCut, retoque de rosto e o
    resto das referências do 1º pedaço do modelo;
  - a música: volume e fades do segmento de música do modelo (a faixa pode ser outra, do mesmo estilo);
  - os efeitos sonoros: o material e o volume de cada efeito do modelo, pelo nome.
O projeto novo já tem o bruto importado (um clipe só); a trilha principal é refeita com os pedaços.

Plano (JSON):
  {"pedacos": [{"fonte": s, "fonte_dur": s, "ini": s, "dur": s, "escala": 1.3, "tx": 0.0, "ty": 0.05}, ...],
   "musica": {"projeto": "<pasta do projeto do CapCut que já usa a faixa>", "nome": "Lofi Garden Groove", "inicio": 0.0},
   "efeitos": [{"nome": "Clique do mouse", "em": 0.0}, ...],
   "broll": [{"arquivo": "<caminho visto pelo CapCut>", "largura": 1152, "altura": 2048, "inicio": s, "fim": s, "zoom": 1.08}, ...],
   "broll_modelo": "<pasta de um projeto com B-roll de foto>"}   (opcional: o jeito do B-roll vem de lá)
  As fotos precisam estar numa pasta que o CapCut (sandbox) lê: ~/Movies/CapCut/User Data/..., com o caminho
  escrito como ele vê (~/Library/Containers/com.lemon.lvoverseas/Data/Movies/CapCut/User Data/...).
  tx/ty: posição do CapCut (metade do quadro; y para cima). Tempos em segundos.

O CapCut precisa estar FECHADO. Backup em ~/Desktop/Concat/backup-capcut/.
Uso: capcut_montar.py <pasta do projeto novo> <pasta do projeto modelo> <plano.json>
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


def copiar_refs(seg, de, para):
    """Copia as referências (velocidade, ruído, retoque, fades...) de um segmento do modelo, com ids novos."""
    ids = []
    for r in seg.get("extra_material_refs", []):
        k, m = material(de, r)
        if m is None:
            continue
        m = copy.deepcopy(m)
        m["id"] = novo_id()
        para["materials"].setdefault(k, []).append(m)
        ids.append(m["id"])
    return ids


def segmento_de(seg_modelo, de, para, material_id, fonte, fonte_dur, ini, dur):
    s = copy.deepcopy(seg_modelo)
    s.update(id=novo_id(), material_id=material_id, extra_material_refs=copiar_refs(seg_modelo, de, para),
             source_timerange={"start": us(fonte), "duration": us(fonte_dur)},
             target_timerange={"start": us(ini), "duration": us(dur)}, common_keyframes=[], keyframe_refs=[])
    return s


def main():
    novo_dir, modelo_dir, plano_arq = [os.path.abspath(a) for a in sys.argv[1:4]]
    if not os.environ.get("CAPCUT_TESTE") and subprocess.run(["pgrep", "-x", "CapCut"], capture_output=True).returncode == 0:
        sys.exit("feche o CapCut antes (ele regrava o projeto aberto por cima)")
    plano = json.load(open(plano_arq, encoding="utf-8"))
    alvos = [p for p in [os.path.join(novo_dir, "draft_info.json")] + glob.glob(os.path.join(novo_dir, "Timelines", "*", "draft_info.json"))
             if os.path.exists(p)]
    N = json.load(open(alvos[0], encoding="utf-8"))
    A = json.load(open(os.path.join(modelo_dir, "draft_info.json"), encoding="utf-8"))

    copia = os.path.expanduser(f"~/Desktop/Concat/backup-capcut/{os.path.basename(novo_dir)} {time.strftime('%Y-%m-%d %H%M%S')}")
    for p in glob.glob(os.path.join(novo_dir, "*.json")) + glob.glob(os.path.join(novo_dir, "*.tmp")) + glob.glob(os.path.join(novo_dir, "Timelines", "**", "*"), recursive=True):
        if os.path.isfile(p):
            destino = os.path.join(copia, os.path.relpath(p, novo_dir))
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            shutil.copy2(p, destino)

    # trilha principal: o bruto vira os pedaços do plano, cada um com os ajustes de voz do modelo
    principal = next(t for t in N["tracks"] if t["type"] == "video")
    bruto_id = principal["segments"][0]["material_id"]
    velhos = {r for s in principal["segments"] for r in s.get("extra_material_refs", [])}
    for k, v in N["materials"].items():
        if isinstance(v, list):
            N["materials"][k] = [m for m in v if not (isinstance(m, dict) and m.get("id") in velhos)]
    modelo_voz = sorted(next(t for t in A["tracks"] if t["type"] == "video")["segments"], key=lambda s: s["target_timerange"]["start"])[0]
    segs = []
    for p in plano["pedacos"]:
        s = segmento_de(modelo_voz, A, N, bruto_id, p["fonte"], p["fonte_dur"], p["ini"], p["dur"])
        s["clip"]["scale"] = {"x": p["escala"], "y": p["escala"]}
        s["clip"]["transform"] = {"x": p.get("tx", 0.0), "y": p.get("ty", 0.0)}
        s["uniform_scale"] = {"on": True, "value": p["escala"]}
        segs.append(s)
    principal["segments"] = segs
    total = plano["pedacos"][-1]["ini"] + plano["pedacos"][-1]["dur"]
    N["duration"] = us(total)
    # camadas do vídeo inteiro que vieram do modelo (ajuste de cor, LUT, sombra): vão até o fim do novo
    for t in N["tracks"]:
        if t is not principal and len(t["segments"]) == 1 and t["type"] in ("adjust", "video", "effect", "filter"):
            tt = t["segments"][0]["target_timerange"]
            tt["duration"] = us(total) - tt["start"]
            if t["segments"][0].get("source_timerange"):
                t["segments"][0]["source_timerange"]["duration"] = tt["duration"]

    # B-roll: fotos numa trilha por cima, com a animação de entrada que a usuária usa (Fade-in do modelo)
    # e um avanço lento de zoom no tempo todo (movimento na foto; pedido de 2026-10-27)
    N["tracks"] = [t for t in N["tracks"] if not t.get("name", "").startswith("B-roll")]
    brolls = plano.get("broll", [])
    if brolls:
        B = json.load(open(os.path.join(plano["broll_modelo"], "draft_info.json"), encoding="utf-8")) if plano.get("broll_modelo") else A
        trilha_modelo = next(t for t in B["tracks"] if t["type"] == "video" and t.get("flag") == 2
                             and any(material(B, s["material_id"])[1].get("type") == "photo" for s in t["segments"]))
        foto_seg = next(s for s in trilha_modelo["segments"] if material(B, s["material_id"])[1].get("type") == "photo")
        anim_modelo = next(m for s in trilha_modelo["segments"] for r in s["extra_material_refs"]
                           for k, m in [material(B, r)] if k == "material_animations" and m.get("animations"))
        entrada = [a for a in anim_modelo["animations"] if a["type"] == "in"]
        _, foto_mat = material(B, foto_seg["material_id"])
        tr = dict(copy.deepcopy({k: v for k, v in trilha_modelo.items() if k != "segments"}), id=novo_id(), name="B-roll", segments=[])
        bruto_mat = material(N, bruto_id)[1]
        for b in brolls:
            dur = b["fim"] - b["inicio"]
            if b.get("tipo") == "video":   # motion graphics prontos (MP4): material de vídeo, sem animação nem zoom
                m = dict(copy.deepcopy(bruto_mat), id=novo_id(), path=b["arquivo"], width=b["largura"], height=b["altura"],
                         duration=us(b.get("duracao", dur)), material_name=os.path.basename(b["arquivo"]),
                         local_material_id=novo_id().lower(), md5="")
                if isinstance(m.get("matting"), dict):
                    m["matting"].update(flag=0, path="", custom_matting_id="")
            else:
                m = dict(copy.deepcopy(foto_mat), id=novo_id(), path=b["arquivo"], width=b["largura"], height=b["altura"],
                         material_name=os.path.basename(b["arquivo"]))
            N["materials"].setdefault("videos", []).append(m)
            s = segmento_de(foto_seg, B, N, m["id"], 0.0, dur, b["inicio"], dur)
            s["volume"] = 0.0 if b.get("tipo") == "video" else s.get("volume", 1.0)
            if b.get("tipo") != "video":
                anim = dict(copy.deepcopy(anim_modelo), id=novo_id(), animations=copy.deepcopy(entrada))
                N["materials"].setdefault("material_animations", []).append(anim)
                s["extra_material_refs"].append(anim["id"])
            s["clip"]["scale"] = {"x": 1.0, "y": 1.0}
            s["clip"]["transform"] = {"x": 0.0, "y": 0.0}
            zoom = b.get("zoom", 1.0 if b.get("tipo") == "video" else 1.08)
            if abs(zoom - 1.0) < 1e-6:
                tr["segments"].append(s)
                continue
            for prop, v0, v1 in (("KFTypePositionX", 0.0, 0.0), ("KFTypePositionY", 0.0, 0.0), ("KFTypeScaleX", 1.0, zoom), ("KFTypeRotation", 0.0, 0.0)):
                kf = lambda t, v: {"curveType": "Line", "graphID": "", "id": novo_id(), "left_control": {"x": 0.0, "y": 0.0},  # noqa: E731
                                   "right_control": {"x": 0.0, "y": 0.0}, "string_value": "", "time_offset": t, "values": [v]}
                s["common_keyframes"].append({"id": novo_id(), "material_id": "", "property_type": prop,
                                              "keyframe_list": [kf(0, v0), kf(us(dur), v1)]})
            tr["segments"].append(s)
        N["tracks"].insert(1, tr)

    # tira áudio de uma montagem anterior (rodar de novo refaz)
    N["tracks"] = [t for t in N["tracks"] if t["type"] != "audio"]
    audios_modelo = {}
    for t in A["tracks"]:
        if t["type"] == "audio":
            for s in t["segments"]:
                _, m = material(A, s["material_id"])
                audios_modelo.setdefault(m.get("name"), (s, m, t))
    N["materials"].setdefault("audios", [])

    # música: segmento de música do modelo (volume, fades) com a faixa escolhida
    mus = plano.get("musica")
    if mus:
        seg_mus, _, trilha_mus = max(((s, m, t) for s, m, t in audios_modelo.values()), key=lambda x: x[0]["target_timerange"]["duration"])
        F = json.load(open(os.path.join(mus["projeto"], "draft_info.json"), encoding="utf-8"))
        faixa = next(m for m in F["materials"]["audios"] if m.get("name") == mus["nome"])
        faixa = dict(copy.deepcopy(faixa), id=novo_id())
        N["materials"]["audios"].append(faixa)
        s = segmento_de(seg_mus, A, N, faixa["id"], mus.get("inicio", 0.0), total, 0.0, total)
        N["tracks"].append(dict(copy.deepcopy({k: v for k, v in trilha_mus.items() if k != "segments"}), id=novo_id(), segments=[s]))

    # efeitos sonoros: material e volume de cada efeito do modelo, pelo nome; uma trilha por sobreposição
    trilhas = []
    for e in sorted(plano.get("efeitos", []), key=lambda e: e["em"]):
        seg_e, mat_e, trilha_e = audios_modelo[e["nome"]]
        m = dict(copy.deepcopy(mat_e), id=novo_id())
        N["materials"]["audios"].append(m)
        dur = seg_e["target_timerange"]["duration"] / 1e6
        s = segmento_de(seg_e, A, N, m["id"], seg_e["source_timerange"]["start"] / 1e6, seg_e["source_timerange"]["duration"] / 1e6, e["em"], dur)
        livre = next((k for k, (fim, _) in enumerate(trilhas) if fim <= e["em"]), None)
        if livre is None:
            trilhas.append([0.0, dict(copy.deepcopy({k: v for k, v in trilha_e.items() if k != "segments"}), id=novo_id(), segments=[])])
            livre = len(trilhas) - 1
        trilhas[livre][0] = e["em"] + dur
        trilhas[livre][1]["segments"].append(s)
    N["tracks"] += [t for _, t in trilhas]

    texto = json.dumps(N, ensure_ascii=False, separators=(",", ":"))
    for p in alvos:
        open(p, "w", encoding="utf-8").write(texto)
        tmp = os.path.join(os.path.dirname(p), "template-2.tmp")
        if os.path.exists(tmp):
            open(tmp, "w", encoding="utf-8").write(texto)
    meta = os.path.join(novo_dir, "draft_meta_info.json")
    if os.path.exists(meta):
        mi = json.load(open(meta, encoding="utf-8"))
        mi["tm_duration"] = us(total)
        json.dump(mi, open(meta, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"{len(segs)} pedaços ({total:.2f}s), música {mus['nome'] if mus else '-'}, {len(plano.get('efeitos', []))} efeitos; backup em {copia}")


if __name__ == "__main__":
    main()
