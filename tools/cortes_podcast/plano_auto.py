"""Texto das legendas do corte: words.json -> words_leg.json (correções e maiúsculas).

Uso: plano_auto.py <dir do corte>
- aplica correcoes.json ({"indice": "palavra certa"}) e as maiúsculas (1ª palavra do vídeo, depois de ?/!, nomes
  próprios da lista PROPRIOS e siglas; o resto minúsculo); a pontuação fica (estilo das legendas desde 2026-10-29);
- as legendas (simples + blocos) saem do capcut_legendas_ig.py; os blocos vêm do destaques.py (blocos.json).
"""
import json, os, re, sys

pasta = sys.argv[1]
words = json.load(open(os.path.join(pasta, "words.json")))
corr = {}
if os.path.exists(os.path.join(pasta, "correcoes.json")):
    corr = json.load(open(os.path.join(pasta, "correcoes.json")))   # {"indice": "palavra certa"}
for i, w in enumerate(words):
    t = corr.get(str(i), w["word"]).strip()
    w["leg"] = t
# maiúsculas: 1ª palavra do vídeo, depois de ?/!, nomes próprios e siglas; o resto minúsculo
PROPRIOS = set("Rafael Rafa Bruno Ive Simone Barra Recreio Brasil Deus Cushing Fantástico Bia Isabela Isa Caxias TikTok Farah Rio Janeiro São Paulo Nordeste Minas Gerais Moçambique Angola Elon Musk Paula Paulinha".split())
for i, w in enumerate(words):
    t = w["leg"]
    nome = re.sub(r"[^\wÀ-ú]", "", t)
    if not nome:
        continue
    sigla = len(nome) >= 2 and nome.isupper()
    if i == 0 or re.search(r"[?!]$", words[i - 1]["leg"]):
        t = t[0].upper() + t[1:]
    elif nome not in PROPRIOS and not sigla:
        t = t[0].lower() + t[1:]
    w["leg"] = t
json.dump([{"word": w["leg"], "start": w["start"], "end": w["end"]} for w in words],
          open(os.path.join(pasta, "words_leg.json"), "w"), ensure_ascii=False, indent=1)
print(f"{len(words)} palavras em words_leg.json ({words[-1]['end']:.1f}s); blocos: destaques.py")
