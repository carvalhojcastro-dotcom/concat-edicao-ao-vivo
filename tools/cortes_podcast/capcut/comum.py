"""Coisas comuns aos cortes de podcast montados no CapCut (processo do Podcast 12 do Dr. Rafael, 2026-11-10).

Pasta de trabalho de um episódio (W):
  config.json   {"fonte": "<vídeo>", "velocidade": 1.1,
                 "pessoas": {"esq": {"nome": "rafael", "voz": "M"}, "dir": {"nome": "ivy", "voz": "F"}},
                 "convidado": "convidado", "foco": "rafael"}
                 (esq/dir = quem fica à esquerda/direita no plano dos apresentadores)
  audio.wav     áudio 16 kHz mono do episódio;  turbo.json / rotulado.json  transcrição do episódio
  cortes.txt    "<id> <in> <out>" em segundos do bruto, um por linha
  c<id>/        um corte: analise.json, plano.json, tl.wav, words_tl.json, words_med.json, correcoes_tl.json,
                words.json, words_leg.json, blocos.json
"""
import json, os, sys
import numpy as np

TOOLS = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
PY = os.path.join(TOOLS, ".venv", "bin", "python")
FPS = 30


def config(W):
    return json.load(open(os.path.join(W, "config.json"), encoding="utf-8"))


def cortes(W):
    out = []
    for l in open(os.path.join(W, "cortes.txt")):
        if l.strip() and not l.startswith("#"):
            c, s, e = l.split()[:3]
            out.append((c, float(s), float(e)))
    return out


def dur_timeline(S, E, vel):
    return (E - S) / vel


def rms_db(wav, a, b, jan=0.05):
    import wave
    w = wave.open(wav)
    sr = w.getframerate()
    w.setpos(int(a * sr))
    x = np.frombuffer(w.readframes(int((b - a) * sr)), np.int16).astype(np.float32) / 32768
    h = int(sr * jan)
    n = len(x) // h
    return 20 * np.log10(np.sqrt((x[:n * h].reshape(n, h) ** 2).mean(1)) + 1e-9)
