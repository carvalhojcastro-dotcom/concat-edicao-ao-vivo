"""Enquadramento vertical em quem fala, para podcast em 2-shots (sem tela dividida).

Uso: enquadrar.py <corte.json> [--layout host=MF,guest=FM]
corte.json: {"src": video, "segmentos": [[s, e], ...], "falas": [{"t0", "t1", "voz"}...]}  (tempos da fonte)
Grava corte.json["pecas"]: [{"s", "e", "cx", "cy", "fh", "layout", "quem", "z"}], uma por trecho
contínuo de crop (troca na emenda de câmera ou na troca de locutor).
"""
import json, os, subprocess, sys
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions, vision
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..")); import plataforma  # noqa: E401,E402 (acha o ffmpeg no Windows)

MODELO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "modelos", "face_landmarker.task")
FPS = 30
AW, AH = 1280, 720
PASSO = 3            # landmarker a cada 3 quadros (10 por segundo)
MIN_PECA = 1.2       # s


def quadros(src, s, e):
    n = int(round((e - s) * FPS))
    cmd = ["ffmpeg", "-v", "error", "-nostdin", "-ss", f"{s:.4f}", "-i", src, "-frames:v", str(n),
           "-vf", f"scale={AW}:{AH}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    k = AW * AH * 3
    return [np.frombuffer(raw[i * k:(i + 1) * k], np.uint8).reshape(AH, AW, 3) for i in range(len(raw) // k)]


def emendas(fr):
    """Índices de quadro onde começa um plano novo."""
    peq = [cv2.resize(cv2.cvtColor(f, cv2.COLOR_RGB2GRAY), (160, 90)).astype(np.float32) for f in fr]
    d = np.array([0] + [np.abs(peq[i] - peq[i - 1]).mean() for i in range(1, len(peq))])
    cortes = [0]
    for i in range(1, len(d)):
        viz = np.median(d[max(1, i - 8):i + 8])
        if d[i] > 18 and d[i] > 3 * max(viz, 2) and i - cortes[-1] >= 3:
            cortes.append(i)
    return cortes


def layout(f):
    r = f[0:int(AH * .25), 0:int(AW * .3)].reshape(-1, 3).mean(0)   # RGB
    return "host" if r[0] > 120 else "guest"


def main():
    caminho = sys.argv[1]
    cfg = json.load(open(caminho))
    ordem = {"host": "MF", "guest": "FM"}
    for a in sys.argv[2:]:
        if a.startswith("--layout"):
            for par in a.split(" ", 1)[-1].split("=", 1)[1].split(","):
                k, v = par.split("="); ordem[k] = v
    ordem.update(cfg.get("ordem", {}))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from rostos import Rostos
    det = Rostos(AW, AH)
    falas = cfg["falas"]
    pecas = []
    for s, e in cfg["segmentos"]:
        fr = quadros(cfg["src"], s, e)
        cs = emendas(fr) + [len(fr)]
        for a, b in zip(cs[:-1], cs[1:]):
            lay = layout(fr[(a + b) // 2])
            amostras = []   # (t, [(cx, cy, fh, boca)])
            for i in range(a, b, PASSO):
                fs = det(np.ascontiguousarray(fr[i]))
                amostras.append((s + i / FPS, fs))
            # trilhas por posição horizontal
            xs = sorted(f[0] for _, fs in amostras for f in fs)
            centros = []
            for x in xs:
                if not centros or x - centros[-1][-1] > 0.12:
                    centros.append([x])
                else:
                    centros[-1].append(x)
            centros = [c for c in centros if len(c) >= max(2, 0.3 * len(amostras))]
            tr = [float(np.median(c)) for c in centros]
            ini, fim = s + a / FPS, s + b / FPS
            if len(tr) >= 3:   # câmera aberta: quadro inteiro sobre fundo desfocado (crop não acha o locutor com segurança)
                pecas.append({"s": round(ini * FPS) / FPS, "e": round(fim * FPS) / FPS, "cx": 0.5, "cy": 0.4, "fh": 0.2,
                              "layout": "aberto", "quem": "todos", "n": len(tr), "wide": True})
                continue
            if not tr:
                pecas.append({"s": ini, "e": fim, "cx": 0.5, "cy": 0.4, "fh": 0.25, "layout": lay, "quem": "?"})
                continue
            series = {k: [] for k in range(len(tr))}
            for t, fs in amostras:
                for f in fs:
                    k = int(np.argmin([abs(f[0] - c) for c in tr]))
                    if abs(f[0] - tr[k]) < 0.1:
                        series[k].append((t, f))
            gen = list(ordem[lay]) if len(tr) == 2 else [None] * len(tr)

            # só um rosto achado num 2-shot conhecido: o outro entra pela posição padrão
            modelo = cfg.get("posicoes", {}).get(lay)
            if modelo and len(tr) == 1:
                k_det = int(np.argmin([abs(tr[0] - m["cx"]) for m in modelo]))
                outro = modelo[1 - k_det]
                tr = sorted([tr[0], outro["cx"]])
                series = {i: [] for i in range(2)}
                for t, fs in amostras:
                    for f in fs:
                        k = int(np.argmin([abs(f[0] - c) for c in tr]))
                        series[k].append((t, f))
                for i in range(2):
                    if not series[i]:
                        series[i] = [(ini, (outro["cx"], outro["cy"], outro["fh"], 0.0))]
                gen = list(ordem[lay])

            def escolha(t0, t1, voz):
                sc = []
                for k in range(len(tr)):
                    v = [f[3] for t, f in series[k] if t0 <= t < t1 and len(series[k]) > 1]
                    act = float(np.std(v) + np.abs(np.diff(v)).mean()) if len(v) >= 3 else 0.0
                    sc.append(act)
                m = max(sc) or 1
                tot = [sc[k] / m + (0.6 if gen[k] and gen[k] == voz else 0) for k in range(len(tr))]
                return int(np.argmax(tot)), sc
            # unidades = falas que cruzam o plano
            unid = []
            for fl in falas:
                t0, t1 = max(fl["t0"], ini), min(fl["t1"], fim)
                if t1 - t0 >= 0.25:
                    k, sc = escolha(t0, t1, fl.get("voz"))
                    unid.append([t0, t1, k])
            if not unid:
                k, _ = escolha(ini, fim, None)
                unid = [[ini, fim, k]]
            # cobre o plano inteiro: cada unidade vai até o começo da próxima
            unid[0][0] = ini
            for j in range(len(unid) - 1):
                unid[j][1] = unid[j + 1][0]
            unid[-1][1] = fim
            # junta iguais e absorve curtas
            mud = True
            while mud:
                mud = False
                junt = []
                for u in unid:
                    if junt and junt[-1][2] == u[2]:
                        junt[-1][1] = u[1]
                    else:
                        junt.append(list(u))
                unid = junt
                if len(unid) > 1:
                    j = min(range(len(unid)), key=lambda j: unid[j][1] - unid[j][0])
                    if unid[j][1] - unid[j][0] < MIN_PECA:
                        viz = [x for x in (j - 1, j + 1) if 0 <= x < len(unid)]
                        alvo = max(viz, key=lambda x: unid[x][1] - unid[x][0])
                        unid[j][2] = unid[alvo][2]
                        mud = True
            for t0, t1, k in unid:
                pts = [f for t, f in series[k]] or [(tr[k], 0.4, 0.25, 0)]
                pecas.append({"s": round(t0 * FPS) / FPS, "e": round(t1 * FPS) / FPS,
                              "cx": float(np.median([p[0] for p in pts])), "cy": float(np.median([p[1] for p in pts])),
                              "fh": float(np.median([p[2] for p in pts])), "layout": lay,
                              "quem": (gen[k] or "?") + str(k), "n": len(tr)})
    cfg["pecas"] = [p for p in pecas if p["e"] - p["s"] >= 1 / FPS - 1e-6]
    json.dump(cfg, open(caminho, "w"), ensure_ascii=False, indent=1)
    for p in cfg["pecas"]:
        print(f'{p["s"]:9.2f}-{p["e"]:9.2f} {p["layout"]:5s} {p["quem"]} cx={p["cx"]:.2f} faces={p.get("n")}')


if __name__ == "__main__":
    main()
