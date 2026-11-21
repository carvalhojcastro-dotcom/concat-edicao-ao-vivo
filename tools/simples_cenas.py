#!/usr/bin/env python3
"""Telas de motion do Simples Medicina (Dr. Leonardo Luna) para os vídeos editados no CapCut, com o kit da marca.

Pedido de 2026-11-05 (estilo novo, mesclado ao nosso): "usar mais elementos visuais como animações e motions quando
for falado de números e informações estatísticas ... manter aquela cor de fundo nas legendas ... usar a tela dividida
para chamar mais atenção", tomando como base o manual da marca (skills simples-medicina-video e -marca da Bia) e o
vídeo de apresentação aprovado em 03/11/2026.

Dois formatos, como no manual:
  - "painel": 1080x960 para a tela dividida (painel em cima, ele embaixo). Os 110 px de baixo são a faixa marinho
    onde a legenda passa (STRIP_H). Fundo off-white, informação no primeiro kit, versão clara.
  - "tela": 1080x1920 só de motion, sem o rosto (conceitos, a pergunta). Sem legenda por cima: o texto já é a fala.
Regras da marca seguidas aqui: paleta marinho/verde/coral/off-white; Inter e Inter Display; coral nunca como texto
em fundo claro (só em formas, fios e barras); ícone Lucide verde + rótulo em caixa alta (nada de bolinha); o nome
da coisa sempre junto do número; nada de painel vazio (rótulos entram com o painel, valores na palavra que ele fala);
fios que não terminam no meio da tela; sem travessão.

O kit (código da Bia, fora do Git) fica em ~/Desktop/Edições/Kit de edição/Simples Medicina (SIMPLES_KIT muda).

Uso: simples_cenas.py <cenas.json> <pasta de saída>        (renderiza cada tela em MP4, 30 fps)
     simples_cenas.py <cenas.json> <pasta de saída> --quadros (só uma folha de quadros parados de cada tela)
  cenas.json: {"cenas": [{"id": "2 - numero", "formato": "painel"|"tela", "cena": "<nome>", "dur": s,
                          "ancoras": [s, ...], "params": {...}}, ...]}
  ancoras: segundos desde o começo da tela (a fala que dispara cada elemento; o capcut_simples.py calcula).
"""
import json
import math
import os
import subprocess
import sys

KIT = os.environ.get("SIMPLES_KIT", os.path.expanduser("~/Desktop/Edições/Kit de edição/Simples Medicina"))
sys.path.insert(0, os.path.join(KIT, "kit"))
os.environ["KIT_THEME"] = "light"
import numpy as np  # noqa: E402
import skia  # noqa: E402
import motion as KM  # noqa: E402
KM.LIGHT = False          # as cenas da marca desenham com as cores literais (texto marinho no off-white)
import marca as M  # noqa: E402
import components as K  # noqa: E402
from motion import text, reveal, tw, font, Life, lin, expo, eo, eo5, ei, eio, spring, clamp, icon, counter, mix  # noqa: E402

P = M.P
MAR, VER, COR, OFF = M.MAR, M.VER, M.COR, M.OFF
BRANCO = (255, 255, 255)
CINZA = (226, 221, 212)          # barra/figura apagada no fundo claro
W, H, PH, FPS = 1080, 1920, 960, 30
STRIP_H = 110                    # faixa marinho do painel (a legenda da tela dividida passa nela)
X0, X1 = 72, 1008


# ---------------------------------------------------------------- peças comuns
def life(t, t0, T, d=0.0, din=0.7, dout=0.4, od=0.0):
    return Life(t, t0, T, d, din, dout, od)


def ancora(a, i, padrao):
    """Tempo da âncora i (entra ~0,25 s antes da palavra, como no vídeo aprovado); sem âncora, o padrão."""
    return max(0.35, a[i] - 0.25) if a and i < len(a) and a[i] is not None else padrao


def tag(c, t, T, s, ico, y=178, color=VER):
    """Ícone Lucide (linha 2 px, verde) + rótulo em caixa alta verde 24 px, com o fio fino até a margem."""
    L = life(t, 0, T, 0, 0.6, 0.35)
    icon(c, ico, X0, y - 27 + L.dy(10, -6), 32, color, L.a, 2.0)
    text(c, s.upper(), X0 + 46, y + L.dy(10, -6), ("Inter-SemiBold", 24), color, L.a, tracking=0.14)
    k = eo5(lin(t, 0.1, 1.0)) * (1 - ei(lin(t, T - 0.5, 0.4)))
    c.drawLine(X0, y + 28, X0 + (W - X0) * k, y + 28, P(MAR if color != OFF else OFF, 0.10, 1.2))   # sai pela borda


def fio(c, x0, x1, y, k, k0=0.0, w=5.5):
    """Fio coral que se desenha sob a palavra-chave."""
    th = skia.Path()
    th.moveTo(x0, y)
    th.quadTo((x0 + x1) / 2, y - 12, x1, y + 4)
    M.trim(c, th, k, COR, w, 1, k0)


def caber(s, face, size, maxw):
    """Tamanho que faz a linha caber em maxw (encolhe, nunca cresce)."""
    w = tw(s, font(face, size))
    return size if w <= maxw else size * maxw / w


