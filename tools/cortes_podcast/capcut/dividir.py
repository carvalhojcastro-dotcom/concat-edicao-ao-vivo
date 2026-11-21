"""Tela dividida nos momentos em que um apresentador fala olhando para o outro (pedido de 2026-11-10: "momentos em que
eu estou falando, mas eu olho para a Myrian ou vice-versa ... enquadrasse ela também ... não precisa ser toda hora,
mas uma vez ou outra"). Divide o pedaço do plano dos apresentadores em: antes (sozinho), dupla (quem fala em cima,
o outro embaixo, cada um num recorte 1080x960 com o rosto a ~42% da altura) e depois (sozinho).
Uso: dividir.py <W> <id> "<t0>-<t1>:<cima>/<baixo>" [...]   (s do bruto; nomes de config "pessoas")
     dividir.py <W> <id> "<t0>-<t1>:<nome>" [...]           corte seco para essa pessoa em tela cheia (sem dividir)
Regrava c<id>/plano.json (o original fica em plano_sem_dupla.json)."""
import json, os, shutil, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comum import config, FPS  # noqa: E402

W, cid = sys.argv[1], sys.argv[2]
cfg = config(W)
pasta = os.path.join(W, f"c{cid}")
if not os.path.exists(os.path.join(pasta, "plano_sem_dupla.json")):
    shutil.copy(os.path.join(pasta, "plano.json"), os.path.join(pasta, "plano_sem_dupla.json"))
plano = json.load(open(os.path.join(pasta, "plano_sem_dupla.json")))
A = json.load(open(os.path.join(pasta, "analise.json")))
q = lambda t: round(t * FPS) / FPS  # noqa: E731
lado = {v["nome"]: k for k, v in cfg["pessoas"].items()}   # nome -> "esq"/"dir"
ALT = cfg.get("dupla_altura", 0.72)                        # altura do recorte em fração do bruto
LARG = ALT * (1080 / 960) * 9 / 16                          # largura que dá 1080:960 num bruto 16:9


def caixa(nome, t0, t1, rosto=0.42):
    fs = [f for t, ff in A["amostras"] if t0 <= t < t1 for f in ff if f[2] > 0.12
          and ((f[0] < 0.5) == (lado[nome] == "esq"))]
    cx = float(np.median([f[0] for f in fs])) if fs else (0.25 if lado[nome] == "esq" else 0.75)
    cy = float(np.median([f[1] for f in fs])) if fs else 0.35
    alt = ALT
    if cy - rosto * alt < 0:      # sem espaço acima do rosto no bruto: recorte mais fechado para o rosto descer
        alt = max(0.5, cy / rosto)
    larg = alt * (1080 / 960) * 9 / 16
    x0 = min(max(cx - larg / 2, 0.0), 1 - larg)
    y0 = min(max(cy - rosto * alt, 0.0), 1 - alt)
    return [round(x0, 4), round(y0, 4), round(x0 + larg, 4), round(y0 + alt, 4)]


def recorta_kx(kx, s, e):
    if not kx:
        return None
    ts, vs = [a for a, _ in kx], [b for _, b in kx]
    pts = [[s, float(np.interp(s, ts, vs))]] + [[a, b] for a, b in kx if s < a < e] + [[e - 1 / FPS, float(np.interp(e - 1 / FPS, ts, vs))]]
    return pts if len({round(v, 4) for _, v in pts}) > 1 else None


pecas = plano["pecas"]
for arg in sys.argv[3:]:
    faixa, quem = arg.split(":")
    t0, t1 = (q(float(x)) for x in faixa.split("-"))
    cima, baixo = (quem.split("/") + [""])[:2]
    i = next(k for k, p in enumerate(pecas) if p["fonte"] - 1e-3 <= t0 < p["fonte"] + p["fonte_dur"] and p.get("layout") == "solo")
    p = pecas[i]
    s, e = p["fonte"], q(p["fonte"] + p["fonte_dur"])
    t1 = min(t1, e)
    novas = []
    for a, b, tipo in ((s, t0, "solo"), (t0, t1, "dupla"), (t1, e, "solo")):
        if b - a < 1 / FPS - 1e-6:
            continue
        n = dict(p, fonte=round(a, 4), fonte_dur=round(b - a, 4))
        n.pop("kx", None)
        if tipo == "solo":
            kx = recorta_kx(p.get("kx"), a, b)
            if kx:
                n["kx"] = [[round(x, 4), round(y, 4)] for x, y in kx]
                n["tx"] = n["kx"][0][1]
        elif not baixo:     # "t0-t1:myrian": corte seco para a outra pessoa, em tela cheia (pedido seguinte do usuário)
            fs = [f for t, ff in A["amostras"] if a <= t < b for f in ff if f[2] > 0.12 and ((f[0] < 0.5) == (lado[cima] == "esq"))]
            cx = float(np.median([f[0] for f in fs])) if fs else (0.25 if lado[cima] == "esq" else 0.75)
            K = p["escala"]
            n.update(quem=cima, tx=round(-(cx - 0.5) * K * 2, 4))
        else:
            n.update(layout="dupla", quem=f"{cima}/{baixo}", cima=caixa(cima, a, b),
                     # embaixo o rosto desce (~58% da metade): a legenda, na linha de 64% da tela, fica acima da cabeça
                     baixo=caixa(baixo, a, b, cfg.get("dupla_rosto_baixo", 0.58)))
        novas.append(n)
    pecas[i:i + 1] = novas
json.dump(plano, open(os.path.join(pasta, "plano.json"), "w"), ensure_ascii=False, indent=1)
for p in pecas:
    print(f'{p["fonte"]:8.2f} +{p["fonte_dur"]:6.2f} {p["cam"]} {p["quem"]:12s} {p.get("layout")}' + (f' cima={p["cima"]} baixo={p["baixo"]}' if p.get("layout") == "dupla" else ""))
