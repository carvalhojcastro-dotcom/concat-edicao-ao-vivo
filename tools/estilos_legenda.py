#!/usr/bin/env python3
"""Pacote de estilos de legenda para o Concat: fontes, composições e animações de entrada.

Referências analisadas em 2026-10-19:
  - vitrine Vimeo 1189819698: 24 animações em Poppins Black (Abaixo, Acima, Blur, BlurUp,
    Brilho, Cinematic, Corte, CORTE riscado, Destacado, Direita, Esquerda, Fade in, Flicker,
    FLICKING, Girando, GOLD, MODERNO, Palavra por palavra, REVEAL, Slide, Sublinhado, SILVER,
    Surgir, Zoom Out);
  - reel DeaL7FgRV4C (e DdsIOERNQNo): frases montadas palavra por palavra em Plus Jakarta Sans,
    em degraus, com tamanhos misturados; a cursiva rosa dela vira Scholar Itálico branco/amarelo;
  - modelos estáticos: "Copie e cole MODELOS PRONTOS", "Quebre o PADRÃO com DINAMISMO",
    "Textos CHAMATIVOS com ESTILO", "Textos elegantes que IMPRESSIONAM".

Como funciona: cada pedaço de texto é um Elemento. O normal é virar um clipe de texto do Concat
(editável depois). Quando o Concat não desenha o efeito - degradê, dourado, prata, brilho que passa
por dentro das letras, a palavra fatiada do "Corte" - o elemento vira PNG (ou vídeo ProRes 4444 com
transparência) renderizado aqui com as mesmas fontes, no mesmo lugar em que o texto estaria.
As animações são keyframes de posição, escala, rotação e opacidade, mais o raio do Gaussian Blur e o
comprimento do Motion Blur (o Concat aceita keyframe nos parâmetros dos efeitos).

Achados sobre o Concat 0.2.7 (testados):
  - escala e rotação giram em volta da própria palavra; vêm de setClipTransform, não de updateClip;
  - recorte (crop) não vale em texto; em imagem sim;
  - texto vazado: cor "#ffffff00" + contorno; retângulo: texto " " com fundo e maxWidth/maxHeight;
  - imagem/vídeo entram encaixados no quadro (contain) a escala 1;
  - vídeo ProRes 4444 com alfa é composto com a transparência certa;
  - edit.apply devolve createdId;
  - keys em offsetY de título somam com a base: com keys, a base fica 0 e as keys são absolutas.
"""
import json
import math
import os
import random
import subprocess
import sys
from dataclasses import dataclass, field

import numpy as np
from fontTools.ttLib import TTFont
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from concat_api import Concat, timeline  # noqa: E402

FONTES = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts"))

# face: (família CSS no Concat, peso, itálico, arquivo, família para registrar)
FACES = {
    "pop-black": ("Poppins", 900, False, "Poppins-Black.ttf"),
    "pop-black-it": ("Poppins", 900, True, "Poppins-BlackItalic.ttf"),
    "pop-xbold": ("Poppins", 800, False, "Poppins-ExtraBold.ttf"),
    "pop-xbold-it": ("Poppins", 800, True, "Poppins-ExtraBoldItalic.ttf"),
    "pop-bold": ("Poppins", 700, False, "Poppins-Bold.ttf"),
    "pop-bold-it": ("Poppins", 700, True, "Poppins-BoldItalic.ttf"),
    "pop-semibold": ("Poppins", 600, False, "Poppins-SemiBold.ttf"),
    "pop-semibold-it": ("Poppins", 600, True, "Poppins-SemiBoldItalic.ttf"),
    "pop-medium": ("Poppins", 500, False, "Poppins-Medium.ttf"),
    "pop-medium-it": ("Poppins", 500, True, "Poppins-MediumItalic.ttf"),
    "jak-medium": ('"Plus Jakarta Sans"', 500, False, "PlusJakartaSans-Medium.ttf"),
    "jak": ('"Plus Jakarta Sans"', 600, False, "PlusJakartaSans-SemiBold.ttf"),
    "jak-bold": ('"Plus Jakarta Sans"', 700, False, "PlusJakartaSans-Bold.ttf"),
    "jak-xbold": ('"Plus Jakarta Sans"', 800, False, "PlusJakartaSans-ExtraBold.ttf"),
    "scholar": ("Scholar", 400, False, "Scholar-Regular.otf"),
    "scholar-it": ("Scholar", 400, True, "Scholar-Italic.otf"),
    "playfair-bold": ('"Playfair Display"', 700, False, "PlayfairDisplay-Bold.ttf"),
    "playfair-black": ('"Playfair Display"', 900, False, "PlayfairDisplay-Black.ttf"),
    "playfair-it": ('"Playfair Display"', 600, True, "PlayfairDisplay-SemiBoldItalic.ttf"),
    "playfair-xbold-it": ('"Playfair Display"', 800, True, "PlayfairDisplay-ExtraBoldItalic.ttf"),
    "mont-black": ("Montserrat", 900, False, "Montserrat-Black.ttf"),
    "mont-bold": ("Montserrat", 700, False, "Montserrat-Bold.otf"),
    "helv-medium": ('"Helvetica Neue Medium"', 500, False, "HelveticaNeue-Medium.ttf"),
}

BRANCO, AMARELO = "#ffffff", "#f4c430"
OUT = [0.16, 1.0, 0.3, 1.0]        # sai rápido e assenta (expo-out)
SUAVE = [0.25, 0.1, 0.25, 1.0]
LINEAR = [0.0, 0.0, 1.0, 1.0]
DEGRAU = [1.0, 0.0, 1.0, 0.0]      # segura e pula no fim (para piscar)

# ─────────────────────────────── fontes e medidas ───────────────────────────────

_tt, _pil = {}, {}


def _arquivo(face):
    return os.path.join(FONTES, FACES[face][3])


def fonte_pil(face, px):
    k = (face, int(round(px)))
    if k not in _pil:
        _pil[k] = ImageFont.truetype(_arquivo(face), size=max(1, k[1]))
    return _pil[k]


def metricas(face):
    """(ascendente, descendente, altura de maiúscula) em em, como o Concat lê."""
    if face not in _tt:
        tt = TTFont(_arquivo(face))
        upem, os2 = tt["head"].unitsPerEm, tt["OS/2"]
        if os2.fsSelection & (1 << 7):
            asc, desc = os2.sTypoAscender, os2.sTypoDescender
        else:
            asc, desc = tt["hhea"].ascent, tt["hhea"].descent
        cap = getattr(os2, "sCapHeight", 0) or int(asc * 0.7)
        _tt[face] = (asc / upem, -desc / upem, cap / upem)
    return _tt[face]


def largura(face, em, texto, trk=0.0):
    return fonte_pil(face, em).getlength(texto) + trk * em * max(len(texto) - 1, 0)


def tinta(face, em, texto):
    """Quanto a tinta sobe e desce em relação à linha de base (px)."""
    _, topo, _, pe = fonte_pil(face, em).getbbox(texto, anchor="ls")
    return -topo, max(pe, 0)


# ─────────────────────────────────── elementos ───────────────────────────────────