def linhas_chave(c, t, T, linhas, chave, x, y0, lh, face, size, t0=0.35, passo=0.16, cor=MAR, cor_chave=VER, centro=False,
                 fio_em=None):
    """Linhas grandes com a palavra-chave em verde e o fio coral sob ela. Devolve a base da última linha."""
    size = min(caber(s, face, size, X1 - X0) for s in linhas)
    f = font(face, size)
    xk = None
    for i, s in enumerate(linhas):
        Li = life(t, t0 + i * passo, T, 0, 0.8, 0.4, 0.04 * i)
        y = y0 + i * lh
        xl = (W - tw(s, f)) / 2 if centro else x
        if chave and chave in s:
            a, b = s.split(chave, 1)
            wa = tw(a, f)
            if a:
                reveal(c, a, xl, y, (face, size), cor, Li.i, Li.a, out=Li.o)
            reveal(c, chave, xl + wa, y, (face, size), cor_chave, Li.i, Li.a, out=Li.o)
            if b:
                reveal(c, b, xl + wa + tw(chave, f), y, (face, size), cor, Li.i, Li.a, out=Li.o)
            xk = (xl + wa, xl + wa + tw(chave.rstrip("?,.!"), f), y + size * 0.29)
        else:
            reveal(c, s, xl, y, (face, size), cor, Li.i, Li.a, out=Li.o)
    if xk:
        ki = fio_em if fio_em is not None else t0 + len(linhas) * passo + 0.5
        fio(c, xk[0], xk[1], xk[2], eio(lin(t, ki, 0.9)), ei(lin(t, T - 0.6, 0.45)))
    return y0 + (len(linhas) - 1) * lh


def linha_item(c, t, T, d, x, y, larg, ico, s, sub=None, cor=MAR, size=34):
    """Item de lista: fio fino que se desenha, ícone verde e texto (entra em d)."""
    Li = life(t, d, T, 0, 0.6, 0.35)
    k = eo5(lin(t, d, 0.7))
    c.drawLine(x, y - 44, x + larg * k, y - 44, P(cor, 0.12, 1.5))
    if ico:
        icon(c, ico, x, y - 30 + Li.dy(10, -6), 40, VER if cor == MAR else OFF, Li.a, 2.0)
    xt = x + (58 if ico else 0)
    size = caber(s, "Inter-SemiBold", size, X1 - xt)
    reveal(c, s, xt, y, ("Inter-SemiBold", size), cor, Li.i, Li.a, out=Li.o)
    if sub:
        reveal(c, sub, xt, y + 42, ("Inter-Medium", 28), cor, Li.i, 0.7 * Li.a, out=Li.o)


def fonte_rodape(c, t, T, s, d=1.0, y=812, cor=MAR):
    if not s:
        return
    L = life(t, d, T, 0, 0.6)
    icon(c, "file-text", X0, y - 21 + L.dy(10, -6), 26, VER, 0.8 * L.a, 2)
    text(c, s, X0 + 38, y + L.dy(10, -6), ("Inter-Medium", 22), cor, 0.6 * L.a)


def nota(c, t, T, s, d, y, cor=MAR, ico="info"):
    """Ressalva em 33 px (hierarquia do manual), com ícone."""
    if not s:
        return
    L = life(t, d, T, 0, 0.6)
    icon(c, ico, X0, y - 26 + L.dy(10, -6), 32, VER, L.a, 2.0)
    s_size = caber(s, "Inter-Medium", 33, X1 - X0 - 46)
    reveal(c, s, X0 + 46, y, ("Inter-Medium", s_size), cor, L.i, 0.85 * L.a, out=L.o)


def pessoa(c, x, y, s, color, a):
    K.person(c, x, y, s, color, a)    # bonequinho simples do primeiro kit (nunca as figuras do logo)


# ---------------------------------------------------------------- telas (1080x1920, sem o rosto)
def pergunta(c, t, T, a, p):
    """A pergunta (do paciente ou dele mesmo), em 2 a 4 linhas grandes, palavra-chave em verde com fio coral."""
    c.drawRect(skia.Rect(0, 0, W, H), P(OFF))
    linhas = p["linhas"]
    lh = 124
    y0 = (H - (len(linhas) - 1) * lh) / 2 + 40
    c.save()
    L = life(t, 0, T, 0, 0.6)
    yk = y0 - 190
    icon(c, p.get("icone", "user-round"), X0, yk - 27 + L.dy(10, -6), 32, VER, L.a, 2.0)
    text(c, p.get("rotulo", "A pergunta").upper(), X0 + 46, yk + L.dy(10, -6), ("Inter-SemiBold", 24), VER, L.a, tracking=0.14)
    linhas_chave(c, t, T, linhas, p.get("chave"), X0, y0, lh, "InterDisplay-SemiBold", 96)
    c.restore()


def frase(c, t, T, a, p):
    """Frase de conclusão sobre o verde, com o símbolo original no disco off-white e até 3 itens com ícone."""
    c.drawRect(skia.Rect(0, 0, W, H), P(VER))
    itens = p.get("itens", [])
    linhas = p["linhas"]
    alto = 240 + len(linhas) * 120 + (90 + len(itens) * 170 if itens else 0)
    c.save()
    c.translate(0, (H - alto) / 2 - 60)
    M.symbol_badge(c, W / 2, 110, 96, lin(t, 0.15, 1.0))
    size = min(caber(s, "InterDisplay-SemiBold", 92, X1 - X0) for s in linhas)
    f = font("InterDisplay-SemiBold", size)
    chave = p.get("chave")
    y = 330
    for i, s in enumerate(linhas):
        L = life(t, 0.5 + i * 0.16, T, 0, 0.8, 0.4, 0.04 * i)
        reveal(c, s, W / 2, y + i * 116, ("InterDisplay-SemiBold", size), OFF, L.i, L.a, align="center", out=L.o)
        if chave and chave in s:
            x = (W - tw(s, f)) / 2 + tw(s.split(chave, 1)[0], f)
            fio(c, x, x + tw(chave.rstrip("?,.!"), f), y + i * 116 + 30, eio(lin(t, 1.2 + 0.16 * i, 0.9)), ei(lin(t, T - 0.6, 0.45)), 6)
    yi = y + len(linhas) * 116 + 90
    for i, it in enumerate(itens):
        d = ancora(a, i, 1.4 + i * 0.5)
        L = life(t, d, T, 0, 0.7, 0.4)
        yy = yi + i * 170
        c.drawLine(X0, yy - 50, X0 + (W - X0) * eo5(lin(t, d, 0.8)), yy - 50, P(OFF, 0.25, 1.5))
        icon(c, it[0], X0, yy - 14 + L.dy(10, -6), 52, OFF, L.a, 2.0)
        reveal(c, it[1], X0 + 86, yy + 22, ("Inter-SemiBold", caber(it[1], "Inter-SemiBold", 40, X1 - X0 - 86)), OFF, L.i, L.a, out=L.o)
        if len(it) > 2:
            reveal(c, it[2], X0 + 86, yy + 70, ("Inter-Medium", 34), OFF, L.i, 0.82 * L.a, out=L.o)
    c.restore()


