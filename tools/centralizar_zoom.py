#!/usr/bin/env python3
"""Enquadra cada take do projeto: pessoa centralizada, margem entre o topo e a cabeça, zoom por conjunto.

Regras do usuário (2026-10-21, Ozempic):
  - a pessoa sempre centralizada, em todo take, inclusive nos abertos (por isso o aberto não é 100%: com
    --aberto=1.08 sobra imagem para mover o quadro);
  - sempre uma margem entre o topo do vídeo e a cabeça: a cabeça fica em --topo (0,13) e nunca acima de
    --topo-min (0,10), para a margem não pular de um take para o outro;
  - o zoom de cada conjunto vem do plano (zoom_cortes.py): clipes seguidos com a mesma escala.
Com --estampa (camiseta com estampa no peito: clara em roupa escura ou escura em roupa clara), a estampa nunca desce abaixo de 0,745 (ou do valor
dado), para não cair sobre a legenda; se cabeça e estampa não cabem juntas, o zoom do conjunto diminui.
Pessoa de lado faz o zoom subir (até 1,30) para dar folga, mas a estampa vence: a legenda nunca fica em
cima dela (2026-10-23); para isso a cabeça pode subir até 0,06 do topo.

As medidas vêm de quadros que o próprio Concat renderiza com os takes a 100% (a cor do bruto HLG não
serve para achar a estampa). O centro da pessoa é o rosto; quando o rosto não aparece, o peito (estampa).

Uso: centralizar_zoom.py <projeto> [--aberto=1.08] [--topo=0.13] [--topo-min=0.10] [--estampa[=0.745]] [--fechado[=1.7]] [--corpo] [--seguir]
  --fechado: com --estampa, o zoom in vira close (até 1,7): a estampa desce inteira para baixo das legendas
"""
import os
import shutil
import sys
import tempfile

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from concat_api import Concat, timeline  # noqa: E402
from render_projeto import projeto_para_render  # noqa: E402

args = [a for a in sys.argv[1:] if not a.startswith("--")]
opc = dict(a[2:].split("=", 1) if "=" in a else (a[2:], "") for a in sys.argv[1:] if a.startswith("--"))
path = args[0]
ABERTO = float(opc.get("aberto", 1.08))
TOPO = float(opc.get("topo", 0.13))
TOPO_MIN = float(opc.get("topo-min", 0.10))
EST_MAX = float(opc["estampa"] or 0.745) if "estampa" in opc else None
SEGUIR = "seguir" in opc   # câmera que anda: o quadro acompanha a pessoa dentro do take (keyframes)
CORPO = "corpo" in opc   # palestra em plano aberto: centro e topo pela silhueta (o rosto pequeno some)
ROSTO_MIN = float(opc.get("rosto-min", 0.125))   # menor rosto procurado (fração da largura); plano aberto de palestra: 0.04
CENTRO_TOL = 0.03   # pessoa até 3% fora do centro passa; além disso o zoom do conjunto sobe para centralizar
ZOOM_MAX = 1.30
# --fechado: o zoom in vira close (pedido de 2026-10-23: "pode dar mais zoom nos zoom ins"); o topo da
# estampa desce para baixo de LEG_FIM, onde as legendas (simples e blocos dinâmicos) já acabaram
FECHADO_MAX = float(opc["fechado"] or 1.7) if "fechado" in opc else None
LEG_FIM = 0.88
TOPO_DURO = 0.06    # para tirar a estampa de baixo da legenda, a cabeça pode subir até aqui
cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


def natural(doc):
    """Cópia para medir: todos os takes a 100% e no lugar, sem legendas por cima."""
    for t in doc["timelines"]:
        for c in t["clips"]:
            if c["kind"] == "video":
                c["scale"], c["offsetX"], c["offsetY"] = 1.0, 0.0, 0.0
                c["keys"] = [k for k in c.get("keys", []) if k.get("property") not in ("scale", "offsetX", "offsetY")]
            elif c["kind"] in ("text", "image"):
                c["opacity"] = 0.0


