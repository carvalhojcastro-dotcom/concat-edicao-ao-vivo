#!/usr/bin/env python3
"""Monta os conjuntos de zoom (aberto / zoom in) seguindo as frases, só nos cortes que já existem.

Cada take é marcado pelo texto que começa nele (as legendas do projeto dão as palavras e os tempos). Um
conjunto junta takes seguidos até ter pelo menos --min segundos (2) e fecha quando o próximo take começa
uma frase; depois de --ideia segundos (3), fecha também num começo de ideia (depois de vírgula). Take
de fala contínua com mais de --max (4 s) é dividido nesses mesmos pontos. Os conjuntos alternam aberto (escala 1.0) e zoom in (--zoom, 1.18), começando aberto. Nunca
corta fala contínua: a troca é sempre num corte que já existe (pedido de 2026-10-21: "conjuntos ...
variando de acordo com as frases, para fazerem sentido"; corte só para trocar zoom atrapalha).
Depois rode o centralizar_zoom.py (enquadra cada take; --estampa com estampa no peito).

Uso: zoom_por_frases.py <projeto> [--zoom=1.18] [--min=2] [--ideia=3] [--max=4] [--corte=2.5 [--cortes=cortes.json]]
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from concat_api import Concat, timeline  # noqa: E402

args = [a for a in sys.argv[1:] if not a.startswith("--")]
opc = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
path = args[0]
ZOOM, MIN, MAX = float(opc.get("zoom", 1.18)), float(opc.get("min", 2.0)), float(opc.get("max", 4.0))
IDEIA = float(opc.get("ideia", 3.0))   # depois de tantos segundos, troca também num começo de ideia (vírgula)
# vídeo que já veio cortado (ex.: CAP do CapCut): depois de tantos segundos, troca em qualquer corte do
# usuário, mesmo no meio da frase (o corte já está lá; pedido de 2026-10-23: "encaixar com os cortes")
CORTE = float(opc["corte"]) if "corte" in opc else None
# os cortes do usuário em segundos do vídeo de origem (JSON); sem a lista, corte = salto no bruto
CORTES_USUARIO = json.load(open(opc["cortes"])) if "cortes" in opc else None

api = Concat(path)
api.sock.settimeout(120)
api.call("project.open", path=path)
tl = timeline(api.view())
takes = sorted([c for c in tl["clips"] if c["kind"] == "video"], key=lambda c: c["start"])
palavras = sorted([(c["start"], c["text"]["content"].strip()) for c in tl["clips"] if c["kind"] == "text"])
if not palavras:
    sys.exit("o projeto ainda não tem legendas: rode capcut_legendas_ig.py --concat= antes")


PROPRIOS = {"Ozempic", "Leonardo", "Luna", "Cochrane", "Colaboração", "Mounjaro"}


def comeca_frase(k):
    """A palavra k abre frase? As legendas simples não têm ponto final: vale a maiúscula (fora nomes
    próprios) ou ? ! na palavra de antes."""
    w = palavras[k][1]
    antes = palavras[k - 1][1] if k else "."
    return antes.endswith((".", "?", "!")) or (w[:1].isupper() and w.strip(",.?!") not in PROPRIOS)


def dividir_longos():
    """Take com mais de MAX segundos (fala sem pausa) é dividido no começo de uma frase - ou, se não
    houver, de uma ideia (depois de vírgula) - a pelo menos MIN s das pontas. É um punch-in: o áudio
    segue contínuo, só o enquadramento muda na troca de frase."""
    cmds = 0
    for c in sorted([c for c in timeline(api.view())["clips"] if c["kind"] == "video"], key=lambda c: c["start"]):
        ini, fim = c["start"], c["start"] + c["duration"]
        if fim - ini <= MAX:
            continue
        dentro = [(t, k) for k, (t, w) in enumerate(palavras) if ini + MIN <= t <= fim - MIN]
        ultimo = ini
        for t, k in dentro:
            antes = palavras[k - 1][1] if k else ""
            frase = comeca_frase(k)
            ideia = antes.endswith(",")
            if (frase and t - ultimo >= MIN or ideia and t - ultimo >= IDEIA) and fim - t >= MIN:
                corte = round((t - 0.03) * 30) / 30
                alvo = [x for x in timeline(api.view())["clips"]
                        if x["kind"] == "video" and x["start"] + 1e-6 < corte < x["start"] + x["duration"] - 1e-6]
                if alvo:
                    api.edit({"op": "splitClips", "clipIds": [alvo[0]["id"]], "time": corte})
                    ultimo = corte
                    cmds += 1
    return cmds


print(f"{dividir_longos()} takes longos divididos em começo de frase")
takes = sorted([c for c in timeline(api.view())["clips"] if c["kind"] == "video"], key=lambda c: c["start"])


def abre(k):
    """Como o take k começa: 'frase' (depois de . ? !), 'ideia' (depois de vírgula) ou ''."""
    ini = takes[k]["start"]
    antes = [w for t, w in palavras if t < ini - 1e-3]
    depois = [w for t, w in palavras if t >= ini - 1e-3]
    if not antes:
        return "frase"
    if not depois:
        return ""
    if comeca_frase(len(antes)):
        return "frase"
    return "ideia" if antes[-1].endswith(",") else ""


def corte_real(k):
    """O take k começa num corte de verdade (o anterior vem de outro ponto do bruto), não numa divisão nossa."""
    if CORTES_USUARIO is not None:
        return any(abs(takes[k]["sourceStart"] - c) < 0.06 for c in CORTES_USUARIO)
    a = takes[k - 1]
    return abs(a["sourceStart"] + a["duration"] * a.get("speed", 1.0) - takes[k]["sourceStart"]) > 0.05


conjuntos, atual = [], [0]
for k in range(1, len(takes)):
    dur = takes[k]["start"] - takes[atual[0]]["start"]
    tipo = abre(k)
    if (dur >= MIN and tipo == "frase") or (dur >= IDEIA and tipo == "ideia") or (CORTE and dur >= CORTE and corte_real(k)):
        conjuntos.append(atual)
        atual = [k]
    else:
        atual.append(k)
conjuntos.append(atual)
# um conjunto curto no fim junta ao anterior (não troca o zoom por menos de 1 s)
if len(conjuntos) > 1:
    ult = conjuntos[-1]
    if takes[ult[-1]]["start"] + takes[ult[-1]]["duration"] - takes[ult[0]]["start"] < 1.0:
        conjuntos[-2] += conjuntos.pop()

cmds = []
for g, ks in enumerate(conjuntos):
    s = ZOOM if g % 2 else 1.0
    cmds += [{"op": "setClipTransform", "clipId": takes[k]["id"], "scale": s, "offsetX": 0.0, "offsetY": 0.0} for k in ks]
    ini, fim = takes[ks[0]]["start"], takes[ks[-1]]["start"] + takes[ks[-1]]["duration"]
    texto = " ".join(w for t, w in palavras if ini - 1e-3 <= t < fim)
    print(f"{ini:6.2f}s {'zoom  ' if g % 2 else 'aberto'} {fim - ini:4.1f}s  {texto[:70]}")
api.batch(cmds)
api.call("project.save", path=path)
dur = takes[-1]["start"] + takes[-1]["duration"]
print(f"{len(conjuntos)} conjuntos em {dur:.0f}s ({(len(conjuntos) - 1) / dur * 60:.0f} trocas por minuto)")
