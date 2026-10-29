#!/usr/bin/env python3
"""Põe B-rolls de foto num projeto do CapCut que já está cortado (sem refazer a trilha principal).

Pedido de 2026-10-29 ("o vídeo já está cortado, eu só preciso que você adicione as legendas e b-rolls, linkando
sempre com o Higgsfield"): as fotos (broll_higgsfield.py) entram numa trilha "B-roll (Concat)" por cima do vídeo,
no jeito do projeto modelo: o segmento de foto dele e as entradas nativas que a usuária escolheu lá (no
"13 - Bioestimulador de colágeno" ela trocou para "Diminuir zoom" e "Slide lateral", alternadas aqui), mais o
avanço lento de zoom (100% -> 108%) que ela manteve.

Uso: capcut_broll.py <pasta do projeto no CapCut> <plano.json> <pasta das imagens> [--modelo=<projeto modelo>]
  plano.json: o mesmo do broll_higgsfield.py ({"cenas": [{"nome", "inicio", "fim"}, ...]}); imagem = <nome>.png
O CapCut precisa estar FECHADO. Backup em ~/Desktop/Concat/backup-capcut/. Rodar de novo troca os B-rolls.
"""
import copy
import glob
import json
import os
import shutil
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from capcut_montar import material, segmento_de, novo_id, us  # noqa: E402

RAIZ = os.path.expanduser("~/Movies/CapCut/User Data/Projects/com.lveditor.draft")
BROLL = os.path.expanduser("~/Movies/CapCut/User Data/Broll Concat")
BROLL_VISTA = os.path.expanduser("~/Library/Containers/com.lemon.lvoverseas/Data/Movies/CapCut/User Data/Broll Concat")
NOME_TRILHA = "B-roll (Concat)"
ZOOM = 1.08


def main():
    pasta, plano, imagens = os.path.abspath(sys.argv[1]), json.load(open(sys.argv[2])), sys.argv[3]
    modelo_nome = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--modelo=")), "13 - Bioestimulador de colágeno")
    if not os.environ.get("CAPCUT_TESTE") and subprocess.run(["pgrep", "-x", "CapCut"], capture_output=True).returncode == 0:
        sys.exit("feche o CapCut antes (ele regrava o projeto aberto por cima)")
    alvos = [p for p in [os.path.join(pasta, "draft_info.json")] + glob.glob(os.path.join(pasta, "Timelines", "*", "draft_info.json"))
             if os.path.exists(p)]
    N = json.load(open(alvos[0], encoding="utf-8"))
    B = json.load(open(os.path.join(RAIZ, modelo_nome, "draft_info.json"), encoding="utf-8"))
    copia = os.path.expanduser(f"~/Desktop/Concat/backup-capcut/{os.path.basename(pasta)} {time.strftime('%Y-%m-%d %H%M%S')}")
    while os.path.exists(copia):
        copia += "+"
    for p in glob.glob(os.path.join(pasta, "*.json")) + glob.glob(os.path.join(pasta, "*.tmp")) + glob.glob(os.path.join(pasta, "Timelines", "**", "*"), recursive=True):
        if os.path.isfile(p):
            destino = os.path.join(copia, os.path.relpath(p, pasta))
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            shutil.copy2(p, destino)

    # o jeito do B-roll: segmento de foto do modelo e as entradas nativas que ela usa nas fotos
    trilha_mod, foto_seg = next((t, s) for t in B["tracks"] if t["type"] == "video" for s in t["segments"]
                                if (material(B, s["material_id"])[1] or {}).get("type") == "photo"
                                and (material(B, s["material_id"])[1] or {}).get("path", "").endswith((".png", ".jpg")))
    _, foto_mat = material(B, foto_seg["material_id"])
    entradas, anim_mod = [], None
    for t in B["tracks"]:
        for s in t["segments"]:
            if (material(B, s["material_id"])[1] or {}).get("type") != "photo":
                continue
            for r in s["extra_material_refs"]:
                k, m = material(B, r)
                if k == "material_animations" and m.get("animations"):
                    anim_mod = anim_mod or m
                    for a in m["animations"]:
                        if a["type"] == "in" and a["name"] not in [e["name"] for e in entradas]:
                            entradas.append(a)

    destino = os.path.join(BROLL, os.path.basename(pasta)[:60])
    os.makedirs(destino, exist_ok=True)
    N["tracks"] = [t for t in N["tracks"] if t.get("name") != NOME_TRILHA]
    tr = dict(copy.deepcopy({k: v for k, v in trilha_mod.items() if k != "segments"}), id=novo_id(), name=NOME_TRILHA,
              is_default_name=False, segments=[])
    for n, c in enumerate(plano["cenas"]):
        arq = os.path.join(imagens, c["nome"] + ".png")
        shutil.copy2(arq, os.path.join(destino, os.path.basename(arq)))
        from PIL import Image
        larg, alt = Image.open(arq).size
        m = dict(copy.deepcopy(foto_mat), id=novo_id(), path=os.path.join(BROLL_VISTA, os.path.basename(destino), os.path.basename(arq)),
                 width=larg, height=alt, material_name=os.path.basename(arq), local_material_id="", category_name="local")
        N["materials"].setdefault("videos", []).append(m)
        dur = c["fim"] - c["inicio"]
        s = segmento_de(foto_seg, B, N, m["id"], 0.0, dur, c["inicio"], dur)
        s["extra_material_refs"] = [r for r in s["extra_material_refs"] if material(N, r)[0] != "material_animations"]
        if entradas:
            anim = dict(copy.deepcopy(anim_mod), id=novo_id(), animations=[copy.deepcopy(entradas[n % len(entradas)])])
            N["materials"].setdefault("material_animations", []).append(anim)
            s["extra_material_refs"].append(anim["id"])
        # a foto cobre o quadro (9:16) e avança devagar
        s["clip"]["scale"] = {"x": 1.0, "y": 1.0}
        s["clip"]["transform"] = {"x": 0.0, "y": 0.0}
        for prop, v0, v1 in (("KFTypePositionX", 0.0, 0.0), ("KFTypePositionY", 0.0, 0.0), ("KFTypeScaleX", 1.0, ZOOM), ("KFTypeRotation", 0.0, 0.0)):
            kf = lambda t, v: {"curveType": "Line", "graphID": "", "id": novo_id(), "left_control": {"x": 0.0, "y": 0.0},  # noqa: E731
                               "right_control": {"x": 0.0, "y": 0.0}, "string_value": "", "time_offset": t, "values": [v]}
            s["common_keyframes"].append({"id": novo_id(), "material_id": "", "property_type": prop,
                                          "keyframe_list": [kf(0, v0), kf(us(dur), v1)]})
        tr["segments"].append(s)
    principal = next(i for i, t in enumerate(N["tracks"]) if t["type"] == "video")
    N["tracks"].insert(principal + 1, tr)
    if N.get("render_index_track_mode_on"):
        for i, t in enumerate(N["tracks"]):
            for seg in t["segments"]:
                seg["track_render_index"] = i
    texto = json.dumps(N, ensure_ascii=False, separators=(",", ":"))
    for p in alvos:
        open(p, "w", encoding="utf-8").write(texto)
        tmp = os.path.join(os.path.dirname(p), "template-2.tmp")
        if os.path.exists(tmp):
            open(tmp, "w", encoding="utf-8").write(texto)
    print(f"{len(tr['segments'])} B-rolls na trilha \"{NOME_TRILHA}\" (entradas: {[e['name'] for e in entradas]}); backup em {copia}")


if __name__ == "__main__":
    main()
