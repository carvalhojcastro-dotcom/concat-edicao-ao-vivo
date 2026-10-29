#!/usr/bin/env python3
"""Cria um projeto novo no CapCut a partir de um projeto que a usuária já editou (o "modelo"), com o bruto
de outro vídeo no lugar do dela. Depois a montagem entra com capcut_montar.py e as legendas com
capcut_legendas_ig.py.

Pedido de 2026-10-28 ("edite o vídeo da pasta 13 ... abra no CapCut"): não havia projeto no CapCut para o
vídeo. O modelo é um projeto da mesma cliente; dele ficam as camadas que valem para o vídeo inteiro
(ajustes de cor, LUT, a sombra escura atrás das legendas) e o jeito da trilha principal (velocidade,
retoque); sai o que era daquele vídeo (cortes, B-roll, clipes compostos, legendas, música e efeitos).

O CapCut precisa estar FECHADO. A pasta nova fica ao lado das outras e entra na lista de projetos
(root_meta_info.json, com backup em ~/Desktop/Concat/backup-capcut/).
Uso: capcut_novo.py <pasta do projeto modelo> "<nome do projeto novo>" <vídeo bruto>
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
RAIZ = os.path.expanduser("~/Movies/CapCut/User Data/Projects/com.lveditor.draft")
# O CapCut (sandbox) só abre arquivo fora da pasta dele se a pessoa o importou pela janela; um caminho escrito
# por nós aparece como "arquivo não acessível" (2026-10-28). O bruto entra por link físico (mesmo arquivo, sem
# ocupar espaço) na pasta dele, com o caminho como ele vê.
BRUTOS = os.path.expanduser("~/Movies/CapCut/User Data/Brutos Concat")
BRUTOS_VISTA = os.path.expanduser("~/Library/Containers/com.lemon.lvoverseas/Data/Movies/CapCut/User Data/Brutos Concat")


def bruto_visivel(video, pasta_nome):
    destino = os.path.join(BRUTOS, pasta_nome, os.path.basename(video))
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    if not os.path.exists(destino):
        try:
            os.link(video, destino)
        except OSError:          # outro disco: copia
            shutil.copy2(video, destino)
    return os.path.join(BRUTOS_VISTA, pasta_nome, os.path.basename(video))
PULAR = {"matting", "subdraft", "video", "qr_upload", "smart_crop", "adjust_mask"}   # caches do vídeo do modelo


def sonda(video):
    """(largura, altura, duração em us) como o CapCut grava: já com a rotação do celular/câmera aplicada."""
    r = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=width,height:stream_side_data=rotation:format=duration", "-of", "json", video],
                                  capture_output=True, text=True).stdout)
    s = r["streams"][0]
    w, h = s["width"], s["height"]
    if any(abs(int(d.get("rotation", 0))) in (90, 270) for d in s.get("side_data_list", [])):
        w, h = h, w
    return w, h, int(round(float(r["format"]["duration"]) * 1e6))


def main():
    modelo, nome, video = os.path.abspath(sys.argv[1]), sys.argv[2], os.path.abspath(sys.argv[3])
    if subprocess.run(["pgrep", "-x", "CapCut"], capture_output=True).returncode == 0:
        sys.exit("feche o CapCut antes (ele regrava a lista de projetos ao sair)")
    pasta = os.path.join(RAIZ, nome[:50].rstrip(" .,"))
    if os.path.exists(pasta):
        sys.exit(f"já existe: {pasta}")
    shutil.copytree(modelo, pasta, ignore=lambda d, fs: [f for f in fs if (d == modelo and f in PULAR) or f.endswith(".bak")])
    for d in PULAR:
        os.makedirs(os.path.join(pasta, d), exist_ok=True)

    # linha do tempo com id próprio (o id do draft_info é o da linha do tempo)
    pj = json.load(open(os.path.join(pasta, "Timelines", "project.json")))
    velho, tl = pj["main_timeline_id"], novo_id()
    agora = int(time.time() * 1e6)
    pj.update(id=novo_id(), main_timeline_id=tl, create_time=agora, update_time=agora)
    for t in pj["timelines"]:
        if t["id"] == velho:
            t.update(id=tl, create_time=agora, update_time=agora)
    pj["timelines"] = [t for t in pj["timelines"] if t["id"] == tl]
    json.dump(pj, open(os.path.join(pasta, "Timelines", "project.json"), "w"))
    for d in os.listdir(os.path.join(pasta, "Timelines")):
        caminho = os.path.join(pasta, "Timelines", d)
        if os.path.isdir(caminho) and d != velho:
            shutil.rmtree(caminho)
    os.rename(os.path.join(pasta, "Timelines", velho), os.path.join(pasta, "Timelines", tl))
    lay = os.path.join(pasta, "timeline_layout.json")
    if os.path.exists(lay):
        open(lay, "w").write(open(lay).read().replace(velho, tl))

    # draft_info: a trilha principal vira um clipe só com o bruto novo; ficam só as camadas do vídeo todo
    w, h, dur = sonda(video)
    caminho = bruto_visivel(video, os.path.basename(pasta))
    mid = str(uuid.uuid4())     # o mesmo id liga a mídia da lista ao clipe da timeline
    alvos = [os.path.join(pasta, "draft_info.json"), os.path.join(pasta, "Timelines", tl, "draft_info.json")]
    d = json.load(open(alvos[0], encoding="utf-8"))
    total = d["duration"]
    principal = next(t for t in d["tracks"] if t["type"] == "video")
    seg = copy.deepcopy(sorted(principal["segments"], key=lambda s: s["target_timerange"]["start"])[0])
    mat = copy.deepcopy(next(m for m in d["materials"]["videos"] if m["id"] == seg["material_id"]))
    mat.update(id=novo_id(), path=caminho, material_name=os.path.basename(video), width=w, height=h, duration=dur,
               local_material_id=mid, md5="", crop_ratio="free", type="video", category_name="local", is_copyright=False)
    if isinstance(mat.get("matting"), dict):
        mat["matting"].update(flag=0, path="", custom_matting_id="")
    seg.update(id=novo_id(), material_id=mat["id"], source_timerange={"start": 0, "duration": dur},
               target_timerange={"start": 0, "duration": int(dur / seg.get("speed", 1.0))}, common_keyframes=[], keyframe_refs=[])
    seg["extra_material_refs"] = [r for r in seg["extra_material_refs"]
                                  if not any(m.get("id") == r and k in ("transitions", "drafts")
                                             for k, v in d["materials"].items() if isinstance(v, list) for m in v if isinstance(m, dict))]
    principal["segments"] = [seg]

    def inteira(t):   # camada que cobre o vídeo todo (ajuste, LUT, sombra): fica
        return len(t["segments"]) == 1 and t["segments"][0]["target_timerange"]["duration"] >= 0.9 * total
    d["tracks"] = [t for t in d["tracks"] if t is principal or (t["type"] in ("adjust", "video", "effect", "filter") and inteira(t))]
    d["materials"]["videos"].append(mat)
    d["materials"]["drafts"] = []
    d.update(id=tl, duration=seg["target_timerange"]["duration"])
    texto = json.dumps(d, ensure_ascii=False, separators=(",", ":"))
    for p in alvos + [os.path.join(pasta, "template-2.tmp"), os.path.join(pasta, "Timelines", tl, "template-2.tmp")]:
        if os.path.exists(p) or p in alvos:
            open(p, "w", encoding="utf-8").write(texto)

    # meta do projeto e lista de projetos
    did = novo_id()
    meta_p = os.path.join(pasta, "draft_meta_info.json")
    meta = json.load(open(meta_p, encoding="utf-8"))
    meta.update(draft_id=did, draft_name=nome, draft_fold_path=pasta, draft_root_path=RAIZ, tm_draft_create=agora,
                tm_draft_modified=agora, tm_duration=d["duration"], draft_timeline_materials_size_=0)
    for grupo in meta.get("draft_materials", []):
        if grupo.get("type") == 0:
            grupo["value"] = [{"ai_group_type": "", "create_time": int(time.time()), "duration": dur, "enter_from": 0,
                               "extra_info": os.path.basename(video), "file_Path": caminho, "height": h, "id": mid,
                               "import_time": int(time.time()), "import_time_ms": agora, "item_source": 1, "material_color_tag": "",
                               "md5": "", "metetype": "video", "roughcut_time_range": {"duration": -1, "start": -1},
                               "sub_time_range": {"duration": -1, "start": -1}, "type": 0, "width": w}]
    json.dump(meta, open(meta_p, "w", encoding="utf-8"), ensure_ascii=False)

    raiz_p = os.path.join(RAIZ, "root_meta_info.json")
    copia = os.path.expanduser(f"~/Desktop/Concat/backup-capcut/root_meta_info {time.strftime('%Y-%m-%d %H%M%S')}.json")
    os.makedirs(os.path.dirname(copia), exist_ok=True)
    shutil.copy2(raiz_p, copia)
    raiz = json.load(open(raiz_p, encoding="utf-8"))
    base = next(x for x in raiz["all_draft_store"] if os.path.realpath(x["draft_fold_path"]) == os.path.realpath(modelo))
    raiz["all_draft_store"].insert(0, dict(copy.deepcopy(base), draft_id=did, draft_name=nome, draft_fold_path=pasta,
                                           draft_cover=os.path.join(pasta, "draft_cover.jpg"),
                                           draft_json_file=os.path.join(pasta, "draft_info.json"),
                                           tm_draft_create=agora, tm_draft_modified=agora, tm_duration=d["duration"]))
    json.dump(raiz, open(raiz_p, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"projeto \"{nome}\" em {pasta}: {w}x{h}, {dur / 1e6:.2f}s; camadas mantidas: "
          f"{[t['type'] for t in d['tracks']]}; lista de projetos com backup em {copia}")


if __name__ == "__main__":
    main()
