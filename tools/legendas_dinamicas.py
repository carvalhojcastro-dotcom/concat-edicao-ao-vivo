#!/usr/bin/env python3
"""Legendas Dinâmicas: frases em destaque montadas palavra por palavra, ao vivo pela API.

Parte de um projeto que já tem as legendas simples da Parte 1 (uma palavra por
clipe de texto, Helvetica, sem animação). Para cada frase do plano:
  - apaga as legendas simples daquelas palavras;
  - cria um clipe de texto por palavra, cada um entrando quando a palavra é dita
    (desliza para cima e aparece) e todos saindo juntos quando a frase acaba;
  - arruma as palavras como nos prints de referência (ver os estilos abaixo).
As legendas simples ficam como estão: sem animação.

Uso:
  legendas_dinamicas.py <pasta do projeto> <plano.json>

plano.json: [{"estilo": "serifa", "linhas": [[0, 1], [2], [3]], "chave": [2]}, ...]
  ou {"destaque": "#2563c9", "frases": [...]} para usar a cor da paleta do cliente
  (padrão: amarelo; Dr. Rafael: azul #2563c9).
  linhas: índices das legendas simples (na ordem da timeline), agrupados por linha;
  chave:  os índices que levam o destaque.
Regra de leitura (do usuário): palavras PEQUENAS sempre em letra normal e reta (Helvetica /
Montserrat), nunca fina nem cursiva; fontes finas e cursivas (Scholar Itálico, Bold Oblíqua)
só nas palavras GRANDES de destaque.
Estilos (prints em ~/Desktop/Legendas dinamicas):
  serifa   - "Estilo 3": escadinha; linhas pequenas em Helvetica normal, chave em Scholar Itálico amarelo, palavra final
             maior alinhada à direita embaixo da chave.
  classico - "Estilo 5": palavras pequenas (Helvetica) espalhadas sobre uma linha grande
             em Helvetica Bold apertada.
  elegante - "Estilo 6": linha pequena em negrito sobre uma palavra enorme em Scholar Itálico,
             encostadas.
  impacto  - "Estilos 1 e 2": bloco alinhado à esquerda, Helvetica normal (reta) e a chave em
             Helvetica Bold Oblíqua grande (podem dividir a mesma linha).

Requer Pillow e fontTools (para medir as palavras com as mesmas fontes que o Concat usa).
"""
import json
import os
import sys

from fontTools.ttLib import TTFont
from PIL import ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from concat_api import Concat, timeline, fps_de  # noqa: E402

W, H = 2160, 3840
FPS = fps_de(sys.argv[1])  # o fps do projeto (24 ou 30)
FONTES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts")
HELV = "/System/Library/Fonts/Helvetica.ttc"  # "Helvetica Neue" o Concat não acha; "Helvetica" sim

# Cada face: família no Concat, peso, itálico, arquivo e índice (para medir).
FACES = {
    "helv": ("Helvetica", 400, False, HELV, 0),
    "helv-bold": ("Helvetica", 700, False, HELV, 1),
    "helv-oblique": ("Helvetica", 400, True, HELV, 2),
    "helv-bold-oblique": ("Helvetica", 700, True, HELV, 3),
    "helv-light-oblique": ("Helvetica", 300, True, HELV, 5),
    "scholar": ("Scholar", 400, False, os.path.join(FONTES, "Scholar-Regular.otf"), 0),
    "scholar-italic": ("Scholar", 400, True, os.path.join(FONTES, "Scholar-Italic.otf"), 0),
    "montserrat-bold": ("Montserrat", 700, False, os.path.join(FONTES, "Montserrat-Bold.otf"), 0),
}
# Fontes que o projeto precisa registrar (as do sistema o Concat já acha).
REGISTRAR = [("Scholar", "Scholar-Regular.otf"), ("Scholar", "Scholar-Italic.otf"),
             ("Montserrat", "Montserrat-Bold.otf")]

AMARELO = "#f4c430"
DESTAQUE = AMARELO  # cor da chave no estilo serifa; o plano pode trocar pela do cliente
BRANCO = "#ffffff"
LARGURA_MAX = 0.84 * W
ENTRADA = 0.20           # segundos da entrada deslizando
DESLIZE = 0.010          # quanto sobe na entrada, em fração da altura
SAIDA = 2 / FPS          # some nos últimos 2 quadros
EASE_OUT = [0.0, 0.0, 0.58, 1.0]
LINEAR = [0.0, 0.0, 1.0, 1.0]
SEM_CONTORNO = "--sem-contorno" in sys.argv  # só a sombra leve
_opc = dict(a[2:].split("=", 1) for a in sys.argv[3:] if a.startswith("--") and "=" in a)
ESCALA = float(_opc.get("escala", 0.92))   # padrão do usuário: 92% do tamanho
CENTRO_Y = float(_opc.get("centro", 0.67)) * H  # padrão do usuário: abaixo do rosto (antes 0.60)