@dataclass
class El:
    texto: str = ""
    face: str = "pop-black"
    em: float = 100.0            # px no quadro do projeto
    cor: str = BRANCO
    trk: float = 0.0             # espaçamento, em em
    x: float = 0.0               # esquerda da palavra (px)
    base: float = 0.0            # linha de base (px)
    contorno: float = 0.0        # px
    cor_contorno: str = "#000000"
    sombra: bool = True
    tipo: str = "texto"          # texto | caixa | png | video
    fundo: str = ""              # caixa: cor; texto: placa atrás
    raio: float = 0.0            # caixa: raio do canto (px)
    w: float = 0.0               # caixa/png/video: tamanho (px)
    h: float = 0.0
    cx: float = 0.0              # caixa/png/video: centro (px)
    cy: float = 0.0
    arquivo: str = ""
    inicio: float = 0.0
    fim: float = 0.0
    escala: float = 1.0
    rot: float = 0.0
    keys: list = field(default_factory=list)      # (prop, t, valor, ease); dx/dy em px
    efeitos: list = field(default_factory=list)   # {"id", "params", "keys": [(param, t, valor, ease)]}
    papel: str = ""
    palavra: int = -1            # índice da palavra falada (para o tempo)

    @property
    def larg(self):
        return largura(self.face, self.em, self.texto, self.trk) if self.tipo == "texto" else self.w

    def centro(self):
        """Centro (px) do que aparece na tela."""
        if self.tipo == "texto":
            asc, desc, cap = metricas(self.face)
            return self.x + self.larg / 2, self.base - cap * self.em / 2
        return self.cx, self.cy

    def copia(self, **kw):
        d = dict(self.__dict__)
        d["keys"], d["efeitos"] = list(self.keys), [dict(e, keys=list(e.get("keys", []))) for e in self.efeitos]
        d.update(kw)
        return El(**d)

    def key(self, prop, t, valor, ease=OUT):
        self.keys.append((prop, t, valor, ease))
        return self

    def efeito(self, ident, params, keys=()):
        self.efeitos.append({"id": ident, "params": dict(params), "keys": list(keys)})
        return self


def palavra(texto, face, em, cor=BRANCO, trk=0.0, **kw):
    return El(texto=texto, face=face, em=em, cor=cor, trk=trk, **kw)


def letras(el):
    """A palavra quebrada em letras posicionadas (sem os espaços)."""
    f = fonte_pil(el.face, el.em)
    out = []
    for i, ch in enumerate(el.texto):
        if ch.isspace():
            continue
        x = el.x + f.getlength(el.texto[:i]) + el.trk * el.em * i
        out.append(el.copia(texto=ch, x=x, trk=0.0, keys=[], efeitos=[]))
    return out


def caixa(cx, cy, w, h, cor, raio=0.0, **kw):
    return El(tipo="caixa", cx=cx, cy=cy, w=w, h=h, fundo=cor, raio=raio, sombra=False, **kw)


# ─────────────────────────────── renderização PNG ───────────────────────────────

def _mascara(el, margem):
    """Máscara (L) do texto e onde fica a linha de base dentro dela."""
    f = fonte_pil(el.face, el.em)
    asc, desc, _ = metricas(el.face)
    larg = int(el.larg + 2 * margem + el.em * 0.3)
    alt = int((asc + desc) * el.em + 2 * margem)
    m = Image.new("L", (larg, alt), 0)
    d = ImageDraw.Draw(m)
    x0, base = margem, margem + asc * el.em
    for i, ch in enumerate(el.texto):
        d.text((x0 + f.getlength(el.texto[:i]) + el.trk * el.em * i, base), ch, font=f, fill=255, anchor="ls")
    return m, x0, base


def _degrade(tam, paradas, angulo=90):
    """Degradê linear; paradas = [(0..1, "#rrggbb"), ...]; ângulo 90 = de cima para baixo."""
    w, h = tam
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    a = math.radians(angulo)
    p = (xx * math.cos(a) + yy * math.sin(a))
    p = (p - p.min()) / max(p.max() - p.min(), 1)
    cores = [(t, np.array([int(c[i:i + 2], 16) for i in (1, 3, 5)], np.float32)) for t, c in paradas]
    out = np.zeros((h, w, 3), np.float32)
    for (t0, c0), (t1, c1) in zip(cores, cores[1:]):
        sel = (p >= t0) & (p <= t1)
        k = ((p - t0) / max(t1 - t0, 1e-6))[..., None]
        out = np.where(sel[..., None], c0 + (c1 - c0) * k, out)
    return Image.fromarray(out.clip(0, 255).astype(np.uint8), "RGB")


OURO = [(0.0, "#fff1b8"), (0.28, "#f6c64e"), (0.5, "#c98a12"), (0.62, "#f7d36a"), (0.8, "#b8780e"), (1.0, "#7a4a08")]
PRATA = [(0.0, "#ffffff"), (0.3, "#d8d8d8"), (0.48, "#6f6f6f"), (0.55, "#f2f2f2"), (0.75, "#9a9a9a"), (1.0, "#4a4a4a")]
BRANCO_CINZA = [(0.0, "#ffffff"), (0.55, "#f4f4f4"), (1.0, "#bdbdbd")]


def textura_metal(tam, paradas, faixas=7, semente=1):
    """Metal escovado: degradê diagonal + faixas de reflexo, como o GOLD/SILVER da vitrine."""
    w, h = tam
    base = np.asarray(_degrade(tam, paradas, angulo=70), np.float32)
    rng = np.random.default_rng(semente)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    diag = xx + yy * 0.6
    luz = np.zeros((h, w), np.float32)
    for _ in range(faixas):
        c, lw = rng.uniform(0, w + h * 0.6), rng.uniform(w * 0.01, w * 0.05)
        luz += np.exp(-((diag - c) / lw) ** 2) * rng.uniform(0.25, 0.6)
    out = base + (255 - base) * np.clip(luz, 0, 1)[..., None] * 0.8
    return Image.fromarray(out.clip(0, 255).astype(np.uint8), "RGB")


def render_png(el, destino, preench="cor", brilho=None, sombra=True, faixa=None):
    """Desenha o texto de `el` num PNG transparente e devolve um El tipo "png" no mesmo lugar."""
    out, x0, base = render_img(el, preench, brilho, sombra, faixa)
    out.save(destino)
    tam = out.size
    return el.copia(tipo="png", arquivo=destino, w=tam[0], h=tam[1], cx=el.x - x0 + tam[0] / 2, cy=el.base - base + tam[1] / 2)


def render_img(el, preench="cor", brilho=None, sombra=True, faixa=None):
    """A imagem RGBA do texto, a esquerda do texto e a linha de base dentro dela.

    preench: "cor" | "branco_cinza" | "ouro" | "prata" | lista de paradas de degradê
    brilho:  (cor, raio_px, força) - halo em volta das letras (neon)
    faixa:   (posição 0..1, largura 0..1) - faixa de luz branca atravessando as letras
    """
    margem = int(el.em * 0.6 + (brilho[1] * 2 if brilho else 0))
    m, x0, base = _mascara(el, margem)
    tam = m.size
    if preench == "cor":
        tinta_img = Image.new("RGB", tam, el.cor)
    elif preench == "ouro":
        tinta_img = textura_metal(tam, OURO, semente=3)
    elif preench == "prata":
        tinta_img = textura_metal(tam, PRATA, faixas=9, semente=7)
    elif preench == "branco_cinza":
        tinta_img = _degrade(tam, BRANCO_CINZA)
    else:
        tinta_img = _degrade(tam, preench)
    if faixa:
        pos, lw = faixa
        yy, xx = np.mgrid[0:tam[1], 0:tam[0]].astype(np.float32)
        diag = (xx + yy * 0.35) / (tam[0] + tam[1] * 0.35)
        luz = np.exp(-((diag - pos) / lw) ** 2)[..., None]
        arr = np.asarray(tinta_img, np.float32)
        tinta_img = Image.fromarray((arr + (255 - arr) * luz * 0.9).clip(0, 255).astype(np.uint8))
    out = Image.new("RGBA", tam, (0, 0, 0, 0))
    if sombra:
        s = m.filter(ImageFilter.GaussianBlur(el.em * 0.045)).point(lambda v: int(v * (0.8 if preench != "cor" else 0.55)))
        sh = Image.new("RGBA", tam, (0, 0, 0, 255)); sh.putalpha(s)
        out.alpha_composite(sh, (int(el.em * 0.02), int(el.em * 0.05)))
    if brilho:
        cor, raio, forca = brilho
        g = m.filter(ImageFilter.GaussianBlur(raio)).point(lambda v: min(255, int(v * forca)))
        gl = Image.new("RGBA", tam, cor); gl.putalpha(g)
        out.alpha_composite(gl)
    t = tinta_img.convert("RGBA"); t.putalpha(m)
    out.alpha_composite(t)
    return out, x0, base


