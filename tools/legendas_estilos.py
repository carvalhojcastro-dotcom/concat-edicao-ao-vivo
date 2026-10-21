#!/usr/bin/env python3
"""Aplica os estilos de estilos_legenda.py num projeto, frase por frase, no tempo da fala.

Uso:
  legendas_estilos.py <projeto> <words.json> <plano.json> [--seco]
  words.json: palavras do Whisper já corrigidas, tempos da timeline (projeto sem cortes).
  plano.json: {"destaque": "#ffffff", "frases": [   (destaque: branco por padrão)
      {"preset": "escada",            "linhas": ["A regra da", "ovelha", "negra{#22305e}"], "de": 12, "anim": "pop"},
      {"preset": "modelo:padrao",     "linhas": [["Quebre", "o"], ["PADRÃO"], ["com", "DINAMISMO"]], "de": 20, "anim": "blurup"},
      {"preset": "grande", "familia": "pop", "linhas": ["Blur"], "de": 30, "anim": "blur"}]}
  "de": índice da 1ª palavra falada da frase; cada palavra das linhas entra no tempo da palavra
  falada correspondente (de, de+1, ...). Sem "de", use "inicio" (s) e as palavras entram a cada 0,3 s.
  A frase fica até a próxima começar (ou 0,6 s depois da última palavra, se vier pausa).
  "sombra_suave": 0.6 põe um esfumado escuro difuso atrás das letras (fundo claro, sem traço forte).
  "contorno": 0.05 põe contorno preto (fração do tamanho da letra) para fundo claro.
  "largura_max" (fração do quadro, padrão 0.86) e "altura_max" encolhem o bloco para caber num espaço livre (ex.: entre o queixo e
  um logo na camiseta).
Presets: linha, grande, escada, sanduiche, numero, dupla, quatro, chave (reel) e modelo:modelos,
modelo:padrao, modelo:chamativos, modelo:elegantes. Animações: veja estilos_legenda.ANIMACOES.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import estilos_legenda as E  # noqa: E402

SOBRA = 0.6


def main():
    path, words, plano = sys.argv[1], json.load(open(sys.argv[2])), json.load(open(sys.argv[3]))
    seco = "--seco" in sys.argv
    destaque = plano.get("destaque", E.BRANCO)
    frases = plano["frases"]
    P = E.Projeto(path)
    snap = lambda t: round(t * P.FPS) / P.FPS
    for n, f in enumerate(frases):
        preset = f["preset"]
        if preset.startswith("modelo:"):
            els = E.compor_modelo(preset[7:], P.W, P.H, textos=f.get("linhas"), centro=tuple(f.get("centro", (0.5, 0.6))))
            n_pal = sum(len(l) for l in f["linhas"]) if f.get("linhas") else len(els)
        else:
            els = E.compor_reel(preset, f["linhas"], P.W, P.H, centro=tuple(f.get("centro", (0.5, 0.6))),
                                larg_max=f.get("largura_max", 0.86),
                                destaque=f.get("destaque", destaque), familia=f.get("familia", "jak"),
                                alt_max=f.get("altura_max"))
            n_pal = len(els)
            if f.get("contorno"):   # fundo claro (ex.: B-roll): contorno escuro em fração do tamanho da letra
                for e in els:
                    if e.tipo == "texto":
                        e.contorno, e.cor_contorno = f["contorno"] * e.em, "#000000"
        if "de" in f:
            idx = list(range(f["de"], f["de"] + n_pal))
            tempos = [snap(words[i]["start"]) for i in idx]
            fim_fala = words[idx[-1]]["end"]
        else:
            tempos = [f["inicio"] + 0.3 * k for k in range(n_pal)]
            fim_fala = tempos[-1] + 0.4
        prox = None
        if n + 1 < len(frases):
            g = frases[n + 1]
            prox = words[g["de"]]["start"] if "de" in g else g.get("inicio")
        fim = f.get("fim") or (prox if prox is not None and prox - fim_fala <= SOBRA else fim_fala + SOBRA)
        fim = snap(min(fim, P.fim_video()))
        texto = " / ".join(l if isinstance(l, str) else " ".join(l) for l in f.get("linhas", []))
        falado = " ".join(words[i]["word"].strip() for i in range(f["de"], f["de"] + n_pal)) if "de" in f else ""
        print(f"[{n + 1}/{len(frases)}] {tempos[0]:.2f}-{fim:.2f} {preset} {f.get('anim', 'pop')}: {texto}   (falado: {falado})", flush=True)
        if seco:
            continue
        grupos = E.materializar(els, P)
        if f.get("sombra_suave"):   # fundo claro: esfumado escuro e difuso atrás das letras (sem traço marcado)
            novos = []
            for principal, g in grupos:
                halos = []
                for e in g:
                    if e.tipo == "texto":   # duas camadas: uma larga (esfumado) e uma justa (contraste), sem borda dura
                        for raio in (40, 12):
                            h = e.copia(cor="#000000", sombra=False, contorno=0.0)
                            h.efeito("concat.gaussian-blur", {"radius": raio})
                            halos.append(h)
                novos.append((principal, halos + g))
            grupos = novos
        P.criar(E.animar_frase(grupos, tempos, f.get("anim", "pop"), P, fim))
    if not seco:
        P.salvar()
        print("pronto; projeto salvo")
    P.fechar()


if __name__ == "__main__":
    main()
