#!/usr/bin/env python3
"""Folha de revisão de um vídeo montado para o CapCut, sem abrir o CapCut: em cada tempo pedido, o quadro do
bruto com a escala e a posição do pedaço (ou o B-roll em vídeo, se houver um ali) e as legendas IG por cima,
desenhadas com as métricas do CapCut (capcut_legendas_ig.desenhar).

Serve para conferir rosto centrado nos zooms, legenda abaixo do rosto e fora dos motions, e os motions.
Uso: capcut_previa.py <plano.json do capcut_montar> <words da timeline> <blocos.json> <vídeo bruto> <saida.jpg> "<t1,t2,...>"
"""
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import capcut_legendas_ig as ig  # noqa: E402

VISTA = "/Library/Containers/com.lemon.lvoverseas/Data"


def main():
    plano_arq, words_arq, blocos_arq, video, saida, tempos = sys.argv[1:7]
    plano = json.load(open(plano_arq, encoding="utf-8"))
    P = plano["pedacos"]
    total = P[-1]["ini"] + P[-1]["dur"]
    itens = ig.montar(json.load(open(words_arq, encoding="utf-8")), json.load(open(blocos_arq, encoding="utf-8")))
    for it in itens:
        it["fim"] = min(it["fim"], total - 2 / 30)
    png = os.path.join(tempfile.mkdtemp(), "q.png")
    quadros = []
    for t in (float(x) for x in tempos.split(",")):
        br = next((b for b in plano.get("broll", []) if b["inicio"] <= t < b["fim"] and b.get("tipo") == "video"), None)
        if br:
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t - br['inicio']:.3f}", "-i", br["arquivo"].replace(VISTA, ""),
                            "-frames:v", "1", png], check=True)
            img = Image.open(png).convert("RGB").resize((1080, 1920))
        else:
            p = next(p for p in P if p["ini"] <= t < p["ini"] + p["dur"])
            vel = p.get("velocidade", plano.get("velocidade", 1.0))
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{p['fonte'] + (t - p['ini']) * vel:.3f}", "-i", video,
                            "-frames:v", "1", "-vf", "scale=1080:1920", png], check=True)
            s = p["escala"]
            grande = Image.open(png).convert("RGB").resize((int(1080 * s), int(1920 * s)))
            img = Image.new("RGB", (1080, 1920))
            img.paste(grande, (int((1080 - 1080 * s) / 2 + p.get("tx", 0) * 540), int((1920 - 1920 * s) / 2 - p.get("ty", 0) * 960)))
        q = Image.fromarray(np.asarray(ig.desenhar(itens, t, np.array(img)))).convert("RGB").resize((270, 480))
        quadros.append(q)
    col = 6
    folha = Image.new("RGB", (270 * col, 480 * ((len(quadros) + col - 1) // col)))
    for i, q in enumerate(quadros):
        folha.paste(q, (270 * (i % col), 480 * (i // col)))
    folha.save(saida, quality=88)
    print(saida)


if __name__ == "__main__":
    main()
