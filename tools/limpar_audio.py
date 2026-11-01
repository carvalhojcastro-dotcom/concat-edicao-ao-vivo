#!/usr/bin/env python3
"""Limpa o ruído de fundo da fala com o DeepFilterNet (rede neural feita para voz) e, se pedir, troca a
mídia dos clipes do projeto pela versão limpa. O vídeo não é recodificado (cópia), só o áudio muda.

Uso:
  tools/.venv/bin/python tools/limpar_audio.py <video> <saida.mov> [--projeto <projeto>] [--limite=24]
  ... --amostra=<ini>-<fim>   só gera <saida>.wav com esse trecho (segundos do bruto), para ouvir antes
  ... --bips=4605,2801,...     filtros bem estreitos nessas frequências antes do DeepFilterNet (bips e apitos de
                               máquina com tom fixo, ex.: centro cirúrgico)
  ... --bips=auto              acha esses tons sozinho no espectro das pausas da fala (padrão para vídeo de
                               centro cirúrgico, 2026-11-01: "quero esses aprimoramentos ... quando o vídeo for de
                               centro cirúrgico")

Por que não o "Noise Reduction" do Concat: ele é o afftdn do ffmpeg (subtração espectral); para tirar
o chiado de verdade ele abafa a voz e deixa "metálica". O DeepFilterNet separa voz de ruído.
--limite: quanto o ruído pode cair, em dB (padrão 24). Com 24, no Ozempic (2026-10-21), o fundo foi de
-40 a -63 dB, a fala ficou igual e os agudos também (não abafa); 30+ deixa um "vácuo" artificial.
Com --projeto, os clipes ficam como "Enhance" (dá para voltar ao original no Concat). Depois disso,
tire o concat.denoise dos clipes: o áudio já chega limpo.
"""
import json
import os
import subprocess
import sys

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import plataforma  # noqa: E402,F401  (acha o ffmpeg no Windows)

SR = 48000            # o DeepFilterNet trabalha a 48 kHz
BLOCO = 30.0          # s por pedaço (vídeo longo não estoura a memória)
EMENDA = 0.5          # s de sobreposição entre pedaços, com cruzamento linear


def canais(video):
    s = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=channels",
                        "-of", "json", video], capture_output=True, text=True, check=True).stdout
    return max(1, min(2, json.loads(s)["streams"][0]["channels"]))


def ler(video, nc, ini=None, dur=None):
    cmd = ["ffmpeg", "-v", "error"] + (["-ss", f"{ini:.3f}"] if ini is not None else []) + ["-i", video]
    cmd += (["-t", f"{dur:.3f}"] if dur is not None else []) + ["-vn", "-ac", str(nc), "-ar", str(SR), "-f", "f32le", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, nc).T.copy()


def tirar_bips(x, freqs, q=30.0):
    """Entalhes estreitos (Q 30: ~150 Hz de largura a 4,6 kHz) nas frequências dos bips, sem defasar (filtfilt).
    Pedido de 2026-11-01 (Dra. Luciana no centro cirúrgico): o DeepFilterNet sozinho deixava os bips de monitor."""
    import scipy.signal as sinal
    for f in freqs:
        b, a = sinal.iirnotch(f, q, SR)
        x = sinal.filtfilt(b, a, x, axis=1).astype(np.float32)
    return x


def achar_bips(x, minimo_db=8.0, maximo=12):
    """Tons fixos de máquina: picos estreitos no espectro dos 25% de trechos mais quietos (as pausas), ao menos
    `minimo_db` acima do ruído em volta, entre 150 Hz e 8 kHz. No centro cirúrgico do vídeo 16 da Dra. Luciana
    vieram 1,2/1,6/2,0/2,8/3,6/4,2/4,4/4,6 kHz e dois zumbidos de 182 e 229 Hz."""
    import scipy.signal as sinal
    m = x.mean(0)
    h = int(0.05 * SR)
    n = len(m) // h
    rms = np.sqrt((m[:n * h].reshape(n, h) ** 2).mean(1) + 1e-12)
    quietos = m[:n * h].reshape(n, h)[rms <= np.percentile(rms, 25)].ravel()
    f, p = sinal.welch(quietos, SR, nperseg=16384)
    pdb = 10 * np.log10(p + 1e-20)
    acima = pdb - sinal.medfilt(pdb, 101)
    picos = [i for i in sinal.find_peaks(acima, height=minimo_db, distance=10)[0] if 150 < f[i] < 8000]
    picos = sorted(picos, key=lambda i: -acima[i])[:maximo]
    return [round(float(f[i]), 1) for i in sorted(picos)]


