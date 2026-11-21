"""Confere as emendas de um corte já gravado no CapCut: em cada pedaço da trilha principal, os quadros que ele mostra
(lidos de 3 jeitos: arredondando para baixo, para cima e para o mais próximo) têm que ser todos do mesmo plano do bruto.
Erro de 2026-11-10: com velocidade 1,1 redonda e duração arredondada a quadros, o último quadro de um pedaço mostrava
o primeiro quadro do plano seguinte ainda com o enquadramento antigo. As trocas de câmera vêm do bruto, com pts real.
Uso: emendas.py <vídeo bruto> <pasta do projeto> [...]"""
import json, math, subprocess, sys
import numpy as np


def trocas_perto(V, f, raio=8):
    t0 = (f - raio) / 30
    cmd = ["ffmpeg", "-hide_banner", "-v", "info", "-copyts", "-ss", f"{t0 - 0.0001:.4f}", "-i", V, "-frames:v", str(2 * raio + 1),
           "-vf", "scale=64:36,showinfo", "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    r = subprocess.run(cmd, capture_output=True)
    fr = np.frombuffer(r.stdout, np.uint8).reshape(-1, 36, 64).astype(float)
    pts = [round(float(l.split("pts_time:")[1].split()[0]) * 30) for l in r.stderr.decode(errors="ignore").splitlines() if "pts_time:" in l]
    return [pts[i] for i in range(1, len(fr)) if np.abs(fr[i] - fr[i - 1]).mean() > 20]


V = sys.argv[1]
for pasta in sys.argv[2:]:
    d = json.load(open(pasta.rstrip("/") + "/draft_info.json"))
    v = next(t for t in d["tracks"] if t["type"] == "video")
    segs = sorted(v["segments"], key=lambda s: s["target_timerange"]["start"])
    pontos = [s["source_timerange"]["start"] / 1e6 * 30 for s in segs]
    pontos.append((segs[-1]["source_timerange"]["start"] + segs[-1]["source_timerange"]["duration"]) / 1e6 * 30)
    trocas = sorted({c for f in pontos for c in trocas_perto(V, round(f))})
    plano = lambda f: sum(1 for c in trocas if c <= f)  # noqa: E731
    ruins = []
    for k, s in enumerate(segs):
        st = s["source_timerange"]["start"] / 1e6 * 30
        n = round(s["target_timerange"]["duration"] / 1e6 * 30)
        for nome, regra in (("baixo", lambda a: math.floor(a + 1e-9)), ("cima", lambda a: math.ceil(a - 1e-9)), ("próximo", round)):
            if len({plano(regra(st + j * s["speed"])) for j in range(n)}) > 1:
                ruins.append((k, nome))
    emendas_no_corte = [c for c in trocas if pontos[0] < c < pontos[-1]]
    print(pasta.rstrip("/").rsplit("/", 1)[-1], f"| {len(segs)} pedaços, {len(emendas_no_corte)} trocas de câmera dentro do corte |",
          "OK" if not ruins else f"PEDAÇOS COM QUADRO DE OUTRO PLANO: {ruins}")
