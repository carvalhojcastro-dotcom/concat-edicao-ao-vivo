#!/usr/bin/env python3
"""Monta um corte de podcast (vídeo horizontal) num projeto vertical do CapCut: pessoa em tela cheia ou tela
dividida em duas metades, com a velocidade e o ganho de voz do plano.

Pedido de 2026-10-31 (Humman 02, Dr. Rafael Almeida e Dra. Ive): "se estivermos todos na câmera mais ampla ...
divida a tela colocando o Dr. Rafael e a doutora Ive em cima e eu e a minha esposa embaixo ... Quando a Ive
estiver se direcionando para o Rafael, é importante que ele também apareça ... Em outros casos, você pode
simplesmente botar a pessoa e alternar entre uma pessoa e outra com a tela cheia ... acelere o vídeo em 1.05".

Como o CapCut desenha (medido na capa de um projeto com recorte, 2026-10-31): o recorte do material vira o
quadro do clipe, que é encaixado na tela (largura ou altura) e só então recebe escala e posição (posição em
metades da tela, y para cima). Então:
  - tela cheia: sem recorte, escala ~3,2 (o 16:9 enche a altura de 1920) e x no rosto, como nos cortes do EP01;
  - tela dividida: recorte na proporção 1080:960 (largura/altura em pixels do bruto), escala 1, y +0,5 (cima)
    ou -0,5 (baixo). A metade de baixo vai numa trilha própria, muda.

Plano:
{"velocidade": 1.05, "volume": 4.0,
 "pecas": [{"fonte": 812.4, "fonte_dur": 6.2, "layout": "solo", "escala": 3.2, "tx": 1.1, "ty": 0.0,
            "kx": [[812.4, 1.1], [814.0, 1.1], [814.8, 1.25]]},   # opcional: seguir a pessoa (s do bruto, x)
           {"fonte": 818.6, "fonte_dur": 4.0, "layout": "dupla", "cima": [x0, y0, x1, y1], "baixo": [x0, y0, x1, y1]}]}
  (recortes em fração do bruto: canto de cima à esquerda e de baixo à direita)
O projeto vem do capcut_novo.py (um clipe do bruto na trilha principal); rodar de novo refaz a montagem.
O CapCut precisa estar FECHADO. Backup em ~/Desktop/Claude Code Skills/backup-capcut/.
Uso: capcut_podcast.py <pasta do projeto no CapCut> <plano.json>
"""
import copy
import glob
import json
import math
import os
import shutil
import subprocess
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from capcut_montar import material  # noqa: E402

novo_id = lambda: str(uuid.uuid4()).upper()  # noqa: E731
us = lambda s: int(round(s * 1e6))  # noqa: E731
TRILHA_BAIXO = "Tela dividida (Concat)"


def recorte(x0, y0, x1, y1):
    return {"upper_left_x": x0, "upper_left_y": y0, "upper_right_x": x1, "upper_right_y": y0,
            "lower_left_x": x0, "lower_left_y": y1, "lower_right_x": x1, "lower_right_y": y1}


def chaves(prop, pontos):
    """Uma propriedade com keyframes lineares, como o CapCut grava (time_offset em us do BRUTO, como nos keyframes
    que o usuário pôs à mão no "12 - Linda pro Natal")."""
    return {"id": novo_id(), "material_id": "", "property_type": prop,
            "keyframe_list": [{"id": novo_id(), "curveType": "Line", "time_offset": us(t),
                               "left_control": {"x": 0.0, "y": 0.0}, "right_control": {"x": 0.0, "y": 0.0},
                               "values": [v], "string_value": "", "graphID": ""} for t, v in pontos]}


