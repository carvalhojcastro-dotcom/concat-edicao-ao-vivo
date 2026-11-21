"""Áudio de cada corte como fica na timeline (trecho contínuo do bruto na velocidade do config) e duas transcrições:
turbo (mlx, palavras) e medium (faster-whisper), para conferir palavra errada ou pulada (comparar.py).
Uso: transcrever_cortes.py <W> [ids...]   -> c<id>/tl.wav, words_tl.json, texto.txt, words_med.json"""
import json, os, subprocess, sys
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.join(AQUI, "..", ".."))
from comum import config, cortes  # noqa: E402
import plataforma  # noqa: E402

W = sys.argv[1]
vel = config(W).get("velocidade", 1.1)
sel = set(sys.argv[2:])
lista = [c for c in cortes(W) if not sel or c[0] in sel]
for cid, S, E in lista:
    d = os.path.join(W, f"c{cid}")
    os.makedirs(d, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{S:.3f}", "-t", f"{E - S:.3f}", "-i", os.path.join(W, "audio.wav"),
                    "-af", f"atempo={vel}", "-ar", "16000", "-ac", "1", os.path.join(d, "tl.wav")], check=True)
    r = plataforma.transcrever(os.path.join(d, "tl.wav"), language="pt")
    ws = [{"word": w["word"].strip(), "start": round(w["start"], 3), "end": round(w["end"], 3)}
          for s in r["segments"] for w in s.get("words", []) if w["word"].strip()]
    json.dump(ws, open(os.path.join(d, "words_tl.json"), "w"), ensure_ascii=False, indent=0)
    open(os.path.join(d, "texto.txt"), "w").write(" ".join(f"{i}:{w['word']}" for i, w in enumerate(ws)))
    print(cid, "turbo", len(ws), "palavras", flush=True)
from faster_whisper import WhisperModel  # noqa: E402
m = WhisperModel("medium", device="cpu", compute_type="int8", cpu_threads=6)
for cid, S, E in lista:
    d = os.path.join(W, f"c{cid}")
    segs, _ = m.transcribe(os.path.join(d, "tl.wav"), language="pt", word_timestamps=True, condition_on_previous_text=False)
    ws = [{"word": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3)} for s in segs for w in s.words if w.word.strip()]
    json.dump(ws, open(os.path.join(d, "words_med.json"), "w"), ensure_ascii=False, indent=0)
    print(cid, "medium", len(ws), "palavras", flush=True)