def passos(c, t, T, a, p):
    """Título + cartões numerados em sequência, ligados por seta (como "Médico e metodologista")."""
    c.drawRect(skia.Rect(0, 0, W, H), P(OFF))
    itens = p["itens"]
    alto = 300 + len(p["linhas"]) * 128 + len(itens) * 190
    c.save()
    c.translate(0, (H - alto) / 2)
    tag(c, t, T, p.get("rotulo", ""), p.get("icone", "list-checks"), y=40)
    linhas_chave(c, t, T, p["linhas"], p.get("chave"), X0, 200, 128, "InterDisplay-SemiBold", 108, t0=0.2)
    y0 = 200 + len(p["linhas"]) * 128 + 60
    for i, s in enumerate(itens):
        d = ancora(a, i, 1.0 + i * 0.8)
        L = life(t, d, T, 0, 0.7, 0.4)
        y = y0 + i * 190
        if L.a <= 0.003:
            continue
        sp = spring(lin(t, d, 0.9), 7, 1.5)
        c.save()
        c.translate(0, (1 - sp) * 40)
        rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(X0, y, W - 2 * X0, 128), 28, 28)
        c.drawRRect(rr, P(BRANCO, L.a))
        c.drawRRect(rr, P(MAR, 0.10 * L.a, 1.5))
        text(c, f"0{i + 1}", X0 + 40, y + 78, ("InterDisplay-SemiBold", 34), VER, L.a)
        text(c, s, X0 + 120, y + 78, ("Inter-SemiBold", caber(s, "Inter-SemiBold", 36, W - 2 * X0 - 160)), MAR, L.a)
        c.restore()
        if i < len(itens) - 1 and p.get("setas", True):
            La = life(t, d + 0.35, T, 0, 0.5, 0.4)
            icon(c, "arrow-down", W / 2 - 22, y + 140, 44, VER, La.a * 0.9, 2.2)
    c.restore()


def tempo(c, t, T, a, p):
    """Linha do tempo em anos: trechos (ex.: "1 a 1,5 ano") e um marco final (ex.: "3 anos e poucos meses")."""
    tela = p.get("_formato") == "tela"
    if tela:
        c.drawRect(skia.Rect(0, 0, W, H), P(OFF))
        c.save()
        c.translate(0, 560)
    tag(c, t, T, p.get("rotulo", "Duração dos estudos"), p.get("icone", "calendar-range"))
    Lt = life(t, 0.15, T, 0, 0.7)
    reveal(c, p["titulo"], X0, 282, ("InterDisplay-SemiBold", caber(p["titulo"], "InterDisplay-SemiBold", 54, X1 - X0)), MAR, Lt.i, Lt.a, out=Lt.o)
    amax = p.get("max", 4)
    gx0, gx1, gy = X0 + 10, X1 - 10, 560
    px = lambda v: gx0 + (gx1 - gx0) * v / amax   # noqa: E731
    La = life(t, 0.3, T, 0, 0.6, 0.4)
    kb = eo5(lin(t, 0.3, 1.0))
    c.drawLine(gx0, gy, gx0 + (gx1 - gx0) * kb, gy, P(MAR, 0.35 * La.a, 2.5))
    for v in range(0, amax + 1):
        ka = eo5(lin(t, 0.4 + v * 0.06, 0.5))
        c.drawLine(px(v), gy - 12 * ka, px(v), gy + 12 * ka, P(MAR, 0.35 * La.a, 2.5))
        text(c, f"{v} ano" + ("s" if v != 1 else "") if v else "início", px(v), gy + 58, ("Inter-Medium", 24), MAR, 0.55 * La.a, align="center")
    for i, tr in enumerate(p.get("trechos", [])):
        d = ancora(a, i, 0.9 + i * 0.8)
        L = life(t, d, T, 0, 0.6, 0.4)
        k = eio(lin(t, d, 0.9))
        x0, x1 = px(tr["de"]), px(tr["ate"])
        xx = x0 + (x1 - x0) * k
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(x0, gy - 26, max(xx, x0 + 52), gy + 26), 26, 26), P(VER, L.a))
        xc = max(X0 + 160, (x0 + x1) / 2)
        reveal(c, tr["rotulo"], xc, gy - 64, ("InterDisplay-SemiBold", 44), VER, L.i, L.a, align="center", out=L.o)
        if tr.get("sub"):
            reveal(c, tr["sub"], xc, gy - 128, ("Inter-Medium", 28), MAR, L.i, 0.7 * L.a, align="center", out=L.o)
    m = p.get("marco")
    if m:
        d = ancora(a, len(p.get("trechos", [])), 2.2)
        L = life(t, d, T, 0, 0.6, 0.4)
        k = eio(lin(t, d, 1.0))
        x = px(m["em"])
        xe = px(p["trechos"][-1]["ate"]) if p.get("trechos") else px(0)
        c.drawLine(xe, gy, xe + (x - xe) * k, gy, P(COR, L.a, 8))
        ks = spring(lin(t, d + 0.8, 0.8), 6, 1.6)
        if ks > 0.01:
            c.drawCircle(x, gy, 20 * ks, P(COR, L.a))
            c.drawCircle(x, gy, 8 * ks, P(OFF, L.a))
        al = "right" if x > W - 260 else "center"
        xr = min(x + 20, X1) if al == "right" else x
        reveal(c, m["rotulo"], xr, gy + 128, ("InterDisplay-SemiBold", 44), MAR, L.i, L.a, align=al, out=L.o)
        if m.get("sub"):
            reveal(c, m["sub"], xr, gy + 172, ("Inter-Medium", 28), MAR, L.i, 0.7 * L.a, align=al, out=L.o)
    n = p.get("nota")
    if n:
        nota(c, t, T, n, ancora(a, len(p.get("trechos", [])) + (1 if m else 0), 3.0), 800, ico=p.get("nota_icone", "check"))
    if tela:
        c.restore()


