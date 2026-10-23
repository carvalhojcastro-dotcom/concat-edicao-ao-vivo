#!/usr/bin/env python3
"""Música de fundo baixinha (lofi) no vídeo todo, numa trilha própria, com fade de entrada e de saída.

O volume é calculado para a música ficar --abaixo dB abaixo da voz (a voz vai a -14 LUFS com o
user.voz-redes-sociais): mede o loudness da música e ajusta o volume do clipe. Padrão do kit de edição:
música ~17 dB abaixo da voz, fade-in de 1,7 s e fade-out de 2,4 s. Rodar de novo troca a música anterior.

Uso: musica_fundo.py <projeto> <musica.mp3> [--abaixo=17] [--voz=-14] [--inicio=0]
  --inicio: de que ponto da música começar (s)
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from concat_api import Concat, timeline  # noqa: E402

args = [a for a in sys.argv[1:] if not a.startswith("--")]
opc = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--") and "=" in a)
path, musica = args[0], os.path.abspath(args[1])
ABAIXO, VOZ, INICIO = float(opc.get("abaixo", 17)), float(opc.get("voz", -14)), float(opc.get("inicio", 0))
FADE_IN, FADE_OUT = 1.7, 2.4

r = subprocess.run(["ffmpeg", "-nostats", "-i", musica, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
lufs = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1])
volume = round(10 ** ((VOZ - ABAIXO - lufs) / 20), 4)

api = Concat(path)
api.sock.settimeout(300)
try:
    api.call("project.get", path=path)
except RuntimeError:
    api.call("project.open", path=path)
proj = api.view()["project"]
tl = timeline(api.view())
velhas = [c["id"] for c in tl["clips"] if c["kind"] == "audio"]   # só a música é clipe de áudio solto
if velhas:
    api.edit({"op": "removeClips", "clipIds": velhas})
fim = max(c["start"] + c["duration"] for c in timeline(api.view())["clips"] if c["kind"] == "video")
mid = next((m["id"] for m in proj["media"] if m.get("path") == musica), None)
if mid is None:
    antes = {m["id"] for m in proj["media"]}
    api.call("media.import", path=path, file=musica)
    mid = next(m["id"] for m in api.view()["project"]["media"] if m["id"] not in antes)
antes = {t["id"] for t in timeline(api.view())["tracks"]}
tl = timeline(api.edit({"op": "addTrack"}))   # trilha própria, por cima (áudio não aparece na imagem)
trilha = next(t["id"] for t in tl["tracks"] if t["id"] not in antes)
antes_c = {c["id"] for c in tl["clips"]}
tl = timeline(api.edit({"op": "addClip", "mediaId": mid, "trackId": trilha, "start": 0.0}))
clip = next(c for c in tl["clips"] if c["id"] not in antes_c)
if INICIO:
    api.edit({"op": "trimClip", "clipId": clip["id"], "edge": "start", "delta": INICIO, "ripple": False})
    clip = next(c for c in timeline(api.view())["clips"] if c["id"] == clip["id"])
    api.edit({"op": "moveClips", "moves": [{"clipId": clip["id"], "start": 0.0, "trackId": trilha}]})
    clip = next(c for c in timeline(api.view())["clips"] if c["id"] == clip["id"])
api.edit({"op": "trimClip", "clipId": clip["id"], "edge": "end", "delta": fim - clip["duration"], "ripple": False})
api.edit({"op": "updateClip", "clipId": clip["id"], "patch": {"volume": volume, "fadeIn": FADE_IN, "fadeOut": FADE_OUT}})
api.call("project.save", path=path)
c = next(c for c in timeline(api.view())["clips"] if c["id"] == clip["id"])
print(f"música {os.path.basename(musica)} ({lufs:.1f} LUFS) em {trilha}: 0-{c['start'] + c['duration']:.2f}s, "
      f"volume {volume} ({VOZ - ABAIXO:.0f} LUFS, {ABAIXO:g} dB abaixo da voz), fades {FADE_IN}/{FADE_OUT} s")
