#!/usr/bin/env python3
"""Acha os cortes "assados" num vídeo que já chega cortado e acelerado (um arquivo só) e, se pedir,
divide o clipe do projeto neles - para o zoom seco e o B-roll trocarem nas emendas.

Uso:
  detectar_cortes.py <video>                      lista os cortes (segundos)
  detectar_cortes.py <video> --dividir <projeto>  também move o vídeo para T1 e divide o clipe nos cortes

Como acha: diferença média entre quadros seguidos (em 216x384, cinza); um corte é um pico de pelo menos
3x a mediana dos 30 quadros em volta (e +2 de folga). Num talking head isso pega as emendas de jump cut.
"""
import json
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from concat_api import Concat, timeline  # noqa: E402

W, H = 216, 384


def cortes(video):
    info = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                           "-of", "csv=p=0", video], capture_output=True, text=True).stdout.strip()
    num, den = (info.split("/") + ["1"])[:2]
    fps = float(num) / float(den)
    bruto = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vf", f"scale={W}:{H},format=gray", "-f", "rawvideo", "-"],
                           capture_output=True, check=True).stdout
    a = np.frombuffer(bruto, np.uint8).reshape(-1, H, W).astype(np.float32)
    d = np.abs(np.diff(a, axis=0)).mean(axis=(1, 2))
    med = np.array([np.median(d[max(0, i - 15):i + 15]) for i in range(len(d))])
    picos = [i + 1 for i in range(len(d)) if d[i] > max(3 * med[i], med[i] + 2.0)
             and (i == 0 or d[i] > d[i - 1]) and (i + 1 >= len(d) or d[i] >= d[i + 1])]
    return fps, picos


def dividir(projeto, fps, quadros):
    api = Concat(projeto); api.sock.settimeout(300)
    try:
        api.call("project.get", path=projeto)
    except RuntimeError:
        api.call("project.open", path=projeto)
    tl = timeline(api.view())
    vs = [c for c in tl["clips"] if c["kind"] == "video"]
    if len(vs) != 1:
        sys.exit(f"esperava 1 clipe de vídeo, achei {len(vs)}: o vídeo já foi dividido?")
    api.edit({"op": "moveClips", "moves": [{"clipId": vs[0]["id"], "start": 0.0, "trackId": tl["tracks"][0]["id"]}]})
    for q in quadros:
        t = q / fps
        dentro = [c for c in timeline(api.view())["clips"]
                  if c["kind"] == "video" and c["start"] + 1e-6 < t < c["start"] + c["duration"] - 1e-6]
        if dentro:
            api.edit({"op": "splitClips", "clipIds": [dentro[0]["id"]], "time": t})
    api.call("project.save", path=projeto)
    n = len([c for c in timeline(api.view())["clips"] if c["kind"] == "video"])
    print(f"vídeo em T1, dividido em {n} trechos; projeto salvo")


def main():
    video = sys.argv[1]
    fps, qs = cortes(video)
    print(json.dumps({"fps": fps, "cortes_s": [round(q / fps, 3) for q in qs], "cortes_quadro": qs}))
    if "--dividir" in sys.argv:
        dividir(sys.argv[sys.argv.index("--dividir") + 1], fps, qs)


if __name__ == "__main__":
    main()