def limpar(x, limite):
    import torch
    from df.enhance import enhance, init_df
    modelo, estado, _ = init_df(log_level="ERROR")
    n, passo, emenda = x.shape[1], int(BLOCO * SR), int(EMENDA * SR)
    if n <= passo + emenda:
        return enhance(modelo, estado, torch.from_numpy(x), atten_lim_db=limite).numpy()
    saida = np.zeros_like(x)
    peso = np.zeros(n, np.float32)
    rampa = np.linspace(0, 1, emenda, dtype=np.float32)
    ini = 0
    while ini < n:
        fim = min(n, ini + passo + emenda)
        y = enhance(modelo, estado, torch.from_numpy(x[:, ini:fim].copy()), atten_lim_db=limite).numpy()
        w = np.ones(fim - ini, np.float32)
        if ini > 0:
            w[:emenda] = rampa
        if fim < n:
            w[-emenda:] = rampa[::-1]
        saida[:, ini:fim] += y * w
        peso[ini:fim] += w
        print(f"  {fim / SR:7.1f} / {n / SR:.1f} s", flush=True)
        ini += passo
    return saida / np.maximum(peso, 1e-6)


def gravar(y, destino, video=None):
    """WAV solto, ou o vídeo original (cópia do vídeo, metadados e rotação) com este áudio."""
    nc = y.shape[0]
    entrada = ["-f", "f32le", "-ar", str(SR), "-ac", str(nc), "-i", "-"]
    if video is None:
        cmd = ["ffmpeg", "-v", "error", "-y"] + entrada + ["-c:a", "pcm_s16le", destino]
    else:
        cmd = ["ffmpeg", "-v", "error", "-y", "-i", video] + entrada + [
            "-map", "0:v:0", "-map", "1:a:0", "-map_metadata", "0", "-c:v", "copy", "-c:a", "pcm_s24le", destino]
    subprocess.run(cmd, input=np.ascontiguousarray(y.T.astype(np.float32)).tobytes(), check=True)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opc = dict(a[2:].split("=", 1) if "=" in a else (a[2:], "") for a in sys.argv[1:] if a.startswith("--"))
    if len(args) < 2:
        sys.exit(__doc__)
    video, saida = os.path.abspath(args[0]), os.path.abspath(args[1])
    limite = float(opc.get("limite", 24))
    nc = canais(video)
    if opc.get("bips") == "auto":
        bips = achar_bips(ler(video, nc))
        print("tons de máquina achados (Hz):", ", ".join(f"{b:g}" for b in bips) or "nenhum", flush=True)
    else:
        bips = [float(f) for f in opc["bips"].split(",")] if opc.get("bips") else []
    if "amostra" in opc:
        a, b = (float(v) for v in opc["amostra"].split("-"))
        y = limpar(tirar_bips(ler(video, nc, a, b - a), bips), limite)
        gravar(y, os.path.splitext(saida)[0] + ".wav")
        print("amostra:", os.path.splitext(saida)[0] + ".wav")
        return
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    print(f"limpando {os.path.basename(video)} (teto de {limite:.0f} dB)", flush=True)
    gravar(limpar(tirar_bips(ler(video, nc), bips), limite), saida, video)
    print("pronto:", saida)
    projeto = opc.get("projeto") or (args[2] if "projeto" in opc and len(args) > 2 else None)
    if projeto:
        from retoque import trocar_midia
        trocar_midia(projeto, saida)


if __name__ == "__main__":
    main()