# ---------------------------------------------------------------- painéis (1080x960, faixa marinho embaixo)
def numero(c, t, T, a, p):
    """Número em destaque: rótulo, "mais de" / contexto, NÚMERO + unidade, frase de apoio e, opcional, de -> para
    (ex.: 100 kg -> 84 kg) e itens com ícone. Âncoras: [número, de_para, itens...]."""
    tag(c, t, T, p.get("rotulo", ""), p.get("icone", "activity"))
    y = 276
    if p.get("titulo"):        # o nome da condição sempre junto do dado (54 px)
        Lt = life(t, 0.15, T, 0, 0.6, 0.35)
        reveal(c, p["titulo"], X0, y, ("InterDisplay-SemiBold", caber(p["titulo"], "InterDisplay-SemiBold", 54, X1 - X0)), MAR, Lt.i, Lt.a, out=Lt.o)
    elif p.get("pre"):
        Lt = life(t, 0.15, T, 0, 0.6, 0.35)
        reveal(c, p["pre"], X0, y, ("Inter-Medium", 38), MAR, Lt.i, 0.7 * Lt.a, out=Lt.o)
    dn = ancora(a, 0, 0.6)
    L = life(t, dn, T, 0, 0.8, 0.4)
    fs = ("InterDisplay-SemiBold", p.get("tamanho", 210))
    yb = 470
    num = str(p["num"])
    valor = p.get("valor")
    c.save()
    c.clipRect(skia.Rect(0, yb - fs[1] * 0.95, W, yb + 40))
    if valor is not None and p.get("contar"):   # conta até o valor, com dígitos em células fixas (sem tremer)
        kc = eo5(lin(round(t * 30) / 30, dn, 1.3))
        wn = counter(c, valor * kc, X0 - 8, yb + (1 - L.i) * 200 - L.o * 200, fs, MAR, L.a, p.get("casas", 0))
    else:
        reveal(c, num, X0 - 8, yb, fs, MAR, L.i, L.a, out=L.o)
        wn = tw(num, font(*fs))
    c.restore()
    Lu = life(t, dn + 0.2, T, 0, 0.7, 0.4, 0.03)
    if p.get("unidade"):
        reveal(c, p["unidade"], X0 - 8 + wn + 10, yb, ("InterDisplay-SemiBold", fs[1] * 0.45), VER, Lu.i, Lu.a, out=Lu.o)
        wu = tw(p["unidade"], font("InterDisplay-SemiBold", fs[1] * 0.45))
    else:
        wu = 0
    fio(c, X0, X0 + min(wn + wu + 18, 560), yb + 38, eio(lin(t, dn + 0.6, 0.8)), ei(lin(t, T - 0.6, 0.45)))
    if p.get("sub"):
        Ls = life(t, dn + 0.4, T, 0, 0.7, 0.4, 0.05)
        reveal(c, p["sub"], X0, 572, ("Inter-Medium", caber(p["sub"], "Inter-Medium", 38, X1 - X0)), MAR, Ls.i, 0.78 * Ls.a, out=Ls.o)
    dp = p.get("de_para")
    if dp:
        d0 = ancora(a, 1, dn + 1.2)
        de_para(c, t, T, (d0, ancora(a, 2, d0 + 0.6)), dp, 640)
    itens = p.get("itens", [])
    if itens:
        cols = 2 if len(itens) == 4 else 1
        for i, it in enumerate(itens):
            d = ancora(a, 1 + i, dn + 0.8 + 0.4 * i)
            if cols == 2:
                x, yy = X0 + (i % 2) * 480, 690 + (i // 2) * 88
            else:
                x, yy = X0, 676 + i * 70
            linha_item(c, t, T, d, x, yy, (W - 2 * X0) / cols - 24, it[0], it[1])
    if p.get("nota"):
        nota(c, t, T, p["nota"], ancora(a, 1 + len(itens) + (2 if dp else 0), dn + 1.6), 690 if not (dp or itens) else 812,
             ico=p.get("nota_icone", "info"))
    fonte_rodape(c, t, T, p.get("fonte"), dn + 1.0)


def de_para(c, t, T, ds, dp, y):
    """De -> para com duas barras: a de cima (cinza) cresce até o "de"; a de baixo (verde) nasce no "de" e vai até o
    "para" (ex.: 100 kg descendo a 84 kg), com o número acompanhando; ds = (entrada do de, começo da ida ao para)."""
    de, para, un = float(dp["de"]), float(dp["para"]), dp.get("unidade", "")
    base = max(de, para)
    gx0, gx1 = X0, X1 - 230
    for i, (rot, cor) in enumerate(((dp.get("rotulo_de", "antes"), CINZA), (dp.get("rotulo_para", "depois"), VER))):
        yy = y + i * 86
        d = ds[i]
        Li = life(t, d, T, 0, 0.6, 0.4)
        if i == 0:
            v = de * eo5(lin(t, d, 0.9))
            vv = de
        else:     # o "para" parte do "de" e chega ao valor em 0,6 s, junto com a fala (números parados por quadro)
            k = eio(lin(round(t * 30) / 30, d, 0.6))
            v = vv = de + (para - de) * k
        text(c, rot, gx0, yy + 2 + Li.dy(10, -6), ("Inter-Medium", 26), MAR, 0.65 * Li.a)
        bw = (gx1 - gx0) * v / base
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(gx0, yy + 14, max(bw, 1), 44), 14, 14), P(cor, Li.a))
        s = KM.fmt_num(vv, 0) + (" " + un if un else "")
        text(c, s, gx0 + max(bw, 1) + 18, yy + 50, ("InterDisplay-SemiBold", 40), VER if i else MAR, Li.a)


