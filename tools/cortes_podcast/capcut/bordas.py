"""Ajuda a escolher in/out em silêncio: palavras do episódio com tempo e a energia (dB a cada 50 ms) perto de um ponto.
Uso: bordas.py <W> palavras <a> <b>      (palavras do rotulado.json entre a e b, com tempo e voz M/F)
     bordas.py <W> energia <a-b> [<a-b> ...]"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comum import rms_db  # noqa: E402

W, modo = sys.argv[1], sys.argv[2]
if modo == "palavras":
    a, b = float(sys.argv[3]), float(sys.argv[4])
    d = json.load(open(os.path.join(W, "rotulado.json")))
    print(" ".join(f"{w['start']:.2f}{s['speaker']}{w['word']}" for s in d["segments"] for w in s["words"] if a <= w["start"] <= b))
else:
    for arg in sys.argv[3:]:
        a, b = map(float, arg.split("-"))
        db = rms_db(os.path.join(W, "audio.wav"), a, b)
        print(arg, " ".join(f"{a + k * 0.05:.2f}:{int(v)}" for k, v in enumerate(db)))
