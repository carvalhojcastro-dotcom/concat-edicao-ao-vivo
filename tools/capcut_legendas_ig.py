#!/usr/bin/env python3
"""Legendas no estilo das referências do Instagram (2026-10-29), direto num projeto do CapCut.

Pedido: "aprenda como elas são feitas e replique no CapCut ... avalie se ficou de fato igual". Medido quadro a quadro
em referencias/legenda-simples-ig (simples) e referencias/legenda-mista-ig, legenda-mista-ig-2 (simples + blocos):
  - Simples: Poppins Medium, branca, em = 2,71% da altura (52 px em 1920), espaçamento -0,065 em (o espaço entre
    palavras encolhe junto), centrada, linha de base a 63,9% da altura, sombra preta suave, sem contorno, sem
    animação; 1 a 4 palavras (até ~40% da largura), uma emendada na outra, some nas pausas.
  - Blocos dinâmicos: Poppins SemiBold; linhas pequenas com em de 4,4% da altura e a chave com 7,6% (até 9,7% na
    frase de fecho); espaçamento -0,07 / -0,06 em; entrelinha bem fechada (o topo das minúsculas de baixo fica 0,2 em
    da linha de cima abaixo da base dela); a linha da chave na base da legenda simples; palavra por palavra, sem
    animação. Centrado (o usuário alinha ao centro), só branco, sem serifa nem cursiva (pedido dele).
Tamanho no CapCut (medido no export do "11 - Caixinha", 2026-10-29): o CapCut faz a altura typo da fonte
(ascendente - descendente do OS/2) = tamanho x 0,0032 da altura do quadro, e centra essa caixa na posição (a base
fica 0,018 em abaixo do meio dela). Erro medido: ~2%.

Uso: capcut_legendas_ig.py <pasta do projeto no CapCut> <words.json> <plano.json> [--previa=<pasta>]
     capcut_legendas_ig.py --concat=<projeto do Concat> <words.json> <plano.json>
  words.json: no CapCut, palavras com tempos da TIMELINE (word, start, end). No Concat, o words.json do
  reel.py cortes (tempos do bruto): o script leva cada palavra para a timeline pelos clipes (corte, velocidade)
  e troca as legendas do projeto (a headline, com placa, fica).
  plano.json: {"blocos": [{"linhas": [[i, i], [i]], "chave": [i], "fecho": false}, ...]}  (índices de words.json)
  --base=0.70: desce (ou sobe) a linha das legendas (fração da altura; padrão 0.639), ex.: estampa no peito.
O CapCut precisa estar FECHADO (rodar de novo troca as legendas; trilhas "Legendas IG").
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFilter, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
FONTES = os.path.abspath(os.path.join(AQUI, "..", "fonts"))
CAPCUT_FONTES = os.path.expanduser("~/Movies/CapCut/User Data/Fontes Concat")
CAPCUT_FONTES_VISTA = os.path.expanduser("~/Library/Containers/com.lemon.lvoverseas/Data/Movies/CapCut/User Data/Fontes Concat")
NOME_TRILHA = "Legendas IG"
K_CAPCUT = 0.0032          # altura typo = tamanho x K x altura do quadro (medido)
BASE_EXTRA = 0.018         # a base fica isso (em) abaixo do meio da caixa typo (medido)

W, H = 1080, 1920
SIMPLES = dict(arq="Poppins-Medium.ttf", titulo="Poppins Medium", em=52 / 1920, trk=-0.065, base=1227 / 1920)
PEQUENA = dict(arq="Poppins-SemiBold.ttf", titulo="Poppins SemiBold", em=85 / 1920, trk=-0.07)
CHAVE = dict(arq="Poppins-SemiBold.ttf", titulo="Poppins SemiBold", em=146 / 1920, trk=-0.06)
FECHO = dict(CHAVE, em=186 / 1920, trk=-0.05)
SOMBRA = dict(alpha=0.50, blur=0.008, desloc=0.0015)   # blur e deslocamento em fração da altura (prévia)
LARGURA_SIMPLES = 0.42     # a simples nunca passa disso (referência: até 40%)
LARGURA_BLOCO = 0.70       # margens do usuário (15% a 85%)
MAX_PALAVRAS = 4
PAUSA = 0.45               # pausa maior que isso apaga a legenda

novo_id = lambda: str(uuid.uuid4()).upper()  # noqa: E731
_fontes, _metr = {}, {}


def fonte(arq, px):
    k = (arq, int(round(px)))
    if k not in _fontes:
        _fontes[k] = ImageFont.truetype(os.path.join(FONTES, arq), size=int(round(px)))
    return _fontes[k]


def metricas(arq):
    if arq not in _metr:
        t = TTFont(os.path.join(FONTES, arq))
        o, u = t["OS/2"], t["head"].unitsPerEm
        _metr[arq] = dict(asc=o.sTypoAscender / u, desc=-o.sTypoDescender / u, xh=o.sxHeight / u)
    return _metr[arq]


def largura(texto, est, em_px):
    f = fonte(est["arq"], em_px)
    return sum(f.getlength(c) for c in texto) + est["trk"] * em_px * (len(texto) - 1)


def espaco(est, em_px):
    return fonte(est["arq"], em_px).getlength(" ") + 2 * est["trk"] * em_px


# ---------------------------------------------------------------- montagem
def simples(words, livres):
    """Agrupa as palavras fora dos blocos em legendas de 1 a 4 palavras, emendadas, que somem nas pausas."""
    itens, atual = [], []
    em = SIMPLES["em"] * H

    def fecha():
        if atual:
            itens.append(list(atual))
            atual.clear()
    for k, i in enumerate(livres):
        w = words[i]
        if atual:
            ant = words[atual[-1]]
            junto = " ".join(words[j]["word"].strip() for j in atual + [i])
            if (i != atual[-1] + 1 or w["start"] - ant["end"] > PAUSA or len(atual) >= MAX_PALAVRAS
                    or largura(junto, SIMPLES, em) > LARGURA_SIMPLES * W or ant["word"].strip()[-1:] in ".?!:"):
                fecha()
        atual.append(i)
        if w["word"].strip()[-1:] in ",.?!:" and len(atual) >= 2:
            fecha()
    fecha()
    out = []
    for n, grupo in enumerate(itens):
        ini = words[grupo[0]]["start"]
        fim_fala = words[grupo[-1]]["end"]
        prox = words[grupo[-1] + 1]["start"] if grupo[-1] + 1 < len(words) else None
        fim = prox if prox is not None and prox - fim_fala <= PAUSA else fim_fala + 0.15
        texto = " ".join(words[j]["word"].strip() for j in grupo)
        out.append(dict(texto=texto, est=SIMPLES, em=SIMPLES["em"], cx=0.5, base=SIMPLES["base"], ini=ini, fim=fim, anim=False))
    return out


def bloco(words, b, fim):
    """Palavras de um bloco: linhas centradas, chave grande, entrelinha fechada, cada palavra entra quando é dita."""
    chave = set(b["chave"])
    grande = FECHO if b.get("fecho") else CHAVE
    linhas = []
    for linha in b["linhas"]:
        ps = [(i, grande if i in chave else PEQUENA) for i in linha]
        linhas.append(ps)
    # tamanho: se alguma linha passa da margem, o bloco todo encolhe
    def larg_linha(ps, k):
        tot = 0.0
        for n, (i, est) in enumerate(ps):
            em = est["em"] * H * k
            tot += largura(words[i]["word"].strip(), est, em)
            if n + 1 < len(ps):
                tot += espaco(ps[n + 1][1] if ps[n + 1][1]["em"] < est["em"] else est, min(em, ps[n + 1][1]["em"] * H * k))
        return tot
    k = min(1.0, min(LARGURA_BLOCO * W / larg_linha(ps, 1.0) for ps in linhas))
    # cada linha centrada; as palavras com o x de cada uma
    dispostas = []
    for ps in linhas:
        x = W / 2 - larg_linha(ps, k) / 2
        linha = []
        for m, (i, est) in enumerate(ps):
            em = est["em"] * H * k
            t = words[i]["word"].strip()
            if i in chave:
                t = t.rstrip(",")
            w = largura(t, est, em)
            linha.append((i, est, em, x, t, w))
            x += w
            if m + 1 < len(ps):
                prox = ps[m + 1][1]
                x += espaco(prox if prox["em"] < est["em"] else est, min(em, prox["em"] * H * k))
        dispostas.append(linha)
    # bases: o topo das minúsculas de baixo a 0,2 em da linha de cima abaixo da base dela (como nas referências);
    # se uma descendente de cima (g, ç, p) cair sobre uma letra de baixo, a linha de baixo desce só o necessário
    # (a referência resolvia tirando a palavra do centro; centrado, desce)
    ems = [max(em for _, _, em, *_ in ln) for ln in dispostas]
    xhs = [max(metricas(est["arq"])["xh"] * em for _, est, em, *_ in ln) for ln in dispostas]
    bases = [0.0]
    for n in range(1, len(dispostas)):
        b = bases[-1] + 0.2 * ems[n - 1] + xhs[n]
        cima = tinta(dispostas[n - 1], bases[-1], folga=0.06 * min(ems[n - 1], ems[n]))
        while (tinta(dispostas[n], b) & cima).any():
            b += 2
        bases.append(b)
    ik = next((n for n, ps in enumerate(linhas) if any(i in chave for i, _ in ps)), len(linhas) - 1)
    desloc = SIMPLES["base"] * H - bases[ik]
    out = []
    for n, ln in enumerate(dispostas):
        for i, est, em, x, t, w in ln:
            out.append(dict(texto=t, est=est, em=em / H, cx=(x + w / 2) / W, base=(bases[n] + desloc) / H,
                            ini=words[i]["start"], fim=fim, anim=False))
    return out


def tinta(linha, base, folga=0.0):
    """Máscara da tinta de uma linha (quadro de 3 alturas, base no meio), engordada pela folga."""
    img = Image.new("L", (W, 3 * H // 4), 0)
    d = ImageDraw.Draw(img)
    for i, est, em, x, t, w in linha:
        f = fonte(est["arq"], em)
        for c in t:
            d.text((x, base + H // 4), c, font=f, fill=255, anchor="ls")
            x += f.getlength(c) + est["trk"] * em
    if folga >= 1:
        img = img.filter(ImageFilter.MaxFilter(2 * int(folga) + 1))
    return np.array(img) > 60


def montar(words, plano):
    usados, itens = set(), []
    for n, b in enumerate(plano.get("blocos", [])):
        idx = [i for linha in b["linhas"] for i in linha]
        assert idx == list(range(idx[0], idx[-1] + 1)), f"bloco {n + 1}: índices fora de ordem"
        usados |= set(idx)
        ult = idx[-1]
        fim = words[ult + 1]["start"] if ult + 1 < len(words) else words[ult]["end"] + 0.3
        if fim - words[ult]["end"] > PAUSA:
            fim = words[ult]["end"] + 0.3
        itens += bloco(words, b, fim)
    itens += simples(words, [i for i in range(len(words)) if i not in usados])
    return sorted(itens, key=lambda it: (it["ini"], it["base"]))


# ---------------------------------------------------------------- prévia (como o CapCut desenha)
def desenhar(itens, t, fundo):
    """Quadro com as legendas visíveis em t, desenhadas com as métricas do CapCut, sobre `fundo` (RGB 1080x1920)."""
    img = Image.fromarray(fundo).convert("RGBA")
    texto = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(texto)
    for it in itens:
        if not (it["ini"] <= t < it["fim"]):
            continue
        em = it["em"] * H
        f = fonte(it["est"]["arq"], em)
        w = largura(it["texto"], it["est"], em)
        x = it["cx"] * W - w / 2
        for c in it["texto"]:
            d.text((x, it["base"] * H), c, font=f, fill=255, anchor="ls")
            x += f.getlength(c) + it["est"]["trk"] * em
    sombra = texto.filter(ImageFilter.GaussianBlur(SOMBRA["blur"] * H))
    sombra = Image.fromarray((np.array(sombra).astype(float) * SOMBRA["alpha"]).astype(np.uint8))
    preto = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    img = Image.composite(preto, img, sombra.transform((W, H), Image.AFFINE, (1, 0, 0, 0, 1, -SOMBRA["desloc"] * H)))
    img = Image.composite(Image.new("RGBA", (W, H), (255, 255, 255, 255)), img, texto)
    return np.array(img.convert("RGB"))


# ---------------------------------------------------------------- CapCut
def fonte_capcut(arq):
    os.makedirs(CAPCUT_FONTES, exist_ok=True)
    destino = os.path.join(CAPCUT_FONTES, arq)
    if not os.path.exists(destino) or os.path.getsize(destino) != os.path.getsize(os.path.join(FONTES, arq)):
        shutil.copy2(os.path.join(FONTES, arq), destino)
    return os.path.join(CAPCUT_FONTES_VISTA, arq)


def segmento(it, modelo, render_index):
    est = it["est"]
    caminho = fonte_capcut(est["arq"])
    mt = metricas(est["arq"])
    tamanho = round(it["em"] * (mt["asc"] + mt["desc"]) / K_CAPCUT, 3)
    estilo = json.loads(modelo["material"]["content"])["styles"][0]
    estilo = dict(estilo, range=[0, len(it["texto"])], size=tamanho, font={"path": caminho, "id": ""},
                  fill={"content": {"solid": {"color": [1.0, 1.0, 1.0]}, "render_type": "solid"}})
    estilo.pop("strokes", None)
    for sh in estilo.get("shadows", []):
        sh.update(alpha=SOMBRA["alpha"], diffuse=0.35, distance=3.0, angle=-90)
    m = copy.deepcopy(modelo["material"])
    m.update(id=novo_id(), type="text", content=json.dumps({"styles": [estilo], "text": it["texto"]}, ensure_ascii=False),
             font_path=caminho, font_title=est["titulo"], font_name="", font_size=tamanho, letter_spacing=est["trk"],
             has_shadow=True, shadow_alpha=SOMBRA["alpha"], border_width=0.0, text_color="#FFFFFF", alignment=1, group_id="",
             add_type=0, recognize_task_id="", recognize_text="", name="")
    anim = copy.deepcopy(modelo["refs"]["material_animations"])
    anim.update(id=novo_id(), animations=[])
    ini = int(round(round(it["ini"] * 30) / 30 * 1e6))
    fim = int(round(round(it["fim"] * 30) / 30 * 1e6))
    em = it["em"] * H
    centro_y = it["base"] * H - ((mt["asc"] - mt["desc"]) / 2 + BASE_EXTRA) * em
    s = copy.deepcopy(modelo["segmento"])
    s.update(id=novo_id(), material_id=m["id"], extra_material_refs=[anim["id"]], render_index=render_index,
             target_timerange={"start": ini, "duration": max(fim - ini, 33333)}, keyframe_refs=[], common_keyframes=[], group_id="")
    s["clip"] = {"scale": {"x": 1.0, "y": 1.0}, "rotation": 0.0, "alpha": 1.0, "flip": {"vertical": False, "horizontal": False},
                 "transform": {"x": round(2 * it["cx"] - 1, 6), "y": round(1 - 2 * centro_y / H, 6)}}
    return m, anim, s


def escrever(pasta, itens):
    if not os.environ.get("CAPCUT_TESTE") and subprocess.run(["pgrep", "-x", "CapCut"], capture_output=True).returncode == 0:
        sys.exit("feche o CapCut antes (ele regrava o projeto aberto por cima)")
    alvos = [p for p in [os.path.join(pasta, "draft_info.json")] + glob.glob(os.path.join(pasta, "Timelines", "*", "draft_info.json"))
             if os.path.exists(p)]
    base = json.load(open(alvos[0], encoding="utf-8"))
    modelo = json.load(open(os.path.join(AQUI, "capcut_modelo_texto.json"), encoding="utf-8"))
    copia = os.path.expanduser(f"~/Desktop/Concat/backup-capcut/{os.path.basename(pasta)} {time.strftime('%Y-%m-%d %H%M%S')}")
    while os.path.exists(copia):
        copia += "+"
    for p in glob.glob(os.path.join(pasta, "*.json")) + glob.glob(os.path.join(pasta, "*.tmp")) + glob.glob(os.path.join(pasta, "Timelines", "**", "*"), recursive=True):
        if os.path.isfile(p):
            destino = os.path.join(copia, os.path.relpath(p, pasta))
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            shutil.copy2(p, destino)
    velhas = [t for t in base["tracks"] if t.get("name", "").startswith(NOME_TRILHA)]
    ids = {s["material_id"] for t in velhas for s in t["segments"]}
    refs = {r for t in velhas for s in t["segments"] for r in s.get("extra_material_refs", [])}
    base["tracks"] = [t for t in base["tracks"] if t not in velhas]
    base["materials"]["texts"] = [m for m in base["materials"].get("texts", []) if m["id"] not in ids]
    base["materials"]["material_animations"] = [m for m in base["materials"].get("material_animations", []) if m["id"] not in refs]
    render = max([s.get("render_index", 0) for t in base["tracks"] for s in t["segments"]] + [0]) + 1
    trilhas = []
    for it in itens:
        m, anim, s = segmento(it, modelo, render)
        render += 1
        base["materials"].setdefault("texts", []).append(m)
        base["materials"].setdefault("material_animations", []).append(anim)
        ini, fim = s["target_timerange"]["start"], s["target_timerange"]["start"] + s["target_timerange"]["duration"]
        livre = next((k for k, (f, _) in enumerate(trilhas) if f <= ini), None)
        if livre is None:
            trilhas.append([fim, dict(copy.deepcopy(modelo["trilha"]), id=novo_id(), type="text", flag=0,
                                      name=f"{NOME_TRILHA} {len(trilhas) + 1}", is_default_name=False, segments=[])])
            livre = len(trilhas) - 1
        trilhas[livre][0] = fim
        trilhas[livre][1]["segments"].append(s)
    base["tracks"] += [tr for _, tr in trilhas]
    if base.get("render_index_track_mode_on"):
        for i, t in enumerate(base["tracks"]):
            for s in t["segments"]:
                s["track_render_index"] = i
    texto = json.dumps(base, ensure_ascii=False, separators=(",", ":"))
    for p in alvos:
        open(p, "w", encoding="utf-8").write(texto)
        tmp = os.path.join(os.path.dirname(p), "template-2.tmp")
        if os.path.exists(tmp):
            open(tmp, "w", encoding="utf-8").write(texto)
    print(f"{len(itens)} textos em {len(trilhas)} trilhas \"{NOME_TRILHA}\"; backup em {copia}")


# ---------------------------------------------------------------- Concat
def palavras_do_concat(api, words):
    """Tempos da timeline das palavras do words.json (tempos do bruto, do reel.py cortes), pelos clipes de vídeo
    (corte, velocidade, ordem). Mantém todas as palavras, na ordem e com os índices do words.json (os blocos do
    plano usam esses índices); a que não cai em nenhum trecho para o script."""
    from concat_api import timeline
    tl = timeline(api.view())
    segs = sorted([(c["sourceStart"], c["sourceStart"] + c["duration"] * c["speed"], c["start"], c["speed"])
                   for c in tl["clips"] if c["kind"] == "video"])

    def tmap(src, prefer):
        # dentro de um trecho, direto; numa pausa cortada, o início vai para o trecho seguinte e o fim para o anterior
        for a, b, st, sp in segs:
            if a - 1e-6 <= src <= b + 1e-6:
                return st + (src - a) / sp
        if prefer == "next":
            return next((st for a, b, st, sp in segs if a > src), None)
        return next((st + (b - a) / sp for a, b, st, sp in reversed(segs) if b < src), None)
    out, fora = [], []
    for w in words:
        ini, fim = tmap(w["start"], "next"), tmap(w["end"], "prev")
        if ini is None or fim is None:
            fora.append(w["word"].strip())
            continue
        if fim < ini + 0.02 or fim - ini > 3:   # palavra que pula de trecho: dura o mínimo
            fim = ini + max(0.06, min(w["end"] - w["start"], 0.4))
        out.append(dict(word=w["word"], start=ini, end=fim))
    if fora:
        sys.exit(f"palavras fora dos trechos do projeto (corrija o words.json): {' '.join(fora)}")
    return out, tl


def fonte_concat(est):
    """Cópia da fonte como família própria de uma face só (regular): o Concat junta as Poppins pela família interna
    "Poppins" e escolhe pelo peso (SemiBold pedida a 500 saía Medium; a 600, mais grossa e 8% mais larga que a
    SemiBold de verdade). Com família e nome próprios, ele desenha exatamente este arquivo."""
    from fontTools.ttLib import TTFont
    familia = est["titulo"] + " IG"
    pasta = os.path.join(AQUI, "..", "dist", "fontes_concat")
    destino = os.path.join(pasta, est["arq"].replace(".ttf", "-IG.ttf"))
    if not os.path.exists(destino):
        os.makedirs(pasta, exist_ok=True)
        t = TTFont(os.path.join(FONTES, est["arq"]))
        nomes = t["name"]
        for rec in list(nomes.names):
            if rec.nameID in (16, 17, 21, 22):
                nomes.removeNames(nameID=rec.nameID)
        for nid, valor in ((1, familia), (2, "Regular"), (4, familia), (6, familia.replace(" ", "-"))):
            nomes.setName(valor, nid, 3, 1, 0x409)
            nomes.setName(valor, nid, 1, 0, 0)
        t["OS/2"].usWeightClass = 400
        t["OS/2"].fsSelection = (t["OS/2"].fsSelection & ~0b1100001) | 0b1000000   # regular, nem negrito nem itálico
        t["head"].macStyle = 0
        t.save(destino)
    return familia, destino


def registrar_fontes_concat(api):
    """Registra as Poppins (cópias com família própria) no projeto aberto; devolve {arquivo: família}."""
    familias = {}
    for est in (SIMPLES, PEQUENA):
        familia, caminho = fonte_concat(est)
        api.edit({"op": "addFont", "family": familia, "path": caminho})
        familias[est["arq"]] = familia
    return familias


def estilo_concat(it, familias):
    """(estilo do texto no Concat, offsetY) de um item da montagem."""
    mt = metricas(it["est"]["arq"])
    oy = it["base"] - 0.5 - (mt["asc"] - mt["desc"]) / 2 * it["em"]   # o Concat põe a base em H/2 + oy + (asc-desc)/2·em
    return ({"content": it["texto"], "fontFamily": f'"{familias[it["est"]["arq"]]}"', "fontWeight": 400.0,
             "italic": False, "fontSize": it["em"], "color": "#ffffff", "align": "center", "shadow": True,
             "strokeWidth": 0.0, "strokeColor": "#000000", "tracking": it["est"]["trk"] * it["em"], "lineHeight": 1.0,
             "background": "", "opacity": 1.0, "maxWidth": 0.0, "maxHeight": 0.0}, oy)


def escrever_concat(projeto, words_src, plano):
    """O mesmo estilo num projeto do Concat: troca todos os textos pelos desta montagem."""
    from concat_api import Concat, timeline
    api = Concat(projeto)
    api.sock.settimeout(300)
    try:
        api.call("project.get", path=projeto)
    except RuntimeError:
        api.call("project.open", path=projeto)
    words, tl = palavras_do_concat(api, words_src)
    itens = montar(words, plano)
    familias = registrar_fontes_concat(api)
    # troca as legendas (texto sem placa atrás); a headline (caixa branca, headline.py) fica
    api.batch([{"op": "removeClips", "clipIds": [c["id"] for c in tl["clips"] if c["kind"] == "text"
                                                 and not c["text"].get("background")], "ripple": False}])

    for grupo in ([it for it in itens if it["est"] is SIMPLES], [it for it in itens if it["est"] is not SIMPLES]):
        if not grupo:
            continue
        antes = {c["id"] for c in timeline(api.view())["clips"]}
        cmds = []
        for it in grupo:
            estilo, oy = estilo_concat(it, familias)
            ini = round(it["ini"] * 30) / 30
            fim = max(round(it["fim"] * 30) / 30, ini + 1 / 30)
            cmd = {"op": "addTextClip", "start": ini, "duration": round(fim - ini, 6), "offsetY": round(oy, 6), "style": estilo}
            cmd.update({"trackId": "T4"} if it["est"] is SIMPLES else {"above": True})
            cmds.append(cmd)
        for k in range(0, len(cmds), 50):
            api.batch(cmds[k:k + 50])
        novos = sorted([c for c in timeline(api.view())["clips"] if c["id"] not in antes], key=lambda c: (c["start"], c["id"]))
        alvo = sorted(grupo, key=lambda it: round(it["ini"] * 30))
        pares = {}
        for it in alvo:   # casa clipe e item pelo início e pelo texto
            c = next(c for c in novos if c["id"] not in pares and c["text"]["content"] == it["texto"]
                     and abs(c["start"] - round(it["ini"] * 30) / 30) < 1e-3)
            pares[c["id"]] = it
        api.batch([{"op": "setClipTransform", "clipId": cid, "offsetX": round(it["cx"] - 0.5, 6),
                    "offsetY": round(estilo_concat(it, familias)[1], 6)} for cid, it in pares.items()])
    api.call("project.save", path=projeto)
    print(f"{len(itens)} textos no Concat ({sum(1 for it in itens if it['est'] is SIMPLES)} simples, "
          f"{len(plano.get('blocos', []))} blocos); projeto salvo")


def main():
    base = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--base=")), None)
    if base:   # --base=0.70: linha de base da legenda (e da chave dos blocos) em fração da altura (padrão 0.639)
        SIMPLES["base"] = float(base)
    concat = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--concat=")), None)
    if concat:   # capcut_legendas_ig.py --concat=<projeto> <words.json> <plano.json>
        args = [a for a in sys.argv[1:] if not a.startswith("--")]
        escrever_concat(os.path.abspath(concat), json.load(open(args[0])), json.load(open(args[1])))
        return
    pasta, words, plano = sys.argv[1], json.load(open(sys.argv[2])), json.load(open(sys.argv[3]))
    itens = montar(words, plano)
    previa = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--previa=")), None)
    if previa:
        json.dump([dict(it, est=it["est"]["titulo"]) for it in itens], open(os.path.join(previa, "itens.json"), "w"), ensure_ascii=False, indent=0)
        print(f"{len(itens)} textos montados (prévia em {previa})")
        return
    escrever(os.path.abspath(pasta), itens)


if __name__ == "__main__":
    main()