def barras(c, t, T, a, p):
    """Comparação em barras horizontais (o nome de cada grupo, a barra e o valor escrito). Destaque em verde,
    o resto em cinza; coral só como fio. Âncoras: uma por linha (o valor entra quando ele fala)."""
    tag(c, t, T, p.get("rotulo", ""), p.get("icone", "chart-bar"))
    Lt = life(t, 0.15, T, 0, 0.7)
    tsz = caber(p["titulo"], "InterDisplay-SemiBold", 54, X1 - X0)
    reveal(c, p["titulo"], X0, 282, ("InterDisplay-SemiBold", tsz), MAR, Lt.i, Lt.a, out=Lt.o)
    linhas = p["linhas"]
    n = len(linhas)
    fundo = 760 if p.get("nota") or p.get("fonte") else 800
    passo = min(150, (fundo - 350) / max(n, 1))
    y_ini = 350 + max(0.0, (fundo - 350) - n * passo) / 2 + 20
    vmax = p.get("max") or max(r.get("frac", 1.0) for r in linhas)
    vmin = p.get("min", 0.0)      # eixo que não começa do zero (ex.: 84 x 89 x 93 kg): a diferença aparece
    gx0, gx1 = X0, X1 - 250
    for i, r in enumerate(linhas):
        d = ancora(a, i, 0.6 + i * 0.5)
        y = y_ini + i * passo
        Lr = life(t, 0.3 + 0.08 * i, T, 0, 0.6, 0.4)        # o nome entra com o painel (nada de painel vazio)
        rsz = caber(r["rotulo"], "Inter-SemiBold", 34 if passo >= 120 else 30, X1 - X0)
        reveal(c, r["rotulo"], X0, y, ("Inter-SemiBold", rsz), MAR, Lr.i, Lr.a * (1 if r.get("destaque", True) else 0.75), out=Lr.o)
        bh = 46 if passo >= 120 else 36
        by = y + 18
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(gx0, by, gx1 - gx0, bh), bh / 2, bh / 2), P(MAR, 0.05 * Lr.a))
        k = eo5(lin(t, d, 1.1))
        bw = (gx1 - gx0) * max(0.04, (r.get("frac", 1.0) - vmin) / (vmax - vmin)) * k
        if bw > 1:
            c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(gx0, by, max(bw, bh), bh), bh / 2, bh / 2),
                        P(VER if r.get("destaque", True) else CINZA, Lr.a))
        Lv = life(t, d + 0.3, T, 0, 0.6, 0.4)
        vsz = caber(r["valor"], "InterDisplay-SemiBold", 44 if passo >= 120 else 38, X1 - (gx0 + max(bw, bh) + 20))
        reveal(c, r["valor"], gx0 + max(bw, bh) + 20, by + bh - 6, ("InterDisplay-SemiBold", vsz), VER if r.get("destaque", True) else MAR,
               Lv.i, Lv.a, out=Lv.o)
    if p.get("nota"):
        nota(c, t, T, p["nota"], ancora(a, n, 2.4), 812, ico=p.get("nota_icone", "info"))
    fonte_rodape(c, t, T, p.get("fonte"), 1.2)


