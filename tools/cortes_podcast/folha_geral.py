"""Folha única: 5 quadros por corte (gancho, peças de enquadramento distintas, blocos dinâmicos). Uso: folha_geral.py <saida.jpg> <dir>=<mp4> ..."""
import json, os, subprocess, sys, tempfile
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..")); import plataforma  # noqa: E401,E402 (acha o ffmpeg no Windows)
out = sys.argv[1]; d = tempfile.mkdtemp(); linhas = []
for par in sys.argv[2:]:
    pasta, mp4 = par.split("=", 1)
    cfg = json.load(open(os.path.join(pasta, "corte.json"))); blocos = json.load(open(os.path.join(pasta, "blocos.json")))["blocos"]
    words = json.load(open(os.path.join(pasta, "words_leg.json")))
    segs = cfg["segmentos"]
    def saida(t):
        off = 0
        for a, b in segs:
            if a - 1e-3 <= t <= b + 1e-3: return off + t - a
            off += b - a
    fim_bloco = lambda b: (words[b["linhas"][-1][-1]]["start"] + words[b["linhas"][-1][-1]]["end"]) / 2  # noqa: E731  bloco completo
    ts = [fim_bloco(blocos[0])] if blocos else []
    vistos = set()
    for p in sorted(cfg["pecas"], key=lambda p: -(p["e"] - p["s"])):
        k = (p["layout"], p["quem"])
        if k not in vistos and len(vistos) < 3:
            vistos.add(k); ts.append(saida((p["s"] + p["e"]) / 2))
    for b in blocos[len(blocos) // 2:]:
        if len(ts) >= 5: break
        ts.append(fim_bloco(b))
    ts = sorted(t for t in ts if t is not None)[:5]
    fs = []
    for t in ts:
        a = os.path.join(d, f"{len(linhas)}_{len(fs)}.jpg")
        subprocess.run(["ffmpeg", "-v", "fatal", "-y", "-ss", f"{t:.2f}", "-i", mp4, "-frames:v", "1", "-vf", "scale=150:-1", "-pix_fmt", "yuvj420p", a])
        fs.append(a)
    while len(fs) < 5: fs.append(fs[-1])
    lin = os.path.join(d, f"l{len(linhas)}.jpg")
    subprocess.run(["ffmpeg", "-v", "fatal", "-y"] + sum([["-i", f] for f in fs], []) + ["-filter_complex", "hstack=5", lin])
    linhas.append(lin)
subprocess.run(["ffmpeg", "-v", "fatal", "-y"] + sum([["-i", f] for f in linhas], []) + ["-filter_complex", f"vstack={len(linhas)}" if len(linhas) > 1 else "null", out])
print(out)
