#!/usr/bin/env python3
"""Efeitos sonoros de motion graphics a partir de um mapa (JSON): cada elemento que entra na tela vira um
evento (camadas de sfx_sintese.py misturadas num WAV), na pasta que o CapCut lê, e o plano para o
capcut_sfx.py. Aprovado no vídeo 24/11 da Sabrina (2026-10-30); a skill sfx-motion diz como montar o mapa.

Mapa:
{"trilha": "SFX motions (Concat)", "ganho_db": 2,
 "cenas": [{"nome": "otica", "inicio": 8.9333, "dur": 3.967, "entrada": false, "saida": true,
            "eventos": [{"nome": "titulo", "camadas": [
                {"t": 0.04, "som": "grave", "f0": 90, "f1": 44, "db_pico": -25, "decai": 0.18},
                {"t": 0.05, "som": "letras", "texto": "ÓTICA TÉCNICA", "passo": 0.03, "sem": 11}]}]}]}
  t: segundos dentro da cena (o quadro em que o elemento aparece); "som" é uma função de sfx_sintese.py e o
  resto da camada são os argumentos dela. Especiais: "letras" (texto, passo, t0, db_pico, sem) faz um tique
  por letra; "sobe" aceita "pouso": [camadas] (o som em que o inchaço pousa). "entrada": true põe um sopro
  que chega no início da cena (quando não há whoosh); "saida" (padrão true), um sopro curto que desce no fim;
  as duas aceitam um dict que muda o padrão (ex.: {"sem": 13, "db_pico": -35}).
Uso: sfx_motion.py <mapa.json> <pasta dos WAV> <saida plano.json> [--sufixo=v2]
  Imprime o pico e o volume momentâneo dos efeitos em cada cena (alvo: picos -20 a -27 dBFS, -35 a -42 LUFS
  com a voz em ~-19 LUFS; acima disso, baixe "ganho_db").
"""
import json
import os
import sys

import numpy as np
import scipy.signal as sinal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sfx_sintese as s  # noqa: E402

VISTA = (os.path.expanduser("~/Movies"), os.path.expanduser("~/Library/Containers/com.lemon.lvoverseas/Data/Movies"))


def camada(c):
    c = dict(c)
    t, som = c.pop("t"), c.pop("som")
    if som == "letras":
        t0, passo = c.pop("t0", 0.0), c.pop("passo", 0.03)
        ts = [t0 + i * passo + 0.05 for i, ch in enumerate(c.pop("texto")) if ch != " "]
        return t, s.rolo(ts, db_pico=c.pop("db_pico", -31), sem=c.pop("sem", None))
    if som == "sobe" and "pouso" in c:
        c["pouso"] = s.mix([camada(p) for p in c["pouso"]])
    return t, getattr(s, som)(**c)


def lufs_momentaneo(x):
    """Máximo do volume momentâneo (400 ms), com uma ponderação K aproximada."""
    b, a = sinal.butter(2, 60, "highpass", fs=s.SR)
    alto = sinal.sosfilt(sinal.butter(2, 1500, "highpass", fs=s.SR, output="sos"), x, axis=0)
    y = sinal.lfilter(b, a, x * 0.5 + alto * 0.5, axis=0)
    h, passo = int(0.4 * s.SR), int(0.1 * s.SR)
    ms = [(y[i:i + h] ** 2).mean(0).sum() for i in range(0, max(1, len(y) - h), passo)] or [(y ** 2).mean(0).sum()]
    return -0.691 + 10 * np.log10(max(ms) + 1e-12)


def main():
    mapa_arq, pasta, saida = sys.argv[1:4]
    sufixo = next((" " + a.split("=", 1)[1] for a in sys.argv if a.startswith("--sufixo=")), "")
    mapa = json.load(open(mapa_arq, encoding="utf-8"))
    ganho = s.db(mapa.get("ganho_db", 0.0))
    os.makedirs(pasta, exist_ok=True)
    plano = {"trilha": mapa.get("trilha", "SFX motions (Concat)"), "efeitos": []}
    for k, cena in enumerate(mapa["cenas"]):
        eventos = list(cena["eventos"])
        sem = 1000 + 17 * k
        entrada, fecho = cena.get("entrada"), cena.get("saida", True)   # true ou um dict que muda o padrão
        if entrada:
            c = {"t": -0.4, "som": "ar", "dur": 0.5, "f0": 500, "f1": 3000, "pico": 0.8, "pan0": -0.3, "pan1": 0.3, "db_pico": -24, "sem": sem}
            eventos.insert(0, {"nome": "entrada", "camadas": [dict(c, **entrada) if isinstance(entrada, dict) else c]})
        if fecho:
            c = {"t": cena["dur"] - 0.3, "som": "ar", "dur": 0.3, "f0": 2600, "f1": 900, "pico": 0.4, "pan0": 0.2, "pan1": -0.2,
                 "db_pico": -33, "sem": sem + 1}
            eventos.append({"nome": "saida", "camadas": [dict(c, **fecho) if isinstance(fecho, dict) else c]})
        sons = []
        for j, ev in enumerate(eventos):
            partes = [camada(c) for c in ev["camadas"]]
            som = s.mix(partes) * ganho
            t_ev = min(t for t, _ in partes)
            arq = f"{k + 1}.{j + 1:02d} {cena['nome']} - {ev['nome']}{sufixo}.wav"
            s.salvar(os.path.join(pasta, arq), som)
            plano["efeitos"].append({"arquivo": os.path.join(pasta, arq).replace(*VISTA), "em": round(cena["inicio"] + t_ev, 4),
                                     "duracao": round(len(som) / s.SR, 4), "nome": f"{cena['nome']} - {ev['nome']}"})
            sons.append((t_ev, som))
        tudo = s.mix(sons)
        print(f"cena {k + 1} {cena['nome']:<14} {len(eventos):2d} eventos  pico {20 * np.log10(np.abs(tudo).max() + 1e-9):6.1f} dBFS"
              f"  momentâneo {lufs_momentaneo(tudo):6.1f} LUFS")
    json.dump(plano, open(saida, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(plano['efeitos'])} eventos em {pasta}; plano em {saida}")


if __name__ == "__main__":
    main()