def pessoas(c, t, T, a, p):
    """X em cada 100: o número grande e 100 bonequinhos simples; os casos acendem em coral (forma, não texto).
    Âncoras: [número, casos]."""
    tag(c, t, T, p.get("rotulo", ""), p.get("icone", "users"))
    dn = ancora(a, 0, 0.5)
    Lb = life(t, dn, T, 0, 0.7)
    big = p["big"]
    fsz = caber(big, "InterDisplay-SemiBold", 104, X1 - X0)
    reveal(c, big, X0, 330, ("InterDisplay-SemiBold", fsz), MAR, Lb.i, Lb.a, out=Lb.o)
    Ls = life(t, dn + 0.2, T, 0, 0.7, 0.4, 0.04)
    reveal(c, p["sub"], X0, 390, ("Inter-Medium", caber(p["sub"], "Inter-Medium", 34, X1 - X0)), MAR, Ls.i, 0.7 * Ls.a, out=Ls.o)
    n = int(p["n"])
    cols, rows = 20, 5
    sx = (X1 - X0 - 12) / cols
    gy0, sy = 440, 68
    th = ancora(a, 1, dn + 0.9)
    ordem = sorted(range(100), key=lambda i: ((i * 37) % 100))     # casos espalhados, sempre os mesmos
    casos = set(ordem[:n]) if p.get("espalhar", False) else set(range(n))
    for r in range(rows):
        for q in range(cols):
            i = r * cols + q
            d = 0.25 + (q + r * 1.6) * 0.018
            k = spring(lin(t, d, 0.8), 7, 1.5)
            if k <= 0.001:
                continue
            x = X0 + 6 + sx * (q + 0.5)
            y = gy0 + sy * r + (1 - k) * 26
            ex = ei(lin(t, T - 0.6 + (q + r) * 0.006, 0.35))
            al = min(1, k * 1.5) * (1 - ex)
            if i in casos:
                kh = clamp(lin(t, th + (i % cols) * 0.015 + r * 0.03, 0.35))
                pessoa(c, x, y, 0.78, KM.mixc(CINZA, COR, kh), al)
            else:
                pessoa(c, x, y, 0.78, CINZA, al)
    if p.get("nota"):
        nota(c, t, T, p["nota"], ancora(a, 2, th + 1.2), 822, ico=p.get("nota_icone", "info"))


def lista(c, t, T, a, p):
    """Título + itens com ícone, cada um na palavra em que ele fala. Âncoras: uma por item."""
    tag(c, t, T, p.get("rotulo", ""), p.get("icone", "list"))
    y = 282
    if p.get("titulo"):
        Lt = life(t, 0.15, T, 0, 0.7)
        reveal(c, p["titulo"], X0, y, ("InterDisplay-SemiBold", caber(p["titulo"], "InterDisplay-SemiBold", 54, X1 - X0)), MAR, Lt.i, Lt.a, out=Lt.o)
    itens = p["itens"]
    n = len(itens)
    topo, fundo = (360 if p.get("titulo") else 250), 810
    passo = min(130, (fundo - topo) / max(n, 1))
    y0 = topo + max(0.0, (fundo - topo) - n * passo) / 2 + passo * 0.62
    for i, it in enumerate(itens):
        d = ancora(a, i, 0.7 + 0.5 * i)
        linha_item(c, t, T, d, X0, y0 + i * passo, X1 - X0, it[0], it[1], it[2] if len(it) > 2 else None, size=38)


def fonte(c, t, T, a, p):
    """De onde vem a informação: a frase dele como título (ex.: "Principal instituição de revisão da literatura
    médica"), depois o cartão branco com o ícone e o nome (ex.: "Cochrane") e, abaixo, etiquetas (ex.: "Revisão de
    2025"). Âncoras: [título, cartão com o nome, etiquetas...]."""
    tag(c, t, T, p.get("rotulo", "De onde vem a informação"), p.get("icone", "landmark"))
    dt = ancora(a, 0, 0.3)
    linhas = p.get("desc", [])
    for i, s_ in enumerate(linhas):
        L = life(t, dt + 0.12 * i, T, 0, 0.7, 0.4, 0.03 * i)
        reveal(c, s_, X0, 282 + i * 64, ("InterDisplay-SemiBold", caber(s_, "InterDisplay-SemiBold", 54, X1 - X0)), MAR, L.i, L.a, out=L.o)
    dn = ancora(a, 1, dt + 1.2)
    s = spring(lin(t, dn, 1.1), 7, 1.5)
    L = life(t, dn, T, 0, 0.45)
    bx, by, bw, bh = X0, 282 + len(linhas) * 64 + 10, X1 - X0, 200
    c.save()
    c.translate(0, (1 - s) * 50 + L.o * -30)
    rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(bx, by, bw, bh), 32, 32)
    c.drawRRect(rr, P(BRANCO, L.a))
    c.drawRRect(rr, P(MAR, 0.08 * L.a, 1.5))
    ki = spring(lin(t, dn + 0.15, 0.9), 6, 1.7)
    ix, iy = bx + 48 + 50, by + bh / 2
    if ki > 0.01:
        c.drawCircle(ix, iy, 50 * ki, P(VER, L.a))
        icon(c, p.get("icone_nome", "book-open-check"), ix - 26 * ki, iy - 26 * ki, 52 * ki, OFF, L.a, 2.2)
    Ln = life(t, dn + 0.2, T, 0, 0.7, 0.38)
    nsz = caber(p["nome"], "InterDisplay-SemiBold", 92, bw - 290)
    reveal(c, p["nome"], bx + 180, iy + nsz * 0.36, ("InterDisplay-SemiBold", nsz), MAR, Ln.i, L.a, out=Ln.o)
    ks = spring(lin(t, dn + 0.7, 1.0), 5.5, 1.6)
    if ks > 0.01:
        sx, sy = bx + bw - 48 - 44, iy
        c.save()
        c.translate(sx, sy)
        c.rotate(-25 * (1 - ks))
        c.scale(ks, ks)
        c.drawCircle(0, 0, 44, P(VER, L.a, 3))
        c.drawCircle(0, 0, 36, P(VER, 0.12 * L.a))
        pth = skia.Path()
        pth.moveTo(-15, 1)
        pth.lineTo(-4, 12)
        pth.lineTo(17, -11)
        M.trim(c, pth, eo(lin(t, dn + 0.9, 0.5)), VER, 6, L.a)
        c.restore()
    c.restore()
    x = X0
    yy = by + bh + 44
    for i, e in enumerate(p.get("etiquetas", [])):
        d = ancora(a, 2 + i, dn + 1.2 + 0.3 * i)
        Lp = life(t, d, T, 0, 0.6, 0.38)
        pf = ("Inter-SemiBold", 30)
        pw = tw(e, font(*pf)) + 56
        if x + pw > X1:
            x, yy = X0, yy + 82
        y_ = yy + Lp.dy(24, -14)
        rr = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y_, pw, 64), 32, 32)
        c.drawRRect(rr, P(VER, 0.10 * Lp.a))
        c.drawRRect(rr, P(VER, 0.5 * Lp.a, 1.6))
        text(c, e, x + 28, y_ + 43, pf, VER, Lp.a)
        x += pw + 14