_metricas = {}


def metricas(face):
    """(ascender, descender, altura de maiúscula) em em, como o Concat lê."""
    if face not in _metricas:
        _, _, _, path, index = FACES[face]
        tt = TTFont(path, fontNumber=index)
        upem = tt["head"].unitsPerEm
        os2 = tt["OS/2"]
        if os2.fsSelection & (1 << 7):  # USE_TYPO_METRICS, como o ttf-parser
            asc, desc = os2.sTypoAscender, os2.sTypoDescender
        else:
            asc, desc = tt["hhea"].ascent, tt["hhea"].descent
        cap = getattr(os2, "sCapHeight", 0) or int(asc * 0.7)
        _metricas[face] = (asc / upem, -desc / upem, cap / upem)
    return _metricas[face]


def largura(face, em, texto, trk=0.0):
    """Largura em px; trk é o espaçamento entre letras em em."""
    _, _, _, path, index = FACES[face]
    w = ImageFont.truetype(path, size=max(1, round(em)), index=index).getlength(texto)
    return w + trk * em * max(len(texto) - 1, 0)


def palavra(texto, face, em, cor=BRANCO, trk=0.0):
    return {"texto": texto, "face": face, "em": em, "cor": cor, "trk": trk,
            "w": largura(face, em, texto, trk)}


def espaco(a, b):
    return 0.26 * min(a["em"], b["em"])


def linha_em(ps, x, base):
    """Põe as palavras lado a lado numa linha base, a partir de x. Devolve a largura."""
    for k, p in enumerate(ps):
        p["x"], p["base"] = x, base
        x += p["w"] + (espaco(p, ps[k + 1]) if k + 1 < len(ps) else 0)
    return x - ps[0]["x"]


def larg_linha(ps):
    return sum(p["w"] for p in ps) + sum(espaco(a, b) for a, b in zip(ps, ps[1:]))


def cap(p):
    return metricas(p["face"])[2] * p["em"]


def proxima_base(base, ant, prox, aperto):
    """Linha base seguinte: logo abaixo da anterior, com as maiúsculas da nova encostando."""
    return base + max(cap(p) for p in prox) + aperto * max(p["em"] for p in ant)


# ── estilos: recebem as linhas como listas de (índice, é_chave) e devolvem palavras posicionadas ──

def serifa(linhas, t):
    N, K, F = 0.056 * H, 0.084 * H, 0.072 * H
    rows, chave_li = [], None
    for li, linha in enumerate(linhas):
        if any(c for _, c in linha):
            chave_li = li
            rows.append([palavra(t[i], "scholar-italic", K, DESTAQUE) for i, _ in linha])
        elif chave_li is not None and len(linha) == 1:
            rows.append([palavra(t[i], "scholar", F) for i, _ in linha])  # a palavra final, maior
        else:
            # palavras pequenas: letra normal e reta (Helvetica), nunca fina/cursiva - senão some
            rows.append([palavra(t[i], "helv", N * 0.84, trk=-0.02) for i, _ in linha])
    degraus = [0.6, 0.0, 1.3, 0.3]  # escadinha, em em da linha normal
    base = 0.0
    for li, ps in enumerate(rows):
        if li:
            base = proxima_base(base, rows[li - 1], ps, 0.24 if li == chave_li else 0.12)
        x = degraus[li % len(degraus)] * N
        if chave_li is not None and li > chave_li:
            dir_chave = rows[chave_li][-1]["x"] + rows[chave_li][-1]["w"]
            x = dir_chave - larg_linha(ps) + 0.15 * N  # embaixo da chave, encostada à direita
        linha_em(ps, x, base)
    return [p for ps in rows for p in ps]


