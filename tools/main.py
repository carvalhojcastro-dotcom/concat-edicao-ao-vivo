"""Exemplo do guia do Higgsfield: um vídeo Seedance 2.5 pelo SDK oficial.

Gera cobrança. Uso: tools/.venv/bin/python tools/main.py
A chave vem de HF_KEY em .env.local (id:segredo), carregada na hora e nunca mostrada.
"""
import os
import sys

import higgsfield_client
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env.local"))
if not os.getenv("HF_KEY"):
    sys.exit("HF_KEY não configurada: rode tools/configurar_chave_higgsfield.sh")

result = higgsfield_client.subscribe(
    "bytedance/seedance-2.5/text-to-video",
    arguments={
        "prompt": "A cinematic scene at sunset",
        "duration": 5,
        "resolution": "720p",
        "aspect_ratio": "16:9",
    },
)
status = result.get("status")
if status != "completed":
    sys.exit(f"geração não concluída: status={status} (pedido {result.get('request_id')})")
video = result.get("video") or {}
url = video.get("url") if isinstance(video, dict) else None
if not url:
    sys.exit(f"concluída, mas sem URL de vídeo na resposta: chaves {sorted(result)}")
print(url)