def render_video(el, destino, quadros, fps):
    """`quadros(i, n)` -> PIL RGBA do tamanho do PNG base; grava ProRes 4444 com alfa."""
    n = len(quadros)
    w, h = quadros[0].size
    w2, h2 = w + w % 2, h + h % 2
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{w2}x{h2}", "-r", str(fps),
           "-i", "-", "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", destino]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for q in quadros:
        if q.size != (w2, h2):
            c = Image.new("RGBA", (w2, h2), (0, 0, 0, 0)); c.paste(q, (0, 0)); q = c
        p.stdin.write(q.tobytes())
    p.stdin.close(); p.wait()
    return el.copia(tipo="video", arquivo=destino, w=w2, h=h2)


# ───────────────────────────────── composição ─────────────────────────────────

def linha_em(ps, x, base, espaco=0.26):
    for k, p in enumerate(ps):
        p.x, p.base = x, base
        if k + 1 < len(ps):
            x += p.larg + espaco * min(p.em, ps[k + 1].em)
    return (ps[-1].x + ps[-1].larg - ps[0].x) if ps else 0.0


def larg_linha(ps, espaco=0.26):
    return sum(p.larg for p in ps) + sum(espaco * min(a.em, b.em) for a, b in zip(ps, ps[1:]))


def proxima_base(base, ant, prox, aperto):
    desce = max(tinta(p.face, p.em, p.texto)[1] for p in ant)
    sobe = max(tinta(p.face, p.em, p.texto)[0] for p in prox)
    return base + desce + sobe + aperto * min(min(p.em for p in ant), min(p.em for p in prox))


def bloco(linhas, alinhar="esq", aperto=0.06, espaco=0.26):
    """Empilha linhas de palavras. linhas = [{"ps": [El], "alinha": "esq|centro|dir",
    "recuo": em da linha, "aperto": respiro antes dela (em, pode ser negativo)}]."""
    base = 0.0
    largs = [larg_linha(l["ps"], l.get("espaco", espaco)) for l in linhas]
    total = max(largs)
    for k, l in enumerate(linhas):
        ps = l["ps"]
        if k:
            base = proxima_base(base, linhas[k - 1]["ps"], ps, l.get("aperto", aperto))
        al = l.get("alinha", alinhar)
        x = {"esq": 0.0, "centro": (total - largs[k]) / 2, "dir": total - largs[k]}[al]
        x += l.get("recuo", 0.0) * max(p.em for p in ps)
        linha_em(ps, x, base, l.get("espaco", espaco))
    return [p for l in linhas for p in l["ps"]]


def _caixa_tinta(p, folga):
    sobe, desce = tinta(p.face, p.em, p.texto)
    inclina = 0.12 * p.em if FACES[p.face][2] else 0.0   # itálico passa um pouco da largura
    return (p.x - folga - inclina, p.base - sobe - folga, p.x + p.larg + folga + inclina, p.base + desce + folga)


def separar(linhas, respiro=0.08):
    """Nenhuma palavra encosta em outra (pedido de 2026-10-19: o "8" do 89 encostava no "a"): se a tinta
    de uma linha invade a de qualquer linha de cima, ela e as de baixo descem o necessário + respiro."""
    for k in range(1, len(linhas)):
        cima = [p for l in linhas[:k] for p in l["ps"]]
        for _ in range(20):
            desce = 0.0
            for q in linhas[k]["ps"]:
                folga = respiro * min(q.em, min(p.em for p in cima)) / 2
                a = _caixa_tinta(q, folga)
                for p in cima:
                    b = _caixa_tinta(p, folga)
                    if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
                        desce = max(desce, b[3] - a[1])
            if desce <= 0.5:
                break
            for l in linhas[k:]:
                for q in l["ps"]:
                    q.base += desce


def encaixar(els, W, H, cx, cy, larg_max, alt_max=None):
    """Centraliza o bloco em (cx, cy) e reduz se passar da largura (ou da altura) máxima."""
    esq = min(e.x for e in els if e.tipo == "texto")
    dir_ = max(e.x + e.larg for e in els if e.tipo == "texto")
    topo = min(e.base - metricas(e.face)[2] * e.em for e in els if e.tipo == "texto")
    pe = max(e.base + 0.12 * e.em for e in els if e.tipo == "texto")
    k = min(1.0, larg_max / max(dir_ - esq, 1))
    if alt_max:  # ex.: espaço livre entre o queixo e o logo da camiseta
        k = min(k, alt_max / max(pe - topo, 1))
    mx, my = (esq + dir_) / 2, (topo + pe) / 2
    for e in els:
        if e.tipo == "texto":
            e.x = cx + (e.x - mx) * k
            e.base = cy + (e.base - my) * k
            e.em *= k
        else:
            e.cx = cx + (e.cx - mx) * k
            e.cy = cy + (e.cy - my) * k
            e.w *= k; e.h *= k
            e.raio *= k
    return k


# ─────────────────────────────────── animações ───────────────────────────────────
# Cada animação recebe a lista de elementos de UMA palavra (ou bloco), o instante t em que
# entra e devolve a lista final (pode acrescentar elementos: brilho, caixa, linha...).

def entrar(el, t, dur=0.4, dx=0.0, dy=0.0, opac=0.0, escala=None, rot=None, blur=None, mblur=None, ease=OUT):
    el.inicio = t
    if dx:
        el.key("dx", t, dx, LINEAR).key("dx", t + dur, 0.0, ease)
    if dy:
        el.key("dy", t, dy, LINEAR).key("dy", t + dur, 0.0, ease)
    if opac is not None and opac < 1:
        el.key("opacity", t, opac, LINEAR).key("opacity", t + dur * 0.6, 1.0, ease)
    if escala is not None:
        el.key("scale", t, escala, LINEAR).key("scale", t + dur, 1.0, ease)
    if rot is not None:
        el.key("rotation", t, rot, LINEAR).key("rotation", t + dur, 0.0, ease)
    if blur:
        el.efeito("concat.gaussian-blur", {"radius": 1}, [("radius", t, blur, LINEAR), ("radius", t + dur, 1, ease)])
    if mblur:
        el.efeito("concat.motion-blur", {"length": 2, "angle": 0}, [("length", t, mblur, LINEAR), ("length", t + dur, 2, ease)])
    return el


def _escalonar(els, t, passo, fn):
    for k, e in enumerate(els):
        fn(e, t + k * passo)
    return els


