#!/usr/bin/env python3
"""Gera os B-rolls de imagem de um plano pela API do Higgsfield (SDK oficial) e baixa as imagens.

Uso: tools/.venv/bin/python tools/broll_higgsfield.py <plano.json> <pasta de saída> [nome ...]
  plano: tools/planos/projeto2_broll.json (cenas com nome e prompt). Com nomes, só essas cenas.
  Uma imagem por cena, 9:16, modelo barato (Soul 2). Cena que já tem imagem na pasta é pulada,
  então rodar de novo não paga duas vezes.
A chave vem de HF_KEY em .env.local (id:segredo), carregada na hora e nunca mostrada.
"""
import glob
import json
import os
import sys
import urllib.request

import higgsfield_client
from dotenv import load_dotenv

# Regras fixas do usuário para todo B-roll: quem fala é o médico, então nenhum outro profissional
# de saúde aparece; e nada escrito na imagem.
REGRAS = ("Any person shown is Brazilian, in a Brazilian setting. No doctors, no nurses, no medical staff, no white coats, no stethoscopes. "
          "Absolutely no text, no letters, no numbers, no labels, no writing, no screens with content, no logos.")
# Positivo e neutro: falar de "pessoas" aqui punha gente até em cena de objeto. Quem aparece
# (sempre brasileiros, roupa do dia a dia) vai no prompt da própria cena.
POSITIVO = "Clean image with plain surfaces."
MODELO = "higgsfield-ai/soul/v2/standard"   # o mais barato da API (a partir de US$ 0,003/imagem)
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env.local"))
if not os.getenv("HF_KEY"):
    sys.exit("HF_KEY não configurada: rode tools/configurar_chave_higgsfield.sh")

plano, pasta = json.load(open(sys.argv[1])), sys.argv[2]
modelo = plano.get("modelo_api", MODELO)
so = set(sys.argv[3:])
os.makedirs(pasta, exist_ok=True)
falhas = 0
for cena in plano["cenas"]:
    if so and cena["nome"] not in so:
        continue
    if glob.glob(os.path.join(pasta, cena["nome"] + ".*")):
        print(f"{cena['nome']}: já existe, pulei"); continue
    try:
        prompt = f"{cena['prompt']} {plano['estilo']} {REGRAS}"
        if modelo == "z-image/turbo":  # um pouco melhor (US$ 0,015/imagem); prompt de até 800 caracteres
            # Esse modelo lê negação ao contrário: "no doctors, no stethoscope" PÕE jaleco e estetoscópio.
            # Então só descrição positiva: o prompt da cena já diz quem aparece e como.
            prompt = f"{cena['prompt']} {plano['estilo']} {POSITIVO}"
            args = {"prompt": prompt[:800], "aspect_ratio": "9:16", "resolution": "2k", "prompt_extend": False}
        else:                          # Soul 2, o mais barato
            args = {"prompt": prompt, "aspect_ratio": "9:16", "resolution": "1080p", "batch_size": 1,
                    "enhance_prompt": False}
        r = higgsfield_client.subscribe(modelo, arguments=args)
    except Exception as erro:  # erro HTTP, saldo, rede: conta como falha, sem mostrar credenciais
        print(f"{cena['nome']}: erro ({type(erro).__name__}: {erro})"); falhas += 1; continue
    status = r.get("status")
    if status != "completed":
        print(f"{cena['nome']}: NÃO gerada, status={status} (pedido {r.get('request_id')})"); falhas += 1; continue
    imgs = r.get("images") or []
    if not imgs or not imgs[0].get("url"):
        print(f"{cena['nome']}: concluída sem imagem na resposta"); falhas += 1; continue
    url = imgs[0]["url"]
    ext = os.path.splitext(url.split("?")[0])[1] or ".png"
    destino = os.path.join(pasta, cena["nome"] + ext)
    urllib.request.urlretrieve(url, destino)
    print(f"{cena['nome']}: ok -> {destino}")
sys.exit(1 if falhas else 0)
