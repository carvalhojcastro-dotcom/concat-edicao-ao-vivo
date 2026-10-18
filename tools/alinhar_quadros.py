"""Alinha a quadros inteiros os inícios e fins de vídeo, legendas, camadas e áudio.

O Concat arredonda início e duração de cada clipe para quadros separadamente;
quando os dois arredondam para lados opostos, sobra um quadro preto entre dois
clipes de vídeo encostados. Alinhar tudo a 1/fps evita isso.

Uso: alinhar_quadros.py <pasta do projeto>
"""
import sys
from fractions import Fraction

sys.path.insert(0, __import__("os").path.dirname(__file__))
from concat_api import Concat, timeline


def snap(t, fps):
    return round(t * fps) / fps


def plan(tl, fps):
    cmds, moves = [], []
    for c in tl["clips"]:
        start, end = c["start"], c["start"] + c["duration"]
        s, e = snap(start, fps), snap(end, fps)
        if e - s < 1 / fps:
            e = s + 1 / fps
        if abs(s - start) > 1e-9:
            moves.append({"clipId": c["id"], "start": s, "trackId": c["trackId"]})
        # Duração depois de mover: o fim é o que conta.
        delta = (e - s) - c["duration"]
        if abs(delta) > 1e-9:
            cmds.append({"op": "trimClip", "clipId": c["id"], "edge": "end", "delta": delta, "ripple": False})
    out = []
    # Encurtar antes de mover (nada encosta no vizinho), mover, depois alongar.
    out += [c for c in cmds if c["delta"] < 0]
    if moves:
        out.append({"op": "moveClips", "moves": moves})
    out += [c for c in cmds if c["delta"] > 0]
    return out


def check(tl, fps):
    bad = []
    for c in tl["clips"]:
        for t in (c["start"], c["start"] + c["duration"]):
            if abs(t * fps - round(t * fps)) > 1e-6:
                bad.append((c["id"], t))
    return bad


if __name__ == "__main__":
    api = Concat(sys.argv[1])
    v = api.call("project.open", path=api.path)
    video = timeline(v).get("video") or v["project"]["timelines"][0]["video"]
    fps = Fraction(video["rateNum"], video["rateDen"])
    tl = api.batch(plan(timeline(v), float(fps)))
    tl = timeline(tl)
    print("fora da grade de quadros:", check(tl, float(fps)))
