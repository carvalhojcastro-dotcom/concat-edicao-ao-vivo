#!/usr/bin/env python3
"""Acha os cortes que já existem num vídeo editado fora do Concat (ex.: um corte feito pelo usuário no
CapCut), para o zoom trocar exatamente neles.

Com --bruto=<vídeo original>: o áudio de cada trecho do editado é achado no bruto (correlação); dentro
de um take a distância editado→bruto é constante e num corte ela salta. É o jeito confiável (gesto
rápido de mão não engana). O quadro exato do corte é o de maior diferença de imagem perto do salto.
Sem o bruto: só a diferença de imagem na faixa da cabeça (picos bem acima dos vizinhos).

Uso: achar_cortes.py <video> [--bruto=<original>] [--saida=cortes.json]
  imprime e grava os tempos (s, no vídeo editado) do 1º quadro depois de cada corte.
"""
import json
import subprocess
import sys

import numpy as np

W, H = 72, 128
SR = 8000


def quadros(video):
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vf", f"scale={W}:{H},format=gray", "-f", "rawvideo", "-"],
                       capture_output=True, check=True).stdout
    fps = eval(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                               "-of", "csv=p=0", video], capture_output=True, text=True).stdout.strip())
    q = np.frombuffer(p, np.uint8).reshape(-1, H, W).astype(np.float32)
    return np.abs(np.diff(q[:, 5:58], axis=0)).mean(axis=(1, 2)), fps   # faixa da cabeça: mão não conta


def audio(video):
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                       capture_output=True, check=True).stdout
    return np.frombuffer(p, np.float32)


def deslocamentos(ed, br, jan=0.5, passo=0.1):
    """Para cada janela do editado: (tempo, deslocamento bruto-editado em s, confiança)."""
    n, h = int(jan * SR), int(passo * SR)
    L = 1 << int(np.ceil(np.log2(len(br) + n)))
    BR = np.fft.rfft(br, L)
    br2 = np.concatenate([[0.0], np.cumsum(br.astype(np.float64) ** 2)])
    out = []
    for a in range(0, len(ed) - n, h):
        w = ed[a:a + n] - ed[a:a + n].mean()
        e = np.sqrt((w ** 2).sum())
        if e < 1e-3:
            out.append((a / SR, None, 0.0)); continue
        c = np.fft.irfft(BR * np.conj(np.fft.rfft(w, L)), L)[:len(br) - n]
        en = np.sqrt(br2[n:n + len(c)] - br2[:len(c)]) + 1e-9
        r = c / (en * e)
        k = int(np.argmax(r))
        out.append((a / SR, (k - a) / SR, float(r[k])))
    return out


def com_bruto(video, bruto, d, fps):
    ds = deslocamentos(audio(video), audio(bruto))
    bons = [(t, o) for t, o, c in ds if o is not None and c > 0.6]
    cortes, i = [], 0
    while i + 1 < len(bons):
        (t0, o0), (t1, o1) = bons[i], bons[i + 1]
        if abs(o1 - o0) > 0.08:
            # confirma: as próximas janelas ficam no novo deslocamento (não é eco de uma janela só)
            seg = [o for _, o in bons[i + 1:i + 4]]
            if sum(abs(o - o1) < 0.04 for o in seg) >= min(2, len(seg)):
                a, b = int(t0 * fps), int((t1 + 0.5) * fps) + 1   # o corte cai entre as duas janelas
                k = a + int(np.argmax(d[a:b])) if b > a else a
                cortes.append(round((k + 1) / fps, 3))
        i += 1
    return sorted(set(cortes))


def sem_bruto(d, fps, fator=6.0, minimo=5.0):
    out = []
    for i in range(len(d)):
        viz = np.concatenate([d[max(0, i - 8):max(0, i - 1)], d[i + 2:i + 9]])
        base = np.median(viz) if len(viz) else 0.0
        if d[i] >= minimo and d[i] > fator * max(base, 0.6) and d[i] == d[max(0, i - 1):i + 2].max():
            out.append(round((i + 1) / fps, 3))
    return out


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opc = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
    d, fps = quadros(args[0])
    c = com_bruto(args[0], opc["bruto"], d, fps) if "bruto" in opc else sem_bruto(d, fps)
    # dois cortes a menos de 0,3 s são o mesmo
    c = [t for k, t in enumerate(c) if not k or t - c[k - 1] > 0.3]
    if "saida" in opc:
        json.dump(c, open(opc["saida"], "w"))
    print(f"{len(c)} cortes: " + " ".join(f"{t:.2f}" for t in c))