def montar(d, plano):
    principal = next(t for t in d["tracks"] if t["type"] == "video")
    # o molde é o primeiro clipe da trilha principal (ajustes de voz, retoque etc. do projeto modelo)
    molde = copy.deepcopy(sorted(principal["segments"], key=lambda s: s["target_timerange"]["start"])[0])
    _, mat_bruto = material(d, molde["material_id"])
    if mat_bruto is None:
        sys.exit("a trilha principal não tem o bruto")
    inteiro = recorte(0.0, 0.0, 1.0, 1.0)
    if any(abs(mat_bruto.get("crop", inteiro)[k] - inteiro[k]) > 1e-6 for k in inteiro):
        # rodar de novo com o 1º clipe em tela dividida: o molde veio recortado; o bruto é o material sem recorte
        mat_bruto = next((m for m in d["materials"]["videos"] if m.get("path") == mat_bruto["path"]
                          and all(abs(m.get("crop", inteiro)[k] - inteiro[k]) < 1e-6 for k in inteiro)), None) \
            or dict(copy.deepcopy(mat_bruto), id=novo_id(), crop=inteiro)
        if mat_bruto not in d["materials"]["videos"]:
            d["materials"]["videos"].append(mat_bruto)
    # ajustes do molde (velocidade, canal de som...) guardados antes de apagar a montagem anterior
    refs_molde = [(k, copy.deepcopy(m)) for r in molde.get("extra_material_refs", []) for k, m in [material(d, r)] if m]
    # rodar de novo: tira a montagem anterior (clipes, recortes e a trilha da metade de baixo)
    velhos = {r for t in d["tracks"] if t is principal or t.get("name") == TRILHA_BAIXO for s in t["segments"]
              for r in s.get("extra_material_refs", []) + ([s["material_id"]] if s["material_id"] != mat_bruto["id"] else [])}
    for k, v in d["materials"].items():
        if isinstance(v, list):
            d["materials"][k] = [m for m in v if not (isinstance(m, dict) and m.get("id") in velhos)]
    d["tracks"] = [t for t in d["tracks"] if t.get("name") != TRILHA_BAIXO]
    vel, vol = plano.get("velocidade", 1.0), plano.get("volume")

    def clipe(mat_id, p, ini, dur, escala, tx, ty, volume):
        s = copy.deepcopy(molde)
        refs = []
        for k, m in refs_molde:
            m = dict(copy.deepcopy(m), id=novo_id())
            d["materials"].setdefault(k, []).append(m)
            refs.append(m["id"])
        # emendas sem quadro adiantado (2026-11-10, "no primeiro frame do corte b ... ainda tem o enquadramento do
        # corte a"): o pedaço começa no µs logo acima do quadro (o µs truncado lia o quadro anterior) e a velocidade é
        # exatamente origem/timeline; com 1,1 redondo e a duração arredondada a quadros, o último quadro de um pedaço
        # podia ler o primeiro quadro do plano seguinte
        # os pedaços caem na grade de quadros do bruto (fps do plano, 30 por padrão): "fonte" com 4 casas
        # (709,8333) ficava abaixo do quadro 21295 (709,83333…) e o 1º quadro mostrava o plano anterior
        fps = plano.get("fps", 30)
        ini_us = math.ceil(round(round(p["fonte"] * fps) / fps * 1e6, 3))
        src_us = math.ceil(round(round((p["fonte"] + p["fonte_dur"]) * fps) / fps * 1e6, 3)) - ini_us
        vel_p = src_us / us(dur)
        s.update(id=novo_id(), material_id=mat_id, extra_material_refs=refs,
                 source_timerange={"start": ini_us, "duration": src_us},
                 target_timerange={"start": us(ini), "duration": us(dur)}, common_keyframes=[], keyframe_refs=[], speed=vel_p)
        for r in s["extra_material_refs"]:
            k, m = material(d, r)
            if k == "speeds":
                m["speed"] = vel_p
        s["clip"]["scale"] = {"x": escala, "y": escala}
        s["clip"]["transform"] = {"x": tx, "y": ty}
        s["uniform_scale"] = {"on": True, "value": 1.0}   # proporção x/y travada (1,0), não o zoom
        if p.get("kx"):   # seguir a pessoa dentro do mesmo plano com keyframes de posição (pedido de 2026-11-10)
            s["clip"]["transform"]["x"] = p["kx"][0][1]
            s["common_keyframes"] = [chaves(prop, [(t, v if prop == "KFTypePositionX" else fixo) for t, v in p["kx"]])
                                     for prop, fixo in (("KFTypePositionX", None), ("KFTypePositionY", ty),
                                                        ("KFTypeScaleX", escala), ("KFTypeRotation", 0.0))]
        if volume is not None:
            s["volume"] = s["last_nonzero_volume"] = volume
        return s

    def mat_recortado(caixa):
        m = dict(copy.deepcopy(mat_bruto), id=novo_id(), crop=recorte(*caixa), crop_ratio="free", crop_scale=1.0)
        d["materials"]["videos"].append(m)
        return m["id"]

    segs, baixo, ini = [], [], 0.0
    for p in plano["pecas"]:
        dur = round(p["fonte_dur"] / vel * 30) / 30
        if p["layout"] == "dupla":
            segs.append(clipe(mat_recortado(p["cima"]), p, ini, dur, 1.0, 0.0, 0.5, vol))
            b = clipe(mat_recortado(p["baixo"]), p, ini, dur, 1.0, 0.0, -0.5, 0.0)
            b["last_nonzero_volume"] = 1.0
            baixo.append(b)
        else:
            segs.append(clipe(mat_bruto["id"], p, ini, dur, p.get("escala", 3.2), p.get("tx", 0.0), p.get("ty", 0.0), vol))
        ini += dur
    principal["segments"] = segs
    if baixo:
        t = dict(copy.deepcopy({k: v for k, v in principal.items() if k != "segments"}), id=novo_id(), name=TRILHA_BAIXO,
                 segments=baixo, flag=0)
        d["tracks"].insert(d["tracks"].index(principal) + 1, t)
    if d.get("render_index_track_mode_on"):
        for i, t in enumerate(d["tracks"]):
            for s in t["segments"]:
                s["track_render_index"] = i
    d["duration"] = us(ini)
    for t in d["tracks"]:   # camadas do vídeo inteiro (ajuste, LUT) vão até o fim
        if t is not principal and t.get("name") != TRILHA_BAIXO and len(t["segments"]) == 1 and t["type"] in ("adjust", "video", "effect", "filter"):
            tt = t["segments"][0]["target_timerange"]
            tt["duration"] = us(ini) - tt["start"]
    return len(segs), len(baixo), ini