def alerta(c, t, T, a, p):
    """Atenção (ressalva, contraindicação): triângulo coral que se desenha, a mensagem com a chave em verde e uma
    nota. Âncoras: [mensagem, nota]."""
    tag(c, t, T, p.get("rotulo", "Atenção"), p.get("icone", "triangle-alert"))
    dm = ancora(a, 0, 0.5)
    cx, cy = X1 - 120, 390
    ks = spring(lin(t, dm, 1.0), 6, 1.6)
    tri = skia.Path()
    r = 62
    tri.moveTo(cx, cy - r)
    tri.lineTo(cx + r * 1.07, cy + r * 0.78)
    tri.lineTo(cx - r * 1.07, cy + r * 0.78)
    tri.close()
    La = life(t, dm, T, 0, 0.5)
    c.save()
    c.translate(cx, cy)
    c.scale(0.8 + 0.2 * ks, 0.8 + 0.2 * ks)
    c.translate(-cx, -cy)
    kf = eo(lin(t, dm + 0.5, 0.4))
    if kf > 0:
        c.drawPath(tri, P(COR, kf * La.a))
    M.trim(c, tri, eo5(lin(t, dm, 0.8)), COR, 9, La.a)
    c.drawLine(cx, cy - 20, cx, cy + 14, P(MAR, La.a * kf, 10))
    c.drawCircle(cx, cy + 34, 6 * kf, P(MAR, La.a))
    c.restore()
    linhas = p["linhas"]
    lh = 76
    yb = linhas_chave(c, t, T, linhas, p.get("chave"), X0, 360, lh, "InterDisplay-SemiBold", 64, t0=dm, passo=0.14)
    if p.get("nota"):
        nota(c, t, T, p["nota"], ancora(a, 1, dm + 1.4), max(yb + 130, 680), ico=p.get("nota_icone", "info"))
    if p.get("nota2"):
        nota(c, t, T, p["nota2"], ancora(a, 2, dm + 2.2), max(yb + 190, 720), ico=p.get("nota2_icone", "info"))


NIVEIS = ("Muito baixa", "Baixa", "Moderada", "Alta")
COR_NIVEL = {"Alta": VER, "Moderada": MAR, "Baixa": COR, "Muito baixa": COR}     # manual: Alta verde, Moderada marinho, Baixa coral


def certeza(c, t, T, a, p):
    """Certeza da evidência: arco em 4 níveis com as cores do manual e um ponteiro que pousa no nível ("de" -> "nivel":
    ex.: estudos observacionais partem de Baixa e podem subir para Alta). Âncoras: [nível inicial, nível final]."""
    tag(c, t, T, p.get("rotulo", "Certeza da evidência"), p.get("icone", "gauge"))
    Lt = life(t, 0.15, T, 0, 0.7)
    reveal(c, p["titulo"], X0, 282, ("InterDisplay-SemiBold", caber(p["titulo"], "InterDisplay-SemiBold", 54, X1 - X0)), MAR, Lt.i, Lt.a, out=Lt.o)
    cx, cy, R = W / 2, 690, 250
    span = 180 / 4
    Lg = life(t, 0.3, T, 0, 0.5, 0.4)
    n0, n1 = p.get("de", p["nivel"]), p["nivel"]
    d0 = ancora(a, 0, 0.9)
    d1 = ancora(a, 1, d0 + 1.5) if n1 != n0 else d0
    for i, nm in enumerate(NIVEIS):
        st = 180 + i * span + 1.5
        kd = eo5(lin(t, 0.4 + i * 0.14, 0.7))
        ativo = i == n1 and t >= d1 + 0.6 or i == n0 and t < d1 + 0.6
        pth = skia.Path()
        pth.addArc(skia.Rect(cx - R, cy - R, cx + R, cy + R), st, span - 3)
        cor = COR_NIVEL[nm]
        M.trim(c, pth, kd, cor, 46 if not ativo else 56, Lg.a * (1.0 if ativo else 0.28))
        mid = math.radians(st + span / 2)
        lx, ly = cx + math.cos(mid) * (R + 64), cy + math.sin(mid) * (R + 64)
        al = "right" if math.cos(mid) < -0.3 else "left" if math.cos(mid) > 0.3 else "center"
        La = life(t, 0.6 + i * 0.12, T, 0, 0.5, 0.4)
        text(c, nm, lx, ly + 11, ("Inter-SemiBold", 30), MAR, La.a * (1.0 if ativo else 0.5), align=al)
    k0 = spring(lin(t, d0, 1.4), 5.2, 1.3)
    k1 = spring(lin(t, d1, 1.4), 5.2, 1.3) if n1 != n0 else 1.0
    nivel = n0 + (n1 - n0) * k1
    ang = math.radians(180 + (180 + (nivel + 0.5) * span - 180) * k0)
    Ln = life(t, d0 - 0.2, T, 0, 0.4, 0.4)
    nx, ny = cx + math.cos(ang) * (R - 70), cy + math.sin(ang) * (R - 70)
    px_, py_ = -math.sin(ang) * 12, math.cos(ang) * 12
    pth = skia.Path()
    pth.moveTo(cx + px_, cy + py_)
    pth.lineTo(nx, ny)
    pth.lineTo(cx - px_, cy - py_)
    pth.close()
    c.drawPath(pth, P(MAR, Ln.a))
    c.drawCircle(cx, cy, 28, P(MAR, Ln.a))
    c.drawCircle(cx, cy, 11, P(OFF, Ln.a))
    atual = NIVEIS[n1] if t >= d1 + 0.6 else NIVEIS[n0]
    tc = VER if atual == "Alta" else MAR          # coral nunca como texto no fundo claro
    Lr = life(t, d0 + 0.9, T, 0, 0.5, 0.4)
    text(c, atual, cx, cy + 92, ("InterDisplay-SemiBold", 52), tc, Lr.a, align="center")
    if p.get("nota"):
        nota(c, t, T, p["nota"], ancora(a, 2, d1 + 1.0), 830 - 10, ico=p.get("nota_icone", "info"))