def anim_pop(els, t, ctx):            # reel: aparece em ~3 quadros, quase sem movimento
    return [entrar(e, t, 0.12, escala=0.92, opac=0.0) for e in els]


def anim_abaixo(els, t, ctx):
    return [entrar(e, t, 0.45, dy=-0.03 * ctx.H) for e in els]


def anim_acima(els, t, ctx):
    return [entrar(e, t, 0.45, dy=0.03 * ctx.H) for e in els]


def anim_direita(els, t, ctx):
    return [entrar(e, t, 0.4, dx=-0.07 * ctx.W, blur=12) for e in els]


def anim_esquerda(els, t, ctx):
    return [entrar(e, t, 0.4, dx=0.07 * ctx.W, blur=12) for e in els]


def anim_blur(els, t, ctx):
    return [entrar(e, t, 0.5, escala=1.06, blur=45) for e in els]


def anim_blurup(els, t, ctx):
    return [entrar(e, t, 0.7, dy=0.03 * ctx.H, blur=35) for e in els]


def _escala_bloco(els, t, dur, de, opac=None, ease=OUT):
    """Escala o bloco inteiro em volta do centro dele (cada palavra anda junto)."""
    cs = [e.centro() for e in els]
    bx = (min(e.x for e in els if e.tipo == "texto") + max(e.x + e.larg for e in els if e.tipo == "texto")) / 2 \
        if any(e.tipo == "texto" for e in els) else sum(c[0] for c in cs) / len(cs)
    by = sum(c[1] for c in cs) / len(cs)
    for e, (cx, cy) in zip(els, cs):
        entrar(e, t, dur, escala=de, opac=opac, ease=ease)
        if len(els) > 1:
            e.key("dx", t, (cx - bx) * (de - 1), LINEAR).key("dx", t + dur, 0.0, ease)
            e.key("dy", t, (cy - by) * (de - 1), LINEAR).key("dy", t + dur, 0.0, ease)
    return els


def anim_zoomout(els, t, ctx):
    return _escala_bloco(els, t, 1.2, 1.35, opac=0.3)


def anim_slide(els, t, ctx):
    return [entrar(e, t, 0.5, dx=-0.14 * ctx.W, mblur=60) for e in els]


def anim_palavra(els, t, ctx):
    return _escalonar(els, t, ctx.passo or 0.22, lambda e, tt: entrar(e, tt, 0.3, dy=0.015 * ctx.H))


def _por_letra(els, t, passo, fn):
    out = []
    for e in els:
        ls = letras(e) if e.tipo == "texto" else [e]
        _escalonar(ls, t, passo, fn)
        t += passo * len(ls)
        out += ls
    return out


def anim_fadein(els, t, ctx):
    return _por_letra(els, t, 0.035, lambda e, tt: entrar(e, tt, 0.28))


def anim_surgir(els, t, ctx):
    return _por_letra(els, t, 0.03, lambda e, tt: entrar(e, tt, 0.3, dy=0.025 * ctx.H, blur=12))


def anim_reveal(els, t, ctx):
    return _por_letra(els, t, 0.06, lambda e, tt: entrar(e, tt, 0.35, dy=0.03 * ctx.H))


def anim_girando(els, t, ctx):
    return _por_letra(els, t, 0.05, lambda e, tt: entrar(e, tt, 0.42, rot=-110, escala=0.6, blur=15))


def anim_flicker(els, t, ctx):
    padrao = [(0.0, 0.0), (0.05, 1.0), (0.1, 0.0), (0.2, 0.0), (0.24, 0.6), (0.3, 0.1), (0.36, 1.0), (0.44, 0.25), (0.5, 1.0)]
    for e in els:
        e.inicio = t
        for dt, v in padrao:
            e.key("opacity", t + dt, v, LINEAR)
    return els


def anim_maquina(els, t, ctx, passo=0.045):
    """Digitação: cada letra aparece seca."""
    return _por_letra(els, t, passo, lambda e, tt: setattr(e, "inicio", tt))


def anim_riscado(els, t, ctx):
    """CORTE: digita e depois uma linha vermelha risca a palavra da esquerda para a direita."""
    ls = anim_maquina(els, t, ctx)
    fim_dig = t + 0.045 * len(ls)
    out = list(ls)
    for e in els:
        cx, cy = e.centro()
        lw = e.larg + 0.18 * e.em
        risco = caixa(cx, cy, lw, 0.075 * e.em, "#a3101a", raio=0.02 * e.em)
        _desenhar_linha(risco, fim_dig + 0.05, 0.22)
        out.append(risco)
    return out


def _desenhar_linha(el, t, dur):
    """Linha que cresce da esquerda: escala 0→1 compensando o centro."""
    el.inicio = t
    x0 = -el.w / 2
    for k in range(6):
        f = k / 5
        s = max(f, 0.02)
        el.key("scale", t + dur * f, s, LINEAR)
        el.key("dx", t + dur * f, x0 * (1 - s), LINEAR)
    return el


def anim_flicking(els, t, ctx):
    """FLICKING: contorno vazado aparece e as letras se acendem em ordem aleatória, piscando."""
    out = []
    rng = random.Random(4)
    for e in els:
        vaz = e.copia(cor="#ffffff00", contorno=0.03 * e.em, cor_contorno=e.cor, sombra=False)
        entrar(vaz, t, 0.12)
        out.append(vaz)
        ls = letras(e)
        ordem = list(range(len(ls))); rng.shuffle(ordem)
        for k, i in enumerate(ordem):
            tt = t + 0.25 + k * 0.11
            ls[i].inicio = tt
            for dt, v in [(0, 0.0), (0.03, 1.0), (0.07, 0.2), (0.11, 1.0)]:
                ls[i].key("opacity", tt + dt, v, LINEAR)
        out += ls
    return out


def anim_destacado(els, t, ctx, cor="#12a8d8"):
    """Destacado: letras entram em fade e uma placa colorida com brilho aparece por trás."""
    out = []
    for e in els:
        cx, cy = e.centro()
        w, h = e.larg + 0.5 * e.em, metricas(e.face)[2] * e.em + 0.5 * e.em
        fim_l = t + 0.04 * len(e.texto)
        halo = caixa(cx, cy, w, h, cor, raio=0.18 * e.em)
        halo.efeito("concat.gaussian-blur", {"radius": 30})
        entrar(halo, fim_l, 0.25, escala=0.85)
        halo.key("opacity", fim_l + 0.25, 0.7, LINEAR)
        placa = caixa(cx, cy, w, h, cor, raio=0.18 * e.em)
        entrar(placa, fim_l, 0.22, escala=0.85)
        out += [halo, placa]
        out += _por_letra([e], t, 0.04, lambda x, tt: entrar(x, tt, 0.25))
    return out


def anim_sublinhado(els, t, ctx, cor="#f6e15a"):
    out = []
    for e in els:
        out += _por_letra([e], t, 0.04, lambda x, tt: entrar(x, tt, 0.25))
        cx, _ = e.centro()
        y = e.base + 0.2 * e.em
        fim_l = t + 0.04 * len(e.texto)
        halo = caixa(cx, y, e.larg + 0.1 * e.em, 0.09 * e.em, cor, raio=0.04 * e.em)
        halo.efeito("concat.gaussian-blur", {"radius": 14})
        linha = caixa(cx, y, e.larg + 0.1 * e.em, 0.065 * e.em, cor, raio=0.03 * e.em)
        _desenhar_linha(halo, fim_l + 0.05, 0.3)
        _desenhar_linha(linha, fim_l + 0.05, 0.3)
        out += [halo, linha]
    return out


