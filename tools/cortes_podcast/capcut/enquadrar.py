"""Pedaços de um corte e o enquadramento de cada um (CapCut, tela cheia 9:16, escala 3,2).
Regras do usuário (Podcast 12 do Dr. Rafael, 2026-11-10):
  - corte seco só quando a câmera troca ou muda a pessoa enquadrada;
  - cada pessoa tem um X fixo por câmera (sem variar de um pedaço para outro), com o CORPO centrado;
  - se a pessoa se desloca dentro do plano, a câmera a segue com keyframes de posição (linear), nunca com corte seco;
  - no plano dos apresentadores, a pessoa da voz F só entra quando a voz é feminina E a boca dela mexe; o resto fica
    na pessoa da voz M (com as vozes de config.json "pessoas"); plano curto (< 1,5 s) fica na pessoa padrão.
Uso: enquadrar.py <W> <id> <in> <out> [volume]  -> c<id>/plano.json (formato do capcut_podcast.py)"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comum import config, FPS  # noqa: E402

W, cid, S, E = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
vol = float(sys.argv[5]) if len(sys.argv) > 5 else None
cfg = config(W)
vel = cfg.get("velocidade", 1.1)
P = cfg["pessoas"]                      # {"esq": {"nome", "voz"}, "dir": {"nome", "voz"}}
CONV = cfg.get("convidado", "convidado")
PADRAO_H = cfg.get("padrao_apresentadores", next(p["nome"] for p in P.values() if p["voz"] == "M"))
CORPO = cfg.get("corpo", {})            # {"nome": desvio em fração do bruto}: centrar o corpo, não só o rosto
ESCALA = 3.2                            # o 16:9 encaixa na largura: com 3,2 o bruto ocupa 3,2 larguras de tela
# plano aberto (mesa): a pessoa fica pequena; aproxima mais nela (cortes do Humman EP01 aprovados com ~1,6x a mais)
ESCALAS = {"G": ESCALA, "H": ESCALA, "W": cfg.get("escala_mesa", 5.0)}
MIN_PECA = 2.0
LIMIAR = 0.045                          # ~155 px na tela: deslocamento que a câmera segue
SEGUE = 0.8
A = json.load(open(os.path.join(W, f"c{cid}", "analise.json")))
q = lambda t: round(t * FPS) / FPS  # noqa: E731
def tx_de(cx, cam="G"):
    K = ESCALAS.get(cam, ESCALA)
    m = 0.5 / K                         # metade da tela em fração do bruto: além disso aparece borda preta
    return round(-(min(max(cx, m + 0.002), 1 - m - 0.002) - 0.5) * K * 2, 4)

planos = [dict(p) for p in A["planos"] if p["e"] > S and p["s"] < E]
planos[0]["s"], planos[-1]["e"] = S, E
amostras, voz = A["amostras"], A["voz"]


def rostos(p):
    # só as amostras do próprio plano (a margem pegava quadros do plano vizinho, 2026-11-10); plano curto demais usa margem
    r = [(t, fs) for t, fs in amostras if p["s"] <= t < p["e"]]
    return r if len(r) >= 2 else [(t, fs) for t, fs in amostras if p["s"] - 0.1 <= t < p["e"] + 0.1]


def trilhas(p, contagem=False):
    xs = sorted(f[0] for _, fs in rostos(p) for f in fs if f[2] > 0.06)
    grupos = []
    for x in xs:
        if grupos and x - grupos[-1][-1] < 0.1:
            grupos[-1].append(x)
        else:
            grupos.append([x])
    n = max(1, len(rostos(p)))
    g = [g for g in grupos if len(g) >= 0.25 * n]
    return [(float(np.median(x)), len(x)) for x in g] if contagem else [float(np.median(x)) for x in g]


def serie(p, cx0):
    return [(t, min(fs, key=lambda f: abs(f[0] - cx0))) for t, fs in rostos(p)
            if fs and min(abs(f[0] - cx0) for f in fs) < 0.08]


# dupla na câmera dos convidados (JFIT: Jonas e Renata, 2026-11-13): "convidados" no config, como "pessoas"
PESSOAS = {"H": P}
if cfg.get("convidados"):
    PESSOAS["G"] = cfg["convidados"]
PADRAO = {"H": PADRAO_H}
if cfg.get("convidados"):
    PADRAO["G"] = cfg.get("padrao_convidados", next(x["nome"] for x in cfg["convidados"].values() if x["voz"] == "M"))

pecas = []
for p in planos:
    tr = trilhas(p)
    Pc = PESSOAS.get(p["cam"]) if p["cam"] in ("H", "G") else None
    if (p["cam"] == "G" and not Pc) or not tr:   # convidado sozinho: o rosto que mais aparece (mão ou reflexo não viram trilha)
        tc = trilhas(p, contagem=True)
        pecas.append({"s": p["s"], "e": p["e"], "cam": p["cam"], "quem": CONV if p["cam"] == "G" else PADRAO_H,
                      "cx": max(tc, key=lambda x: x[1])[0] if tc else 0.5})
        continue
    mesa = cfg.get("mesa")
    if p["cam"] == "W" and mesa:   # mesa com posições fixas (câmera parada): "fixo" (um enquadramento) ou "voz" (M/F)
        if mesa["modo"] == "fixo":
            alvo = mesa
        else:
            vs = [v for t, v in voz if p["s"] - 0.25 <= t < p["e"] and v]
            alvo = mesa["M"] if vs.count("M") >= vs.count("F") else mesa["F"]
        pecas.append({"s": p["s"], "e": p["e"], "cam": "W", "quem": alvo["nome"], "cx": alvo["cx"], "cy": alvo.get("cy"), "fixo": True})
        continue
    if p["cam"] == "W":   # mesa: fica no convidado (o foco), do lado em que ele senta
        cx = tr[0] if cfg.get("lado_convidado_mesa", "esq") == "esq" else tr[-1]
        pecas.append({"s": p["s"], "e": p["e"], "cam": "W", "quem": CONV, "cx": cx})
        continue
    if len(tr) == 1:      # plano de dois com um rosto só
        quem = Pc["esq"]["nome"] if tr[0] < 0.5 else Pc["dir"]["nome"]
        pecas.append({"s": p["s"], "e": p["e"], "cam": p["cam"], "quem": quem, "cx": tr[0]})
        continue
    esq, dir_ = tr[0], tr[-1]
    pos = {Pc["esq"]["nome"]: esq, Pc["dir"]["nome"]: dir_}
    fem = next((k for k, v in Pc.items() if v["voz"] == "F"), None)
    padrao = PADRAO[p["cam"]]
    se, sd = serie(p, esq), serie(p, dir_)

    def mexe(sr, t):
        v = [f[3] for tt, f in sr if t - 0.5 <= tt < t + 1.0]
        return float(np.std(v) + np.abs(np.diff(v)).mean()) if len(v) >= 3 else 0.0
    rotulo = []
    pela_boca = p["cam"] in cfg.get("decide_pela_boca", [])   # voz M/F não separa os dois (JFIT: o Jonas sai "F")
    anterior = padrao
    # quem fala, decidido pelo conteúdo quando a boca erra (JFIT, 2026-11-13: a Renata contando a história e o
    # Jonas na tela porque ria): config "falantes": {"<id>": [[t0 do bruto, t1, "nome"], ...]}
    forca = [f for f in cfg.get("falantes", {}).get(sys.argv[2], []) if f[2] in {x["nome"] for x in Pc.values()}]
    for t, v in voz:
        if not (p["s"] - 0.25 <= t < p["e"]):
            continue
        f = next((f for f in forca if f[0] <= t + 0.25 < f[1]), None)
        if f:
            anterior = f[2]
            rotulo.append([max(t, p["s"]), min(t + 0.5, p["e"]), f[2]])
            continue
        a, b = mexe(se, t), mexe(sd, t)
        if pela_boca:
            quem = anterior
            if max(a, b) > 0.012 and max(a, b) >= 1.25 * max(min(a, b), 1e-6):
                quem = Pc["esq"]["nome"] if a > b else Pc["dir"]["nome"]
            anterior = quem
            rotulo.append([max(t, p["s"]), min(t + 0.5, p["e"]), quem])
            continue
        quem = padrao
        if fem and v == "F":
            bf, bm = (a, b) if fem == "esq" else (b, a)
            if bf >= 0.8 * bm and bf > 0.01:
                quem = Pc[fem]["nome"]
        elif v == "M":
            masc = next(k for k, x in Pc.items() if x["voz"] == "M")
            quem = Pc[masc]["nome"]
        rotulo.append([max(t, p["s"]), min(t + 0.5, p["e"]), quem])
    if not rotulo or p["e"] - p["s"] < 1.5:
        rotulo = [[p["s"], p["e"], padrao]]
    mud = True
    while mud:
        mud = False
        junt = []
        for u in rotulo:
            if junt and junt[-1][2] == u[2]:
                junt[-1][1] = u[1]
            else:
                junt.append(list(u))
        rotulo = junt
        if len(rotulo) > 1:
            j = min(range(len(rotulo)), key=lambda j: rotulo[j][1] - rotulo[j][0])
            if rotulo[j][1] - rotulo[j][0] < MIN_PECA:
                viz = [x for x in (j - 1, j + 1) if 0 <= x < len(rotulo)]
                rotulo[j][2] = rotulo[max(viz, key=lambda x: rotulo[x][1] - rotulo[x][0])][2]
                mud = True
    rotulo[0][0], rotulo[-1][1] = p["s"], p["e"]
    for a, b, quem in rotulo:
        pecas.append({"s": a, "e": b, "cam": p["cam"], "quem": quem, "cx": pos.get(quem, esq)})

# X fixo por pessoa e câmera (mediana no corte todo)
fixo = {}
for k in {(x["cam"], x["quem"]) for x in pecas}:
    vals = [f[0] for x in pecas if (x["cam"], x["quem"]) == k for t, f in serie(x, x["cx"]) if x["s"] <= t < x["e"]]
    fixo[k] = float(np.median(vals)) if vals else [x["cx"] for x in pecas if (x["cam"], x["quem"]) == k][0]

saida = []
for x in pecas:
    s, e = q(x["s"]), q(x["e"])
    if e - s < 1 / FPS:
        continue
    corpo = CORPO.get(x["quem"], 0.0)
    pts = [] if x.get("fixo") else [(t, f[0]) for t, f in serie(x, x["cx"]) if s <= t < e]
    base = (x["cx"] if x.get("fixo") else fixo[(x["cam"], x["quem"])]) + corpo
    if pts and abs(float(np.median([c for _, c in pts])) + corpo - base) > LIMIAR:
        base = float(np.median([c for _, c in pts[:10]])) + corpo
    alvo, kx = base, []
    if len(pts) >= 5:
        tt = np.array([t for t, _ in pts])
        cc = np.array([c for _, c in pts]) + corpo
        suav = np.array([np.median(cc[max(0, i - 3):i + 4]) for i in range(len(cc))])
        i = 0
        while i < len(tt):
            if abs(suav[i] - alvo) > LIMIAR:
                # só segue se ela ficar no lugar novo por 2,5 s (inclinar e voltar não move a câmera)
                j = np.searchsorted(tt, tt[i] + 2.5)
                if j < len(tt) and np.all(np.abs(suav[i:j] - alvo) > LIMIAR * 0.7):
                    novo = float(np.median(suav[i:j]))
                    t0 = max(s, tt[i] - 0.2)
                    t1 = min(e - 1 / FPS, t0 + SEGUE)
                    if not kx:
                        kx.append([s, tx_de(alvo, x["cam"])])
                    kx += [[t0, tx_de(alvo, x["cam"])], [t1, tx_de(novo, x["cam"])]]
                    alvo = novo
                    i = j
                    continue
            i += 1
    if kx:
        kx.append([e - 1 / FPS, tx_de(alvo, x["cam"])])
        kx = [k for n, k in enumerate(kx) if n == 0 or k[0] > kx[n - 1][0] + 1e-3]
    ty = 0.0
    if x["cam"] == "W":   # aproximado, o bruto sobra na altura: o rosto vai para ~36% da altura da tela
        cys = [x["cy"]] if x.get("cy") is not None else [f[1] for t, f in serie(x, x["cx"]) if s <= t < e]
        if cys:
            alt = 1080 * ESCALAS["W"] * 9 / 16
            ty = round(max(-1, min(1, ((960 + (float(np.median(cys)) - 0.5) * alt) - 0.36 * 1920) / 960)) * min(1, (alt - 1920) / 1920), 4)
    peca = {"fonte": round(s, 4), "fonte_dur": round(e - s, 4), "layout": "solo", "escala": ESCALAS.get(x["cam"], ESCALA),
            "tx": tx_de(base, x["cam"]), "ty": ty, "cam": x["cam"], "quem": x["quem"]}
    if kx:
        peca["kx"] = [[round(t, 4), v] for t, v in kx]
    saida.append(peca)

plano = {"velocidade": vel, "pecas": saida}
if vol:
    plano["volume"] = vol
json.dump(plano, open(os.path.join(W, f"c{cid}", "plano.json"), "w"), ensure_ascii=False, indent=1)
for p in saida:
    print(f'{p["fonte"]:8.2f} +{p["fonte_dur"]:6.2f} {p["cam"]} {p["quem"]:10s} tx={p["tx"]:+.3f}' + (f' kx={len(p["kx"])}' if "kx" in p else ""))
print("fixos:", {f"{k[0]}/{k[1]}": round(v, 3) for k, v in fixo.items()})