def corpo(img):
    """(centro x, topo da cabeça) de quem fala num plano aberto de palestra, sem depender do rosto: a maior
    mancha escura acima do chão (paletó, cabelo) dá o centro; o cabelo logo acima dela dá o topo."""
    h, w = img.shape[:2]
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    m = (hsv[..., 2] < 75).astype(np.uint8)
    m[int(0.72 * h):] = 0   # carpete escuro
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    if n < 2:
        return None
    k = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    if st[k, cv2.CC_STAT_AREA] < 0.01 * w * h:
        return None
    ys, xs = np.nonzero(lab == k)
    cx, topo = int(np.median(xs)), int(ys.min())
    # o cabelo pode ter ficado separado do paletó: sobe pela coluna do centro enquanto houver escuro
    faixa = hsv[:, max(0, cx - int(0.05 * w)):cx + int(0.05 * w), 2] < 110
    linha = faixa.mean(1) > 0.15
    yy, vazio = topo, 0
    while yy > 0 and vazio < int(0.02 * h):
        yy -= 1
        if linha[yy]:
            topo, vazio = yy, 0
        else:
            vazio += 1
    return cx / w, topo / h


def medir(img):
    """(centro x do rosto, topo da cabeça), (centro x da estampa, fim da estampa) - em fração do quadro."""
    h, w = img.shape[:2]
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = [f for f in cascade.detectMultiScale(g, 1.1, 5, minSize=(int(w * ROSTO_MIN), int(w * ROSTO_MIN)))
             if 0.15 * h < f[1] + f[3] / 2 < 0.55 * h and 0.2 * w < f[0] + f[2] / 2 < 0.8 * w]
    rosto = None
    if CORPO:
        return corpo(img), None
    if faces:
        x, y, fw, fh = max(faces, key=lambda f: f[2])
        # cabelo: escuro e sem cor (azulejo azul escuro atrás não conta), linhas seguidas subindo do rosto
        hsv_c = cv2.cvtColor(img[:, x + fw // 4:x + 3 * fw // 4], cv2.COLOR_BGR2HSV)
        linha = ((hsv_c[..., 2] < 90) & (hsv_c[..., 1] < 110)).mean(1) > 0.3
        topo = None
        for yy in range(min(y + fh // 4, h - 1), -1, -1):
            if linha[yy]:
                topo = yy
            elif topo is not None and topo - yy > 4:
                break
        rosto = ((x + fw / 2) / w, (topo / h) if topo is not None and topo < y else (y - 0.35 * fh) / h)
    estampa = None
    if EST_MAX is not None:
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        peito = hsv[int(0.5 * h):int(0.82 * h), int(0.3 * w):int(0.7 * w)]
        if np.median(peito[..., 2]) < 150:   # camiseta escura com estampa clara
            escuro = cv2.blur(((hsv[..., 2] < 150) & (hsv[..., 1] > 40)).astype(np.float32), (31, 31)) > 0.35
            m = (hsv[..., 2] > 170) & (hsv[..., 1] < 70) & escuro
        else:
            # camiseta clara com estampa escura: letra escura, preta ou verde-escura ("MEDICINA"), mas não o
            # azul do azulejo atrás
            claro = cv2.blur(((hsv[..., 2] > 150) & (hsv[..., 1] < 60)).astype(np.float32), (31, 31)) > 0.35
            azul = (hsv[..., 0] > 95) & (hsv[..., 0] < 135) & (hsv[..., 1] > 60)
            m = (hsv[..., 2] < 110) & ~azul & claro
        # só a faixa do peito: tira chão, parede dos lados e mãos lá embaixo
        m[:int(0.5 * h)] = False
        m[int(0.82 * h):] = False
        m[:, :int(0.25 * w)] = False
        m[:, int(0.75 * w):] = False
        linhas = np.nonzero(m.sum(1) > 6)[0]
        if len(linhas):
            # SIMPLES e MEDICINA são um bloco só (a linha de baixo é a que encosta na legenda)
            blocos = np.split(linhas, np.nonzero(np.diff(linhas) > 30)[0] + 1)
            bloco = max(blocos, key=lambda b: int(m[b[0]:b[-1] + 1].sum()))   # o de mais "letra"
            ys, xs = np.nonzero(m[bloco[0]:bloco[-1] + 1])
            estampa = ((np.percentile(xs, 5) + np.percentile(xs, 95)) / 2 / w, bloco[-1] / h, bloco[0] / h)
    return rosto, estampa


api = Concat(path)
api.sock.settimeout(600)
def medir_takes(api_r, alvo, takes_r, tmp):
    out = []
    for k, c in enumerate(takes_r):
        rs, es, serie = [], [], []
        # --seguir: a câmera da palestra é de mão e anda dentro do take; ~3 medidas por segundo
        fracs = np.linspace(0.04, 0.96, max(3, int(c["duration"] * 3))) if SEGUIR else (0.2, 0.5, 0.8)
        for f in fracs:
            png = os.path.join(tmp, f"q{k}_{f}.png")
            api_r.call("preview.frame", path=alvo, time=c["start"] + c["duration"] * f, output=png, width=540, height=960)
            r, e = medir(cv2.imread(png))
            if r:
                serie.append((float(f), r[0]))
            rs += [r] if r else []
            es += [e] if e else []
        out.append({"fx": float(np.median([r[0] for r in rs])) if rs else None,
                    "topo": float(min(r[1] for r in rs)) if rs else None,
                    "ex": float(np.median([e[0] for e in es])) if es else None,
                    "est": float(max(e[1] for e in es)) if es else None,
                    "est_topo": float(min(e[2] for e in es)) if es else None,
                    "serie": serie})
    return out


with projeto_para_render(path, transformar=natural) as (api_r, alvo):
    takes_r = sorted([c for c in timeline(api_r.call("project.get", path=alvo))["clips"] if c["kind"] == "video"],
                     key=lambda c: c["start"])
    tmp = tempfile.mkdtemp(dir=os.path.expanduser("~"), prefix=".concat-medidas-")  # o Concat só grava na pasta do usuário
    try:
        medidas = medir_takes(api_r, alvo, takes_r, tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

# o que um take não mostrou vem do vizinho mais próximo
for chave in ("topo", "est", "est_topo"):
    for k, m in enumerate(medidas):
        if m[chave] is None:
            viz = [medidas[j][chave] for j in sorted(range(len(medidas)), key=lambda j: abs(j - k))
                   if medidas[j][chave] is not None]
            m[chave] = viz[0] if viz else {"topo": 0.18, "est": EST_MAX or 0.7, "est_topo": 0.6}[chave]

clips = sorted([c for c in timeline(api.call("project.open", path=path))["clips"] if c["kind"] == "video"],
               key=lambda c: c["start"])
# conjuntos: clipes seguidos com a mesma escala do plano
conjuntos = []
for k, c in enumerate(clips):
    s = c.get("scale", 1.0)
    if conjuntos and abs(conjuntos[-1][0] - s) < 1e-6:
        conjuntos[-1][1].append(k)
    else:
        conjuntos.append((s, [k]))

cl = lambda v, f: max(-f, min(f, v))  # noqa: E731
def cx_de(m):
    """Centro da pessoa: o rosto; o peito (estampa) se não houver rosto ou se os dois discordam muito (um
    rosto achado num quadro só, de lado, puxava o close para a beira)."""
    if m["fx"] is not None and (m["ex"] is None or abs(m["fx"] - m["ex"]) <= 0.08):
        return m["fx"]
    return m["ex"] if m["ex"] is not None else (m["fx"] if m["fx"] is not None else 0.5)
cmds, log, finais = [], [], []
for s_plano, ks in conjuntos:
    s = max(s_plano, ABERTO)
    # pessoa de lado mais que CENTRO_TOL: o conjunto ganha o zoom que dá folga para trazê-la ao centro
    desvio = lambda m: (float(np.percentile([abs(x - 0.5) for _, x in m["serie"]], 90))   # noqa: E731
                        if SEGUIR and len(m.get("serie", [])) >= 3 else abs(cx_de(m) - 0.5))
    lado = max(max(desvio(medidas[k]) - CENTRO_TOL, 0.0) for k in ks)
    s = max(s, min(1 / (1 - 2 * lado), ZOOM_MAX))
    # mas a legenda nunca em cima da estampa (pedido de 2026-10-23: "posicionando-as bem para não ficarem
    # em cima da estampa da camisa"): cabeça a TOPO_DURO do topo e estampa até EST_MAX só cabem até esta
    # escala, e ela vence o centralizar
    fechado = False
    if FECHADO_MAX and EST_MAX is not None and s_plano > ABERTO + 1e-3:
        s_f = max(max((LEG_FIM - TOPO) / max(medidas[k]["est_topo"] - medidas[k]["topo"], 1e-3) for k in ks), s)
        if s_f <= FECHADO_MAX:
            s, fechado = s_f, True
    if EST_MAX is not None and not fechado:
        s = min(s, min((EST_MAX - TOPO_DURO) / max(medidas[k]["est"] - medidas[k]["topo"], 1e-3) for k in ks))
    s = round(max(1.0, s), 3)
    f = (s - 1) / 2
    for k in ks:
        m = medidas[k]
        cx = cx_de(m)
        ox = cl(-(cx - 0.5) * s, f)
        y = lambda v, o: 0.5 + (v - 0.5) * s + o  # noqa: E731
        oy = TOPO - y(m["topo"], 0.0)
        oy = max(oy, TOPO_MIN - y(m["topo"], 0.0))
        if fechado:   # close: a estampa passa inteira para baixo das legendas
            oy = max(oy, LEG_FIM - y(m["est_topo"], 0.0))
        elif EST_MAX is not None and y(m["est"], oy) > EST_MAX:
            oy = max(EST_MAX - y(m["est"], 0.0), TOPO_DURO - y(m["topo"], 0.0))   # estampa vence, até TOPO_DURO
        oy = cl(oy, f)
        cmds.append({"op": "setClipTransform", "clipId": clips[k]["id"], "scale": s,
                     "offsetX": round(ox, 4), "offsetY": round(oy, 4)})
        cmds.append({"op": "clearClipKeys", "clipId": clips[k]["id"], "property": "offsetX"})
        if SEGUIR and len(m.get("serie", [])) >= 3:
            # segue a pessoa: centro medido ao longo do take, mediana de 3 e média de 3 (sem tremer)
            fs, xs = zip(*m["serie"])
            xs = np.array(xs)
            xs = np.array([np.median(xs[max(0, i - 1):i + 2]) for i in range(len(xs))])
            xs = np.convolve(np.pad(xs, 1, mode="edge"), np.ones(3) / 3, mode="valid")
            for fr, x in zip(fs, xs):
                cmds.append({"op": "setClipKey", "clipId": clips[k]["id"], "property": "offsetX", "at": round(fr, 4),
                             "value": round(cl(-(x - 0.5) * s, f), 4), "ease": [0.42, 0.0, 0.58, 1.0]})
            cx = float(np.median(xs))
        finais.append((k, 0.5 + (cx - 0.5) * s + ox, y(m["topo"], oy)))
        if fechado and y(m["est_topo"], oy) < LEG_FIM - 0.01:
            print(f"  take {k + 1}: no close, o topo da estampa fica em {y(m['est_topo'], oy):.2f} (encosta na legenda)")
        elif not fechado and EST_MAX is not None and y(m["est"], oy) > EST_MAX + 0.01:
            print(f"  take {k + 1}: estampa desce até {y(m['est'], oy):.2f} (encosta na legenda)")
    log.append(f"{clips[ks[0]]['start']:6.2f}s  takes {ks[0] + 1}-{ks[-1] + 1}: {round(s * 100)}%" + (" close" if fechado else "")
               + ("" if abs(s - max(s_plano, ABERTO)) < 1e-3 else f" (plano {round(s_plano * 100)}%: limitado)"))
api.batch(cmds)
api.call("project.save", path=path)
print("\n".join(log))
print("centro da pessoa entre %.2f e %.2f | cabeça entre %.2f e %.2f do topo" % (
    min(f[1] for f in finais), max(f[1] for f in finais), min(f[2] for f in finais), max(f[2] for f in finais)))
for k, cx, cab in finais:
    if cab < TOPO_MIN - 0.015:
        print(f"  take {k + 1}: cabeça a {cab:.2f} do topo (sem folga para descer a imagem)")
    if abs(cx - 0.5) > CENTRO_TOL + 0.005:
        print(f"  take {k + 1}: centro em {cx:.2f} (a pessoa está muito de lado; o zoom não dá folga para mais)")