def capa(d, destino):
    """Primeiro quadro do corte como o CapCut desenha (recorte do material, encaixe na largura, escala e posição)."""
    from PIL import Image
    tela = Image.new("RGB", (1080, 1920))
    for tr in [t for t in d["tracks"] if t["type"] == "video"]:
        s = next((s for s in tr["segments"] if s["target_timerange"]["start"] == 0), None)
        if not s:
            continue
        _, m = material(d, s["material_id"])
        bruto = m["path"].replace("/Library/Containers/com.lemon.lvoverseas/Data", "")
        t0 = s["source_timerange"]["start"] / 1e6 + 0.3
        png = destino + ".png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t0:.3f}", "-i", "file:" + bruto, "-frames:v", "1", png], check=True)
        img = Image.open(png).convert("RGB")
        os.remove(png)
        c = m.get("crop", {})
        W0, H0 = img.size
        img = img.crop((int(c.get("upper_left_x", 0) * W0), int(c.get("upper_left_y", 0) * H0),
                        int(c.get("lower_right_x", 1) * W0), int(c.get("lower_right_y", 1) * H0)))
        e, tx, ty = s["clip"]["scale"]["x"], s["clip"]["transform"]["x"], s["clip"]["transform"]["y"]
        w, h = int(1080 * e), int(img.height * 1080 / img.width * e)
        tela.paste(img.resize((w, h)), (int(540 - w / 2 + tx * 540), int(960 - h / 2 - ty * 960)))
    tela.save(destino, quality=90)


def main():
    pasta, plano_arq = os.path.abspath(sys.argv[1]), sys.argv[2]
    if subprocess.run(["pgrep", "-x", "CapCut"], capture_output=True).returncode == 0:
        sys.exit("feche o CapCut antes (ele regrava o projeto aberto por cima)")
    plano = json.load(open(plano_arq, encoding="utf-8"))
    alvos = [p for p in [os.path.join(pasta, "draft_info.json"), os.path.join(pasta, "template-2.tmp")]
             + glob.glob(os.path.join(pasta, "Timelines", "*", "draft_info.json")) if os.path.exists(p)]
    copia = os.path.expanduser(f"~/Desktop/Claude Code Skills/backup-capcut/{os.path.basename(pasta)} {time.strftime('%Y-%m-%d %H%M%S')}")
    while os.path.exists(copia):
        copia += "+"
    for p in glob.glob(os.path.join(pasta, "*.json")) + glob.glob(os.path.join(pasta, "*.tmp")) + glob.glob(os.path.join(pasta, "Timelines", "**", "*"), recursive=True):
        if os.path.isfile(p):
            destino = os.path.join(copia, os.path.relpath(p, pasta))
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            shutil.copy2(p, destino)
    for p in alvos:
        d = json.load(open(p, encoding="utf-8"))
        n, nb, total = montar(d, plano)
        open(p, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, separators=(",", ":")))
    meta = os.path.join(pasta, "draft_meta_info.json")
    if os.path.exists(meta):
        mi = json.load(open(meta, encoding="utf-8"))
        mi["tm_duration"] = us(total)
        json.dump(mi, open(meta, "w", encoding="utf-8"), ensure_ascii=False)
    # lista de projetos: duração do corte (não a do bruto) e capa com o primeiro quadro enquadrado (2026-11-05)
    raiz_p = os.path.join(os.path.dirname(pasta), "root_meta_info.json")
    raiz = json.load(open(raiz_p, encoding="utf-8"))
    for e in raiz["all_draft_store"]:
        if os.path.realpath(e.get("draft_fold_path", "")) == os.path.realpath(pasta):
            e["tm_duration"] = us(total)
    json.dump(raiz, open(raiz_p, "w", encoding="utf-8"), ensure_ascii=False)
    try:
        capa(d, os.path.join(pasta, "draft_cover.jpg"))
    except Exception as erro:   # a capa é só a miniatura da lista: não impede a montagem
        print("capa não gerada:", erro)
    print(f"{n} pedaços ({nb} com tela dividida), {total:.2f}s a {plano.get('velocidade', 1.0)}x; backup em {copia}")


if __name__ == "__main__":
    main()
