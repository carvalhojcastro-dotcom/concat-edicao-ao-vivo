#!/usr/bin/env python3
"""Põe B-rolls de imagem num projeto do Concat (ao vivo, se ele estiver aberto na janela).

Uso: broll_imagens.py <projeto> <plano.json> <pasta das imagens>
  plano: {"cenas": [{"inicio": s, "fim": s, "nome": "x"}, ...]}; a imagem de cada cena é
  <pasta>/<nome>.(png|jpg|webp). Tempos em segundos da timeline.
Trilhas: o vídeo desce para a trilha mais baixa (T1), os B-rolls ficam na de cima dele (T2),
a camada de ajuste (nitidez) continua por cima dos dois e as legendas por cima de tudo.
"""
import glob, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from concat_api import Concat, timeline, fps_de

FPS = fps_de(sys.argv[1])  # o fps do projeto (24 ou 30)
path, plano, pasta = sys.argv[1], json.load(open(sys.argv[2])), sys.argv[3]
api = Concat(path); api.sock.settimeout(300)
api.call("project.open", path=path)
tl = timeline(api.view())
trilhas = [t["id"] for t in tl["tracks"]]
video = [c for c in tl["clips"] if c["kind"] == "video"]
baixo, broll = trilhas[0], trilhas[1]
if any(c["trackId"] != baixo for c in video):
    api.edit({"op": "moveClips", "moves": [{"clipId": c["id"], "start": c["start"], "trackId": baixo} for c in video]})
ocupado = [c for c in timeline(api.view())["clips"] if c["trackId"] == broll]
assert not ocupado, f"a trilha {broll} não está livre"
snap = lambda t: round(t * FPS) / FPS
for cena in plano["cenas"]:
    arq = next(iter(sorted(glob.glob(os.path.join(pasta, cena["nome"] + ".*")))), None)
    if not arq:
        print(f"sem imagem para {cena['nome']}, pulei"); continue
    antes = {m["id"] for m in api.view()["project"]["media"]}
    api.call("media.import", path=path, file=os.path.abspath(arq))
    mid = next(m["id"] for m in api.view()["project"]["media"] if m["id"] not in antes)
    ini, fim = snap(cena["inicio"]), snap(cena["fim"] + 0.15)
    antes_c = {c["id"] for c in timeline(api.view())["clips"]}
    tl = timeline(api.edit({"op": "addClip", "mediaId": mid, "trackId": broll, "start": ini}))
    clip = next(c for c in tl["clips"] if c["id"] not in antes_c)
    api.edit({"op": "trimClip", "clipId": clip["id"], "edge": "end", "delta": (fim - ini) - clip["duration"], "ripple": False})
    print(f"{ini:6.2f}-{fim:6.2f}s  {cena['nome']}")
api.call("project.save", path=path)
print("pronto")
