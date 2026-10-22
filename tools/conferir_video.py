#!/usr/bin/env python3
"""Confere um vídeo editado antes de entregar: as falas estão inteiras nos cortes?

Transcreve o vídeo (o MP4 exportado, ou o áudio que o Concat renderiza) com o Whisper e compara palavra
por palavra com o texto das legendas simples do projeto (o roteiro final). Aponta:
  - palavras que faltam ou sobram (corte comendo palavra, palavra repetida, take duplicado);
  - palavras ditas com pouca clareza (probabilidade baixa) até 0,3 s de um corte: fala cortada no
    começo ou no fim ("pe-", "u-", "-tão").
O usuário pediu (2026-10-21): "sempre confira os vídeos editados antes de exportá-los para garantir que
não fez cortes errados dificultando o entendimento das palavras e frases".

Uso: conferir_video.py <projeto> <video.mp4>
Sai com 0 se não achou problema.
"""
import difflib
import json
import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plataforma  # noqa: E402

norm = lambda t: re.sub(r"[^\wà-ú%]", "", t.lower())  # noqa: E731


def main():
    projeto, video = sys.argv[1], sys.argv[2]
    doc = json.load(open(os.path.join(projeto, "concat.json")))["timelines"][0]
    # cada palavra é um clipe de texto que entra quando é dita (simples ou de bloco dinâmico): em ordem
    # de entrada, elas são o roteiro; no mesmo instante, a ordem de criação desempata
    num = lambda c: int(re.sub(r"\D", "", c["id"]) or 0)  # noqa: E731
    simples = sorted([c for c in doc["clips"] if c.get("kind") == "text"], key=lambda c: (round(c["start"], 3), num(c)))
    roteiro = [norm(c["text"]["content"]) for c in simples]
    roteiro = [w for w in roteiro if w]
    cortes = sorted(c["start"] for c in doc["clips"] if c.get("kind") == "video")[1:]

    wav = os.path.join(tempfile.mkdtemp(), "a.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vn", "-ac", "1", "-ar", "16000", wav], check=True)
    r = plataforma.transcrever(wav, language="pt")   # sem initial_prompt: com ele o Whisper pula o começo
    ouvido = [w for s in r["segments"] for w in s["words"]]
    falado = [norm(w["word"]) for w in ouvido]

    problemas = 0
    sm = difflib.SequenceMatcher(a=roteiro, b=falado, autojunk=False)
    for op, a1, a2, b1, b2 in sm.get_opcodes():
        if op == "equal":
            continue
        t = ouvido[min(b1, len(ouvido) - 1)]["start"] if ouvido else 0
        esperado, ouvido_txt = " ".join(roteiro[a1:a2]), " ".join(falado[b1:b2])
        # diferença só de grafia (Whisper escreve "pra"/"para", números) não é corte errado
        if op == "replace" and difflib.SequenceMatcher(a=esperado, b=ouvido_txt).ratio() > 0.75:
            continue
        problemas += 1
        print(f"  {t:6.2f}s  {op:7s} esperado: '{esperado}'  ouvido: '{ouvido_txt}'")
    for w in ouvido:
        perto = [c for c in cortes if abs(c - w["start"]) < 0.3 or abs(c - w["end"]) < 0.3]
        if perto and w.get("probability", 1) < 0.45:
            problemas += 1
            print(f"  {w['start']:6.2f}s  pouco claro perto do corte em {perto[0]:.2f}s: '{w['word'].strip()}' "
                  f"(prob. {w['probability']:.2f})")
    print(f"{len(roteiro)} palavras no roteiro, {len(falado)} ouvidas; "
          + ("nenhum problema" if not problemas else f"{problemas} ponto(s) para ouvir"))
    return 0 if not problemas else 1


if __name__ == "__main__":
    sys.exit(main())
