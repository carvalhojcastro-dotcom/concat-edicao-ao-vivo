#!/usr/bin/env python3
"""Legendas direto das palavras do Whisper, sem passar pelas legendas simples.

Duas partes, ao vivo pela API:
  - "dinamicas": blocos montados com os estilos de legendas_dinamicas.py (índices das palavras);
  - "linha": daí em diante, frases curtas de UMA linha, palavra por palavra - cada palavra entra
    quando é dita (desliza para cima e aparece) e a frase inteira sai junta.

Uso:
  legendas_linha.py <projeto> <words.json> <plano.json> [--escala=1.0]
  words.json: [{"word", "start", "end"}] já corrigido, em tempos da timeline (projeto sem cortes).
  plano.json: {"dinamicas": [{"estilo", "linhas", "chave"}], "linha_de": 15,
               "max_palavras": 5, "escala_linha": 1.0, "destaque": "#ffffff"}
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import legendas_dinamicas as ld  # noqa: E402  (lê fps e --escala de sys.argv)
from concat_api import Concat, timeline  # noqa: E402

W, H, FPS = ld.W, ld.H, ld.FPS
TAM = 0.04302   # tamanho da legenda simples a 100% (Helvetica 12 do CapCut)
TRK = -0.052    # o "-0.3" do CapCut, em em
PAUSA = 0.35    # pausa que quebra a frase
SOBRA = 0.6     # quanto a frase fica na tela depois da última palavra, se vier pausa


def snap(t):
    return round(t * FPS) / FPS


def limpa(txt):
    return txt.strip().rstrip(".")


def linha(linhas, t):
    """Estilo "linha": uma linha só, Helvetica semibold, no tamanho da legenda simples."""
    ps = [ld.palavra(t[i], "helv", TAM * H, trk=TRK) for ln in linhas for i, _ in ln]
    ld.linha_em(ps, 0.0, 0.0)
    return ps


def nome(linhas, t):
    """Nome em destaque: linha pequena em cima e o nome em Helvetica Bold Oblíqua grande, alinhado
    à esquerda e com as linhas grandes bem juntas (no impacto ficavam soltas demais)."""
    S, B = 0.046 * H, 0.096 * H
    rows = [[ld.palavra(t[i], "helv-bold-oblique", B, trk=-0.04) if c else ld.palavra(t[i], "helv", S * 0.92, trk=-0.02)
             for i, c in ln] for ln in linhas]
    base = 0.0
    for li, ps in enumerate(rows):
        grande = ps[0]["face"] == "helv-bold-oblique"
        if li:
            junto = grande and rows[li - 1][0]["face"] == "helv-bold-oblique"
            base = ld.proxima_base(base, rows[li - 1], ps, 0.10 if junto else 0.22)
        ld.linha_em(ps, 0.0 if grande else 0.35 * S, base)
    return [p for ps in rows for p in ps]


ld.ESTILOS["linha"] = linha
ld.ESTILOS["nome"] = nome


def cabe(textos, idx):
    ps = [ld.palavra(textos[i], "helv", TAM * H, trk=TRK) for i in idx]
    return ld.larg_linha(ps) * ESCALA_LINHA <= ld.LARGURA_MAX


# Palavras que não fecham bem uma linha ("extraordinárias no / meu caminho").
FRACAS = {"a", "o", "as", "os", "à", "ao", "aos", "de", "da", "do", "das", "dos", "em", "no", "na", "nos", "nas",
          "e", "ou", "que", "por", "para", "um", "uma", "me", "se", "eu", "meu", "minha", "mais", "é", "com"}
PAUSA_FORTE = 0.8   # pausa que sempre fecha a frase (aplauso, emoção)


def frases(words, textos, de, maxp):
    """Divide em frases de uma linha: fim de período ou pausa longa sempre quebra; dentro do
    período, escolhe as quebras (programação dinâmica) preferindo vírgulas e pausas, evitando
    frases de uma palavra e linhas que terminam em preposição/artigo."""
    periodos, atual = [], []
    for i in range(de, len(words)):
        atual.append(i)
        pausa = i + 1 < len(words) and words[i + 1]["start"] - words[i]["end"] > PAUSA_FORTE
        if words[i]["word"].strip()[-1:] in ".?!" or pausa:
            periodos.append(atual); atual = []
    if atual:
        periodos.append(atual)

    def custo(pc, ultimo_do_periodo):
        c = {1: 4.0, 2: 0.5}.get(len(pc), 0.0)
        c += 2.0 * sum(1 for i in pc[:-1] if words[i]["word"].strip().endswith(","))  # vírgula no meio
        if ultimo_do_periodo:
            return c
        i = pc[-1]
        bruto = words[i]["word"].strip()
        if bruto.endswith(","):
            pass
        elif words[i + 1]["start"] - words[i]["end"] > PAUSA:
            c += 0.5
        else:
            c += 3.0
        if textos[i].lower().rstrip(",") in FRACAS:
            c += 3.0
        return c

    out = []
    for idx in periodos:
        n = len(idx)
        melhor = [0.0] + [math.inf] * n
        de_onde = [0] * (n + 1)
        for j in range(1, n + 1):
            for k in range(max(0, j - maxp), j):
                pc = idx[k:j]
                if len(pc) > 1 and not cabe(textos, pc):
                    continue
                c = melhor[k] + custo(pc, j == n)
                if c < melhor[j]:
                    melhor[j], de_onde[j] = c, k
        pedacos, j = [], n
        while j:
            pedacos.append(idx[de_onde[j]:j]); j = de_onde[j]
        out += reversed(pedacos)
    return out


def colocar(api, blocos, words, textos):
    """blocos: [(estilo, linhas, chave, fim)]; cria, posiciona e anima as palavras."""
    for n, (estilo, linhas, chave, fim) in enumerate(blocos, 1):
        palavras = ld.montar(estilo, linhas, set(chave), textos)
        antes = {c["id"] for c in timeline(api.view())["clips"]}
        cmds = []
        for p in palavras:
            ini = snap(words[p["i"]]["start"])
            cmds.append({"op": "addTextClip", "above": True, "start": ini, "duration": round(fim - ini, 6),
                         "offsetY": 0.0, "style": p["style"]})
        tl = timeline(api.batch(cmds))
        novos = sorted([c for c in tl["clips"] if c["id"] not in antes], key=lambda c: (c["start"], c["id"]))
        keys = []
        for c, p in zip(novos, sorted(palavras, key=lambda p: (snap(words[p["i"]]["start"]), p["i"]))):
            assert c["text"]["content"] == p["texto"], (c["text"]["content"], p["texto"])
            keys.append({"op": "setClipTransform", "clipId": c["id"], "offsetX": p["ox"], "offsetY": 0.0})
            keys += ld.keys_entrada(c["id"], c["duration"], p["oy"])
        api.batch(keys)
        print(f"[{n}/{len(blocos)}] {estilo} {words[linhas[0][0]]['start']:.2f}-{fim:.2f}: "
              f"{' / '.join(' '.join(textos[i] for i in ln) for ln in linhas)}", flush=True)


def main():
    global ESCALA_LINHA
    path, words, plano = sys.argv[1], json.load(open(sys.argv[2])), json.load(open(sys.argv[3]))
    ld.DESTAQUE = plano.get("destaque", ld.DESTAQUE)
    ESCALA_LINHA = plano.get("escala_linha", 1.0)
    textos = [limpa(w["word"]) for w in words]
    din = plano.get("dinamicas", [])
    de = plano.get("linha_de", len(words))
    grupos = [("din", b) for b in din] + [("linha", f) for f in frases(words, textos, de, plano.get("max_palavras", 5))]

    blocos = []
    for k, (tipo, g) in enumerate(grupos):
        idx = [i for ln in g["linhas"] for i in ln] if tipo == "din" else g
        prox = None
        if k + 1 < len(grupos):
            t2, g2 = grupos[k + 1]
            prox = words[(g2["linhas"][0][0] if t2 == "din" else g2[0])]["start"]
        fim_fala = words[idx[-1]]["end"]
        if tipo == "din":   # as dinâmicas ficam até a próxima frase
            fim = prox if prox is not None else fim_fala + SOBRA
        else:
            fim = prox if prox is not None and prox - fim_fala <= SOBRA else fim_fala + SOBRA
        fim = snap(fim)
        if tipo == "din":
            # sem vírgulas nos blocos grandes, como em legendas_dinamicas.py
            for i in idx:
                textos[i] = textos[i].rstrip(",")
            blocos.append((g["estilo"], g["linhas"], g["chave"], fim))
        else:
            blocos.append(("linha", [idx], [], fim))

    if "--seco" in sys.argv:   # só mostra a divisão, sem mexer no projeto
        for b in blocos:
            print(b[0], f"{words[b[1][0][0]]['start']:.2f}-{b[3]:.2f}", " / ".join(" ".join(textos[i] for i in ln) for ln in b[1]))
        return
    api = Concat(path)
    api.sock.settimeout(300)
    try:
        api.call("project.get", path=path)   # aberto na janela? então é ela que responde
    except RuntimeError:
        api.call("project.open", path=path)
    for familia, arquivo in ld.REGISTRAR:
        api.edit({"op": "addFont", "family": familia, "path": os.path.abspath(os.path.join(ld.FONTES, arquivo))})
    colocar(api, blocos, words, textos)
    api.call("project.save", path=path)
    print(f"pronto: {len(blocos)} blocos; projeto salvo")


ESCALA_LINHA = 1.0
if __name__ == "__main__":
    main()
