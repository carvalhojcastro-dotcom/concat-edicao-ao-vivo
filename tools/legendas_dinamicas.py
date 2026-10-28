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
  "fonte_chave" na frase escolhe a fonte da chave no serifa/elegante: "serifa" (DM Serif Display, padrão),
  "italico" (DM Serif Display Itálico), "bold" (Helvetica Neue Condensed Black) ou "coolvetica"; no classico,
  "reta" troca a Condensed Black por Helvetica Bold reta.
  ou {"destaque": "#2563c9", "frases": [...]} para usar a cor da paleta do cliente
  (padrão: branco, pedido de 2026-10-20; Dr. Rafael: azul #2563c9; amarelo #f4c430 só se pedirem).
  linhas: índices das legendas simples (na ordem da timeline), agrupados por linha;
  chave:  os índices que levam o destaque.
Regra de leitura (do usuário): tudo que não é destaque sai em fonte sóbria, normal e reta
(Helvetica Neue Medium, semibold), nunca fina nem cursiva (desde 2026-10-23 sem exceção: "evitando pesos
mais finos"); a serifada (e as cursivas) só na palavra de DESTAQUE (a chave).
Estilos (inspirados em prints de legendas de reels; descritos em EDICAO.md):
  serifa   - "Estilo 3": escadinha; linhas pequenas em Helvetica normal, chave em DM Serif Display branca, palavra final
             maior alinhada à direita embaixo da chave.
  classico - "Estilo 5": palavras pequenas (Helvetica) espalhadas sobre uma linha grande
             em Helvetica Neue Condensed Black.
  elegante - "Estilo 6": linha pequena em Helvetica Neue Medium (semibold; era Montserrat Light, fina
             demais) sobre uma palavra enorme em DM Serif Display, encostadas.
  impacto  - "Estilos 1 e 2": bloco alinhado à esquerda e todo inclinado: pequenas em Helvetica Neue Medium
             Itálico e a chave em Helvetica Bold Oblíqua grande (podem dividir a mesma linha).
  classico, elegante e impacto seguem as medidas dos prints de 2026-10-28 (ver as funções e EDICAO.md).

Requer Pillow e fontTools (para medir as palavras com as mesmas fontes que o Concat usa).
"""
import json
import os
import sys

from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from concat_api import Concat, timeline, fps_de  # noqa: E402
import plataforma  # noqa: E402  (Helvetica no Mac, Arimo/Archivo no Windows)

W, H = 2160, 3840
FPS = fps_de(sys.argv[1])  # o fps do projeto (24 ou 30)
FONTES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts")

# Cada face: família no Concat, peso, itálico, arquivo e índice (para medir).
FACES = {
    # Semibold (pedido do usuário) e Condensed Black (print "helvetica"): no Mac, faces da Helvetica
    # Neue extraídas do sistema para fonts/ (o Concat não lê .ttc; nome com espaço vai entre aspas,
    # sintaxe CSS); no Windows, Arimo e Archivo Condensed Black (OFL). Ver plataforma.py.
    **plataforma.faces_helvetica(),
    # Serifada do destaque: DM Serif Display (OFL, vai no repositório), no lugar da Scholar desde 2026-10-21
    # (a Scholar só tinha licença dentro do CapCut).
    "serif": ("DM Serif Display", 400, False, os.path.join(FONTES, "DMSerifDisplay-Regular.ttf"), 0),
    "serif-italic": ("DM Serif Display", 400, True, os.path.join(FONTES, "DMSerifDisplay-Italic.ttf"), 0),
    "montserrat-bold": ("Montserrat", 700, False, os.path.join(FONTES, "Montserrat-Bold.otf"), 0),
    # Pesos dos prints de fonte em referencias/Legendas dinamicas (pedido de 2026-10-20):
    "coolvetica": ("Coolvetica", 400, False, os.path.join(FONTES, "Coolvetica-Rg.otf"), 0),
    "montserrat-light": ("Montserrat", 300, False, os.path.join(FONTES, "Montserrat-Light.ttf"), 0),
}
# Scholar Itálico, a serifada do print "as minhas / legendas": só para legendas que vão para o CapCut, onde
# ela tem licença (capcut_legendas.py aponta para a fonte da biblioteca do CapCut). Fica fora do Git.
SCHOLAR = os.path.join(FONTES, "Scholar-Italic.otf")
if os.path.exists(SCHOLAR):
    FACES["scholar-italic"] = ("Scholar", 400, True, SCHOLAR, 0)
# Fontes que o projeto precisa registrar (as do sistema o Concat já acha).
REGISTRAR = [("DM Serif Display", "DMSerifDisplay-Regular.ttf"), ("DM Serif Display", "DMSerifDisplay-Italic.ttf"),
             ("Montserrat", "Montserrat-Bold.otf"), ("Coolvetica", "Coolvetica-Rg.otf"),
             ("Montserrat", "Montserrat-Light.ttf")] + plataforma.registrar_helvetica() + \
    ([("Scholar", "Scholar-Italic.otf")] if os.path.exists(SCHOLAR) else [])

AMARELO = "#f4c430"
BRANCO = "#ffffff"
DESTAQUE = BRANCO  # cor da chave no estilo serifa (branco por padrão); o plano pode trocar pela do cliente
FONTE_CHAVE = "serifa"  # destaque do serifa/elegante, por frase com "fonte_chave" no plano (pedido de 2026-10-20)
# fonte_chave -> (face, tracking em em). Pesos iguais aos prints de fonte do usuário.
CHAVES = {
    "serifa": ("serif", -0.02),            # DM Serif Display reta, levemente apertada (print "scholar")
    "italico": ("serif-italic", 0.0),      # DM Serif Display Itálico (prints de estilo 1 e 3)
    "bold": ("helv-cond-black", -0.01),      # Helvetica Neue Condensed Black (print "helvetica")
    "coolvetica": ("coolvetica", -0.02),     # Coolvetica Regular (print "coolvetica")
    "scholar": ("scholar-italic", -0.01),    # Scholar Itálico, só no CapCut (print "as minhas / legendas")
}
LARGURA_MAX = 0.84 * W
ENTRADA = 0.20           # segundos da entrada deslizando
DESLIZE = 0.010          # quanto sobe na entrada, em fração da altura
SAIDA = 2 / FPS          # some nos últimos 2 quadros
EASE_OUT = [0.0, 0.0, 0.58, 1.0]
LINEAR = [0.0, 0.0, 1.0, 1.0]
SEM_CONTORNO = "--sem-contorno" in sys.argv  # só a sombra leve
_opc = dict(a[2:].split("=", 1) for a in sys.argv[3:] if a.startswith("--") and "=" in a)
ESCALA = float(_opc.get("escala", 0.92))   # padrão do usuário: 92% do tamanho
CENTRO_Y = float(_opc.get("centro", 0.67)) * H  # só sem legendas simples no projeto (ou com --centro=)
# Pedido de 2026-10-21: o bloco começa na mesma altura da legenda simples (topo das letras da 1ª linha
# no topo das letras da simples) e cresce para baixo. main() mede a simples do projeto; None = centrar.
TOPO_Y = None
APERTO = float(_opc.get("aperto", 0.30))  # vão entre linhas (base de cima → topo das minúsculas), em em da letra pequena

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


ESPACO = float(_opc.get("espaco", 0.26))  # vão entre palavras, em em (CapCut: 0.16; pedido de 2026-10-27, "diminua a distância")


def espaco(a, b):
    return ESPACO * min(a["em"], b["em"])


def linha_em(ps, x, base, vao=None):
    """Põe as palavras lado a lado numa linha base, a partir de x. Devolve a largura. `vao` fixa o
    espaço entre as palavras em px (os estilos dos prints usam um vão só no bloco todo)."""
    for k, p in enumerate(ps):
        p["x"], p["base"] = x, base
        x += p["w"] + ((espaco(p, ps[k + 1]) if vao is None else vao) if k + 1 < len(ps) else 0)
    return x - ps[0]["x"]


def larg_linha(ps, vao=None):
    return sum(p["w"] for p in ps) + sum((espaco(a, b) if vao is None else vao) for a, b in zip(ps, ps[1:]))


def cap(p):
    return metricas(p["face"])[2] * p["em"]


def tinta(p):
    """(quanto a palavra sobe acima da linha base, quanto desce abaixo), em px, medido no desenho
    real das letras - números e ascendentes da serifada itálica sobem bem mais que a maiúscula."""
    _, _, _, path, index = FACES[p["face"]]
    _, topo, _, pe = ImageFont.truetype(path, size=max(1, round(p["em"])), index=index).getbbox(p["texto"], anchor="ls")
    return -topo, max(pe, 0)


_xalt = {}


def xalt(p):
    """Altura das minúsculas (x-height) da palavra, em px."""
    if p["face"] not in _xalt:
        _, _, _, path, index = FACES[p["face"]]
        os2 = TTFont(path, fontNumber=index)["OS/2"]
        _xalt[p["face"]] = (getattr(os2, "sxHeight", 0) / TTFont(path, fontNumber=index)["head"].unitsPerEm) or 0.5
    return _xalt[p["face"]] * p["em"]


def proxima_base(base, ant, prox, aperto, folga=0.08, ref=None):
    """Linha base seguinte, por espaçamento ótico (pedido de 2026-10-20: o vão era grande e mudava de
    uma linha para outra). O vão vai da linha base de cima ao topo das minúsculas de baixo e é o
    mesmo em todas as linhas (`aperto` em em de `ref`); hastes e perninhas (l, d, g, ç) entram nos
    vãos, como no print. Só desce mais se a tinta de duas palavras sobrepostas na horizontal se
    tocaria, deixando `folga`."""
    ref = ref or min(min(p["em"] for p in ant), min(p["em"] for p in prox))
    nova = base + max(xalt(p) for p in prox) + aperto * ref
    for a in ant:
        pa = perfil(a)
        for b in prox:
            pb = perfil(b)
            # coluna a coluna: só conta onde a letra de cima está de fato sobre a de baixo
            for x in range(int(max(a["x"], b["x"])), int(min(a["x"] + len(pa[1]), b["x"] + len(pb[0])))):
                d, s = pa[1][x - int(a["x"])], pb[0][x - int(b["x"])]
                if d is not None and s is not None:
                    nova = max(nova, base + d + s + folga * ref)
    return nova


_perfis = {}


def perfil(p):
    """Tinta da palavra coluna a coluna: (quanto sobe acima da base, quanto desce abaixo) por coluna
    de px, ou None onde não há tinta."""
    chave = (p["face"], round(p["em"]), p["texto"])
    if chave not in _perfis:
        _, _, _, path, index = FACES[p["face"]]
        f = ImageFont.truetype(path, size=max(1, round(p["em"])), index=index)
        sobe = int(p["em"] * 1.5)
        img = Image.new("L", (int(f.getlength(p["texto"])) + 4, sobe + int(p["em"])), 0)
        ImageDraw.Draw(img).text((0, sobe), p["texto"], font=f, anchor="ls", fill=255)
        larg, alt = img.size
        px = img.load()
        topo, pe = [], []
        for x in range(larg):
            ys = [y for y in range(alt) if px[x, y] > 40]
            topo.append(sobe - ys[0] if ys else None)
            pe.append(max(ys[-1] - sobe, 0) if ys else None)
        _perfis[chave] = (topo, pe)
    return _perfis[chave]


def chave_em(texto, em, cor):
    """A palavra de destaque na fonte de FONTE_CHAVE. `em` é o tamanho pensado para a serifada
    itálica; uma fonte mais larga encolhe até ocupar a mesma largura (nunca cresce), então o
    bloco do estilo não muda de forma com a fonte."""
    face, trk = CHAVES[FONTE_CHAVE]
    ref = largura("serif-italic", em, texto)
    return palavra(texto, face, em * min(1.0, ref / largura(face, em, texto, trk)), cor, trk=trk)


# ── estilos: recebem as linhas como listas de (índice, é_chave) e devolvem palavras posicionadas ──

def serifa(linhas, t):
    N, K, F = 0.056 * H, 0.084 * H, 0.072 * H
    rows, chave_li = [], None
    for li, linha in enumerate(linhas):
        if any(c for _, c in linha):
            chave_li = li
            rows.append([chave_em(t[i], K, DESTAQUE) if c
                         else palavra(t[i], "helv", N * 0.84, trk=-0.02) for i, c in linha])  # serifada só no destaque
        elif chave_li is not None and len(linha) == 1:
            rows.append([palavra(t[i], "helv", F * 0.82, trk=-0.02) for i, _ in linha])  # palavra final maior, sóbria (serifada só no destaque)
        else:
            # palavras pequenas: letra normal e reta (Helvetica), nunca fina/cursiva - senão some
            rows.append([palavra(t[i], "helv", N * 0.84, trk=-0.02) for i, _ in linha])
    degraus = [0.6, 0.0, 1.3, 0.3]  # escadinha, em em da linha normal
    base = 0.0
    for li, ps in enumerate(rows):
        x = degraus[li % len(degraus)] * N
        if chave_li is not None and li > chave_li:
            dir_chave = rows[chave_li][-1]["x"] + rows[chave_li][-1]["w"]
            x = dir_chave - larg_linha(ps) + 0.15 * N  # embaixo da chave, encostada à direita
        linha_em(ps, x, base)  # x primeiro: o espaçamento olha quais palavras ficam uma sobre a outra
        if li:
            base = proxima_base(base, rows[li - 1], ps, APERTO, ref=N * 0.84)
            linha_em(ps, x, base)
    return [p for ps in rows for p in ps]


def caber(ps, vao=None):
    """Encolhe só a linha grande quando ela passa da largura do quadro. Antes o bloco inteiro encolhia
    junto e as palavras pequenas sumiam ao lado de uma chave longa ("no programa / Vem Com A Gente",
    pedido de 2026-10-27: "discrepante o tamanho das palavras da linha de cima")."""
    w = linha_em(ps, 0.0, 0.0, vao)
    if w > LARGURA_MAX:
        ps[:] = [palavra(p["texto"], p["face"], p["em"] * LARGURA_MAX / w, p["cor"], p["trk"]) for p in ps]
    return ps


def xh(face):
    """Altura das minúsculas da face, em em."""
    return xalt({"face": face, "em": 1.0})


def encaixe(base, cima, baixo, vao, folga):
    """Linha base de `baixo` com `cima` na linha base `base`, como nos prints (2026-10-28): o vão vai da base
    de cima ao topo das minúsculas de baixo e é pequeno; as hastes de baixo (f, l, d, t) sobem entre as
    palavras de cima. Só desce mais onde a tinta das duas linhas se tocaria (deixando `folga`)."""
    nova = base + max(xalt(p) for p in baixo) + vao
    for a in cima:
        pa = perfil(a)
        for b in baixo:
            pb = perfil(b)
            for x in range(int(max(a["x"], b["x"])), int(min(a["x"] + len(pa[1]), b["x"] + len(pb[0])))):
                d, s = pa[1][x - int(a["x"])], pb[0][x - int(b["x"])]
                if d is not None and s is not None:
                    nova = max(nova, base + d + s + folga)
    return nova


def assentar(cima, grande, xs, vao, folga, alvos, peso, sx):
    """Escolhe a posição x das palavras de cima entre as candidatas `xs` (listas de x, uma por palavra):
    a que deixa a linha mais encaixada na de baixo (sem subir por causa de uma haste) e mais perto do
    alvo. Devolve a linha base de cima (a grande fica na base 0)."""
    melhor = None
    minimo = max(xalt(p) for p in grande) + vao
    for cand in xs:
        for p, x in zip(cima, cand):
            p["x"], p["base"] = x, 0.0
        sobe = encaixe(0.0, cima, grande, vao, folga) - minimo
        custo = sobe / sx + peso * sum(abs(x - a) for x, a in zip(cand, alvos))
        if melhor is None or custo < melhor[0] - 1e-9:
            melhor = (custo, cand, sobe)
    for p, x in zip(cima, melhor[1]):
        p["x"] = x
    base = -(minimo + melhor[2])
    for p in cima:
        p["base"] = base
    return base


def classico(linhas, t):
    """Print "como que / eu faço" (medido em 2026-10-28): pequenas em Helvetica Neue Medium; a linha grande
    com as minúsculas 2,16x as das pequenas; a 1ª pequena no começo da grande e a última terminando a ~82%
    dela; as pequenas assentam 0,2 altura-x acima das minúsculas da grande, com as hastes subindo entre elas.
    As proporções saem da largura das palavras no print (a altura das letras pequenas vem borrada)."""
    S = 0.042 * H
    sx = xh("helv") * S
    vao = 0.26 * S                       # o mesmo vão no bloco todo (print: ~0,26 em da pequena)
    topo = [palavra(t[i], "helv", S, trk=-0.02) for linha in linhas[:-1] for i, _ in linha]
    # print "helvetica": Condensed Black; com "fonte_chave": "reta", Helvetica Bold reta (print "como que / eu faço")
    face, trk = ("helv-bold", -0.03) if FONTE_CHAVE == "reta" else ("helv-cond-black", -0.01)
    grande = caber([palavra(t[i], face, 2.16 * sx / xh(face), trk=trk) for i, _ in linhas[-1]], vao)
    wb = linha_em(grande, 0.0, 0.0, vao)
    if not topo:
        return grande
    gap, folga = 0.30 * sx, 0.12 * sx      # 0,2 altura-x entre as tintas (+ o arredondado de "o" e "e")
    ws = [p["w"] for p in topo]
    wt = larg_linha(topo, vao)
    passos = [k / 24 for k in range(25)]
    if len(topo) == 2 and wt < wb * 0.92:
        x1s = [a * 0.12 * wb for a in passos[:9]]
        lo, hi = ws[0] + vao, wb - ws[1]
        cands = [[x1, x1 + lo + a * max(0.0, hi - x1 - lo)] for x1 in x1s for a in passos]
        alvos = [0.03 * wb, 0.82 * wb - ws[1]]
    elif wt < wb:
        cands, alvos = [], [0.03 * wb if len(topo) == 1 else (wb - wt) / 2]
        for a in passos:
            x = a * (wb - wt)
            cands.append([x + sum(ws[:k]) + k * vao for k in range(len(topo))])
        alvos = [alvos[0] + sum(ws[:k]) + k * vao for k in range(len(topo))]
    else:
        x = (wb - wt) / 2
        cands = [[x + sum(ws[:k]) + k * vao for k in range(len(topo))]]
        alvos = cands[0]
    assentar(topo, grande, cands, gap, folga, alvos, 0.8 / wb / len(topo), sx)
    return topo + grande


def elegante(linhas, t):
    """Print "as minhas / legendas" (medido em 2026-10-28): linha pequena em Helvetica Neue Medium (semibold)
    sobre uma palavra enorme em serifada itálica (Scholar no CapCut) com minúsculas 2,33x as das pequenas;
    a linha pequena fica no vão entre as hastes (l ... d), 0,45 altura-x acima das minúsculas."""
    S = 0.042 * H
    sx = xh("helv") * S
    vao = 0.26 * S
    face, trk = CHAVES[FONTE_CHAVE]
    pequenas = [[palavra(t[i], "helv", S, trk=-0.02) for i, _ in linha] for linha in linhas[:-1]]
    grande = caber([palavra(t[i], face, 2.33 * sx / xh(face), BRANCO, trk) if c else palavra(t[i], "helv", S, trk=-0.02)
                    for i, c in linhas[-1]], vao)  # serifada só no destaque
    wg = linha_em(grande, 0.0, 0.0, vao)
    if not pequenas:
        return grande
    gap, folga = 0.38 * sx, 0.12 * sx
    ult = pequenas[-1]
    ws = [p["w"] for p in ult]
    wt = larg_linha(ult, vao)
    centro = (wg - wt) / 2
    faixa = [centro + (k / 20 - 0.5) * abs(wg - wt) for k in range(21)] if wt < wg else [centro]
    cands = [[x + sum(ws[:k]) + k * vao for k in range(len(ult))] for x in faixa]
    alvos = [centro + sum(ws[:k]) + k * vao for k in range(len(ult))]
    base = assentar(ult, grande, cands, gap, folga, alvos, 0.6 / wg / len(ult), sx)
    meio = ult[0]["x"] + wt / 2
    for ps in reversed(pequenas[:-1]):      # mais de uma linha pequena: empilha centrada na de baixo
        linha_em(ps, meio - larg_linha(ps, vao) / 2, 0.0, vao)
        base -= encaixe(0.0, ps, ult, 0.5 * sx, folga)
        for p in ps:
            p["base"] = base
        ult = ps
    return [p for ps in pequenas for p in ps] + grande


def impacto(linhas, t):
    """Prints "que você / usa textos" e "pra chamar / atenção / no seu vídeo" (medidos em 2026-10-28): tudo
    inclinado e alinhado à esquerda. Pequenas em Helvetica Neue Medium Itálico; a chave em Helvetica Bold
    Oblíqua com minúsculas 2,37x as da 1ª linha (1,6x quando divide a linha com uma pequena, como "usa");
    a pequena da linha da chave é 0,76 da 1ª e alinha pelo topo das minúsculas da chave, e essa linha
    entra recuada; as linhas depois da chave saem a 0,77."""
    S = 0.046 * H * 0.92
    sx = xh("helv-italic") * S
    vao = 0.30 * S
    ki = next((li for li, linha in enumerate(linhas) if any(c for _, c in linha)), None)
    rows = []
    for li, linha in enumerate(linhas):
        if li == ki:
            xk = (1.6 if any(not c for _, c in linha) else 2.37) * sx
            rows.append([palavra(t[i], "helv-bold-oblique", xk / xh("helv-bold-oblique"), trk=-0.04) if c
                         else palavra(t[i], "helv-italic", 0.76 * S, trk=-0.01) for i, c in linha])
        else:
            em = S if ki is None or li < ki else 0.77 * S
            rows.append([palavra(t[i], "helv-italic", em, trk=-0.01) for i, _ in linha])
    base, folga = 0.0, 0.10 * sx
    for li, ps in enumerate(rows):
        chaves = [p for p in ps if p["face"] == "helv-bold-oblique"]
        # recuo da tinta como nos prints: linha da chave 0,8 altura-x ("atenção"), 1,3 se começa pequena ("usa")
        recuo = (1.3 if ps[0]["face"] != "helv-bold-oblique" else 0.8) * sx if chaves else (0.25 * sx if li else 0.0)
        linha_em(ps, recuo, 0.0, vao)
        if li:
            ant = rows[li - 1]
            gap = 0.80 * sx if chaves else (0.90 * sx if any(p["face"] == "helv-bold-oblique" for p in ant) else 0.60 * sx)
            base = encaixe(base, ant, chaves or ps, gap, folga)
        for p in ps:
            p["base"] = base
        if chaves:   # pequenas da linha da chave: topo das minúsculas 0,2 altura-x acima do da chave
            topo = base - max(xalt(p) for p in chaves) - 0.2 * sx
            for p in ps:
                if p not in chaves:
                    p["base"] = topo + xalt(p)
    return [p for ps in rows for p in ps]


ESTILOS = {"serifa": serifa, "classico": classico, "elegante": elegante, "impacto": impacto}


def topo_da_simples(clip):
    """Altura (px) do topo das maiúsculas de uma legenda simples, como o Concat a desenha."""
    st = clip["text"]
    face = next((f for f, v in FACES.items() if v[0].strip('"') == st["fontFamily"].strip('"')
                 and v[1] == int(st["fontWeight"]) and v[2] == bool(st.get("italic"))), "helv-regular")
    em = st["fontSize"] * H
    asc, desc, capa = metricas(face)
    base = H / 2 + clip.get("offsetY", 0.0) * H + (asc - desc) / 2 * em
    return base - capa * em


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
    if TOPO_Y is not None:  # o topo do bloco cai no topo da legenda simples
        cy = topo + (CENTRO_Y - TOPO_Y) / k
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
    global DESTAQUE, FONTE_CHAVE
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
    global TOPO_Y
    if legendas and "centro" not in _opc:
        TOPO_Y = topo_da_simples(legendas[0])
        print(f"bloco começa na altura da legenda simples: {TOPO_Y / H:.3f} da altura", flush=True)

    for familia, arquivo in REGISTRAR:
        api.edit({"op": "addFont", "family": familia, "path": os.path.abspath(os.path.join(FONTES, arquivo))})

    for n, bloco in enumerate(plano, 1):
        idx = [i for linha in bloco["linhas"] for i in linha]
        assert idx == list(range(idx[0], idx[-1] + 1)), f"frase {n}: índices fora de ordem {idx}"
        ultimo = idx[-1]
        fim = legendas[ultimo + 1]["start"] if ultimo + 1 < len(legendas) else legendas[ultimo]["start"] + legendas[ultimo]["duration"]
        # A legenda simples da última palavra já sai num corte longo (legendas_simples.py); se entre ela
        # e a próxima há uma troca de take, o bloco sai junto, no corte, e não invade o take seguinte.
        fim_ult = legendas[ultimo]["start"] + legendas[ultimo]["duration"]
        if fim_ult < fim - 1e-3 and any(fim_ult - 1.5 / FPS <= c["start"] < fim for c in tl["clips"] if c["kind"] == "video"):
            fim = fim_ult
        fim = round(fim * FPS) / FPS
        FONTE_CHAVE = bloco.get("fonte_chave", "serifa")
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
