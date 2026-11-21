"""Analisa um corte (trecho contínuo do bruto): emendas de câmera no quadro exato, rostos (posição, altura, boca) a
5 fps e voz M/F a cada 0,5 s. A câmera de cada plano sai pelo número e tamanho dos rostos:
  G = um rosto (convidado sozinho), H = dois (plano dos apresentadores), W = três ou mais, ou rostos pequenos (mesa).
config.json pode trocar a regra: "camera_por_cor": {"H": [r, g, b], "G": [...], "W": [...]} (cor média do canto de
cima à esquerda, 64x36), útil quando um plano tem um rosto a mais ou a menos.
Uso: analisar.py <W> <id> <in> <out>   -> c<id>/analise.json"""
import json, os, subprocess, sys
import numpy as np
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.join(AQUI, ".."))
from comum import config, FPS  # noqa: E402
from f0 import carregar, f0_trecho  # noqa: E402
from rostos import Rostos  # noqa: E402

W, cid, S, E = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
cfg = config(W)
V = cfg["fonte"]
out = os.path.join(W, f"c{cid}")
os.makedirs(out, exist_ok=True)


# o decode começa exatamente no quadro round(S*30) (sem isso o -ss num tempo fora do grid pulava para o quadro
# seguinte e todas as emendas saíam 1 quadro adiantadas, 2026-11-10)
F0 = int(round(S * FPS))
SG = F0 / FPS


def ler(w, h, fps, fmt="rgb24"):
    vf = f"fps={fps},scale={w}:{h}" if fps else f"scale={w}:{h}"
    cmd = ["ffmpeg", "-v", "error", "-nostdin", "-hwaccel", "videotoolbox", "-ss", f"{SG - 0.001:.4f}", "-i", V, "-t", f"{E - SG:.3f}",
           "-vf", vf, "-f", "rawvideo", "-pix_fmt", fmt, "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3 if fmt == "rgb24" else 1)


# 1) emendas no quadro exato: frame i do decode = quadro round(S*30)+i (S cai no grid de 1/30)
pq = ler(64, 36, None).astype(np.float32)
f0 = F0
d = np.array([0] + [np.abs(pq[i] - pq[i - 1]).mean() for i in range(1, len(pq))])
em = [0]
for i in range(1, len(d)):
    viz = np.median(d[max(1, i - 15):i + 15])
    if d[i] > 14 and d[i] > 3.5 * max(viz, 2) and i - em[-1] >= 6:
        em.append(i)
em.append(len(pq))
planos = [{"q0": f0 + a, "q1": f0 + b, "s": (f0 + a) / FPS, "e": (f0 + b) / FPS,
           "cor": [float(x) for x in pq[(a + b) // 2][0:9, 0:16].reshape(-1, 3).mean(0)]} for a, b in zip(em[:-1], em[1:])]

# 2) rostos a 5 fps
AW, AH = 960, 540
fr = ler(AW, AH, 5)
det = Rostos(AW, AH)
amostras = [(S + k / 5, [[float(v) for v in f] for f in det(np.ascontiguousarray(fr[k]))]) for k in range(len(fr))]

for p in planos:
    fs = [f for t, ff in amostras if p["s"] <= t < p["e"] for f in [ff]]
    n = [len([x for x in ff if x[2] > 0.06]) for ff in fs] or [0]
    alt = [x[2] for ff in fs for x in ff if x[2] > 0.06] or [0]
    p["rostos"] = float(np.median(n))
    p["altura"] = float(np.median(alt))
    if "camera_por_cor" in cfg:
        ref = cfg["camera_por_cor"]
        p["cam"] = min(ref, key=lambda k: sum((a - b) ** 2 for a, b in zip(ref[k], p["cor"])))
        # cores parecidas (Márcia: convidada x mesa): o tamanho do rosto desempata
        if p["rostos"] >= 1 and p["altura"] < cfg.get("altura_mesa", 0.13) and "W" in ref:
            p["cam"] = "W"
        elif p["cam"] == "W" and p["altura"] > 0.18:
            p["cam"] = min((k for k in ref if k != "W"), key=lambda k: sum((a - b) ** 2 for a, b in zip(ref[k], p["cor"])))
    else:
        p["cam"] = "W" if p["rostos"] >= 3 or (p["rostos"] >= 1 and p["altura"] < cfg.get("altura_mesa", 0.12)) else ("H" if p["rostos"] >= 2 else "G")

# 3) voz a cada 0,5 s
x, sr = carregar(os.path.join(W, "audio.wav"))
voz = []
t = S
while t < E:
    f, n = f0_trecho(x, sr, t, min(t + 0.5, E))
    voz.append((t, None if f is None or n < 4 else ("F" if f >= 160 else "M")))
    t += 0.5

json.dump({"S": S, "E": E, "planos": planos, "amostras": amostras, "voz": voz}, open(os.path.join(out, "analise.json"), "w"))
for p in planos:
    print(f'{p["s"]:8.2f}-{p["e"]:8.2f} {p["cam"]} rostos {p["rostos"]:.0f} altura {p["altura"]:.2f} cor {[int(c) for c in p["cor"]]}')
