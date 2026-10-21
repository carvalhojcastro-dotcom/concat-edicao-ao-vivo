import sys, json, os
modo, wav, out = sys.argv[1], sys.argv[2], sys.argv[3]
if modo == "turbo":
    import mlx_whisper
    r = mlx_whisper.transcribe(wav, path_or_hf_repo="mlx-community/whisper-large-v3-turbo", language="pt",
                               word_timestamps=True, condition_on_previous_text=False)
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
