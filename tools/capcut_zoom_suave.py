#!/usr/bin/env python3
"""Zoom in ou zoom out animado dentro de um take, com a curva predefinida "Desaceleração na saída" do
CapCut no keyframe final, como a usuária faz à mão.

Pedido de 2026-10-30: "às vezes eu gosto de usar, em alguns takes, esse zoom in ou zoom out com
'desaceleração na saída' na curva de movimento predefinida ... usar às vezes, mas não muitas". Medido no
projeto dela "27 - Aplicar 30% de desconto..." (Sabrina): ~1 take animado a cada 7. O movimento começa no
meio do take (0,8 a 2 s depois do corte) e dura 1,1 a 2,5 s, quase sempre de 1,09 para 1,2-1,36 (um zoom out
de 1,4 para 1,2). A posição anda junto para manter o enquadramento, e só o keyframe final leva a curva
(alça de entrada a 42% do intervalo, horizontal; `keyframe_graph_list` com o recurso 7002056258991690241).

Plano: {"zooms": [{"em": 53.6, "ini": 0.3, "fim": 2.6, "escala": 1.3, "tx": -0.07, "ty": 0.03}, ...]}
  em: início do take na timeline (s); ini/fim: segundos dentro do take; escala/tx/ty: onde o zoom chega
  (tx/ty como no CapCut: metade do quadro, y para cima). O ponto de partida é o enquadramento atual do take.
O CapCut precisa estar FECHADO. Backup em ~/Desktop/Concat/backup-capcut/.
Uso: capcut_zoom_suave.py <pasta do projeto no CapCut> <plano.json>
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
CURVA = {"resource_id": "7002056258991690241", "resource_name": "Desaceleração na saída", "source_platform": 1, "graph_points": []}
ALCA = 0.42   # alça de entrada do keyframe final, em fração do intervalo (medida nos keyframes dela)
PROPS = ("KFTypeScaleX", "KFTypePositionX", "KFTypePositionY")


def aplicar(d, zooms):
    principal = next(t for t in d["tracks"] if t["type"] == "video")
    d.setdefault("keyframe_graph_list", [])
    feitos = []
    for z in zooms:
        seg = next((s for s in principal["segments"] if s["target_timerange"]["start"] / 1e6 <= z["em"] + 0.02 <
                    (s["target_timerange"]["start"] + s["target_timerange"]["duration"]) / 1e6), None)
        if seg is None:
            sys.exit(f"nenhum take começa em {z['em']}s")
        dur = seg["target_timerange"]["duration"] / 1e6
        if not 0 <= z["ini"] < z["fim"] <= dur + 1e-3:
            sys.exit(f"take em {z['em']}s tem {dur:.2f}s: ini/fim fora dele")
        vel = seg.get("speed", 1.0)
        fonte = seg["source_timerange"]["start"]
        t1 = int(round(fonte + z["ini"] * vel * 1e6))
        t2 = int(round(fonte + z["fim"] * vel * 1e6))
        clip = seg["clip"]
        de = {"KFTypeScaleX": clip["scale"]["x"], "KFTypePositionX": clip["transform"]["x"], "KFTypePositionY": clip["transform"]["y"]}
        para = {"KFTypeScaleX": z["escala"], "KFTypePositionX": z.get("tx", de["KFTypePositionX"]), "KFTypePositionY": z.get("ty", de["KFTypePositionY"])}
        # tira keyframes antigos dessas propriedades (de uma rodada anterior) e as curvas deles
        velhos = [k for k in seg.get("common_keyframes", []) if k["property_type"] in PROPS]
        gids = {kf.get("graphID") for k in velhos for kf in k["keyframe_list"]}
        d["keyframe_graph_list"] = [g for g in d["keyframe_graph_list"] if g["id"] not in gids]
        seg["common_keyframes"] = [k for k in seg.get("common_keyframes", []) if k["property_type"] not in PROPS]
        for prop in PROPS:
            gid = novo_id()
            d["keyframe_graph_list"].append(dict(copy.deepcopy(CURVA), id=gid))
            seg["common_keyframes"].append({"id": novo_id(), "material_id": "", "property_type": prop, "keyframe_list": [
                {"id": novo_id(), "curveType": "FreeCurveInOut", "time_offset": t1, "left_control": {"x": 0.0, "y": 0.0},
                 "right_control": {"x": 0.0, "y": 0.0}, "values": [de[prop]], "string_value": "", "graphID": ""},
                {"id": novo_id(), "curveType": "FreeCurveInOut", "time_offset": t2, "left_control": {"x": -ALCA * (t2 - t1), "y": 0.0},
                 "right_control": {"x": 0.0, "y": 0.0}, "values": [para[prop]], "string_value": "", "graphID": gid}]})
        # como nos projetos dela: o clipe guarda o enquadramento final
        clip["scale"] = {"x": para["KFTypeScaleX"], "y": para["KFTypeScaleX"]}
        clip["transform"] = {"x": para["KFTypePositionX"], "y": para["KFTypePositionY"]}
        if isinstance(seg.get("uniform_scale"), dict):
            seg["uniform_scale"]["value"] = para["KFTypeScaleX"]
        feitos.append(f"{z['em']:.2f}s: {de['KFTypeScaleX']:.2f} -> {para['KFTypeScaleX']:.2f} de {z['ini']:.2f} a {z['fim']:.2f}s do take")
    return feitos


def main():
    pasta, plano_arq = os.path.abspath(sys.argv[1]), sys.argv[2]
    if subprocess.run(["pgrep", "-x", "CapCut"], capture_output=True).returncode == 0:
        sys.exit("feche o CapCut antes (ele regrava o projeto aberto por cima)")
    zooms = json.load(open(plano_arq, encoding="utf-8"))["zooms"]
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
        feitos = aplicar(d, zooms)
        open(p, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, separators=(",", ":")))
    print("\n".join(feitos) + f"\nbackup em {copia}")


if __name__ == "__main__":
    main()
