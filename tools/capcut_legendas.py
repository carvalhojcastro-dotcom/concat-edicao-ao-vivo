#!/usr/bin/env python3
"""Leva as legendas (simples + dinâmicas) de um projeto do Concat para dentro de um projeto do CapCut,
como textos normais e editáveis.

Pedido de 2026-10-26 ("faça dentro do CapCut ... deixe tudo editável no projeto"): o usuário edita no
CapCut e quer as nossas legendas lá. As legendas são montadas pelo Concat (legendas_simples.py e
legendas_dinamicas.py, numa timeline com o mesmo áudio e a mesma duração do projeto do CapCut) e este
script converte cada palavra num texto do CapCut:
  - tempo, posição, tamanho, fonte (arquivo em fonts/), espaçamento entre letras;
  - contorno e sombra iguais aos das legendas que o usuário já faz no CapCut (tools/capcut_modelo_texto.json,
    tirado do projeto "Cortes Palestra");
  - a entrada de baixo para cima vira keyframes de posição Y e opacidade (as animações prontas do CapCut
    dependem de pacotes baixados que o usuário não tem).
Conversões (medidas): posição do Concat em fração do quadro a partir do centro (y para baixo) -> CapCut
em metades do quadro (y para cima); tamanho 12 no CapCut = fontSize 0.04302 no Concat (kit de edição).

O CapCut precisa estar FECHADO (ele regrava o projeto aberto). Antes de escrever, copia os arquivos do
projeto para ~/Desktop/Concat/backup-capcut/. Rodar de novo troca as legendas anteriores (trilhas
"Legendas (Concat)").

Uso: capcut_legendas.py <projeto do Concat> <pasta do projeto no CapCut>
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

AQUI = os.path.dirname(os.path.abspath(__file__))
FONTES = os.path.abspath(os.path.join(AQUI, "..", "fonts"))
# O CapCut do Mac é da App Store (sandbox): só lê fonte do sistema ou de dentro da pasta dele. A pasta
# ~/Movies/CapCut/User Data é a mesma que ele vê como .../Containers/com.lemon.lvoverseas/Data/Movies/...;
# as fontes do Concat são copiadas para lá e o texto aponta para esse caminho (como as fontes que ele baixa).
CAPCUT_FONTES = os.path.expanduser("~/Movies/CapCut/User Data/Fontes Concat")
CAPCUT_FONTES_VISTA = os.path.expanduser("~/Library/Containers/com.lemon.lvoverseas/Data/Movies/CapCut/User Data/Fontes Concat")


def fonte_biblioteca(rid):
    """Caminho (como o CapCut vê) de uma fonte da biblioteca do CapCut já baixada no cache dele."""
    achados = glob.glob(os.path.expanduser(f"~/Movies/CapCut/User Data/Cache/effect/{rid}/*/*.[ot]tf"))
    if not achados:
        sys.exit(f"a fonte {rid} da biblioteca do CapCut não está no cache: escolha-a uma vez num texto do CapCut")
    return achados[0].replace(os.path.expanduser("~/Movies/CapCut"),
                              os.path.expanduser("~/Library/Containers/com.lemon.lvoverseas/Data/Movies/CapCut"))


def fonte_capcut(arq):
    """Caminho da fonte como o CapCut consegue ler (copia o arquivo para a pasta dele na 1ª vez)."""
    if arq.startswith("capcut:"):
        return fonte_biblioteca(arq[7:])
    if arq.startswith("/"):
        return arq   # fonte do sistema
    os.makedirs(CAPCUT_FONTES, exist_ok=True)
    destino = os.path.join(CAPCUT_FONTES, arq)
    if not os.path.exists(destino) or os.path.getsize(destino) != os.path.getsize(os.path.join(FONTES, arq)):
        shutil.copy2(os.path.join(FONTES, arq), destino)
    return os.path.join(CAPCUT_FONTES_VISTA, arq)
NOME_TRILHA = "Legendas (Concat)"
SOMBRA_SEM_CONTORNO = 0.45   # sem o contorno, a sombra segura a leitura em fundo claro (bolinhas brancas, parede)
FPS = 30

# (família, peso, itálico) do Concat -> (arquivo, nome que o CapCut mostra)
FACES = {
    ('"Helvetica Neue Medium"', 500, False): ("HelveticaNeue-Medium.ttf", "Helvetica Neue Medium"),
    ('"Helvetica Neue Medium Italic"', 500, False): ("HelveticaNeue-MediumItalic.ttf", "Helvetica Neue Medium Italic"),
    # Scholar Itálico (print "as minhas / legendas"): a da biblioteca do CapCut, onde ela tem licença
    ("Scholar", 400, True): ("capcut:7441944210267181569", "Scholar-Italic"),
    ('"Helvetica Neue Condensed Black"', 900, False): ("HelveticaNeue-CondensedBlack.ttf", "Helvetica Neue Condensed Black"),
    ("Helvetica", 700, True): ("Helvetica-BoldOblique.ttf", "Helvetica Bold Oblique"),
    ("Helvetica", 700, False): ("Helvetica-Bold.ttf", "Helvetica Bold"),
    ("Helvetica", 400, False): ("/System/Library/Fonts/Helvetica.ttc", "Helvetica"),
    ("DM Serif Display", 400, False): ("DMSerifDisplay-Regular.ttf", "DM Serif Display"),
    ("DM Serif Display", 400, True): ("DMSerifDisplay-Italic.ttf", "DM Serif Display Italic"),
    ("Coolvetica", 400, False): ("Coolvetica-Rg.otf", "Coolvetica"),
    ("Montserrat", 700, False): ("Montserrat-Bold.otf", "Montserrat Bold"),
    ("Montserrat", 300, False): ("Montserrat-Light.ttf", "Montserrat Light"),
}

novo_id = lambda: str(uuid.uuid4()).upper()  # noqa: E731
us = lambda s: int(round(round(s * FPS) / FPS * 1e6))  # noqa: E731  segundos -> microssegundos na grade de quadros


def chave(t):
    return (t["fontFamily"], int(round(t["fontWeight"])), bool(t.get("italic")))


def keyframe(t_us, valor):
    return {"curveType": "Line", "graphID": "", "id": novo_id(), "left_control": {"x": 0.0, "y": 0.0},
            "right_control": {"x": 0.0, "y": 0.0}, "string_value": "", "time_offset": t_us, "values": [valor]}


def converter(clip, modelo, render_index):
    t = clip["text"]
    arq, titulo = FACES[chave(t)]
    caminho = fonte_capcut(arq)
    tamanho = round(t["fontSize"] / 0.04302 * 12, 3)
    estilo = json.loads(modelo["material"]["content"])["styles"][0]
    rid = arq[7:] if arq.startswith("capcut:") else ""
    estilo = dict(estilo, range=[0, len(t["content"])], size=tamanho, font={"path": caminho, "id": rid})
    cor = t.get("color", "#ffffff").lstrip("#")
    estilo["fill"] = {"content": {"solid": {"color": [int(cor[k:k + 2], 16) / 255 for k in (0, 2, 4)]}, "render_type": "solid"}}
    if not t.get("shadow"):
        estilo.pop("shadows", None)
    sem_contorno = not t.get("strokeWidth")
    if sem_contorno:   # --sem-contorno: só a sombra, como nos prints (Traço desligado, Sombra preta ligada)
        estilo.pop("strokes", None)
        for sh in estilo.get("shadows", []):
            sh.update(alpha=SOMBRA_SEM_CONTORNO, diffuse=0.2)
    m = copy.deepcopy(modelo["material"])
    m.update(id=novo_id(), type="text", content=json.dumps({"styles": [estilo], "text": t["content"]}, ensure_ascii=False),
             font_path=caminho, font_title=titulo, font_name="", font_size=tamanho,
             letter_spacing=round(t["tracking"] / t["fontSize"], 4) if t["fontSize"] else 0.0,
             has_shadow=bool(t.get("shadow")), text_color="#" + cor.upper(), alignment=1, group_id="", add_type=0,
             recognize_task_id="", recognize_text="", name="")
    if sem_contorno:
        m.update(border_width=0.0, shadow_alpha=SOMBRA_SEM_CONTORNO)
    if rid:   # fonte da biblioteca: o CapCut a acha pelo id do recurso
        m.update(font_resource_id=rid, fonts=[{"id": novo_id(), "resource_id": rid, "third_resource_id": "",
                 "category_id": "preset", "category_name": "Predefinições", "source_platform": 1, "path": caminho,
                 "effect_id": rid, "title": titulo, "team_id": "", "file_uri": "", "request_id": ""}])
    anim = copy.deepcopy(modelo["refs"]["material_animations"])
    anim["id"] = novo_id()
    anim["animations"] = []
    ini, dur = us(clip["start"]), us(clip["start"] + clip["duration"]) - us(clip["start"])
    chaves = clip.get("keys") or []
    oy = [k for k in chaves if k["property"] == "offsetY"]
    y_final = sorted(oy, key=lambda k: k["at"])[-1]["value"] if oy else clip.get("offsetY", 0.0)
    s = copy.deepcopy(modelo["segmento"])
    s.update(id=novo_id(), material_id=m["id"], extra_material_refs=[anim["id"]], render_index=render_index,
             target_timerange={"start": ini, "duration": dur}, keyframe_refs=[], common_keyframes=[], group_id="")
    s["clip"] = {"scale": {"x": 1.0, "y": 1.0}, "rotation": 0.0, "alpha": 1.0, "flip": {"vertical": False, "horizontal": False},
                 "transform": {"x": round(2 * clip.get("offsetX", 0.0), 6), "y": round(-2 * y_final, 6)}}
    # Só a entrada vira keyframe. Com as keys da saída (fade de 2 quadros no fim), o CapCut exportava as
    # palavras de mais de ~1 s ampliadas e cortadas nos quadros antes do fim (2026-10-27, "as legendas
    # ficaram bugadas na transição"); a palavra some no corte. E vai o conjunto que o próprio CapCut grava
    # (posição X e Y, escala, rotação), não só a posição Y.
    entrada = [k for k in chaves if k["at"] <= 0.5]
    oy = sorted([k for k in entrada if k["property"] == "offsetY"], key=lambda k: k["at"])
    if oy:
        tempos = [int(round(k["at"] * dur)) for k in oy]
        x = round(2 * clip.get("offsetX", 0.0), 6)
        for tipo, valores in (("KFTypePositionX", [x] * len(oy)), ("KFTypePositionY", [round(-2 * k["value"], 6) for k in oy]),
                              ("KFTypeScaleX", [1.0] * len(oy)), ("KFTypeRotation", [0.0] * len(oy))):
            s["common_keyframes"].append({"id": novo_id(), "material_id": "", "property_type": tipo,
                                          "keyframe_list": [keyframe(t, v) for t, v in zip(tempos, valores)]})
    al = sorted([k for k in entrada if k["property"] == "opacity"], key=lambda k: k["at"])
    if al:
        s["common_keyframes"].append({"id": novo_id(), "material_id": "", "property_type": "KFTypeGlobalAlpha",
                                      "keyframe_list": [keyframe(int(round(k["at"] * dur)), round(k["value"], 6)) for k in al]})
    return m, anim, s


def main():
    projeto, pasta = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    if not os.environ.get("CAPCUT_TESTE") and subprocess.run(["pgrep", "-x", "CapCut"], capture_output=True).returncode == 0:
        sys.exit("feche o CapCut antes (ele regrava o projeto aberto por cima)")
    alvos = [p for p in [os.path.join(pasta, "draft_info.json")] + glob.glob(os.path.join(pasta, "Timelines", "*", "draft_info.json"))
             if os.path.exists(p)]
    base = json.load(open(alvos[0], encoding="utf-8"))
    modelo = json.load(open(os.path.join(AQUI, "capcut_modelo_texto.json"), encoding="utf-8"))

    copia = os.path.expanduser(f"~/Desktop/Concat/backup-capcut/{os.path.basename(pasta)} {time.strftime('%Y-%m-%d %H%M%S')}")
    for p in glob.glob(os.path.join(pasta, "*.json")) + glob.glob(os.path.join(pasta, "*.tmp")) + glob.glob(os.path.join(pasta, "Timelines", "**", "*"), recursive=True):
        if os.path.isfile(p):
            destino = os.path.join(copia, os.path.relpath(p, pasta))
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            shutil.copy2(p, destino)

    # tira as legendas de uma rodada anterior
    velhas = [t for t in base["tracks"] if t.get("name", "").startswith(NOME_TRILHA)]
    ids_seg = {s["material_id"] for t in velhas for s in t["segments"]}
    ids_ref = {r for t in velhas for s in t["segments"] for r in s.get("extra_material_refs", [])}
    base["tracks"] = [t for t in base["tracks"] if t not in velhas]
    base["materials"]["texts"] = [m for m in base["materials"].get("texts", []) if m["id"] not in ids_seg]
    base["materials"]["material_animations"] = [m for m in base["materials"].get("material_animations", []) if m["id"] not in ids_ref]

    doc = json.load(open(os.path.join(projeto, "concat.json"), encoding="utf-8"))
    textos = sorted([c for c in doc["timelines"][0]["clips"] if c["kind"] == "text"], key=lambda c: (c["start"], c["id"]))
    faltam = {chave(c["text"]) for c in textos} - set(FACES)
    if faltam:
        sys.exit(f"fonte sem arquivo para o CapCut: {faltam}")
    render = max([s.get("render_index", 0) for t in base["tracks"] for s in t["segments"]] + [0]) + 1
    trilhas = []   # [(fim em us, trilha)]: cada palavra na 1ª trilha livre (as do bloco dinâmico se sobrepõem)
    for c in textos:
        m, anim, s = converter(c, modelo, render)
        render += 1
        base["materials"]["texts"].append(m)
        base["materials"]["material_animations"].append(anim)
        ini, fim = s["target_timerange"]["start"], s["target_timerange"]["start"] + s["target_timerange"]["duration"]
        livre = next((k for k, (f, _) in enumerate(trilhas) if f <= ini), None)
        if livre is None:
            tr = dict(copy.deepcopy(modelo["trilha"]), id=novo_id(), type="text", flag=0,
                      name=f"{NOME_TRILHA} {len(trilhas) + 1}", is_default_name=False, segments=[])
            trilhas.append([fim, tr])
            livre = len(trilhas) - 1
        trilhas[livre][0] = fim
        trilhas[livre][1]["segments"].append(s)
    base["tracks"] += [tr for _, tr in trilhas]
    if base.get("render_index_track_mode_on"):   # nesse modo o CapCut empilha pela trilha: legendas por cima
        for i, t in enumerate(base["tracks"]):
            for s in t["segments"]:
                s["track_render_index"] = i

    texto =json.dumps(base, ensure_ascii=False, separators=(",", ":"))
    for p in alvos:
        open(p, "w", encoding="utf-8").write(texto)
        tmp = os.path.join(os.path.dirname(p), "template-2.tmp")
        if os.path.exists(tmp):   # espelho que o CapCut usa para recuperar o projeto
            open(tmp, "w", encoding="utf-8").write(texto)
    print(f"{len(textos)} textos em {len(trilhas)} trilhas \"{NOME_TRILHA}\"; backup em {copia}")


if __name__ == "__main__":
    main()
