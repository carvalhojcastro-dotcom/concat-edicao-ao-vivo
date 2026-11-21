#!/usr/bin/env python3
"""Gráfico de barras horizontais da marca Simples Medicina por cima do peito do Dr. Leonardo (sem dividir a tela, sem
arco): cartão off-white com o rótulo, o título com o fio coral e uma barra verde por item, que cresce quando ele fala o
número, com o nome do item dentro da barra e o valor ao lado. Sai com alfa (ProRes 4444), só a faixa do cartão.

Pedido de 2026-11-10 (vídeo 2, 38-55 s): "um gráfico de barras ... mostrando cada efeito colateral ... animação dessa
barra crescendo ... dentro da própria barra, você escreve o nome do efeito ... identidade visual do Dr. Leonardo ... não
quero que você divida a tela ... nem crie uma nova transição ... em cima da barriga/peitoral do doutor ... pode fazer
barras horizontais".

Uso: simples_barras_sobre.py <plano.json> <saída.mov> [--quadros=t1,t2,... <pasta>]
Plano: {"dur": 17.0, "rotulo": "...", "icone": "users", "titulo": "...", "chave": "leves", "max": 30,
        "itens": [{"nome": "Enjoo", "de": 20, "ate": 30, "valor": "20 a 30", "em": 0.6}, ...]}
  "em": segundos desde o começo do cartão em que a barra começa a crescer (a fala do número).
O cartão é desenhado numa faixa 1080x600 (renderizada em 2x); no CapCut ela entra com escala 1 e o centro em y=Y_CENTRO.
"""
import json
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import simples_cenas as SC  # noqa: E402
from simples_cenas import KM, P, MAR, VER, OFF, CINZA, text, icon, tw, font, fio, eo5, eio, lin, ei, skia  # noqa: E402

W, H, ESC, FPS = 1080, 600, 2, 30
Y_CENTRO = 1420          # centro da faixa no quadro 1080x1920 (o cartão começa ~30 px abaixo da linha das legendas)
X0, X1 = 72, 1008        # cartão
BX, BW, BH = 112, 600, 62   # barras: começo, largura do máximo, altura


def desenhar(c, t, p):
    T = p["dur"]
    entra = eo5(lin(t, 0.0, 0.5))
    sai = ei(lin(t, T - 0.45, 0.45))
    a = entra * (1 - sai)
    if a <= 0.003:
        return
    c.save()
    c.translate(0, (1 - entra) * 30 + sai * 20)
    c.saveLayerAlpha(None, int(255 * a))
    # sombra suave e cartão off-white
    sombra = skia.Paint(AntiAlias=True, Color=skia.Color4f(0, 0, 0, 0.16),
                        MaskFilter=skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 16))
    rr = skia.RRect.MakeRectXY(skia.Rect(X0, 34, X1, 566), 28, 28)
    c.drawRRect(rr.makeOffset(0, 8), sombra)
    c.drawRRect(rr, P(OFF))
    # rótulo (ícone Lucide verde + caixa alta) e título com o fio coral na palavra-chave
    icon(c, p.get("icone", "users"), BX, 70, 30, VER, 1.0, 2.0)
    text(c, p["rotulo"].upper(), BX + 44, 94, ("Inter-SemiBold", 23), VER, 1.0, tracking=0.14)
    tf = ("InterDisplay-SemiBold", 40)
    text(c, p["titulo"], BX, 150, tf, MAR, 1.0)
    chave = p.get("chave")
    if chave and chave in p["titulo"]:
        f = font(*tf)
        xk = BX + tw(p["titulo"].split(chave, 1)[0], f)
        fio(c, xk, xk + tw(chave, f), 162, eio(lin(t, 0.5, 0.9)), ei(lin(t, T - 0.6, 0.45)), 5)
    # barras
    vmax = p.get("max", 30)
    px = lambda v: BW * v / vmax  # noqa: E731
    for i, it in enumerate(p["itens"]):
        y = 196 + i * 88
        trilho = skia.RRect.MakeRectXY(skia.Rect(BX, y, BX + BW, y + BH), 14, 14)
        c.drawRRect(trilho, P(CINZA, 0.55))
        k = eio(lin(t, it["em"], 0.85))
        if k <= 0:
            continue
        w_de = max(28, px(it["de"]) * k)
        if it.get("ate", it["de"]) > it["de"]:       # faixa (ex.: 20 a 30): o resto num verde mais claro
            w_ate = max(w_de, px(it["ate"]) * k)
            c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(BX, y, BX + w_ate, y + BH), 14, 14), P(VER, 0.42))
        c.drawRRect(skia.RRect.MakeRectXY(skia.Rect(BX, y, BX + w_de, y + BH), 14, 14), P(VER))
        fl = ("Inter-SemiBold", 30)
        lw = tw(it["nome"], font(*fl))
        al = max(0.0, min(1.0, (w_de - lw - 44) / 40))
        if al > 0:
            text(c, it["nome"], BX + 22, y + BH / 2 + 11, fl, OFF, al)
        av = max(0.0, min(1.0, (k - 0.75) / 0.25))
        if av > 0:
            fim = BX + px(it.get("ate", it["de"])) * k
            text(c, it["valor"], fim + 18, y + BH / 2 + 11, ("Inter-SemiBold", 30), MAR, av)
    c.restore()
    c.restore()


def quadro(p, t):
    def d(c, tt):
        c.scale(ESC, ESC)
        desenhar(c, tt, p)
    rgba = KM.render_rgba(d, t, W * ESC, H * ESC, sub=2)
    a = rgba[..., 3:4]
    rgb = np.where(a > 1e-4, rgba[..., :3] / np.maximum(a, 1e-4), 0)
    return np.clip(np.concatenate([rgb, a], 2) * 255, 0, 255).astype(np.uint8)


def main():
    args = [x for x in sys.argv[1:] if not x.startswith("--")]
    p = json.load(open(args[0], encoding="utf-8"))
    q = next((x.split("=", 1)[1] for x in sys.argv if x.startswith("--quadros=")), None)
    if q:
        from PIL import Image
        for t in [float(x) for x in q.split(",")]:
            Image.fromarray(quadro(p, t)).save(os.path.join(args[1], f"barras_{t:05.2f}.png"))
        return
    n = int(round(p["dur"] * FPS))
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W * ESC}x{H * ESC}",
                             "-r", str(FPS), "-i", "-", "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le",
                             "-alpha_bits", "16", "-vendor", "apl0", args[1]], stdin=subprocess.PIPE)
    for f in range(n):
        proc.stdin.write(quadro(p, f / FPS).tobytes())
    proc.stdin.close()
    proc.wait()
    print(args[1], n, "quadros")


if __name__ == "__main__":
    main()
