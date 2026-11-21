"""Legendas para um corte que o usuário já montou no CapCut (Marcia C01, 2026-11-14: "eu fiz os cortes e acelerei e
consegui fazer umas colagens ... não quero que você mexa em nada dos clipes ... só faça as legendas").
Lê a trilha principal do projeto (pedaços do bruto, velocidade de cada um), junta os trechos do bruto em 1x (exato,
sem atempo, que soma ~7 ms por pedaço), transcreve (turbo e medium) e leva cada palavra para a timeline dela pelo
pedaço em que cai. Depois: comparar.py <W> <id>, correcoes_tl.json, preparar_legenda.py <W> <id> <duração>,
destaques.py e capcut_legendas_ig.py (que só troca as trilhas "Legendas IG"). CapCut FECHADO para gravar.
Uso: transcrever_timeline.py <pasta do projeto> <bruto> <W> <id>   -> W/c<id>/words_tl.json, words_med.json, texto.txt"""
import json, os, subprocess, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
import plataforma  # noqa: E402

pasta, V, W, cid = sys.argv[1:5]
d = os.path.join(W, f"c{cid}")
os.makedirs(d, exist_ok=True)
D = json.load(open(os.path.join(pasta, "draft_info.json"), encoding="utf-8"))
princ = next(t for t in D["tracks"] if t["type"] == "video")
segs = [{"tl": s["target_timerange"]["start"] / 1e6, "tl_dur": s["target_timerange"]["duration"] / 1e6,
         "src": s["source_timerange"]["start"] / 1e6, "src_dur": s["source_timerange"]["duration"] / 1e6, "vel": s["speed"]}
        for s in sorted(princ["segments"], key=lambda s: s["target_timerange"]["start"])]
json.dump(segs, open(os.path.join(d, "segmentos.json"), "w"), indent=0)
cmd, fc = ["ffmpeg", "-v", "error", "-y"], []
for i, s in enumerate(segs):
    cmd += ["-ss", f"{s['src'] - 1:.6f}", "-t", f"{s['src_dur'] + 2:.6f}", "-i", V]
    fc.append(f"[{i}:a]aresample=16000,atrim=start=1:end={1 + s['src_dur']:.6f},asetpts=PTS-STARTPTS[a{i}]")
fc.append("".join(f"[a{i}]" for i in range(len(segs))) + f"concat=n={len(segs)}:v=0:a=1[o]")
wav = os.path.join(d, "src.wav")
subprocess.run(cmd + ["-filter_complex", ";".join(fc), "-map", "[o]", "-ac", "1", wav], check=True)
cum, c = [], 0.0
for s in segs:
    cum.append(c); c += s["src_dur"]
def tl(t):
    i = max(k for k in range(len(segs)) if cum[k] <= t + 1e-6)
    s = segs[i]
    return i, s["tl"] + min(t - cum[i], s["src_dur"]) / s["vel"]
def mapear(ws):
    out = []
    for w in ws:
        i, a = tl(w["start"])
        j, b = tl(w["end"])
        if j != i:
            b = segs[i]["tl"] + segs[i]["tl_dur"]
        out.append({"word": w["word"], "start": round(a, 3), "end": round(max(b, a + 0.04), 3), "seg": i})
    return out
r = plataforma.transcrever(wav, language="pt")
ws = [{"word": w["word"].strip(), "start": w["start"], "end": w["end"]} for s in r["segments"] for w in s.get("words", []) if w["word"].strip()]
ws = mapear(ws)
json.dump(ws, open(os.path.join(d, "words_tl.json"), "w"), ensure_ascii=False, indent=0)
open(os.path.join(d, "texto.txt"), "w").write(" ".join(f"{i}:{w['word']}" for i, w in enumerate(ws)))
print("turbo", len(ws), flush=True)
from faster_whisper import WhisperModel
m = WhisperModel("medium", device="cpu", compute_type="int8", cpu_threads=6)
sg, _ = m.transcribe(wav, language="pt", word_timestamps=True, condition_on_previous_text=False)
wm = mapear([{"word": w.word.strip(), "start": w.start, "end": w.end} for s in sg for w in s.words if w.word.strip()])
json.dump(wm, open(os.path.join(d, "words_med.json"), "w"), ensure_ascii=False, indent=0)
print("medium", len(wm))
