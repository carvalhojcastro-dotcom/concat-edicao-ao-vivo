#!/usr/bin/env python3
"""Monta um projeto-catálogo no Concat com as animações e composições de estilos_legenda.py,
uma depois da outra, para ver no app e comparar com as referências.

Uso: catalogo_estilos.py <pasta do projeto> <vídeo de fundo> [vitrine|reel|modelos|tudo] [--so=nome,nome]
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import estilos_legenda as E  # noqa: E402
from concat_api import Concat, timeline  # noqa: E402

ORDEM_VITRINE = ["abaixo", "acima", "blur", "blurup", "brilho", "cinematic", "corte", "riscado", "destacado", "direita",
                 "esquerda", "fadein", "flicker", "flicking", "girando", "ouro", "moderno", "palavra", "reveal", "slide",
                 "sublinhado", "prata", "surgir", "zoomout"]
DURACAO = {"cinematic": 3.6, "palavra": 2.6, "flicking": 2.6, "zoomout": 2.6}


def preparar(path, fundo):
    path = os.path.abspath(path)
    if not os.path.exists(os.path.join(path, "concat.json")):
        api = Concat(path)
        api.call("project.create", location=os.path.dirname(path), name=os.path.basename(path),
                 video={"width": 2160, "height": 3840, "rateNum": 30, "rateDen": 1})
        api.call("project.open", path=path)
        api.call("media.import", path=path, file=os.path.abspath(fundo))
        v = api.view()
        api.edit({"op": "addClip", "mediaId": v["project"]["media"][0]["id"], "trackId": timeline(v)["tracks"][0]["id"], "start": 0.0})
        api.call("project.save", path=path)
        api.call("project.close", path=path, save=True)
    return E.Projeto(path)


def limpar(P):
    tl = timeline(P.api.view())
    fora = [c["id"] for c in tl["clips"] if not (c["kind"] == "video" and c["start"] == 0.0 and c["trackId"] == tl["tracks"][0]["id"])]
    if fora:
        P.api.edit({"op": "removeClips", "clipIds": fora, "ripple": False})


def vitrine(P, t, so=None):
    W, H = P.W, P.H
    for nome in ORDEM_VITRINE:
        if so and nome not in so:
            continue
        face, texto = E.VITRINE[nome]
        ps = [E.palavra(w, face, 0.075 * H, trk=E.TRK_VITRINE.get(nome, -0.03)) for w in texto.split()]
        E.bloco([{"ps": ps}])
        E.encaixar(ps, W, H, W / 2, 0.62 * H, 0.86 * W)
        els = E.ANIMACOES[nome](ps, t, P)
        fim = t + DURACAO.get(nome, 2.2)
        for e in els:
            e.fim = min(e.fim, fim) if e.fim > e.inicio else fim
        P.criar(els)
        print(f"{t:6.2f}s {nome}: {len(els)} clipes", flush=True)
        t = fim + 0.2
    return t


EXEMPLOS_REEL = [
    ("linha", ["E a regra que"], E.AMARELO),
    ("escada", ["A regra da", "ovelha", "negra{#22305e}"], E.AMARELO),
    ("numero", ["até", "*60%*", "que os seus mais^m", "competidores"], E.AMARELO),
    ("sanduiche", ["padrões", "do seu", "mercado"], E.AMARELO),
    ("chave", ["Use essa", "regra de", "*Marketing*"], E.BRANCO),
    ("dupla", ["geradoras", "de receita"], E.AMARELO),
    ("quatro", ["fazer", "tudo", "completamente", "diferente"], E.AMARELO),
    ("chave", ["inevitavelmente,", "gera", "*compra*"], E.AMARELO),
    ("grande", ["brutal."], E.AMARELO),
]


def reel(P, t, anim="pop", passo=0.3):
    for preset, linhas, destaque in EXEMPLOS_REEL:
        els = E.compor_reel(preset, linhas, P.W, P.H, destaque=destaque)
        grupos = E.materializar(els, P)
        tempos = [t + k * passo for k in range(len(grupos))]
        fim = tempos[-1] + 1.4
        P.criar(E.animar_frase(grupos, tempos, anim, P, fim))
        print(f"{t:6.2f}s reel {preset}: {' / '.join(linhas)}", flush=True)
        t = fim + 0.15
    return t


def modelos(P, t, anim="blurup", passo=0.35):
    for nome in E.MODELOS:
        els = E.compor_modelo(nome, P.W, P.H)
        grupos = E.materializar(els, P)
        tempos = [t + k * passo for k in range(len(grupos))]
        fim = tempos[-1] + 1.8
        P.criar(E.animar_frase(grupos, tempos, anim, P, fim))
        print(f"{t:6.2f}s modelo {nome}", flush=True)
        t = fim + 0.15
    return t


def main():
    path, fundo = sys.argv[1], sys.argv[2]
    qual = next((a for a in sys.argv[3:] if not a.startswith("--")), "tudo")
    so = next((a[5:].split(",") for a in sys.argv[3:] if a.startswith("--so=")), None)
    P = preparar(path, fundo)
    limpar(P)
    t = 0.3
    if qual in ("reel", "tudo"):
        t = reel(P, t)
    if qual in ("modelos", "tudo"):
        t = modelos(P, t)
    if qual in ("vitrine", "tudo"):
        t = vitrine(P, t, so)
    P.salvar()
    print(f"catálogo até {t:.2f}s; projeto salvo")
    P.fechar()


if __name__ == "__main__":
    main()