def classico(linhas, t):
    S, B = 0.042 * H, 0.100 * H
    topo = [palavra(t[i], "helv", S, trk=-0.02) for linha in linhas[:-1] for i, _ in linha]
    grande = [palavra(t[i], "helv-bold", B, trk=-0.05) for i, _ in linhas[-1]]
    wb = linha_em(grande, 0.0, 0.0)
    if topo:
        base_topo = -(max(cap(p) for p in grande) + 0.10 * S)
        wt = larg_linha(topo)
        if len(topo) == 1:
            linha_em(topo, 0.04 * B, base_topo)               # à esquerda, como "como"
        elif len(topo) == 2 and wt < wb:
            sobra = (wb - 0.08 * B - sum(p["w"] for p in topo)) / (len(topo) - 1)
            x = 0.04 * B
            for p in topo:                                     # espalhadas: "como      que"
                p["x"], p["base"] = x, base_topo
                x += p["w"] + sobra
        else:
            linha_em(topo, (wb - wt) / 2, base_topo)
    return topo + grande


def elegante(linhas, t):
    S, K = 0.042 * H, 0.125 * H
    pequenas = [[palavra(t[i], "montserrat-bold", S, trk=-0.03) for i, _ in linha] for linha in linhas[:-1]]
    grande = [palavra(t[i], "scholar-italic", K) for i, _ in linhas[-1]]
    wg = linha_em(grande, 0.0, 0.0)
    base = -0.68 * K  # a palavra grande sobe até encostar na linha de cima
    for ps in reversed(pequenas):
        linha_em(ps, (wg - larg_linha(ps)) / 2, base)
        base -= max(cap(p) for p in ps) + 0.18 * S
    return [p for ps in pequenas for p in ps] + grande


def impacto(linhas, t):
    S, B = 0.046 * H, 0.096 * H
    rows, depois_da_chave = [], False
    for linha in linhas:
        tem_chave = any(c for _, c in linha)
        s = S * (0.85 if depois_da_chave and not tem_chave else 1.0)  # "no seu vídeo", menor
        rows.append([palavra(t[i], "helv-bold-oblique", B, trk=-0.04) if c
                     else palavra(t[i], "helv", s * 0.92, trk=-0.02) for i, c in linha])  # pequenas: normal e reta
        depois_da_chave = depois_da_chave or tem_chave
    base = 0.0
    for li, ps in enumerate(rows):
        if li:
            base = proxima_base(base, rows[li - 1], ps, 0.10)
        grande = any(p["face"] == "helv-bold-oblique" for p in ps)
        recuo = 0.0 if grande else (0.35 if li == 0 else 0.55) * S
        linha_em(ps, recuo, base)
    return [p for ps in rows for p in ps]


ESTILOS = {"serifa": serifa, "classico": classico, "elegante": elegante, "impacto": impacto}


def montar(estilo, linhas, chave, textos):
    """Posição (offsetX, offsetY) e estilo de cada palavra do bloco, já centrado no quadro."""
    marcadas = [[(i, i in chave) for i in linha] for linha in linhas]
    ps = ESTILOS[estilo](marcadas, textos)
    ordem = [i for linha in linhas for i in linha]
    if estilo == "classico":  # devolve topo + grande, que é a mesma ordem das linhas
        pass
    for p, i in zip(ps, ordem):
        p["i"] = i
    # Caixa do bloco: das maiúsculas da primeira linha ao pé da última.
    esq = min(p["x"] for p in ps)
    dir_ = max(p["x"] + p["w"] for p in ps)
    topo = min(p["base"] - cap(p) for p in ps)
    pe = max(p["base"] + 0.15 * p["em"] for p in ps)
    k = min(1.0, LARGURA_MAX / (dir_ - esq)) * ESCALA
    cx, cy = (esq + dir_) / 2, (topo + pe) / 2
    out = []
    for p in ps:
        em = p["em"] * k
        x = W / 2 + (p["x"] - cx) * k
        base = CENTRO_Y + (p["base"] - cy) * k
        w = p["w"] * k
        asc, desc, _ = metricas(p["face"])
        # O Concat centra o título no quadro: a linha base cai em H/2 + (asc - desc)/2·em.
        oy = (base - H / 2 - (asc - desc) / 2 * em) / H
        ox = (x + w / 2 - W / 2) / W
        family, weight, italic, _, _ = FACES[p["face"]]
        out.append({"i": p["i"], "ox": ox, "oy": oy, "texto": p["texto"],
                    "style": {"content": p["texto"], "fontFamily": family, "fontWeight": float(weight),
                              "italic": italic, "fontSize": em / H, "color": p["cor"],
                              # contorno preto fino como o das simples (0.0006 numa letra de 0.04302) + sombra:
                              # sem ele a palavra some em fundo claro (camisa branca)
                              "align": "center", "shadow": True, "strokeWidth": 0.0 if SEM_CONTORNO else round(em / H * 0.0006 / 0.04302, 6),
                              "strokeColor": "#000000", "tracking": p["trk"] * em / H, "lineHeight": 1.0,
                              "background": "", "opacity": 1.0, "maxWidth": 0.0, "maxHeight": 0.0}})
    return out


