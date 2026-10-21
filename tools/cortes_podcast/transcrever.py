import sys, json, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import plataforma  # mlx-whisper no Mac, faster-whisper no Windows
modo, wav, out = sys.argv[1], sys.argv[2], sys.argv[3]
if modo == "turbo":
    r = plataforma.transcrever(wav, language="pt")
    json.dump(r, open(out, "w"), ensure_ascii=False)
else:
    from faster_whisper import WhisperModel
    m = WhisperModel("medium", device="cpu", compute_type="int8", cpu_threads=4)
    segs, info = m.transcribe(wav, language="pt", word_timestamps=True, condition_on_previous_text=False, vad_filter=True)
    res = []
    for s in segs:
        res.append({"start": s.start, "end": s.end, "text": s.text,
                    "words": [{"word": w.word, "start": w.start, "end": w.end, "probability": w.probability} for w in s.words]})
        if len(res) % 50 == 0:
            print(s.end, flush=True)
    json.dump({"segments": res}, open(out, "w"), ensure_ascii=False)
print("FIM", out, flush=True)