def anim_moderno(els, t, ctx):
    """MODERNO: letras pulam uma a uma, brancas sobre um degrau cinza (relevo)."""
    out = []
    for e in els:
        for l in letras(e):
            relevo = l.copia(cor="#8d8d8d", x=l.x + 0.045 * l.em, base=l.base + 0.035 * l.em, sombra=True)
            out += [relevo, l]
    pares = [out[i:i + 2] for i in range(0, len(out), 2)]
    for k, (r, l) in enumerate(pares):
        tt = t + k * 0.06
        entrar(r, tt, 0.12, escala=1.25, opac=1.0)
        entrar(l, tt, 0.12, escala=1.25, opac=1.0)
    return out


def anim_cinematic(els, t, ctx, dur=2.6):
    """Cinematic: letras espaçadas e desfocadas se juntam devagar e ganham nitidez."""
    out = []
    for e in els:
        ls = letras(e)
        meio = (len(ls) - 1) / 2
        for k, l in enumerate(ls):
            entrar(l, t, dur, dx=(k - meio) * 0.28 * l.em, blur=28, ease=SUAVE)
            l.keys = [kk for kk in l.keys if kk[0] != "opacity"]
            l.key("opacity", t, 0.0, LINEAR).key("opacity", t + dur * 0.5, 0.75, SUAVE).key("opacity", t + dur, 1.0, SUAVE)
        out += ls
    return out


def anim_corte(els, t, ctx):
    """Corte: a palavra entra seca e é fatiada na horizontal; as metades deslizam e param tortas."""
    out = []
    for e in els:
        png = render_png(e, ctx.arquivo(e, "corte"), preench="branco_cinza")
        im = Image.open(png.arquivo)
        w, h = im.size
        corte_y = int(h / 2 + (png.cy - e.centro()[1]))
        cima, baixo = im.crop((0, 0, w, corte_y)), im.crop((0, corte_y, w, h))
        a = png.copia(arquivo=ctx.arquivo(e, "corte_cima"), w=w, h=corte_y, cy=png.cy - h / 2 + corte_y / 2)
        b = png.copia(arquivo=ctx.arquivo(e, "corte_baixo"), w=w, h=h - corte_y, cy=png.cy - h / 2 + corte_y + (h - corte_y) / 2)
        cima.save(a.arquivo); baixo.save(b.arquivo)
        for metade, lado in ((a, -1), (b, 1)):
            metade.inicio = t
            d = 0.018 * ctx.W * lado
            metade.key("dx", t + 0.3, 0.0, LINEAR).key("dx", t + 0.42, d, OUT).key("dx", t + 0.75, d * 0.35, SUAVE)
        out += [a, b]
    return out