def revisao(c, t, T, a, p):
    """Revisão sistemática (gráfico de floresta do primeiro kit, versão clara, marcado "conteúdo ilustrativo")."""
    K.HEAD_ICON = "file-search"
    KM.LIGHT = True
    try:
        K.forest(c, t, T, lab=p.get("rotulo", "Revisão sistemática"), title=p.get("titulo", "Juntando todos os estudos"))
    finally:
        KM.LIGHT = False
        K.HEAD_ICON = None


CENAS = dict(pergunta=pergunta, frase=frase, passos=passos, tempo=tempo, numero=numero, barras=barras, pessoas=pessoas,
             lista=lista, fonte=fonte, alerta=alerta, certeza=certeza, revisao=revisao)


# ---------------------------------------------------------------- render
# cenas desenhadas para o painel de 1080x960; em "tela" (motion sozinho, sem o rosto, só com a voz dele) vão para o meio
# da tela cheia (feedback da Bia, 05/11/2026: "mesclar entre ele sozinho, ele dividindo a tela e o motion sozinho ... para
# destacar algumas falas importantes ou alguns números"). O tempo já se ajeita sozinho.
DE_PAINEL = {"numero", "barras", "pessoas", "lista", "fonte", "alerta", "certeza", "revisao"}
DESCE_TELA = 470


def quadro(cena, t):
    nome, formato, T, a, p = cena["cena"], cena["formato"], cena["dur"], cena.get("ancoras", []), dict(cena.get("params", {}))
    p["_formato"] = formato
    fn = CENAS[nome]
    if formato == "tela":
        def d(c, tt):
            c.drawRect(skia.Rect(0, 0, W, H), P(OFF))
            if nome in DE_PAINEL:
                c.save()
                c.translate(0, DESCE_TELA)
                fn(c, tt, T, a, p)
                c.restore()
            else:
                fn(c, tt, T, a, p)
        return KM.render(d, t, w=W, h=H, sub=3, bg=False, grain_amt=0)

    def d(c, tt):
        c.drawRect(skia.Rect(0, 0, W, PH), P(OFF))
        fn(c, tt, T, a, p)
        c.drawRect(skia.Rect(0, PH - STRIP_H, W, PH), P(MAR))     # faixa da legenda
    return KM.render(d, t, w=W, h=PH, sub=3, bg=False, grain_amt=1.5)


def renderizar(cena, saida):
    w, h = (W, H) if cena["formato"] == "tela" else (W, PH)
    n = int(round(cena["dur"] * FPS))
    p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-crf", "14", "-preset", "medium", "-pix_fmt", "yuv420p", "-color_primaries", "bt709",
                          "-color_trc", "bt709", "-colorspace", "bt709", "-movflags", "+faststart", saida], stdin=subprocess.PIPE)
    for f in range(n):
        p.stdin.write(quadro(cena, f / FPS).tobytes())
    p.stdin.close()
    p.wait()
    return n


def folha(cenas, saida):
    """Quadros parados de cada tela (o fim de cada elemento entrar), para aprovar a direção antes de tudo."""
    from PIL import Image
    ims = []
    for cena in cenas:
        t = min(cena["dur"] - 0.7, max(cena.get("ancoras", [0]) + [1.5]) + 1.6)
        im = Image.fromarray(quadro(cena, max(0.0, t)))
        if cena["formato"] == "painel":
            fundo = Image.new("RGB", (W, H), (40, 40, 40))
            fundo.paste(im, (0, 0))
            im = fundo
        ims.append(im.resize((W // 3, H // 3)))
    cols = min(4, len(ims))
    rows = math.ceil(len(ims) / cols)
    sheet = Image.new("RGB", (cols * (W // 3 + 12), rows * (H // 3 + 12)), (255, 255, 255))
    for i, im in enumerate(ims):
        sheet.paste(im, ((i % cols) * (W // 3 + 12), (i // cols) * (H // 3 + 12)))
    sheet.save(saida, quality=90)


def main():
    args = [x for x in sys.argv[1:] if not x.startswith("--")]
    plano = json.load(open(args[0], encoding="utf-8"))
    pasta = args[1]
    os.makedirs(pasta, exist_ok=True)
    cenas = plano["cenas"]
    if "--quadros" in sys.argv:
        folha(cenas, os.path.join(pasta, "folha_cenas.jpg"))
        print(os.path.join(pasta, "folha_cenas.jpg"))
        return
    for cena in cenas:
        saida = os.path.join(pasta, cena["id"] + ".mp4")
        n = renderizar(cena, saida)
        print(f"{cena['id']}: {n} quadros ({cena['formato']})")


if __name__ == "__main__":
    main()
