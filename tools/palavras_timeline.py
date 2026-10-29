#!/usr/bin/env python3
"""Converte as palavras do Whisper (tempos do bruto) para tempos da timeline do projeto, já com cortes,
velocidade e clipes reordenados, para o legendas_estilos.py (cortes de podcast).

Uso: palavras_timeline.py <projeto> <words.json do reel.py cortes> <saida.json>
Palavra que caiu num trecho cortado sai da lista (e é avisada). A ordem final é a da timeline, então
um clipe movido (ex.: "Espero que vocês gostem" levado para o fim) leva as palavras junto.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from concat_api import Concat, timeline  # noqa: E402


def main():
    path, words, saida = sys.argv[1], json.load(open(sys.argv[2])), sys.argv[3]
    api = Concat(path); api.sock.settimeout(120)
    try:
        api.call("project.get", path=path)
    except RuntimeError:
        api.call("project.open", path=path)
    clips = [c for c in timeline(api.view())["clips"] if c["kind"] == "video"]
    segs = sorted([(c["sourceStart"], c["sourceStart"] + c["duration"] * c["speed"], c["start"], c["speed"]) for c in clips])

    def tmap(src, prefer):
        """Dentro de um trecho, mapeia direto; num corte de pausa, o início
        vai para o começo do trecho seguinte e o fim para o fim do anterior (em ordem do bruto)."""
        for a, b, st, sp in segs:
            if a - 1e-6 <= src <= b + 1e-6:
                return st + (src - a) / sp
        if prefer == "next":
            return next((st for a, b, st, sp in segs if a > src), None)
        return next((st + (b - a) / sp for a, b, st, sp in reversed(segs) if b < src), None)

    out, fora = [], []
    for w in words:
        ini, fim = tmap(w["start"], "next"), tmap(w["end"], "prev")
        if ini is None or fim is None:
            fora.append(w["word"].strip()); continue
        if fim < ini + 0.02 or fim - ini > 3:   # palavra que pula de trecho (ou caiu toda num corte): dura o mínimo
            fim = ini + max(0.06, min(w["end"] - w["start"], 0.4))
        out.append({"word": w["word"].strip(), "start": round(ini, 4), "end": round(fim, 4)})
    out.sort(key=lambda w: w["start"])
    json.dump(out, open(saida, "w"), ensure_ascii=False, indent=0)
    print(f"{len(out)} palavras na timeline" + (f"; fora dos trechos: {' '.join(fora)}" if fora else ""))


if __name__ == "__main__":
    main()
