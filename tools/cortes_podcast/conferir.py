"""Segunda transcrição (faster-whisper medium) só do áudio de um corte, e as divergências com o turbo.
Uso: conferir.py <dir do corte> <audio16k.wav da fonte>   -> grava medium.json e imprime as diferenças."""
import difflib, json, os, re, subprocess, sys, tempfile
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..")); import plataforma  # noqa: E401,E402 (acha o ffmpeg no Windows)
pasta, wav = sys.argv[1], sys.argv[2]
cfg = json.load(open(os.path.join(pasta, "corte.json")))
words = json.load(open(os.path.join(pasta, "words.json")))
tmp = os.path.join(pasta, "trecho.wav")
fc = "".join(f"[0:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS[a{i}];" for i, (a, b) in enumerate(cfg["segmentos"]))
fc += "".join(f"[a{i}]" for i in range(len(cfg["segmentos"]))) + f"concat=n={len(cfg['segmentos'])}:v=0:a=1[a]"
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", wav, "-filter_complex", fc, "-map", "[a]", tmp], check=True)
from faster_whisper import WhisperModel
m = WhisperModel("medium", device="cpu", compute_type="int8", cpu_threads=8)
segs, _ = m.transcribe(tmp, language="pt", word_timestamps=True, condition_on_previous_text=False)
med = [{"word": w.word.strip(), "start": w.start, "end": w.end} for s in segs for w in s.words]
json.dump(med, open(os.path.join(pasta, "medium.json"), "w"), ensure_ascii=False)
norm = lambda w: re.sub(r"[^\wà-ú]", "", w.lower())
A = [norm(w["word"]) for w in words]; B = [norm(w["word"]) for w in med]
sm = difflib.SequenceMatcher(a=A, b=B, autojunk=False)
for op, i1, i2, j1, j2 in sm.get_opcodes():
    if op != "equal":
        print(f"{op:8s} [{i1}] turbo: {' '.join(w['word'] for w in words[i1:i2])!r:40s} medium: {' '.join(w['word'] for w in med[j1:j2])!r}")
print(f"concordância: {sm.ratio():.3f}")