def keys_entrada(cid, dur, oy):
    """Desliza de baixo e aparece; some nos últimos quadros."""
    a = min(ENTRADA / dur, 0.5)
    s = 1 - min(SAIDA / dur, 0.2)
    return [
        {"op": "setClipKey", "clipId": cid, "property": "offsetY", "at": 0.0, "value": oy + DESLIZE, "ease": LINEAR},
        {"op": "setClipKey", "clipId": cid, "property": "offsetY", "at": a, "value": oy, "ease": EASE_OUT},
        {"op": "setClipKey", "clipId": cid, "property": "opacity", "at": 0.0, "value": 0.0, "ease": LINEAR},
        {"op": "setClipKey", "clipId": cid, "property": "opacity", "at": a * 0.7, "value": 1.0, "ease": EASE_OUT},
        {"op": "setClipKey", "clipId": cid, "property": "opacity", "at": s, "value": 1.0, "ease": LINEAR},
        {"op": "setClipKey", "clipId": cid, "property": "opacity", "at": 1.0, "value": 0.0, "ease": LINEAR},
    ]


def main():
    global DESTAQUE
    path, plano = sys.argv[1], json.load(open(sys.argv[2]))
    if isinstance(plano, dict):
        DESTAQUE = plano.get("destaque", DESTAQUE)
        plano = plano["frases"]
    api = Concat(path)
    api.sock.settimeout(180)
    api.call("project.open", path=path)
    tl = timeline(api.view())
    legendas = sorted([c for c in tl["clips"] if c["kind"] == "text"], key=lambda c: c["start"])
    textos = [c["text"]["content"].rstrip(",") for c in legendas]

    for familia, arquivo in REGISTRAR:
        api.edit({"op": "addFont", "family": familia, "path": os.path.abspath(os.path.join(FONTES, arquivo))})

    for n, bloco in enumerate(plano, 1):
        idx = [i for linha in bloco["linhas"] for i in linha]
        assert idx == list(range(idx[0], idx[-1] + 1)), f"frase {n}: índices fora de ordem {idx}"
        ultimo = idx[-1]
        fim = legendas[ultimo + 1]["start"] if ultimo + 1 < len(legendas) else legendas[ultimo]["start"] + legendas[ultimo]["duration"]
        fim = round(fim * FPS) / FPS
        palavras = montar(bloco["estilo"], bloco["linhas"], set(bloco["chave"]), textos)
        antes = {c["id"] for c in timeline(api.view())["clips"]}
        cmds = [{"op": "removeClips", "clipIds": [legendas[i]["id"] for i in idx], "ripple": False}]
        for p in palavras:
            ini = legendas[p["i"]]["start"]
            cmds.append({"op": "addTextClip", "above": True, "start": ini, "duration": round(fim - ini, 6),
                         "offsetY": 0.0, "style": p["style"]})
        tl = timeline(api.batch(cmds))
        novos = sorted([c for c in tl["clips"] if c["id"] not in antes], key=lambda c: (c["start"], c["id"]))
        keys = []
        for c, p in zip(novos, sorted(palavras, key=lambda p: (legendas[p["i"]]["start"], p["i"]))):
            assert c["text"]["content"] == p["texto"], (c["text"]["content"], p["texto"])
            # Com keys em offsetY, a base fica 0: o Concat 0.2.7 soma a base às keys
            # nos títulos (titles.rs usa clip.offset_y cru); com 0 fica certo nas duas versões.
            keys.append({"op": "setClipTransform", "clipId": c["id"], "offsetX": p["ox"], "offsetY": 0.0})
            keys += keys_entrada(c["id"], c["duration"], p["oy"])
        api.batch(keys)
        print(f"[{n}/{len(plano)}] {bloco['estilo']}: {' / '.join(' '.join(textos[i] for i in l) for l in bloco['linhas'])}", flush=True)

    api.call("project.save", path=path)
    print(f"pronto: {len(plano)} frases dinâmicas; projeto salvo")


if __name__ == "__main__":
    main()