def _video_revelado(e, ctx, preench, cor_flash, dur=1.2, nome="metal"):
    """Vídeo com as letras sendo reveladas da esquerda para a direita, com um clarão na frente
    e uma faixa de reflexo atravessando; depois fica o PNG parado."""
    base = render_png(e, ctx.arquivo(e, nome), preench=preench)
    im = Image.open(base.arquivo).convert("RGBA")
    w, h = im.size
    alfa = np.asarray(im.split()[3], np.float32) / 255
    n = max(2, int(dur * ctx.FPS))
    xs = np.arange(w, dtype=np.float32)[None, :]
    quadros = []
    esq = base.cx - w / 2
    x_ini, x_fim = e.x - esq, e.x + e.larg - esq
    for i in range(n):
        f = i / (n - 1)
        frente = x_ini + (x_fim - x_ini + e.em) * min(1.0, f / 0.6)
        vis = np.clip((frente - xs) / (0.35 * e.em), 0, 1)
        fr, _, _ = render_img(e, preench=preench, faixa=(f * 1.3 - 0.15, 0.08))
        arr = np.asarray(fr, np.float32)
        arr[..., 3] *= vis
        flash = np.exp(-((xs - frente + 0.25 * e.em) / (0.35 * e.em)) ** 2) * (1 - min(1.0, f / 0.7))
        flash = flash * np.ones((h, 1), np.float32)
        cor = np.array([int(cor_flash[k:k + 2], 16) for k in (1, 3, 5)], np.float32)
        glow = np.asarray(Image.fromarray((alfa * flash * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(e.em * 0.12)), np.float32) / 255
        a2 = np.clip(arr[..., 3] / 255 + glow * 0.9, 0, 1)
        rgb = arr[..., :3] * (arr[..., 3:4] / 255) + cor * glow[..., None] * 0.9
        rgb = rgb / np.maximum(a2[..., None], 1e-3)
        quadros.append(Image.fromarray(np.dstack([rgb.clip(0, 255), a2[..., None] * 255]).astype(np.uint8), "RGBA"))
    vid = render_video(base, ctx.arquivo(e, nome, ".mov"), quadros, ctx.FPS)
    vid.cx, vid.cy = base.cx + (vid.w - w) / 2, base.cy + (vid.h - h) / 2
    return vid, base


def anim_ouro(els, t, ctx):
    out = []
    for e in els:
        vid, png = _video_revelado(e, ctx, "ouro", "#fff2a0", nome="ouro")
        vid.inicio, vid.fim = t, t + 1.2
        png.inicio = t + 1.2 - 1 / ctx.FPS
        out += [vid, png]
    return out


def anim_prata(els, t, ctx):
    out = []
    for e in els:
        vid, png = _video_revelado(e, ctx, "prata", "#ffffff", nome="prata")
        vid.inicio, vid.fim = t, t + 1.2
        png.inicio = t + 1.2 - 1 / ctx.FPS
        out += [vid, png]
    return out


def anim_brilho(els, t, ctx, cor="#c45cff"):
    """Brilho: letras roxas com halo, entrando em sequência, e um reflexo que passa por dentro."""
    out = []
    for e in els:
        e.cor = cor
        halo = e.copia(sombra=False)
        halo.efeito("concat.gaussian-blur", {"radius": 12})
        dig = 0.05 * len(e.texto)
        entrar(halo, t + dig * 0.4, dig)
        halo.key("opacity", t + dig * 1.4, 0.85, LINEAR)
        out.append(halo)
        out += _por_letra([e], t, 0.05, lambda x, tt: entrar(x, tt, 0.3))
        # reflexo: vídeo só com a faixa de luz dentro das letras
        m, x0, base = _mascara(e, int(e.em * 0.6))
        w, h = m.size
        alfa = np.asarray(m, np.float32) / 255
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        n = int(1.0 * ctx.FPS)
        quadros = []
        for i in range(n):
            f = i / (n - 1)
            c = x0 + (e.larg + e.em) * f - 0.5 * e.em
            luz = np.exp(-((xx + (yy - h / 2) * 0.25 - c) / (0.12 * e.em)) ** 2) * alfa
            q = np.zeros((h, w, 4), np.uint8); q[..., :3] = 255; q[..., 3] = (luz * 220).astype(np.uint8)
            quadros.append(Image.fromarray(q, "RGBA"))
        vid = render_video(e, ctx.arquivo(e, "brilho", ".mov"), quadros, ctx.FPS)
        vid.cx = e.x - x0 + vid.w / 2
        vid.cy = e.base - (int(e.em * 0.6) + metricas(e.face)[0] * e.em) + vid.h / 2
        vid.inicio, vid.fim = t + 0.05 * len(e.texto) + 0.1, t + 0.05 * len(e.texto) + 1.1
        vid.keys, vid.efeitos = [], []
        out.append(vid)
    return out


ANIMACOES = {
    "pop": anim_pop, "abaixo": anim_abaixo, "acima": anim_acima, "direita": anim_direita, "esquerda": anim_esquerda,
    "blur": anim_blur, "blurup": anim_blurup, "zoomout": anim_zoomout, "slide": anim_slide, "palavra": anim_palavra,
    "fadein": anim_fadein, "surgir": anim_surgir, "reveal": anim_reveal, "girando": anim_girando, "flicker": anim_flicker,
    "maquina": anim_maquina, "riscado": anim_riscado, "flicking": anim_flicking, "destacado": anim_destacado,
    "sublinhado": anim_sublinhado, "moderno": anim_moderno, "cinematic": anim_cinematic, "corte": anim_corte,
    "ouro": anim_ouro, "prata": anim_prata, "brilho": anim_brilho,
}
# Fonte e jeito de cada animação na vitrine (para usar como na referência)
VITRINE = {
    "abaixo": ("pop-black", "Abaixo"), "acima": ("pop-black", "Acima"), "blur": ("pop-black", "Blur"),
    "blurup": ("pop-black", "BlurUp"), "brilho": ("pop-black", "Brilho"), "cinematic": ("pop-black", "Cinematic"),
    "corte": ("pop-black", "Corte"), "riscado": ("pop-black", "CORTE"), "destacado": ("pop-black", "Destacado"),
    "direita": ("pop-black", "Direita"), "esquerda": ("pop-black", "Esquerda"), "fadein": ("pop-black", "Fade in"),
    "flicker": ("pop-black", "Flicker"), "flicking": ("pop-black", "FLICKING"), "girando": ("pop-black", "Girando"),
    "ouro": ("pop-black-it", "GOLD"), "moderno": ("pop-black", "MODERNO"), "palavra": ("pop-bold", "Palavra por palavra"),
    "reveal": ("pop-black", "REVEAL"), "slide": ("pop-black-it", "Slide"), "sublinhado": ("pop-black", "Sublinhado"),
    "prata": ("pop-black-it", "SILVER"), "surgir": ("pop-black", "Surgir"), "zoomout": ("pop-black", "Zoom Out"),
}
TRK_VITRINE = {"moderno": -0.07, "flicking": -0.07, "cinematic": -0.02}


# ─────────────────────────────────── projeto ───────────────────────────────────

class Projeto:
    """Liga a um projeto do Concat (aberto na janela ou não) e cria os elementos nele."""

    def __init__(self, path):
        self.path = os.path.abspath(path)
        self.api = Concat(self.path)
        self.api.sock.settimeout(600)
        try:
            v = self.api.call("project.get", path=self.path)
            self.na_janela = True
        except RuntimeError:
            v = self.api.call("project.open", path=self.path)
            self.na_janela = False
        vid = (v["project"].get("timelines") or [{}])[0].get("video") or v["project"]["video"]
        self.W, self.H = vid["width"], vid["height"]
        self.FPS = vid["rateNum"] / vid.get("rateDen", 1)
        self.passo = None
        self.cache = os.path.join(self.path, "estilos")
        os.makedirs(self.cache, exist_ok=True)
        self._n = 0
        self._fontes = set()

    def arquivo(self, el, nome, ext=".png"):
        self._n += 1
        base = "".join(c for c in el.texto if c.isalnum())[:16] or "x"
        return os.path.join(self.cache, f"{self._n:04d}_{nome}_{base}{ext}")

    def registrar(self, face):
        arq = FACES[face][3]
        if arq in self._fontes:
            return
        fam = FACES[face][0].strip('"')
        self.api.edit({"op": "addFont", "family": fam, "path": _arquivo(face)})
        self._fontes.add(arq)

    # --- trilhas para imagens e vídeos (o texto usa "above") ---
    def _trilha_acima(self, ini, dur):
        tl = timeline(self.api.view())
        fim = ini + dur
        ocup = lambda tid: any(c["trackId"] == tid and c["start"] < fim and ini < c["start"] + c["duration"] for c in tl["clips"])
        chao = max([i + 1 for i, t in enumerate(tl["tracks"]) if ocup(t["id"])] or [0])
        for t in tl["tracks"][chao:]:
            if not ocup(t["id"]):
                return t["id"]
        tl = timeline(self.api.edit({"op": "addTrack"}))
        return tl["tracks"][-1]["id"]

    def _estilo(self, el):
        fam, peso, it = FACES[el.face][:3] if el.tipo == "texto" else ("Poppins", 400, False)
        s = {"content": el.texto, "fontFamily": fam, "fontWeight": float(peso), "italic": it, "fontSize": el.em / self.H,
             "color": el.cor, "align": "center", "shadow": el.sombra, "strokeWidth": el.contorno / self.H,
             "strokeColor": el.cor_contorno, "tracking": el.trk * el.em / self.H, "lineHeight": 1.0,
             "background": el.fundo, "opacity": 1.0, "maxWidth": 0.0, "maxHeight": 0.0}
        return s

    def _offsets(self, el):
        if el.tipo == "texto":
            asc, desc, _ = metricas(el.face)
            ox = (el.x + el.larg / 2 - self.W / 2) / self.W
            oy = (el.base - self.H / 2 - (asc - desc) / 2 * el.em) / self.H
        else:
            ox, oy = (el.cx - self.W / 2) / self.W, (el.cy - self.H / 2) / self.H
        return ox, oy

    def _escala_base(self, el):
        if el.tipo not in ("png", "video"):
            return 1.0
        return el.w / self.W if el.w / el.h >= self.W / self.H else el.h / self.H

    def _caixa_png(self, el):
        """Retângulo arredondado como PNG no tamanho exato (o texto " " com fundo tem altura mínima
        e o stretchY do Concat não vale para títulos)."""
        w, h = max(2, int(round(el.w))), max(2, int(round(el.h)))
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(im).rounded_rectangle((0, 0, w - 1, h - 1), radius=min(el.raio, h / 2, w / 2), fill=el.fundo)
        arq = self.arquivo(el, "caixa")
        im.save(arq)
        el.tipo, el.arquivo, el.w, el.h = "png", arq, w, h

    def criar(self, els):
        """Cria os clipes, na ordem (o último fica por cima), com keys e efeitos."""
        midias = {}
        els = [e for e in els if e.fim - e.inicio > 0.5 / self.FPS]  # frase curta: o que entraria depois do fim não existe
        for el in els:
            if el.tipo == "caixa":
                self._caixa_png(el)
        for el in els:
            if el.tipo == "texto":
                self.registrar(el.face)
        for el in els:
            dur = round(max(el.fim - el.inicio, 1 / self.FPS), 6)
            ini = round(el.inicio * self.FPS) / self.FPS
            if el.tipo in ("texto", "caixa"):
                r = self.api.edit({"op": "addTextClip", "above": True, "start": ini, "duration": dur, "offsetY": 0.0,
                                   "style": self._estilo(el)})
            else:
                if el.arquivo not in midias:
                    self.api.call("media.import", path=self.path, file=el.arquivo)
                    v = self.api.view()
                    midias[el.arquivo] = next(m["id"] for m in v["project"]["media"] if m["path"] == el.arquivo)
                tid = self._trilha_acima(ini, dur)
                r = self.api.edit({"op": "addClip", "mediaId": midias[el.arquivo], "trackId": tid, "start": ini})
                c = next(c for c in timeline(r)["clips"] if c["id"] == r["createdId"])
                if abs(c["duration"] - dur) > 1e-4:  # a imagem entra com 5 s, o vídeo com o tamanho dele
                    self.api.edit({"op": "trimClip", "clipId": c["id"], "edge": "end", "delta": dur - c["duration"], "ripple": False})
            self._aplicar(el, r["createdId"], ini, dur)

    def _aplicar(self, el, cid, ini, dur):
        api = self.api
        ox, oy = self._offsets(el)
        s0 = self._escala_base(el)
        props = {k[0] for k in el.keys}
        cmds = []
        cmds.append({"op": "setClipTransform", "clipId": cid, "offsetX": 0.0 if "dx" in props else ox,
                     "offsetY": 0.0 if "dy" in props else oy, "scale": s0 * el.escala, "rotation": el.rot})
        if el.efeitos:
            cmds.append({"op": "updateClip", "clipId": cid, "patch": {"videoEffects": [
                {"id": e["id"], "params": e["params"], "enabled": True} for e in el.efeitos]}})
        at = lambda t: min(1.0, max(0.0, (t - ini) / dur))
        for prop, t, v, ease in sorted(el.keys, key=lambda k: (k[0], k[1])):
            if prop == "dx":
                cmds.append({"op": "setClipKey", "clipId": cid, "property": "offsetX", "at": at(t), "value": ox + v / self.W, "ease": ease})
            elif prop == "dy":
                cmds.append({"op": "setClipKey", "clipId": cid, "property": "offsetY", "at": at(t), "value": oy + v / self.H, "ease": ease})
            elif prop == "scale":
                cmds.append({"op": "setClipKey", "clipId": cid, "property": "scale", "at": at(t), "value": s0 * v, "ease": ease})
            else:
                cmds.append({"op": "setClipKey", "clipId": cid, "property": prop, "at": at(t), "value": v, "ease": ease})
        for i, e in enumerate(el.efeitos):
            for param, t, v, ease in e["keys"]:
                cmds.append({"op": "setEffectKey", "clipId": cid, "entry": i, "key": param, "at": at(t), "value": v, "ease": ease})
        # saída: some nos 2 últimos quadros, junto com o resto da frase
        if "opacity" not in props or max(k[1] for k in el.keys if k[0] == "opacity") < ini + dur - 2 / self.FPS:
            if dur > 3 / self.FPS:
                cmds.append({"op": "setClipKey", "clipId": cid, "property": "opacity", "at": 1 - (2 / self.FPS) / dur, "value": 1.0, "ease": LINEAR})
                cmds.append({"op": "setClipKey", "clipId": cid, "property": "opacity", "at": 1.0, "value": 0.0, "ease": LINEAR})
        api.batch(cmds)

    def fim_video(self):
        """Onde acaba o último clipe de vídeo da timeline (as legendas não passam disso)."""
        tl = timeline(self.api.view())
        return max((c["start"] + c["duration"] for c in tl["clips"] if c["kind"] == "video"), default=1e9)

    def limpar_midias(self):
        """Tira da biblioteca as mídias geradas em estilos/ que nenhum clipe usa (sobras de rodadas
        anteriores; se o arquivo foi apagado, o Concat avisa "Missing Media" ao abrir)."""
        v = self.api.view()
        usados = {c.get("mediaId") for t in v["project"]["timelines"] for c in t["clips"]}
        for m in v["project"]["media"]:
            if m["id"] not in usados and os.path.realpath(m["path"]).startswith(os.path.realpath(self.cache) + os.sep):
                self.api.edit({"op": "removeMedia", "mediaId": m["id"]})

    def salvar(self):
        self.limpar_midias()
        self.api.call("project.save", path=self.path)

    def fechar(self):
        if not self.na_janela:
            self.api.call("project.close", path=self.path, save=True)


# ──────────────────────────────── composições ────────────────────────────────
# Uma frase é uma lista de linhas; cada linha tem um tamanho e as palavras dela. Marcação no texto:
#   *palavra*        -> destaque em Scholar Itálico (cor de destaque: amarelo ou branco), grande e
#                       sobreposto, no lugar da cursiva fina rosa da referência
#   palavra{#22305e} -> palavra numa cor própria (ex.: "negra" em azul-noite)
# Tamanhos (em, fração da altura do quadro) medidos no reel DeaL7FgRV4C.

TAM = {"p": 0.030, "m": 0.042, "g": 0.062, "gg": 0.080, "script": 0.115}
FACE_REEL = {"p": "jak", "m": "jak-bold", "g": "jak-bold", "gg": "jak-xbold"}
FACE_POP = {"p": "pop-semibold", "m": "pop-bold", "g": "pop-black", "gg": "pop-black"}
TRK_REEL = -0.02

# Presets do reel: (tamanho, alinhamento, recuo em em, aperto antes da linha)
PRESETS_REEL = {
    "linha": [("p", "centro", 0, 0)],                                               # "E a regra que"
    "linha2": [("p", "centro", 0, 0), ("p", "centro", 0, 0.06)],                    # linha longa em duas curtas
    "grande": [("g", "centro", 0, 0)],                                              # "brutal.", "mais desejáveis"
    "escada": [("p", "esq", 0, 0), ("g", "esq", 0.12, 0.02), ("g", "esq", 0.0, 0.0)],   # A regra da / ovelha / negra
    "sanduiche": [("g", "esq", 0, 0), ("p", "esq", 0.35, 0.02), ("m", "dir", 0, 0.0)],  # padrões / do seu / mercado
    "numero": [("p", "centro", -2.6, 0), ("script", "centro", 0.25, -0.62), ("p", "dir", 0, -0.32), ("g", "centro", 0, -0.02)],
    "dupla": [("m", "esq", 0, 0), ("m", "esq", 0.25, 0.10)],                       # geradoras / de receita
    "quatro": [("p", "centro", 0, 0), ("g", "centro", 0, 0.0), ("p", "centro", 0.4, 0.04), ("gg", "centro", 0, 0.02)],
    "chave": [("m", "esq", 0, 0), ("m", "esq", 0.15, -0.02), ("script", "dir", 0, -0.18)],  # inevitavelmente, / gera / *compra*
}


def _token(tok, tam, destaque, faces=FACE_REEL):
    """Uma palavra marcada -> El (tamanho em em ainda relativo à altura)."""
    cor = None
    if "{" in tok and tok.endswith("}"):
        tok, cor = tok[:-1].split("{", 1)
    if "^" in tok:                      # palavra^g: tamanho próprio dentro da linha
        tok, tam = tok.rsplit("^", 1)
    if tok.startswith("*") and tok.endswith("*") and len(tok) > 2:
        return palavra(tok[1:-1], "scholar-it", TAM["script"], cor or destaque, trk=0.0, papel="script")
    if tam == "script":
        tam = "g"
    return palavra(tok, faces[tam], TAM[tam], cor or BRANCO, trk=TRK_REEL if faces is FACE_REEL else -0.03, papel=tam)


def compor_reel(preset, linhas, W, H, centro=(0.5, 0.6), destaque=BRANCO, larg_max=0.86, familia="jak", alt_max=None):
    """linhas: textos de cada linha, com a marcação acima. Devolve os Els posicionados no quadro."""
    forma = PRESETS_REEL[preset]
    if len(linhas) > len(forma):
        forma = forma + [forma[-1]] * (len(linhas) - len(forma))
    ls = []
    for texto, (tam, al, recuo, aperto) in zip(linhas, forma):
        ps = [_token(t, tam, destaque, FACE_POP if familia == "pop" else FACE_REEL) for t in texto.split()]
        for p in ps:
            p.em *= H
        ls.append({"ps": ps, "alinha": al, "recuo": recuo, "aperto": aperto})
    els = bloco(ls, espaco=0.24)
    separar(ls)
    encaixar(els, W, H, centro[0] * W, centro[1] * H, larg_max * W, alt_max * H if alt_max else None)
    return els


# Modelos das imagens de referência: cada um é (linhas de palavras com papel, alinhamentos).
MODELOS = {
    # Copie  e  cole / MODELOS / PRONTOS (verde neon)
    "modelos": {"linhas": [
        [("Copie", "pop-medium-it", 0.030, "espalha"), ("e", "pop-medium-it", 0.022, "espalha"), ("cole", "pop-medium-it", 0.030, "espalha")],
        [("MODELOS", "mont-black", 0.085, "degrade")],
        [("PRONTOS", "pop-black", 0.040, "neon")]],
        "alinha": ["espalha", "centro", "centro"], "aperto": [0, -0.08, -0.12]},
    # Quebre o / PADRÃO / com DINAMISMO (placa verde)
    "padrao": {"linhas": [
        [("Quebre", "pop-medium-it", 0.030, ""), ("o", "pop-medium-it", 0.030, "")],
        [("PADRÃO", "mont-black", 0.085, "degrade")],
        [("com", "pop-medium-it", 0.026, ""), ("DINAMISMO", "pop-black", 0.034, "placa")]],
        "alinha": ["esq", "centro", "dir"], "aperto": [0, -0.06, 0.05]},
    # Textos / CHAMATIVOS (dourado) / com ESTILO
    "chamativos": {"linhas": [
        [("Textos", "playfair-it", 0.042, "")],
        [("CHAMATIVOS", "playfair-black", 0.070, "ouro")],
        [("com", "pop-medium-it", 0.026, ""), ("ESTILO", "playfair-black", 0.048, "ouro")]],
        "alinha": ["esq", "centro", "dir"], "aperto": [0, 0.04, -0.08]},
    # Textos / elegantes (dourado itálico) / que IMPRESSIONAM (sublinhado)
    "elegantes": {"linhas": [
        [("Textos", "playfair-bold", 0.042, "")],
        [("elegantes", "playfair-xbold-it", 0.082, "ouro")],
        [("que", "pop-medium-it", 0.026, ""), ("IMPRESSIONAM", "jak-bold", 0.032, "ouro_sub")]],
        "alinha": ["esq", "centro", "dir"], "aperto": [0, -0.12, -0.02]},
}
OURO_SUAVE = [(0.0, "#fff0b5"), (0.45, "#f0c25a"), (0.7, "#d39a2e"), (1.0, "#a8701a")]
VERDE_NEON, VERDE_PLACA, CIANO = "#4cff3f", "#36c43a", "#12a8d8"


def compor_modelo(nome, W, H, textos=None, centro=(0.5, 0.6), larg_max=0.86):
    """Monta um dos MODELOS. textos troca as palavras mantendo os papéis: lista de linhas, cada
    linha uma lista de palavras com o mesmo número de itens do modelo."""
    m = MODELOS[nome]
    ls = []
    for k, linha in enumerate(m["linhas"]):
        novos = textos[k] if textos else [w for w, *_ in linha]
        ps = []
        for (w0, face, tam, papel), w in zip(linha, novos):
            trk = -0.02 if face.startswith(("mont", "pop")) else 0.0
            ps.append(palavra(w, face, tam * H, BRANCO, trk=trk, papel=papel))
        al = m["alinha"][k]
        ls.append({"ps": ps, "alinha": "centro" if al == "espalha" else al, "aperto": m["aperto"][k], "espalha": al == "espalha"})
    els = bloco(ls, espaco=0.26)
    # "Copie   e   cole": espalhadas na largura da linha de baixo
    for k, l in enumerate(ls):
        if l["espalha"] and k + 1 < len(ls) and len(l["ps"]) > 1:
            esq = min(p.x for p in ls[k + 1]["ps"]); dir_ = max(p.x + p.larg for p in ls[k + 1]["ps"])
            ps = l["ps"]; livre = (dir_ - esq) - sum(p.larg for p in ps)
            x = esq
            for p in ps:
                p.x = x; x += p.larg + livre / (len(ps) - 1)
            if len(ps) == 3:  # o "e" do meio fica um pouco mais baixo, como na referência
                ps[1].base += 0.25 * ps[0].em
    encaixar(els, W, H, centro[0] * W, centro[1] * H, larg_max * W)
    return els


def materializar(els, ctx):
    """Troca os papéis que o Concat não desenha por PNG e acrescenta brilhos/placas.
    Devolve grupos [(palavra_principal, [elementos na ordem de baixo para cima])]."""
    grupos = []
    for e in els:
        if e.papel == "degrade":
            grupos.append((e, [render_png(e, ctx.arquivo(e, "degrade"), preench="branco_cinza")]))
        elif e.papel in ("ouro", "ouro_sub"):
            g = [render_png(e, ctx.arquivo(e, "ouro"), preench=OURO_SUAVE, sombra=True)]
            if e.papel == "ouro_sub":
                cx, _ = e.centro()
                g.append(caixa(cx, e.base + 0.22 * e.em, e.larg, 0.07 * e.em, "#e9b949", raio=0.03 * e.em))
            grupos.append((e, g))
        elif e.papel == "neon":
            e.cor = VERDE_NEON
            halo = e.copia(sombra=False)
            halo.efeito("concat.gaussian-blur", {"radius": 18})
            grupos.append((e, [halo, e]))
        elif e.papel == "placa":
            cx, cy = e.centro()
            placa = caixa(cx, cy, e.larg + 0.45 * e.em, metricas(e.face)[2] * e.em + 0.45 * e.em, VERDE_PLACA, raio=0.16 * e.em)
            grupos.append((e, [placa, e]))
        elif e.tipo == "texto" and _escura(e.cor):
            # cor escura (ex.: "negra" em azul-noite): halo claro para não sumir em fundo escuro
            halo = e.copia(cor="#ffffff", sombra=False)
            halo.efeito("concat.gaussian-blur", {"radius": 16})
            grupos.append((e, [halo, e]))
        else:
            grupos.append((e, [e]))
    return grupos


def _escura(cor):
    c = cor.lstrip("#")[:6]
    r, g, b = (int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b < 0.35


def animar_frase(grupos, tempos, anim, ctx, fim):
    """Cada palavra entra no seu tempo com a animação escolhida; tudo sai junto em `fim`."""
    out = []
    for (principal, els), t in zip(grupos, tempos):
        fn = ANIMACOES[anim]
        if anim in ("destacado", "sublinhado", "riscado", "brilho", "ouro", "prata", "corte", "flicking", "moderno"):
            novos = fn([e for e in els if e is principal] or els[-1:], t, ctx)
            novos = [e for e in els if e is not principal] + novos
            for e in novos:
                if not e.keys and e.inicio == 0:
                    entrar(e, t, 0.2)
        else:
            novos = []
            for e in els:
                novos += fn([e], t, ctx)
        out += novos
    for e in out:
        e.fim = min(e.fim, fim) if e.fim > e.inicio else fim
    # o destaque em script fica atrás das palavras pequenas (como no reel): criado antes, camada de baixo
    return [e for e in out if e.papel == "script"] + [e for e in out if e.papel != "script"]
